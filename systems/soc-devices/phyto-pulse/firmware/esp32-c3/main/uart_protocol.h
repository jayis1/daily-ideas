/*
 * uart_protocol.h — UART protocol between STM32G474 and ESP32-C3
 */

#ifndef UART_PROTOCOL_H
#define UART_PROTOCOL_H

#include <stdint.h>

void uart_protocol_init(void);
void uart_protocol_task(void *arg);

/* Process a received packet (JSON) from STM32 */
void uart_protocol_handle_packet(const char *json, int len);

#endif /* UART_PROTOCOL_H */