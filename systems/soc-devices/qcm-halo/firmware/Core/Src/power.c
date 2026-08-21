/*
 * power.c — Battery monitoring and power management
 */

#include "main.h"
#include "power.h"

extern ADC_HandleTypeDef hadc1;

float power_read_battery_mv(void)
{
    /* ADC1 channel 15 (PB0) with 2:1 divider */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_15;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_24CYCLES;
    sConfig.SingleDiff = ADC_SINGLE_ENDED;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    /* Vbat = raw/4095 * 3.3 * divider_ratio */
    float v = (float)raw * 3.3f / 4095.0f * VBAT_DIVIDER;
    return v * 1000.0f; /* mV */
}

uint8_t power_get_battery_pct(void)
{
    float mv = power_read_battery_mv();
    /* LiPo: 4200mV = 100%, 3200mV = 0% */
    if (mv >= 4200) return 100;
    if (mv <= 3200) return 0;
    return (uint8_t)((mv - 3200) / 1000.0f * 100.0f);
}

uint8_t power_is_charging(void)
{
    /* Check MCP73831 CHRG pin (active low when charging) */
    /* In this design, the CHRG pin would be connected to a GPIO */
    /* For now, return based on USB-C VBUS presence */
    return 0; /* simplified */
}

uint8_t power_is_low(void)
{
    return (power_read_battery_mv() < VBAT_LOW_MV) ? 1 : 0;
}

void power_enter_lowpower(void)
{
    /* Stop TEC, pump, Si5351 */
    HAL_GPIO_WritePin(TEC_EN_PORT, TEC_EN_PIN, GPIO_PIN_RESET);
    pump_stop();

    /* Enter Stop mode — wake on button interrupt */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

    /* After wake-up, reconfigure clock */
    SystemClock_Config();
}

void power_wakeup(void)
{
    /* Clock is reconfigured after STOP mode exit in caller */
}