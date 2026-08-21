/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/wifi_api.h — Optional Wi-Fi AP for direct phone connection + OTA
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef WIFI_API_H
#define WIFI_API_H

#include <stdbool.h>

void wifi_api_init(void);
bool wifi_is_connected(void);

/* Start OTA from a URL (called by the phone app via BLE command). */
void wifi_ota_start(const char *url);

#endif /* WIFI_API_H */