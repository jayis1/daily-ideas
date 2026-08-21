/*
 * Therma Weave — Power Manager
 * power_manager.h — Battery monitoring and power management
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <stdint.h>
#include <stdbool.h>

/* Battery voltage thresholds for 3S LiPo */
#define VBAT_FULL       12.6f   /* 4.2V × 3 cells */
#define VBAT_NOMINAL   11.1f   /* 3.7V × 3 cells */
#define VBAT_LOW        10.5f   /* 3.5V × 3 cells (cutoff) */
#define VBAT_CRITICAL    9.9f   /* 3.3V × 3 cells (dangerous) */

/* Voltage divider: VBAT → 100kΩ → ADC → 10kΩ → GND */
/* ADC reading = VBAT × 10/110 × (4095/3.3) */
/* VBAT = ADC × 3.3 × 110/10 / 4095 = ADC × 0.008862 */
#define VBAT_DIVIDER_RATIO  0.008862f

typedef struct {
    float vbat;                /* Battery voltage (V) */
    float vbus;                /* USB/VBUS voltage (V) */
    bool  charging;            /* Is battery charging? */
    bool  low_battery;         /* Is battery below low threshold? */
    uint8_t battery_pct;       /* Estimated battery percentage */
} power_manager_t;

/**
 * Initialize power manager.
 */
void power_manager_init(power_manager_t *pm);

/**
 * Read battery voltage via ADC.
 * Returns battery voltage in volts.
 */
float power_manager_read_battery(power_manager_t *pm);

/**
 * Estimate battery percentage from voltage.
 */
uint8_t power_manager_battery_pct(float vbat);

/**
 * Enter deep sleep mode (all heaters off, BLE advertising only).
 */
void power_manager_deep_sleep(uint32_t duration_ms);

#endif /* POWER_MANAGER_H */