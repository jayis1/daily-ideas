/*
 * pump.c — drift-gas micro-pump + 2-way valve control
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * 6V diaphragm pump on PA5 (TIM2_CH2 PWM 25kHz), 2-way valve for drift-gas/sample
 * routing. In normal operation, drift gas flows counter-current to ion drift
 * (clean air from charcoal scrubber). Sample mode routes inlet gas through
 * the ionization region then to exhaust.
 *
 * SPDX-License-Identifier: MIT
 */
#include "pump.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"

extern TIM_HandleTypeDef htim2;

static bool g_on = false;
static uint8_t g_pct = 60;

void pump_init(void)
{
    g_on = false;
    g_pct = 60;
    /* valve control pin — assume PC12 (reuse if available) */
    GPIO_InitTypeDef io = {0};
    io.Pin = GPIO_PIN_12;
    io.Mode = GPIO_MODE_OUTPUT_PP;
    io.Pull = GPIO_NOPULL;
    io.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &io);
    valve_set_sample(false);
}

void pump_set_speed(uint8_t pct)
{
    if (pct > 100) pct = 100;
    g_pct = pct;
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(&htim2);
    uint32_t duty = (uint32_t)((pct / 100.0f) * arr);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, duty);
}

uint8_t pump_get_speed(void) { return g_pct; }

void pump_enable(bool on)
{
    g_on = on;
    if (on) {
        HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_2);
        pump_set_speed(g_pct);
    } else {
        HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_2);
        __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, 0);
    }
}

void valve_set_sample(bool sample)
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, sample ? GPIO_PIN_SET : GPIO_PIN_RESET);
}