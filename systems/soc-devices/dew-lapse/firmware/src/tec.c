/* tec.c — TEC driver: PWM, direction, current/voltage sense, safety cutout.
 * Uses TIM2_CH1 for PWM (20 kHz), DRV8871 IN1/IN2 for direction, ADC1
 * channels 5/6 for voltage/current sense.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "tec.h"

extern TIM_HandleTypeDef htim2;
extern ADC_HandleTypeDef hadc1;

static float tec_current_a;
static float tec_voltage_v;
static int    tec_enabled = 0;

void tec_init(void)
{
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_RESET);  /* forward */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_SET);   /* heater FET off */
    tec_enabled = 1;
}

/* Drive TEC at signed fraction in [-1.0, +1.0].
 * Positive = cool (cold side down), negative = heat (defrost).
 */
void tec_set(float frac)
{
    if (frac >  0.9f) frac =  0.9f;
    if (frac < -0.9f) frac = -0.9f;

    uint32_t duty = (uint32_t)(fabsf(frac) * TEC_PWM_MAX);
    if (frac >= 0.0f) {
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_RESET);   /* cool */
    } else {
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_SET);     /* heat */
    }
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, duty);
}

void tec_off(void)
{
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);
}

void tec_defrost_start(void)
{
    /* Use reverse heating FET for fast defrost. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_RESET);  /* heater on */
    tec_set(-0.7f);
}

void tec_defrost_stop(void)
{
    tec_set(0.0f);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_SET);
}

/* Read current/voltage via ADC1. Called from 1 kHz sampler. */
void tec_sense_update(void)
{
    /* After ADC conversion of channels 5,6 (PA0,PA1) */
    /* (HAL ADC boilerplate elided; use DMA buffer values) */
    extern volatile uint16_t adc_raw[2];
    /* PA0: TEC voltage, 10:1 divider → V_tec = raw/4095 * 3.3 * 10 */
    tec_voltage_v = (float)adc_raw[0] / 4095.0f * 3.3f * 10.0f;
    /* PA1: AD8418 output, gain 28 → V_sense = raw/4095 * 3.3, I = V/28 * (1/Rshunt=1/0.02) */
    /* AD8418 sense: 28 * (I*0.02) = 0.56*I; so I = V_sense/0.56 */
    float vsense = (float)adc_raw[1] / 4095.0f * 3.3f;
    tec_current_a = vsense / 0.56f;
}

float tec_current(void)   { return tec_current_a; }
float tec_voltage(void)   { return tec_voltage_v; }

/* Safety check: overcurrent, over-temp (called from controller). */
int tec_safety_ok(float hot_temp_c)
{
    if (tec_current_a > TEC_CURRENT_LIMIT_A) return 0;
    if (hot_temp_c > TEC_HOT_LIMIT_C)        return 0;
    return 1;
}