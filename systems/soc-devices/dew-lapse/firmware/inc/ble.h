/* ble.h — BLE notification interface */
#ifndef BLE_H
#define BLE_H

#include "dewpoint.h"

void ble_init(void);
void ble_notify(const humidity_t *h, float mirror_c, int state, int8_t tec_pct);

#endif