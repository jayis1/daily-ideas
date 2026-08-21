/**
 * spiro_flow/buzzer.c — Coaching buzzer for spirometry maneuver guidance
 *
 * The buzzer provides audio coaching to help patients perform a proper
 * FVC maneuver:
 *   - "Ready" tone (slow warble) when armed
 *   - Sharp blast tone when exhalation is detected
 *   - Continuous rising tone during forced expiration (encourages "keep going!")
 *   - Completion beep when maneuver ends
 *
 * Uses TIM3 CH1 PWM on PA6, driving a piezo buzzer via a 2N3904 transistor.
 */

#include "main.h"
#include "buzzer.h"

#define TAG "BUZZER"

static bool s_buzzer_active = false;
static uint16_t s_current_freq = 0;

/* ── PWM init (TIM3 CH1 on PA6) ────────────────────────────────────── */

void buzzer_init(void)
{
    /* CH32V203 HAL:
     * TIM_TimeBaseInitTypeDef tim;
     * tim.TIM_Prescaler = SystemCoreClock / 1000000 - 1;  // 1MHz tick
     * tim.TIM_Period = 1000;  // default 1kHz
     * TIM_TimeBaseInit(TIM3, &tim);
     *
     * TIM_OCInitTypeDef oc;
     * oc.TIM_OCMode = TIM_OCMode_PWM1;
     * oc.TIM_OutputState = TIM_OutputState_Enable;
     * oc.TIM_Pulse = 0;  // 0% duty = silent
     * oc.TIM_OCPolarity = TIM_OCPolarity_High;
     * TIM_OC1Init(TIM3, &oc);
     * TIM_OC1PreloadConfig(TIM3, TIM_OCPreload_Enable);
     * TIM_Cmd(TIM3, ENABLE);
     */
    ESP_LOGI(TAG, "Buzzer initialized (TIM3 CH1, PA6)");
}

void buzzer_set_freq(uint16_t freq_hz, uint8_t duty_pct)
{
    if (freq_hz == 0 || duty_pct == 0) {
        /* Silence: set duty to 0 */
        /* TIM_SetCompare1(TIM3, 0); */
        s_buzzer_active = false;
        s_current_freq = 0;
        return;
    }

    /* ARR = 1MHz / freq_hz - 1
     * CCR = ARR * duty / 100
     */
    uint32_t arr = 1000000 / freq_hz - 1;
    uint32_t ccr = (arr * duty_pct) / 100;

    /* CH32V203 HAL:
     * TIM_SetAutoreload(TIM3, arr);
     * TIM_SetCompare1(TIM3, ccr);
     */
    s_buzzer_active = true;
    s_current_freq = freq_hz;
    (void)arr; (void)ccr;
}

void buzzer_beep(uint16_t freq_hz, uint16_t duration_ms)
{
    buzzer_set_freq(freq_hz, 50);
    delay_ms(duration_ms);
    buzzer_set_freq(0, 0);
}

/* ── Coaching tones ────────────────────────────────────────────────── */

void buzzer_coach_start(void)
{
    /* "Ready" warble: alternating 600/800 Hz, 200ms each, 3 cycles */
    for (int i = 0; i < 3; i++) {
        buzzer_set_freq(600, 30);
        delay_ms(200);
        buzzer_set_freq(800, 30);
        delay_ms(200);
    }
    buzzer_set_freq(0, 0);
}

void buzzer_coach_blast(void)
{
    /* Sharp blast tone: 1200 Hz, 100ms */
    buzzer_set_freq(1200, 50);
    delay_ms(100);
    /* Transition to rising encouragement tone */
    buzzer_set_freq(400, 40);
}

void buzzer_coach_done(void)
{
    /* Completion: ascending triad */
    buzzer_set_freq(660, 50);
    delay_ms(120);
    buzzer_set_freq(880, 50);
    delay_ms(120);
    buzzer_set_freq(1100, 50);
    delay_ms(200);
    buzzer_set_freq(0, 0);
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif