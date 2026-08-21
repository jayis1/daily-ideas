/*
 * ble.h — NimBLE BoltCompass GATT service
 */
#ifndef BOLT_COMPASS_BLE_H
#define BOLT_COMPASS_BLE_H

#include "types.h"

void ble_init(void);

/* Notify connected clients of a new sferic event (12-byte packed). */
void ble_notify_sferic(const stroke_t *st);

/* Notify a storm alert. */
void ble_notify_alert(alert_t a);

#endif /* BOLT_COMPASS_BLE_H */