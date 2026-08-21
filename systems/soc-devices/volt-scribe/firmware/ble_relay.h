/*
 * volt-scribe — ble_relay.h
 */

#ifndef BLE_RELAY_H
#define BLE_RELAY_H

#include "stm32g4xx_hal.h"

void ble_relay_init(void);
void ble_relay_send_point(float x, float y);
void ble_relay_send_eis_point(float z_real, float z_imag, float freq);
void ble_relay_poll(void);

#endif