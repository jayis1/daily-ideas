/*
 * power.c — battery, rails, charging
 */

#include "power.h"
#include "stm32g4xx_hal.h"
#include "config.h"

extern ADC_HandleTypeDef hadc1;

void power_init(void)
{
    /* ADC channel for VBAT divider on ADC1 (channel 5, PC3 alt) */
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_5;
    ch.Rank = ADC_REGULAR_RANK_2;
    ch.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &ch);
}

float power_read_battery_mv(void)
{
    /* Sample VBAT through 2:1 divider on PC3 */
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    float v = (raw * 3300.0f) / 4095.0f;  /* mV at ADC */
    return v * 2.0f;                      /* undo divider */
}

uint8_t power_is_charging(void)
{
    /* STAT pin of MCP73831 — high = charging */
    return HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_13) == GPIO_PIN_SET;
}

uint8_t power_battery_pct(void)
{
    float mv = power_read_battery_mv();
    if (mv >= CONFIG_BATTERY_MV_FULL) return 100;
    if (mv <= CONFIG_BATTERY_MV_MIN)  return 0;
    return (uint8_t)((mv - CONFIG_BATTERY_MV_MIN) * 100.0f /
                     (CONFIG_BATTERY_MV_FULL - CONFIG_BATTERY_MV_MIN));
}