/**
 * ble_service.h — BLE GATT Service for Brew Sense
 * 
 * Implements a custom GATT service (0xFFB0) with characteristics
 * for real-time fermentation monitoring over BLE 5.2.
 */

#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include <stdint.h>
#include "fermentation.h"

/* BLE Service and Characteristic UUIDs */
#define BREWSENSE_SERVICE_UUID       0xFFB0
#define BREWSENSE_CHAR_GRAVITY_UUID  0xFFB1
#define BREWSENSE_CHAR_TEMP_UUID     0xFFB2
#define BREWSENSE_CHAR_CO2_UUID      0xFFB3
#define BREWSENSE_CHAR_PH_UUID       0xFFB4
#define BREWSENSE_CHAR_PRESSURE_UUID 0xFFB5
#define BREWSENSE_CHAR_STAGE_UUID    0xFFB6
#define BREWSENSE_CHAR_ACTIVITY_UUID 0xFFB7
#define BREWSENSE_CHAR_BATTERY_UUID  0xFFB8
#define BREWSENSE_CHAR_TREND_UUID    0xFFB9
#define BREWSENSE_CHAR_INFO_UUID     0xFFBA

/**
 * Initialize BLE stack and register GATT services.
 * Sets up advertising with BrewSense UUID.
 * @return 0 on success, negative on error
 */
int ble_service_init(void);

/**
 * Update the gravity characteristic and notify connected clients.
 * @param gravity Specific gravity (e.g., 1.050)
 */
void ble_update_gravity(float gravity);

/**
 * Update the temperature characteristic and notify connected clients.
 * @param temp_c Temperature in °C
 */
void ble_update_temperature(float temp_c);

/**
 * Update the CO₂ characteristic and notify connected clients.
 * @param co2_ppm CO₂ concentration in ppm
 */
void ble_update_co2(uint16_t co2_ppm);

/**
 * Update the pH characteristic and notify connected clients.
 * @param ph pH value (0.0-14.0)
 */
void ble_update_ph(float ph);

/**
 * Update the pressure characteristic.
 * @param pressure_hPa Barometric pressure in hPa
 */
void ble_update_pressure(float pressure_hPa);

/**
 * Update the fermentation stage characteristic.
 * @param stage Current fermentation stage
 */
void ble_update_stage(ferment_stage_t stage);

/**
 * Update the activity index characteristic.
 * @param activity Activity index (0-100)
 */
void ble_update_activity(float activity);

/**
 * Update the battery level characteristic.
 * @param percent Battery percentage (0-100)
 */
void ble_update_battery(uint8_t percent);

/**
 * Update the gravity trend characteristic.
 * @param trend -2 to +2 (falling fast to rising fast)
 */
void ble_update_trend(int8_t trend);

/**
 * Check if a BLE client is currently connected.
 * @return true if connected
 */
bool ble_is_connected(void);

/**
 * Process BLE stack events. Call from main loop.
 */
void ble_process_events(void);

/**
 * Set the device name in BLE advertising.
 * @param name Null-terminated string (max 20 chars)
 */
void ble_set_device_name(const char *name);

#endif /* BLE_SERVICE_H */