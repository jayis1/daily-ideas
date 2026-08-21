/*
 * Hive Mind — LoRaWAN Uplink Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef LORAWAN_UPLINK_H
#define LORAWAN_UPLINK_H

#include <stdint.h>
#include <string.h>
#include "oled_display.h"  /* for sensor_data_t */

typedef enum {
    LORAWAN_OK = 0,
    LORAWAN_ERROR,
    LORAWAN_BUSY,
    LORAWAN_NOT_JOINED,
} lorawan_status_t;

void lorawan_init(void);
lorawan_status_t lorawan_send(const sensor_data_t *data);
lorawan_status_t lorawan_join(void);
void lorawan_set_keys(const uint8_t *dev_eui, const uint8_t *app_eui,
                       const uint8_t *app_key);
void lorawan_get_dev_eui(uint8_t *out_eui);

#endif /* LORAWAN_UPLINK_H */