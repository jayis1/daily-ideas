/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/uart_comm.h
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef UART_COMM_H
#define UART_COMM_H

#include <stdint.h>
#include <stdbool.h>

/* UART config to STM32G474 */
#define UART_NUM        UART_NUM_1
#define UART_TX_PIN     3     /* GPIO3 */
#define UART_RX_PIN      2    /* GPIO2 */
#define UART_BAUDRATE    921600
#define UART_BUF_SIZE    512

/* Frame protocol (matches STM32 uart_proto.h) */
#define UART_SOF0        0xAA
#define UART_SOF1        0x55
#define UART_EOF0        0x0D
#define UART_EOF1        0x0A

/* Commands */
#define CMD_NOTIFY_MEASUREMENT  0x01
#define CMD_NOTIFY_FLAW         0x02
#define CMD_NOTIFY_ASCAN_CHUNK  0x03
#define CMD_NOTIFY_BATTERY      0x04
#define CMD_NOTIFY_STATUS       0x05
#define CMD_NOTIFY_LOG_ENTRY    0x06

#define CMD_GET_MEASUREMENT     0x10
#define CMD_GET_ASCAN           0x11
#define CMD_GET_CONFIG          0x12
#define CMD_SET_CONFIG          0x13
#define CMD_SET_MATERIAL        0x14
#define CMD_SET_MODE            0x15
#define CMD_SET_GATE            0x16
#define CMD_CALIBRATE_ZERO      0x17
#define CMD_CALIBRATE_VEL       0x18
#define CMD_FIRE_SINGLE         0x19
#define CMD_START_CONTINUOUS    0x1A
#define CMD_STOP_CONTINUOUS     0x1B
#define CMD_LIST_MATERIALS      0x1C
#define CMD_GET_LOG             0x1D
#define CMD_OTA_RESET           0x1E
#define CMD_SET_TGC             0x1F

#define CMD_ACK                 0x80
#define CMD_NACK                0x81

void uart_comm_init(void);

/* Send a framed command to the STM32. */
void uart_comm_send(uint8_t cmd, const uint8_t *payload, uint8_t len);

/* RX callback type — called when a frame is received from the STM32. */
typedef void (*uart_rx_cb_t)(uint8_t cmd, const uint8_t *payload, uint8_t len);
void uart_comm_register_rx(uart_rx_cb_t cb);

#endif /* UART_COMM_H */