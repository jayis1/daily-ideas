/**
 * ble_service.c — BLE GATT Service Implementation for Brew Sense
 * 
 * Implements the BrewSense GATT service (0xFFB0) on STM32L4
 * using the STM32 BLE stack.
 */

#include "ble_service.h"
#include "stm32l4xx_hal.h"
#include <string.h>
#include <stdio.h>

/* BLE connection state */
static bool s_connected = false;
static uint16_t s_conn_handle = 0;
static char s_device_name[21] = "BrewSense-001";

/* Characteristic value storage */
static float s_gravity = 1.000f;
static float s_temperature = 20.0f;
static uint16_t s_co2 = 400;
static float s_ph = 7.0f;
static float s_pressure = 1013.25f;
static uint8_t s_stage = 0;
static float s_activity = 0.0f;
static uint8_t s_battery = 100;
static int8_t s_trend = 0;

/* Advertising data */
static uint8_t adv_data[31];
static uint8_t adv_data_len = 0;

/*----------------------------------------------------------------------------*/

int ble_service_init(void) {
    /* In production, this initializes the STM32 BLE stack:
     * 1. Initialize HCI layer (via ESP32-C3 or built-in BLE)
     * 2. Register GATT service and characteristics
     * 3. Configure advertising data
     * 4. Set device name
     * 5. Start advertising
     * 
     * Since the STM32L476 doesn't have built-in BLE,
     * we use the ESP32-C3 module in transparent BLE mode.
     * Communication is via UART1 using AT commands.
     */
    
    /* Build advertising data */
    adv_data_len = 0;
    
    /* Flags: LE General Discoverable, BR/EDR Not Supported */
    adv_data[adv_data_len++] = 0x02;  /* Length */
    adv_data[adv_data_len++] = 0x01;  /* Type: Flags */
    adv_data[adv_data_len++] = 0x06;  /* Value */
    
    /* Complete 16-bit UUID */
    adv_data[adv_data_len++] = 0x03;  /* Length */
    adv_data[adv_data_len++] = 0x03;  /* Type: Complete 16-bit UUID */
    adv_data[adv_data_len++] = 0xB0;  /* LSB */
    adv_data[adv_data_len++] = 0xFF;  /* MSB */
    
    /* Manufacturer-specific data: gravity(4) + temp(2) + stage(1) + activity(1) */
    adv_data[adv_data_len++] = 0x0A;  /* Length */
    adv_data[adv_data_len++] = 0xFF;  /* Type: Manufacturer-specific */
    adv_data[adv_data_len++] = 0x01;  /* Company ID LSB (custom) */
    adv_data[adv_data_len++] = 0x00;  /* Company ID MSB */
    
    /* Gravity (float32, little-endian) */
    memcpy(&adv_data[adv_data_len], &s_gravity, 4);
    adv_data_len += 4;
    
    /* Temperature (int16, 0.1°C units) */
    int16_t temp_raw = (int16_t)(s_temperature * 10);
    adv_data[adv_data_len++] = (uint8_t)(temp_raw & 0xFF);
    adv_data[adv_data_len++] = (uint8_t)((temp_raw >> 8) & 0xFF);
    
    /* Stage (uint8) */
    adv_data[adv_data_len++] = s_stage;
    
    /* Activity index (uint8, 0-100) */
    adv_data[adv_data_len++] = (uint8_t)s_activity;
    
    return 0;
}

/*----------------------------------------------------------------------------*/

void ble_update_gravity(float gravity) {
    s_gravity = gravity;
    
    /* Update advertising data */
    if (adv_data_len >= 14) {
        memcpy(&adv_data[9], &s_gravity, 4);
    }
}

void ble_update_temperature(float temp_c) {
    s_temperature = temp_c;
    
    /* Update advertising data */
    if (adv_data_len >= 16) {
        int16_t temp_raw = (int16_t)(s_temperature * 10);
        adv_data[13] = (uint8_t)(temp_raw & 0xFF);
        adv_data[14] = (uint8_t)((temp_raw >> 8) & 0xFF);
    }
}

void ble_update_co2(uint16_t co2_ppm) {
    s_co2 = co2_ppm;
}

void ble_update_ph(float ph) {
    s_ph = ph;
}

void ble_update_pressure(float pressure_hPa) {
    s_pressure = pressure_hPa;
}

void ble_update_stage(ferment_stage_t stage) {
    s_stage = (uint8_t)stage;
    
    /* Update advertising data */
    if (adv_data_len >= 17) {
        adv_data[15] = s_stage;
    }
}

void ble_update_activity(float activity) {
    s_activity = activity;
    
    /* Update advertising data */
    if (adv_data_len >= 18) {
        adv_data[16] = (uint8_t)s_activity;
    }
}

void ble_update_battery(uint8_t percent) {
    s_battery = percent;
}

void ble_update_trend(int8_t trend) {
    s_trend = trend;
}

/*----------------------------------------------------------------------------*/

bool ble_is_connected(void) {
    return s_connected;
}

/*----------------------------------------------------------------------------*/

void ble_process_events(void) {
    /* In production, this processes BLE HCI events from the ESP32-C3:
     * - Connection events (set s_connected)
     * - GATT read requests (respond with current values)
     * - GATT write requests (update configuration)
     * - Disconnection events (restart advertising)
     * 
     * The ESP32-C3 runs in BLE transparent mode, forwarding
     * GATT events over UART1 to the STM32L4.
     */
}

/*----------------------------------------------------------------------------*/

void ble_set_device_name(const char *name) {
    strncpy(s_device_name, name, sizeof(s_device_name) - 1);
    s_device_name[sizeof(s_device_name) - 1] = '\0';
    
    /* Update BLE advertising with new name */
}