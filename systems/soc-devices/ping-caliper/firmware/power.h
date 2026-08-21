/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * power.h — Power management, rail gating, fuel gauge, charge status
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef POWER_H
#define POWER_H

#include "config.h"

typedef enum {
    POWER_STATE_RUN = 0,       /* fully active — measuring              */
    POWER_STATE_IDLE,          /* display on, HV/analog off            */
    POWER_STATE_SLEEP,         /* display off, deep-sleep until trigger */
    POWER_STATE_CHARGE,        /* USB-C connected, charging            */
} power_state_t;

typedef struct {
    power_state_t state;
    uint8_t        battery_pct;   /* 0..100 from MAX17048              */
    uint16_t       battery_mv;    /* estimated pack voltage            */
    uint8_t        charging;      /* 1 = charger active                 */
    uint8_t        vbus_present;   /* 1 = USB-C connected                */
    uint8_t        hv_enabled;     /* 1 = HV boost on                    */
    uint8_t        afe_enabled;    /* 1 = analog front-end rail on       */
} power_t;

void power_init(void);
void power_update(power_t *pwr);
void power_set_state(power_state_t state);

/* Rail control. */
void power_enable_hv(uint8_t en);
void power_enable_afe(uint8_t en);
void power_enable_sd(uint8_t en);

/* Fuel gauge (MAX17048 over I²C). */
uint8_t power_read_battery(uint8_t *pct, uint16_t *mv);
uint8_t power_read_charge_status(uint8_t *charging, uint8_t *standby);

/* Low-battery cutoff (shut down HV + AFE, warn, sleep). */
void power_low_battery_handler(void);

const power_t *power_get(void);

#endif /* POWER_H */