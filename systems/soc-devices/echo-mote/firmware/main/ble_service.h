/**
 * ble_service.h — BLE 5.0 GATT server for Echo Mote
 */

#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include <stdint.h>
#include <stdbool.h>
#include "acoustic_params.h"

/**
 * Initialize BLE GATT server with Echo Mote service (0xFFB0).
 * Starts advertising when complete.
 */
int ble_service_init(void);

/**
 * Notify connected clients of new measurement results.
 *
 * @param mode    Measurement mode
 * @param results Results to send
 * @return 0 on success
 */
int ble_service_notify_results(uint32_t mode, const acoustic_results_t *results);

/**
 * Check if a BLE client is connected.
 */
bool ble_service_is_connected(void);

#endif /* BLE_SERVICE_H */