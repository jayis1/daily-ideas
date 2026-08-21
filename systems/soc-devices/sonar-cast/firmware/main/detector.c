/*
 * sonar-cast / firmware / detector.c
 * CFAR detection, bottom return detection, fish target detection + size estimate.
 */
#include "main.h"
#include <math.h>

static float cfar_threshold(const float *env, uint32_t i, uint32_t n)
{
    /* Cell-averaging CFAR: mean of training cells outside guard cells. */
    const int G = CFAR_GUARD, T = CFAR_TRAIN;
    double sum = 0.0;
    int cnt = 0;
    for (int k = -G - T; k <= G + T; k++) {
        if (k == 0) continue;
        int idx = (int)i + k;
        if (idx < 0 || idx >= (int)n) continue;
        if (abs(k) <= G) continue;   /* guard */
        sum += env[idx];
        cnt++;
    }
    if (cnt == 0) return 1e9f;
    float mean = (float)(sum / cnt);
    /* Threshold multiplier for Pfa = 1e-4 (exponential noise model):
       T = N · (Pfa^(-1/N) − 1)  ≈ 9.2 for N=32 */
    float alpha = 9.2f;
    return mean * alpha;
}

/* Love (1971) target-strength → fish length (cm) at 200 kHz.
   TS = 20·log10(L_cm) + 20·log10(f_kHz) − 65.4
   → L_cm = 10^((TS − 20·log10(f) + 65.4)/20) */
static float ts_to_length_cm(float ts_db, float freq_khz)
{
    float l = (ts_db - 20.0f * log10f(freq_khz) + 65.4f) / 20.0f;
    return powf(10.0f, l);
}

/* Estimate target strength (dB) from envelope amplitude and range.
   TS = 10·log10(pr/pi) + 40·log10(R) + 2·α·R  (sonar equation, simplified)
   pr/pi = env (normalized received power), R in meters, α ~ 0.005 dB/m @200k. */
static float env_to_ts(float env_norm, float range_m)
{
    const float alpha_db_m = 0.005f;
    if (env_norm < 1e-6f) return -120.0f;
    float pr_db = 10.0f * log10f(env_norm);
    return pr_db + 40.0f * log10f(range_m + 0.1f) + 2.0f * alpha_db_m * range_m;
}

void detector_run(const float *env, uint32_t n, sonar_result_t *r)
{
    memset(r->fish_depths, 0, sizeof(r->fish_depths));
    memset(r->fish_lengths, 0, sizeof(r->fish_lengths));
    memset(r->fish_ts, 0, sizeof(r->fish_ts));
    r->fish_count = 0;

    /* 1. Bottom detection: strongest peak after blanking zone. */
    uint32_t bottom_idx = BLANK_SAMPLES;
    float bottom_val = 0.0f;
    for (uint32_t i = BLANK_SAMPLES; i < n; i++) {
        if (env[i] > bottom_val) { bottom_val = env[i]; bottom_idx = i; }
    }

    /* Bottom depth = (idx / fs) · c / 2, tilt-corrected. */
    float raw_depth = (float)bottom_idx / (float)ADC_SAMPLE_RATE
                      * r->sound_speed / 2.0f;
    float cos_tilt = cosf(r->tilt_deg * (float)M_PI / 180.0f);
    if (cos_tilt < 0.3f) cos_tilt = 0.3f;   /* reject near-horizontal */
    r->depth_m = raw_depth * cos_tilt;

    /* 2. Second-bounce confirmation: look for a peak near 2×bottom_idx. */
    uint32_t sb_lo = bottom_idx + bottom_idx / 2;
    uint32_t sb_hi = bottom_idx * 2 + 8;
    if (sb_hi > n) sb_hi = n;
    float sb_val = 0.0f;
    for (uint32_t i = sb_lo; i < sb_hi; i++)
        if (env[i] > sb_val) sb_val = env[i];
    /* second-bounce ratio used by bottom_class */

    /* 3. Fish detection via CFAR — peaks above threshold, below bottom,
       with echo width < 2× compressed pulse width (reject diffuse). */
    const uint32_t pulse_w = 4;   /* ~4 µs = 4 samples compressed width */
    for (uint32_t i = BLANK_SAMPLES; i < bottom_idx - pulse_w; i++) {
        float thr = cfar_threshold(env, i, n);
        if (env[i] < thr) continue;

        /* Local peak? */
        if (i > 0 && i < n - 1 && env[i] >= env[i-1] && env[i] >= env[i+1]) {
            /* Echo width: count contiguous samples > 0.5·peak */
            float half = env[i] * 0.5f;
            int w = 1;
            for (int j = 1; j < 16; j++) {
                if ((int)i - j >= 0 && env[i-j] > half) w++; else break;
                if (i + j < n && env[i+j] > half) w++; else break;
            }
            if (w > 2 * (int)pulse_w) continue;   /* too wide → diffuse */

            if (r->fish_count >= MAX_FISH_PER_PING) break;

            float range_m = (float)i / (float)ADC_SAMPLE_RATE
                            * r->sound_speed / 2.0f * cos_tilt;
            float ts = env_to_ts(env[i], range_m);
            r->fish_depths[r->fish_count]  = range_m;
            r->fish_ts[r->fish_count]      = ts;
            r->fish_lengths[r->fish_count] = ts_to_length_cm(ts, 200.0f);
            r->fish_count++;
        }
    }

    /* 4. Bottom type classification (delegated). */
    bottom_class_run(env, n, bottom_idx, r);
}