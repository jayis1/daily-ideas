/*
 * hall-puck / firmware / Core / Inc / esp32_link.h
 * UART bridge to ESP32-C3 companion (BLE + WiFi)
 *
 * Protocol: framed binary over UART1 @ 460800 baud
 *
 * MIT License.
 */
#ifndef ESP32_LINK_H
#define ESP32_LINK_H

#include <stdint.h>
#include <stdbool.h>
#include "measurement.h"

/* Frame types */
#define ESP_FRAME_RESULT    0x01
#define ESP_FRAME_POINT     0x02
#define ESP_FRAME_INFO      0x03
#define ESP_FRAME_CMD       0x04
#define ESP_FRAME_STATE     0x05
#define ESP_FRAME_ACK       0x06

/* Command codes (received from ESP32-C3) */
#define ESP_CMD_START       0x01
#define ESP_CMD_STOP        0x02
#define ESP_CMD_SET_CURRENT 0x03  /* payload: 4 bytes float mA */
#define ESP_CMD_SET_THICK   0x04  /* payload: 4 bytes float mm */
#define ESP_CMD_SET_MODE    0x05  /* payload: 1 byte mode */
#define ESP_CMD_CALIBRATE   0x06
#define ESP_CMD_GET_INFO    0x07

typedef void (*esp_cmd_callback_t)(uint8_t cmd, const uint8_t *payload, int len);

void esp32_link_init(void);
void esp32_link_set_cmd_callback(esp_cmd_callback_t cb);
void esp32_link_send_result(const meas_result_t *r);
void esp32_link_send_point(const meas_point_t *p, int idx);
void esp32_link_send_state(meas_state_t state);
void esp32_link_send_info(const char *fw_version, float b_field, uint32_t cal_date);
void esp32_link_poll(void);
bool esp32_link_is_connected(void);

#endif /* ESP32_LINK_H */