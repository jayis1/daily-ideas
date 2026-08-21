/**
 * ble_service.h — BLE GATT server for Refracto Bead
 */
#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include "uart_protocol.h"
#include <stdint.h>
#include <stdbool.h>

int ble_service_init(void);
void ble_service_notify_result(const ri_result_t *result);
void ble_service_notify_status(uint8_t status, uint8_t battery);
bool ble_service_is_connected(void);

#endif /* BLE_SERVICE_H */