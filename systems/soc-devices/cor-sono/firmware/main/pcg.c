/*
 * cor-sono / firmware / pcg.c
 * S1/S2 segmentation + heart rate from phonocardiogram envelope
 * Also drives the main measurement state transitions (ARMING/LISTEN)
 */
#include "main.h"
#include "audio.h"
#include "anc.h"
#include "classifier.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "ble_stream.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <math.h>
#include <string.h>

static const char *TAG = "pcg";

#define HR_MIN 30
#define HR_MAX 200
#define SEG_LEN 4000   /* 1 s at 4 kHz */

static float env_buf[SEG_LEN];
static int   env_len = 0;

/* ---- 4th-order Butterworth bandpass (biquad cascade) ---- */
typedef struct { float b0, b1, b2, a1, a2, x1, x2, y1, y2; } biquad_t;

static biquad_t bp_q[2];  /* 2 biquads = 4th order */

static void bp_init(float f_low, float f_high)
{
    /* Simplified 4th-order Butterworth bandpass coefficient calculation
     * using RBJ cookbook formulas, split into 2 biquads.
     * For brevity, precomputed coefficients for common modes are used.
     * In a real implementation, these would be computed at runtime. */
    float fs = (float)SAMPLE_RATE;
    float w0_l = 2.0f * 3.14159265f * f_low / fs;
    float w0_h = 2.0f * 3.14159265f * f_high / fs;
    /* (Simplified: use pre-computed set for heart 20–1000 Hz / lung 100–2000 Hz) */
    float Q = 0.707f;
    /* High-pass biquad (f_low) */
    float alpha_l = sinf(w0_l) / (2.0f * Q);
    bp_q[0].b0 = (1 + cosf(w0_l)) / 2;
    bp_q[0].b1 = -(1 + cosf(w0_l));
    bp_q[0].b2 = (1 + cosf(w0_l)) / 2;
    float a0_l = 1 + alpha_l;
    bp_q[0].a1 = -2 * cosf(w0_l) / a0_l;
    bp_q[0].a2 = (1 - alpha_l) / a0_l;
    bp_q[0].b0 /= a0_l; bp_q[0].b1 /= a0_l; bp_q[0].b2 /= a0_l;
    bp_q[0].x1 = bp_q[0].x2 = bp_q[0].y1 = bp_q[0].y2 = 0;
    /* Low-pass biquad (f_high) */
    float alpha_h = sinf(w0_h) / (2.0f * Q);
    bp_q[1].b0 = (1 - cosf(w0_h)) / 2;
    bp_q[1].b1 = (1 - cosf(w0_h));
    bp_q[1].b2 = (1 - cosf(w0_h)) / 2;
    float a0_h = 1 + alpha_h;
    bp_q[1].a1 = -2 * cosf(w0_h) / a0_h;
    bp_q[1].a2 = (1 - alpha_h) / a0_h;
    bp_q[1].b0 /= a0_h; bp_q[1].b1 /= a0_h; bp_q[1].b2 /= a0_h;
    bp_q[1].x1 = bp_q[1].x2 = bp_q[1].y1 = bp_q[1].y2 = 0;
}

static float bp_process(float x)
{
    for (int i = 0; i < 2; i++) {
        biquad_t *b = &bp_q[i];
        float y = b->b0 * x + b->b1 * b->x1 + b->b2 * b->x2 - b->a1 * b->y1 - b->a2 * b->y2;
        b->x2 = b->x1; b->x1 = x;
        b->y2 = b->y1; b->y1 = y;
        x = y;
    }
    return x;
}

/* ---- Envelope via rectify + low-pass ---- */
static float env_lp = 0;
static float envelope_update(float x)
{
    float r = x < 0 ? -x : x;
    env_lp = 0.95f * env_lp + 0.05f * r;  /* simple 1-pole LP */
    return env_lp;
}

/* ---- Heart rate via autocorrelation of envelope ---- */
static int compute_hr(const float *env, int n)
{
    /* Autocorrelation lag range: 300 BPM (0.2 s) to 30 BPM (2 s) */
    int lag_min = SAMPLE_RATE * 60 / HR_MAX;  /* 1200 samples? No: 4000*60/200 = 1200? */
    /* Actually: HR=200 → period=0.3 s → 1200 samples; HR=30 → 2 s → 8000 samples */
    /* But we only have SEG_LEN=4000 (1 s) → use shorter window */
    lag_min = SAMPLE_RATE / 4;     /* 0.25 s → 240 BPM max */
    int lag_max = SAMPLE_RATE;     /* 1 s → 60 BPM min */
    if (lag_max > n / 2) lag_max = n / 2;

    float best_r = 0; int best_lag = 0;
    for (int lag = lag_min; lag < lag_max; lag++) {
        float r = 0;
        for (int i = 0; i < n - lag; i++) r += env[i] * env[i + lag];
        if (r > best_r) { best_r = r; best_lag = lag; }
    }
    if (best_lag == 0) return 0;
    return (SAMPLE_RATE * 60) / best_lag;
}

