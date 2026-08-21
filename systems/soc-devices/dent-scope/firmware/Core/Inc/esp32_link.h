/*
 * dent-scope / Core/Inc/esp32_link.h
 * Dent Scope — UART protocol to ESP32-C3 for BLE/Wi-Fi
 * MIT License.
 */
#ifndef ESP32_LINK_H
#define ESP32_LINK_H

#include "main.h"

void esp32_link_init(void);
void esp32_link_poll(void);
void esp32_send_point(float force_mN, float depth_um, uint32_t t_ms);
void esp32_send_result(ds_status_t *st);

#endif /* ESP32_LINK_H */