/**
 * power_manager.c — Low-power management and battery monitoring
 *
 * The STM32G491 enters Stop 2 mode (~12 µA) between measurements.
 * Battery voltage is read via a 1:2 voltage divider on PB13 (ADC1_IN11).
 * Charge status from MCP73831 is read on PB12.
 */

#include "power_manager.h"

extern ADC_HandleTypeDef hadc1;

#define VBAT_DIVIDER_RATIO   2.0f   /* 100k + 100k divider */
#define LIPO_FULL_MV         4200
#define LIPO_EMPTY_MV        3300

/* Charge status pin: PB12 */
#define CHARGE_STAT_PORT  GPIOB
#define CHARGE_STAT_PIN   GPIO_PIN_12

void power_manager_init(void) {
    /* CHARGE_STAT pin is already configured as input in MX_GPIO_Init */
}

void power_manager_enter_stop(void) {
    /* Enter Stop 2 mode — lowest power with RTC and SRAM retention */
    HAL_SuspendTick();
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

    /* Upon wake (from EXTI button press), clocks need reconfiguration */
    /* This is done by the caller after this function returns */
    HAL_ResumeTick();
}

uint8_t power_manager_read_battery(void) {
    /* Read VBAT_SENSE via ADC1 channel 11 (PB13) */
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_11;
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &ch);

    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint16_t adc_val = (uint16_t)HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    /* Convert ADC (12-bit, 3.3V ref) to battery voltage */
    float v_sense = (float)adc_val * 3.3f / 4095.0f;
    float v_bat = v_sense * VBAT_DIVIDER_RATIO;

    /* Convert to percentage (linear approximation) */
    float pct = (v_bat * 1000.0f - LIPO_EMPTY_MV) /
                (float)(LIPO_FULL_MV - LIPO_EMPTY_MV) * 100.0f;

    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;

    return (uint8_t)pct;
}

uint8_t power_manager_is_charging(void) {
    /* MCP73831 STAT pin: LOW = charging, HIGH = not charging (or done) */
    return (HAL_GPIO_ReadPin(CHARGE_STAT_PORT, CHARGE_STAT_PIN) == GPIO_PIN_RESET);
}