/*
 * Therma Weave — BLE Service
 * ble_service.h — BLE GATT server for ThermaWeave control
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include <stdint.h>
#include <stdbool.h>
#include "zone_controller.h"
#include "safety_watchdog.h"

/* BLE UUIDs */
#define THERMA_SERVICE_UUID          0xFFB0
#define ENV_SERVICE_UUID             0x181A

/* ThermaWeave Control Characteristic UUIDs */
#define CHAR_ZONE0_TARGET_UUID       0xFFB1
#define CHAR_ZONE1_TARGET_UUID       0xFFB2
#define CHAR_ZONE2_TARGET_UUID       0xFFB3
#define CHAR_ZONE3_TARGET_UUID       0xFFB4
#define CHAR_ZONE0_DUTY_UUID         0xFFB5
#define CHAR_ZONE1_DUTY_UUID         0xFFB6
#define CHAR_ZONE2_DUTY_UUID         0xFFB7
#define CHAR_ZONE3_DUTY_UUID         0xFFB8
#define CHAR_ZONE0_CURRENT_UUID      0xFFB9
#define CHAR_ZONE1_CURRENT_UUID      0xFFBA
#define CHAR_ZONE2_CURRENT_UUID      0xFFBB
#define CHAR_ZONE3_CURRENT_UUID      0xFFBC
#define CHAR_ACTIVITY_UUID           0xFFBD
#define CHAR_ENABLE_UUID             0xFFBE
#define CHAR_SAFETY_UUID             0xFFBF
#define CHAR_FAULT_UUID              0xFFC0
#define CHAR_PID_KP_UUID             0xFFC1
#define CHAR_PID_KI_UUID             0xFFC2
#define CHAR_PID_KD_UUID             0xFFC3
#define CHAR_DEVICE_INFO_UUID        0xFFFF

typedef struct {
    zone_controller_t *zones;
    safety_watchdog_t *safety;
    bool connected;
    uint16_t conn_handle;
} ble_service_t;

/**
 * Initialize BLE GATT server and start advertising.
 */
void ble_service_init(void);

/**
 * Set pointer to zone controllers for BLE read/write access.
 */
void ble_service_set_zone_controllers(zone_controller_t *zones);

/**
 * Set pointer to safety watchdog for BLE fault reporting.
 */
void ble_service_set_safety_watchdog(safety_watchdog_t *safety);

/**
 * BLE task — handles GATT events, notifications, and connection management.
 */
void ble_service_task(void *pvParameters);

/**
 * Notify all connected clients with current zone data.
 */
void ble_service_notify_zone_data(void);

#endif /* BLE_SERVICE_H */