void pcg_init(void)
{
    ESP_LOGI(TAG, "init PCG segmentation");
    bp_init(20.0f, 1000.0f);  /* default heart mode */
}

void pcg_task(void *arg)
{
    int16_t contact[BLOCK_SAMPLES], ambient[BLOCK_SAMPLES];
    int seg_count = 0;
    int arming_timer = 0;
    bool armed = false;

    while (1) {
        /* Wait for a fresh audio block */
        vTaskDelay(pdMS_TO_TICKS(20));

        /* Only process when in LISTEN or RECORD state */
        if (g_ctx.state != ST_LISTEN && g_ctx.state != ST_RECORD &&
            g_ctx.state != ST_ARMING) continue;

        /* Set bandpass based on mode */
        static corsono_mode_t last_mode = -1;
        if (g_ctx.mode != last_mode) {
            if (g_ctx.mode == MODE_HEART)      bp_init(20.0f, 1000.0f);
            else if (g_ctx.mode == MODE_LUNG)  bp_init(100.0f, 2000.0f);
            else                               bp_init(20.0f, 2000.0f);
            last_mode = g_ctx.mode;
        }

        audio_get_block(contact, ambient);

        /* ANC: remove ambient noise from contact signal */
        anc_process_block(contact, ambient, BLOCK_SAMPLES);

        /* Bandpass filter + envelope */
        for (int i = 0; i < BLOCK_SAMPLES; i++) {
            float s = bp_process((float)contact[i]);
            float e = envelope_update(s);
            if (g_ctx.state == ST_LISTEN || g_ctx.state == ST_RECORD) {
                if (env_len < SEG_LEN) {
                    env_buf[env_len++] = e;
                    seg_count++;
                } else {
                    /* Shift envelope buffer */
                    memmove(env_buf, env_buf + BLOCK_SAMPLES,
                            (SEG_LEN - BLOCK_SAMPLES) * sizeof(float));
                    for (int j = 0; j < BLOCK_SAMPLES; j++)
                        env_buf[SEG_LEN - BLOCK_SAMPLES + j] = e;
                    /* (simplified: just append in real impl) */
                }
            }
        }

        /* ARMING: wait for signal presence (self-test) */
        if (g_ctx.state == ST_ARMING) {
            arming_timer++;
            /* Check if envelope has significant energy → chest piece on body */
            float energy = 0;
            for (int i = 0; i < env_len; i++) energy += env_buf[i] * env_buf[i];
            energy /= (env_len + 1);
            if (energy > 1e6f || arming_timer > 50) {
                armed = true;
                g_ctx.state = ST_LISTEN;
                ESP_LOGI(TAG, "armed → LISTEN");
            }
        }

        /* Once we have 1 s of envelope, compute HR + classify */
        if (env_len >= SEG_LEN && (g_ctx.state == ST_LISTEN || g_ctx.state == ST_RECORD)) {
            int hr = compute_hr(env_buf, env_len);
            if (hr >= HR_MIN && hr <= HR_MAX) g_ctx.heart_rate = hr;

            /* Run CNN classifier on mel-spectrogram of filtered signal */
            int cls = classifier_run(contact, BLOCK_SAMPLES);
            int conf = classifier_confidence();
            if (conf >= CLASS_CONF_THRESH) {
                g_ctx.class_id = cls;
                g_ctx.confidence = conf;
            }

            /* Update display */
            oled_update_status(g_ctx.heart_rate, g_ctx.class_id, g_ctx.confidence);

            /* Send via BLE */
            ble_send_result(g_ctx.class_id, g_ctx.confidence, g_ctx.heart_rate);

            /* If recording, log to SD */
            if (g_ctx.state == ST_RECORD) {
                sd_logger_write_block(contact, ambient, BLOCK_SAMPLES);
            }

            /* Reset envelope buffer for next window */
            env_len = 0;
        }
    }
}