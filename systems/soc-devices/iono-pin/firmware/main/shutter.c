/*
 * shutter.c — Bradbury-Nielsen shutter grid control
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * The Bradbury-Nielsen grid is two interleaved wire sets. When biased +/-90V
 * relative to each other, the field between wires traps ions (shutter CLOSED).
 * When the bias is briefly removed (200 us pulse), ions pass through (OPEN).
 *
 * Control: PA3 (SHUTTER_P) + PA4 (SHUTTER_N) drive an H-bridge that applies
 * the +/-90V bias. TIM6 generates the repetition rate; TIM7 generates the
 * 200us open pulse width.
 *
 * SPDX-License-Identifier: MIT
 */
#include "shutter.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"

static bool g_armed = false;
static uint32_t g_rep_hz = IMS_REP_RATE_HZ;

extern TIM_HandleTypeDef htim6;   /* rep rate */
extern TIM_HandleTypeDef htim7;   /* pulse width */

void shutter_init(void)
{
    g_armed = false;
    shutter_set_rep_rate_hz(IMS_REP_RATE_HZ);
}

void shutter_set_rep_rate_hz(uint32_t hz)
{
    if (hz < 5) hz = 5;
    if (hz > 60) hz = 60;
    g_rep_hz = hz;
    /* TIM6: 1 MHz timebase -> ARR = 1e6/hz */
    uint32_t arr = 1000000UL / hz;
    __HAL_TIM_SET_AUTORELOAD(&htim6, arr - 1);
}

uint32_t shutter_get_rep_rate(void) { return g_rep_hz; }

void shutter_arm(bool on)
{
    g_armed = on;
    if (on) {
        HAL_TIM_Base_Start_IT(&htim6);   /* start rep-rate timer */
    } else {
        HAL_TIM_Base_Stop_IT(&htim6);
        HAL_TIM_Base_Stop_IT(&htim7);
    }
}

bool shutter_is_armed(void) { return g_armed; }

/* Called from TIM6 update IRQ — fires the 200 us open pulse */
void shutter_on_rep_tick(void)
{
    if (!g_armed) return;
    /* Lower the bias (open shutter) for 200us via TIM7 one-shot */
    HAL_TIM_Base_Start_IT(&htim7);
    /* Drive SHUTTER_P/N low to remove bias (H-bridge off) */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
}

/* Called from TIM7 update IRQ — end of 200us open pulse, re-apply bias */
void shutter_on_pulse_end(void)
{
    /* Re-apply +/-90V bias: drive H-bridge to bias state */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
    HAL_TIM_Base_Stop_IT(&htim7);
}

void shutter_trigger_pulse(void)
{
    /* Manual single pulse (used in calibration mode) */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    /* busy-wait 200us (170MHz: 200us = 34000 cycles, trivial) */
    for (volatile int i = 0; i < 2000; i++) __NOP();
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
}