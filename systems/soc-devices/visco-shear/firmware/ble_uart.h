/*
 * visco-shear / firmware / ble_uart.h
 * UART bridge to ESP32-C3 for BLE + Wi-Fi communication
 */
#ifndef VISCO_SHEAR_BLE_UART_H
#define VISCO_SHEAR_BLE_UART_H

#include "main.h"

typedef void (*cmd_callback_t)(uint8_t cmd, const uint8_t *payload, int len);

void ble_uart_init(cmd_callback_t cb);
void ble_uart_poll(void);
void ble_uart_send_torque_sample(uint16_t ts, int16_t torque, int16_t omega);
void ble_uart_send_result(const measure_result_t *res);
void ble_uart_send_info(const char *version, spindle_type_t sp, float temp);

#endif