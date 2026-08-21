/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * uart_proto.h — Framed binary protocol to ESP32-C3 (BLE/Wi-Fi bridge)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef UART_PROTO_H
#define UART_PROTO_H

#include "config.h"
#include "receiver.h"
#include "thickness.h"
#include "flaw.h"

/* Protocol frame format (UART, 921600 baud, DMA):
 *
 *  ┌──────┬──────┬──────┬───────────────┬────────────────┬──────┐
 *  │SOF   │LEN   │ CMD  │  payload[LEN] │ CRC16 (2 bytes)│ EOF  │
 *  │0xAA55│u8   │ u8   │               │ lo hi           │0x0D0A│
 *  └──────┴──────┴──────┴───────────────┴────────────────┴──────┘
 *
 * SOF is two bytes (0xAA 0x55). LEN is payload length (0..250).
 * CRC16-CCITT over [LEN..payload], polynomial 0x1021, init 0xFFFF.
 */

#define UART_SOF_0       0xAA
#define UART_SOF_1       0x55
#define UART_EOF_0       0x0D
#define UART_EOF_1       0x0A
#define UART_MAX_PAYLOAD 250

/* Commands (STM32 → ESP32-C3, unsolicited/notify) */
#define CMD_NOTIFY_MEASUREMENT  0x01
#define CMD_NOTIFY_FLAW         0x02
#define CMD_NOTIFY_ASCAN_CHUNK  0x03
#define CMD_NOTIFY_BATTERY      0x04
#define CMD_NOTIFY_STATUS       0x05
#define CMD_NOTIFY_LOG_ENTRY    0x06

/* Commands (ESP32-C3 → STM32, request) */
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

/* ACKs */
#define CMD_ACK                 0x80
#define CMD_NACK                0x81

void uart_proto_init(void);

/* Send helpers (called by process/ui tasks). */
void uart_send_measurement(const thickness_result_t *thk,
                             const flaw_result_t *flaw,
                             const char *material,
                             int16_t battery_pct);
void uart_send_ascan(const ascan_t *scan, uint16_t chunk_idx, uint16_t total_chunks);
void uart_send_status(uint8_t armed, uint8_t measuring, uint8_t battery_pct);

/* Poll the incoming ring; dispatch to handlers. Non-blocking. */
void uart_proto_poll(void);

/* Register a callback for SET_CONFIG / SET_MATERIAL etc. */
typedef void (*uart_cmd_handler_t)(uint8_t cmd, const uint8_t *payload, uint8_t len);
void uart_proto_register_handler(uart_cmd_handler_t handler);

#endif /* UART_PROTO_H */