/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * power.c — Battery/solar monitoring, sleep management
 *
 * Uses the nRF52840 SAADC (12-bit) to read:
 *  - Battery voltage via a ÷2 resistor divider on P0.05
 *  - Solar panel voltage via a ÷2 resistor divider on P0.06
 *
 * The SAADC uses the internal 0.6 V reference with 1/6 gain → Vref = 3.6 V,
 * 12-bit resolution (0–4095 counts → 0–3.6 V at the ADC input).
 * With the ÷2 divider, the full battery range (0–4.2 V) maps to 0–2.1 V
 * at the ADC, well within the 3.6 V reference.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "power.h"
#include "config.h"
#include <math.h>

/* ---- Platform HAL stubs ---- */
extern void saadc_init(int channel, int pin, int ref_mv);
extern int  saadc_sample(int channel);
extern void enter_light_sleep(uint32_t ms);
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);

/* SAADC channel assignments */
#define SAADC_CH_BATTERY  0
#define SAADC_CH_SOLAR    1

int power_init(void)
{
    /* Configure SAADC channels:
     *  - Channel 0: battery voltage (P0.05, ÷2 divider)
     *  - Channel 1: solar voltage (P0.06, ÷2 divider)
     * Reference: internal 0.6 V, gain 1/6 → full-scale 3.6 V */
    saadc_init(SAADC_CH_BATTERY, PIN_BATTERY_V, 3600);
    saadc_init(SAADC_CH_SOLAR, PIN_SOLAR_V, 3600);
    return 0;
}

float power_read_battery_v(void)
{
    int raw = saadc_sample(SAADC_CH_BATTERY);
    if (raw < 0) return 0.0f;

    /* Convert raw ADC counts to voltage at the ADC input:
     * V_adc = raw / 4095 * 3.6 V
     * Then multiply by the divider ratio (2.0) to get the battery voltage. */
    float v_adc = (float)raw / 4095.0f * (SAADC_REF_MV / 1000.0f);
    return v_adc * BATTERY_DIVIDER_RATIO;
}

float power_read_solar_v(void)
{
    int raw = saadc_sample(SAADC_CH_SOLAR);
    if (raw < 0) return 0.0f;

    float v_adc = (float)raw / 4095.0f * (SAADC_REF_MV / 1000.0f);
    return v_adc * BATTERY_DIVIDER_RATIO;
}

int power_battery_pct(float voltage)
{
    /* LiPo discharge curve approximation (simplified piecewise linear) */
    if (voltage >= BATTERY_FULL_MV / 1000.0f) return 100;
    if (voltage <= BATTERY_EMPTY_MV / 1000.0f) return 0;

    /* Linear interpolation between 3.2 V (0%) and 4.2 V (100%) */
    float pct = (voltage - (BATTERY_EMPTY_MV / 1000.0f)) /
                ((BATTERY_FULL_MV - BATTERY_EMPTY_MV) / 1000.0f) * 100.0f;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    return (int)pct;
}

int power_is_charging(float solar_v)
{
    /* The MCP73871 charge controller charges when the solar panel
     * voltage exceeds the battery voltage. We consider charging active
     * when solar voltage > 4.0 V (above the LiPo full voltage). */
    return (solar_v > (SOLAR_CHARGE_THRESHOLD_MV / 1000.0f)) ? 1 : 0;
}

void power_enter_sleep(uint32_t ms)
{
    /* Power down peripherals to minimize sleep current:
     *  - Sensor head load switch OFF (saves ~2 mA)
     *  - SD card power OFF (saves ~0.1 mA)
     *  - SX1262 to sleep mode (saves ~1.5 mA)
     *  - DO probe power OFF (saves ~0.5 mA)
     *
     * The nRF52840 enters System ON sleep (~1.5 µA) with RTC wakeup. */
    gpio_set(PIN_SENSOR_PWR, 0);
    gpio_set(PIN_SD_PWR, 0);
    gpio_set(PIN_DO_PWR, 0);

    /* Enter light sleep (RTC wakeup after ms) */
    enter_light_sleep(ms);

    /* Re-power sensor head after wake */
    gpio_set(PIN_SENSOR_PWR, 1);
    delay_ms(50);  /* sensor stabilization */
}

void power_manage(mussel_watch_state_t *st)
{
    st->battery_v = power_read_battery_v();
    st->solar_v = power_read_solar_v();
    st->battery_pct = power_battery_pct(st->battery_v);
    st->charging = power_is_charging(st->solar_v);

    /* Low battery alert */
    if (st->battery_pct < BATTERY_LOW_PCT) {
        st->current_alert = ALERT_LOW_BATTERY;
    }
}