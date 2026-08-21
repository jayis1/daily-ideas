/*
 * power.c — Battery management and power monitoring
 *
 * Monitors battery voltage and current via ADC.
 * MCP73831 handles LiPo charging from USB-C.
 * TPS63020 provides 3.3V buck-boost regulation.
 */

#include "power.h"
#include "main.h"
#include <math.h>

extern ADC_HandleTypeDef hadc1;

/* ── Private helpers ──────────────────────────────────── */

static uint16_t read_adc(ADC_HandleTypeDef *hadc, uint32_t channel)
{
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = channel;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(hadc, &sConfig);

    HAL_ADC_Start(hadc);
    HAL_ADC_PollForConversion(hadc, 10);
    return (uint16_t)HAL_ADC_GetValue(hadc);
}

/* ── Public Functions ─────────────────────────────────── */

void power_init(void)
{
    /* ADC already initialized in MX_ADC1_Init */
}

float power_battery_voltage(void)
{
    uint16_t raw = read_adc(&hadc1, BATTERY_V_CHANNEL);
    /* Voltage divider: V_bat = V_adc × 2.0
     * V_adc = raw / 4096 × 3.3V */
    float v_adc = (float)raw / (float)ADC_RESOLUTION * ADC_REF_V;
    return v_adc * BATTERY_DIVIDER;
}

float power_battery_current(void)
{
    uint16_t raw = read_adc(&hadc1, BATTERY_I_CHANNEL);
    /* INA181A1: 20 V/V gain, shunt resistor 0.1Ω
     * I = V_shunt / R_shunt, V_out = 20 × V_shunt
     * V_shunt = V_adc / 20
     * I = V_shunt / 0.1 = V_adc / (20 × 0.1) = V_adc / 2
     * V_adc = raw / 4096 × 3.3
     * I (mA) = V_adc / 2 × 1000  (in mV → mA) */
    float v_adc = (float)raw / (float)ADC_RESOLUTION * ADC_REF_V;
    float current_ma = (v_adc / 2.0f) * 1000.0f;
    /* Subtract zero-current offset (mid-supply = 1.65V) */
    current_ma = current_ma - 825.0f;
    return current_ma;
}

uint8_t power_battery_pct(void)
{
    float v = power_battery_voltage();
    /* LiPo discharge curve: 4.2V = 100%, 3.3V = 0% */
    float pct = (v - BATTERY_MIN_V) / (BATTERY_MAX_V - BATTERY_MIN_V) * 100.0f;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    return (uint8_t)pct;
}

int power_is_charging(void)
{
    /* MCP73831 STAT pin: low = charging, high = not charging */
    return (HAL_GPIO_ReadPin(CHARGE_STAT_GPIO, CHARGE_STAT_PIN) == GPIO_PIN_RESET) ? 1 : 0;
}

void power_low_power(void)
{
    /* Reduce clock, disable unused peripherals */
    /* In production: switch to low-power run mode, gate ADC, lower OLED */
    HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
}

void power_wake(void)
{
    /* Return to normal run mode */
    /* Clock is restored by interrupt handler */
}

int power_battery_low(void)
{
    return (power_battery_voltage() < BATTERY_WARN_V) ? 1 : 0;
}

uint16_t power_remaining_minutes(void)
{
    /* Estimate remaining runtime from current consumption and battery capacity */
    float i = power_battery_current();
    if (i >= 0) return 0;  /* charging */

    float capacity_mah = 1800.0f;  /* 1800 mAh battery */
    float remaining_mah = capacity_mah * (float)power_battery_pct() / 100.0f;
    float current_ma = -i;  /* make positive */

    if (current_ma < 1) current_ma = 150;  /* average consumption estimate */

    return (uint16_t)(remaining_mah / current_ma * 60.0f);
}