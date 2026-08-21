/*
 * Therma Weave — Safety Watchdog
 * safety_watchdog.h — Over-temperature and over-current protection
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef SAFETY_WATCHDOG_H
#define SAFETY_WATCHDOG_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_timer.h"

/* Fault types */
typedef enum {
    FAULT_NONE            = 0x00,
    FAULT_OVERCURRENT     = 0x01,
    FAULT_OVERTEMP        = 0x02,
    FAULT_THERMISTOR_OPEN = 0x04,
    FAULT_THERMISTOR_SHORT= 0x08,
    FAULT_LOW_BATTERY     = 0x10,
    FAULT_WATCHDOG        = 0x20,
    FAULT_COMM_ERROR      = 0x40,
} fault_type_t;

typedef struct {
    uint8_t safety_shutdown_pin;  /* GPIO for hardware shutdown OR gate */
    uint32_t fault_bitmap;         /* Current fault status */
    uint32_t fault_history[4];    /* Fault log per zone */
    bool     global_shutdown;      /* True if safety shutdown is active */
    int64_t  shutdown_time;        /* When shutdown was triggered */
    int      fault_count;          /* Total fault count */
    int      auto_retry_count;     /* Auto-retry attempts */
    int64_t  auto_retry_time;      /* Time of next auto-retry (µs) */
} safety_watchdog_t;

/**
 * Initialize safety watchdog.
 * safety_shutdown_pin: GPIO connected to OR gate that forces all MOSFET gates LOW.
 */
void safety_watchdog_init(safety_watchdog_t *sw, uint8_t safety_shutdown_pin);

/**
 * Record a fault for a specific zone.
 */
void safety_watchdog_fault(safety_watchdog_t *sw, fault_type_t fault, uint8_t zone);

/**
 * Clear all faults and re-enable zones.
 */
void safety_watchdog_clear_faults(safety_watchdog_t *sw);

/**
 * Emergency shutdown: force all heaters OFF via hardware OR gate.
 */
void safety_watchdog_emergency_shutdown(safety_watchdog_t *sw);

/**
 * Re-enable after shutdown (with cooldown period).
 */
bool safety_watchdog_try_recover(safety_watchdog_t *sw);

/**
 * Check if global shutdown is active.
 */
bool safety_watchdog_is_shutdown(safety_watchdog_t *sw);

/**
 * Check if any fault is active.
 */
bool safety_watchdog_has_fault(safety_watchdog_t *sw);

/**
 * Safety watchdog task — periodically checks for over-temperature
 * and over-current conditions.
 */
void safety_watchdog_task(void *pvParameters);

#endif /* SAFETY_WATCHDOG_H */