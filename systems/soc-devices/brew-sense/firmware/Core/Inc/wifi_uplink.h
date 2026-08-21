/**
 * wifi_uplink.h — Wi-Fi Uplink via ESP32-C3 AT Commands
 * 
 * Manages communication with an ESP32-C3 co-processor running
 * in AT-command mode for Wi-Fi connectivity and MQTT publishing.
 */

#ifndef WIFI_UPLINK_H
#define WIFI_UPLINK_H

#include <stdint.h>
#include <stdbool.h>
#include "fermentation.h"

/* MQTT configuration */
typedef struct {
    const char *broker_url;    /* e.g., "mqtt://homeassistant.local" */
    uint16_t broker_port;      /* e.g., 1883 */
    const char *device_id;    /* e.g., "brewsense-001" */
    const char *username;     /* MQTT username (can be NULL) */
    const char *password;     /* MQTT password (can be NULL) */
} wifi_mqtt_config_t;

/* Wi-Fi configuration */
typedef struct {
    const char *ssid;          /* Wi-Fi SSID */
    const char *password;      /* Wi-Fi password */
} wifi_config_t;

/**
 * Initialize UART connection to ESP32-C3 and configure AT mode.
 * @return 0 on success, negative on error
 */
int wifi_uplink_init(void);

/**
 * Configure Wi-Fi credentials on the ESP32-C3.
 * @param config Wi-Fi SSID and password
 * @return 0 on success, negative on error
 */
int wifi_configure(const wifi_config_t *config);

/**
 * Connect to Wi-Fi access point.
 * Blocks until connected or timeout.
 * @param timeout_ms Connection timeout in ms
 * @return 0 on success, negative on error
 */
int wifi_connect(uint32_t timeout_ms);

/**
 * Disconnect from Wi-Fi.
 */
void wifi_disconnect(void);

/**
 * Check if Wi-Fi is currently connected.
 * @return true if connected
 */
bool wifi_is_connected(void);

/**
 * Configure MQTT broker settings.
 * @param config MQTT broker configuration
 * @return 0 on success, negative on error
 */
int wifi_mqtt_configure(const wifi_mqtt_config_t *config);

/**
 * Connect to MQTT broker.
 * @param timeout_ms Connection timeout in ms
 * @return 0 on success, negative on error
 */
int wifi_mqtt_connect(uint32_t timeout_ms);

/**
 * Publish all sensor data to MQTT as a JSON message.
 * Publishes to brewsense/{device_id}/status
 * @param gravity Specific gravity
 * @param temperature Temperature in °C
 * @param co2_ppm CO₂ in ppm
 * @param ph pH value
 * @param pressure Pressure in hPa
 * @param stage Fermentation stage
 * @param activity Activity index (0-100)
 * @return 0 on success, negative on error
 */
int wifi_push_all(float gravity, float temperature, uint16_t co2_ppm,
                  float ph, float pressure, ferment_stage_t stage,
                  float activity);

/**
 * Publish to individual MQTT topics.
 * @param topic_suffix Topic suffix (e.g., "gravity", "temperature")
 * @param value Float value to publish
 * @return 0 on success, negative on error
 */
int wifi_publish_value(const char *topic_suffix, float value);

/**
 * Disconnect from MQTT broker.
 */
void wifi_mqtt_disconnect(void);

/**
 * Put ESP32-C3 into deep sleep mode to save power.
 */
void wifi_sleep(void);

/**
 * Wake ESP32-C3 from deep sleep.
 */
void wifi_wake(void);

/**
 * Get RSSI of current Wi-Fi connection.
 * @return RSSI in dBm, or 0 if not connected
 */
int8_t wifi_get_rssi(void);

#endif /* WIFI_UPLINK_H */