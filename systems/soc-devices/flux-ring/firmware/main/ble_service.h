/*
 * Flux Ring — ble_service.h
 * BLE GATT service for Flux Ring field data streaming.
 */

#ifndef BLE_SERVICE_H_
#define BLE_SERVICE_H_

#include "field_engine.h"
#include "accel_sensor.h"
#include "baro_sensor.h"
#include "compass.h"
#include <stdbool.h>
#include <stdint.h>

/* Flux Ring GATT Service UUID */
#define FLUX_RING_SERVICE_UUID  0xFFB0

/* Characteristic UUIDs */
#define FLUX_CHAR_FIELD_X       0xFFB1
#define FLUX_CHAR_FIELD_Y       0xFFB2
#define FLUX_CHAR_FIELD_Z       0xFFB3
#define FLUX_CHAR_MAGNITUDE     0xFFB4
#define FLUX_CHAR_HEADING       0xFFB5
#define FLUX_CHAR_POLE          0xFFB6
#define FLUX_CHAR_SAMPLE_RATE   0xFFB7
#define FLUX_CHAR_MODE          0xFFB8
#define FLUX_CHAR_BATTERY       0xFFB9
#define FLUX_CHAR_DEVICE_INFO   0xFFBA

/**
 * Initialize BLE stack and register GATT services.
 */
int ble_service_init(void);

/**
 * Update field-related GATT characteristics.
 */
void ble_service_update_field(float x, float y, float z,
                              float magnitude,
                              compass_heading_t heading,
                              pole_t pole,
                              uint8_t battery_pct);

/**
 * Update BLE advertising data (for non-connected modes).
 */
void ble_service_update_advertising(float magnitude,
                                    compass_heading_t heading,
                                    pole_t pole,
                                    uint8_t mode);

/**
 * Stream a complete sample packet to connected client.
 * Packet format: [timestamp(4)] [field(12)] [accel(6)] [heading(2)] = 24 bytes
 */
void ble_stream_sample(const field_vector_t *field,
                       const accel_data_t *accel,
                       const baro_data_t *baro,
                       compass_heading_t heading,
                       uint32_t timestamp_ms);

/**
 * Check if a BLE client is currently connected.
 */
bool ble_is_connected(void);

#endif /* BLE_SERVICE_H_ */