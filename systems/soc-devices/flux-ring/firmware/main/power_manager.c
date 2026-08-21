/*
 * Flux Ring — power_manager.c
 * Power management, battery monitoring, and sleep modes.
 *
 * SPDX-License-Identifier: MIT
 */

#include "power_manager.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/pm/device.h>
#include <zephyr/pm/pm.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(power_manager, LOG_LEVEL_INF);

/* Battery voltage is read through a 1:2 divider on ADC channel 2 (P0.04) */
#define BATT_ADC_NODE    DT_NODELABEL(batt_adc)
#define CHARGE_STAT_PIN  17

/* LiPo voltage curve (approximate percentage mapping) */
static const uint16_t lipo_mv_table[][2] = {
    { 3000,   0 },   /* 0%   */
    { 3200,  10 },   /* 10%  */
    { 3400,  20 },   /* 20%  */
    { 3500,  30 },   /* 30%  */
    { 3600,  50 },   /* 50%  */
    { 3700,  60 },   /* 60%  */
    { 3800,  70 },   /* 70%  */
    { 3900,  80 },   /* 80%  */
    { 4050,  90 },   /* 90%  */
    { 4200, 100 },   /* 100% */
};
#define LIPO_TABLE_SIZE (sizeof(lipo_mv_table) / sizeof(lipo_mv_table[0]))

static uint16_t battery_voltage_mv = 3700;
static bool usb_connected = false;

int power_manager_init(void)
{
    /* ADC is configured via devicetree */
    LOG_INF("Power manager initialized");
    return 0;
}

uint8_t power_manager_battery_pct(void)
{
    /* Look up percentage from voltage table */
    for (int i = 0; i < LIPO_TABLE_SIZE - 1; i++) {
        if (battery_voltage_mv <= lipo_mv_table[i + 1][0]) {
            uint16_t v0 = lipo_mv_table[i][0];
            uint16_t v1 = lipo_mv_table[i + 1][0];
            uint16_t p0 = lipo_mv_table[i][1];
            uint16_t p1 = lipo_mv_table[i + 1][1];
            if (v1 == v0) return (uint8_t)p0;
            uint16_t pct = p0 + ((battery_voltage_mv - v0) * (p1 - p0)) / (v1 - v0);
            return (uint8_t)(pct > 100 ? 100 : pct);
        }
    }
    return 100;
}

uint16_t power_manager_battery_mv(void)
{
    /* In a real implementation, this would read the ADC channel.
     * Battery voltage = ADC_reading * 2 (voltage divider) * reference / full_scale
     * Simplified here — return cached value.
     */
    return battery_voltage_mv;
}

void power_manager_deep_sleep(void)
{
    /* Configure wake source: accelerometer INT2 (wake-on-motion)
     * and RTC (periodic wake)
     */
    LOG_INF("Entering deep sleep...");

    /* In Zephyr, use the power management subsystem */
    k_sleep(K_MSEC(10000));  /* Simplified: 10s deep sleep */
}

void power_manager_idle(void)
{
    /* Light sleep: CPU halts, peripherals stay on
     * Wake on any interrupt (GPIO, timer, BLE)
     */
    k_cpu_idle();
}

bool power_manager_usb_connected(void)
{
    /* Read charge status pin from MCP73831 */
    return usb_connected;
}