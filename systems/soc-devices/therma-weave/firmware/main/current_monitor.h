/*
 * Therma Weave — Current Monitor
 * current_monitor.h — INA199 current sense amplifier interface
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef CURRENT_MONITOR_H
#define CURRENT_MONITOR_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#define INA199_ADDR         0x40   /* INA199 I²C address (A0=GND) */
#define INA199_SHUNT_MOHM   10     /* 0.01 Ω shunt resistor */
#define INA199_GAIN         100    /* INA199A2: 100 V/V gain */
#define CURRENT_FULLSCALE_MA 3300  /* Full-scale current (3.3V ADC / 0.01Ω / 100) */

/* Current sense register map (INA199-compatible) */
#define INA199_REG_CFG       0x00
#define INA199_REG_SHUNT     0x01
#define INA199_REG_BUS       0x02
#define INA199_REG_POWER     0x03
#define INA199_REG_CURRENT   0x04
#define INA199_REG_CAL       0x05
#define INA199_REG_MASK_EN   0x06
#define INA199_REG_ALERT     0x07

typedef struct {
    i2c_port_t i2c_num;
    float zone_currents[NUM_ZONES];   /* Current per zone in mA */
    float total_current_ma;          /* Total current in mA */
    bool  overcurrent_fault[NUM_ZONES];
    float overcurrent_threshold_ma;  /* Default 4000 mA */
} current_monitor_t;

/**
 * Initialize INA199 current sense amplifier.
 */
void current_monitor_init(current_monitor_t *cm, i2c_port_t i2c_num);

/**
 * Read current for a specific zone.
 * Returns current in mA. Uses multiplexed INA199 or individual readings.
 */
float current_monitor_read_zone(current_monitor_t *cm, uint8_t zone);

/**
 * Read total current (all zones).
 */
float current_monitor_read_total(current_monitor_t *cm);

/**
 * Set overcurrent threshold in mA.
 */
void current_monitor_set_threshold(current_monitor_t *cm, float threshold_ma);

/**
 * Check if overcurrent alert is active.
 */
bool current_monitor_check_alert(current_monitor_t *cm);

#endif /* CURRENT_MONITOR_H */