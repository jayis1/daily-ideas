/*
 * hv_supply.c — EMCO F50CT 5kV HV supply control + drift-voltage servo
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * HV chain: EMCO F50CT 5kV -> 8x 10M resistor ring (drift tube) -> 2125V total.
 * Drift voltage monitored via 2000:1 divider on PA1 (ADC2).
 * Safety: reed interlock + TLV3201 over-current comparator + IWDG + thermal fuse.
 *
 * SPDX-License-Identifier: MIT
 */
#include "hv_supply.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"

static bool g_enabled = false;
static bool g_fault_latched = false;
static float g_target_v = 0.0f;

extern ADC_HandleTypeDef hadc2;
extern TIM_HandleTypeDef htim2;   /* PWM to EMCO control pin */

void hv_init(void)
{
    g_enabled = false;
    g_fault_latched = false;
    g_target_v = 0.0f;
    /* EMCO SHDN pin: PC5 — output high = shutdown */
    GPIO_InitTypeDef io = {0};
    io.Pin = GPIO_PIN_5;
    io.Mode = GPIO_MODE_OUTPUT_PP;
    io.Pull = GPIO_NOPULL;
    io.Speed = GPIO_SPEED_FREQ_LOW;
    io.Alternate = 0;
    HAL_GPIO_Init(GPIOC, &io);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_5, GPIO_PIN_SET);   /* shutdown (active low SHDN: high=off) */

    /* Fault input PC4 */
    GPIO_InitTypeDef fin = {0};
    fin.Pin = GPIO_PIN_4;
    fin.Mode = GPIO_MODE_INPUT;
    fin.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &fin);
}

void hv_enable(bool on)
{
    if (on && !g_fault_latched) {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_5, GPIO_PIN_RESET);  /* SHDN low = ON */
        g_enabled = true;
    } else {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_5, GPIO_PIN_SET);    /* SHDN high = OFF */
        g_enabled = false;
    }
}

bool hv_is_enabled(void) { return g_enabled; }

void hv_set_drift_v(float target_v)
{
    if (target_v < 0.0f) target_v = 0.0f;
    if (target_v > HV_SUPPLY_MAX_V) target_v = HV_SUPPLY_MAX_V;
    g_target_v = target_v;
    /* EMCO F50CT control via PWM duty (TIM2_CH1) — 0..5V control -> 0..5kV out */
    extern TIM_HandleTypeDef htim2;
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(&htim2);
    uint32_t duty = (uint32_t)((target_v / HV_SUPPLY_MAX_V) * arr);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, duty);
}

float hv_read_drift_v(void)
{
    /* ADC2 channel 1 (PA1) reads HV monitor divider 2000:1 */
    extern ADC_HandleTypeDef hadc2;
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_1;
    ch.Rank = 1;
    ch.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc2, &ch);
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 5);
    uint32_t v = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);
    /* 12-bit ADC, 3.0V ref -> voltage = v/4095*3.0 ; HV = v_mon * 2000 */
    float vmon = (float)v / 4095.0f * 3.0f;
    return vmon * 2000.0f;
}

void hv_emergency_shutdown(void)
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_5, GPIO_PIN_SET);   /* SHDN high = OFF */
    g_enabled = false;
    g_target_v = 0.0f;
}

bool hv_fault(void)
{
    /* TLV3201 output PC4 (active high on over-current) */
    if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_4) == GPIO_PIN_SET) {
        g_fault_latched = true;
        hv_emergency_shutdown();
    }
    return g_fault_latched;
}