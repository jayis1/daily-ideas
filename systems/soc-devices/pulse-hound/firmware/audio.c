/*
 * Pulse Hound — RF Signal Hunter
 * audio.c — Geiger-counter-style audio feedback via LEDC PWM + LM386
 *
 * The click rate is proportional to RSSI: near-noise floor → 1 click/s,
 * strong signal (−10 dBm) → 50 clicks/s (continuous tone).
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "audio.h"
#include "config.h"
#include <math.h>

/* ---- HAL stubs ---- */
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);
extern void pwm_set_duty(int gpio, int channel, uint32_t duty);
extern void pwm_set_freq(int channel, uint32_t freq_hz);
extern uint32_t rtc_get_time_ms(void);

/* ---- Audio state ---- */
static int audio_enabled = 0;
static int audio_muted = 0;
static float last_rssi = RSSI_NOISE_FLOOR_DBM;
static uint32_t last_click_ms = 0;
static int click_phase = 0; /* 0 = idle, 1 = click on */

/* ---- Map RSSI to click rate ---- */
static float rssi_to_click_rate(float rssi_dbm)
{
    /* Map -80..+5 dBm to 0.5..50 clicks/s (exponential curve for sensitivity) */
    float range = RSSI_MAX_DBM - RSSI_MIN_DBM;
    float norm = (rssi_dbm - RSSI_MIN_DBM) / range;
    if (norm < 0.0f) norm = 0.0f;
    if (norm > 1.0f) norm = 1.0f;

    /* Exponential mapping: gives more sensitivity at low end */
    float rate = AUDIO_CLICK_MIN_RATE_HZ *
                 powf((float)AUDIO_CLICK_MAX_RATE_HZ / AUDIO_CLICK_MIN_RATE_HZ, norm);
    return rate;
}

/* ---- Generate a single click waveform ---- */
static void audio_click(void)
{
    /* A click is a short burst of PWM tone (2 ms on, then off) */
    /* Use a 1 kHz tone for the click (carrier is 10 kHz, we modulate duty) */
    int channel = 0;

    /* Click envelope: quick attack, exponential decay over 2 ms */
    uint32_t click_duration_ms = 2;
    int steps = 20; /* 20 sub-samples in 2 ms (100 µs each) */

    for (int i = 0; i < steps; i++) {
        /* Exponential decay envelope: duty = max * exp(-i/steps * 4) */
        float envelope = expf(-(float)i / (float)steps * 4.0f);
        uint32_t duty = (uint32_t)(envelope * (float)((1 << AUDIO_PWM_RES_BITS) - 1) * 0.3f);
        pwm_set_duty(AUDIO_PWM_GPIO, channel, duty);
        delay_ms(click_duration_ms / steps);
    }

    pwm_set_duty(AUDIO_PWM_GPIO, channel, 0);
}

/* ---- Update audio: called from main loop (100 Hz) ---- */
void audio_update(float rssi_dbm)
{
    last_rssi = rssi_dbm;
    if (!audio_enabled || audio_muted) return;

    float click_rate = rssi_to_click_rate(rssi_dbm);
    if (click_rate < 0.1f) return;

    /* Click interval in ms */
    uint32_t interval_ms = (uint32_t)(1000.0f / click_rate);
    if (interval_ms < 10) interval_ms = 10; /* cap at 100 clicks/s */

    uint32_t now = rtc_get_time_ms();
    if (now - last_click_ms >= interval_ms) {
        last_click_ms = now;
        audio_click();
    }
}

/* ---- Control ---- */
void audio_init(void)
{
    /* Configure LEDC PWM for audio output */
    int channel = 0;
    pwm_set_freq(channel, AUDIO_PWM_FREQ_HZ);
    pwm_set_duty(AUDIO_PWM_GPIO, channel, 0);

    /* LM386 shutdown: off initially */
    gpio_set(AUDIO_AMP_SHUTDOWN_GPIO, 0);
    audio_enabled = 0;
}

void audio_enable(void)
{
    gpio_set(AUDIO_AMP_SHUTDOWN_GPIO, 1); /* wake LM386 */
    delay_ms(10);
    audio_enabled = 1;
    audio_muted = 0;
}

void audio_disable(void)
{
    audio_enabled = 0;
    gpio_set(AUDIO_AMP_SHUTDOWN_GPIO, 0); /* shutdown LM386 */
}

void audio_mute(void)
{
    audio_muted = 1;
    pwm_set_duty(AUDIO_PWM_GPIO, 0, 0);
}

void audio_unmute(void)
{
    audio_muted = 0;
}

int audio_is_enabled(void)
{
    return audio_enabled && !audio_muted;
}

float audio_get_click_rate(void)
{
    return rssi_to_click_rate(last_rssi);
}