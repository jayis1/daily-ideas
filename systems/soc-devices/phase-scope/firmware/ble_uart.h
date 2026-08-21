/*
 * Phase Scope — BLE UART header
 */

#ifndef BLE_UART_H
#define BLE_UART_H

#include <stdint.h>
#include "power_quality.h"

void ble_uart_init(void);
void ble_uart_send_status(const power_results_t *res);
uint8_t ble_uart_get_command(uint8_t *buf, uint8_t *len);

#endif /* BLE_UART_H */