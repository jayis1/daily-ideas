/**
 * uart_protocol.c — Binary frame parser for STM32 → ESP32-C3 link
 *
 * Frame format: [0xAA][0x55][cmd][len_hi][len_lo][payload...][crc8]
 *
 * Commands:
 *   0x01: RESULT — measurement result
 *   0x02: STATUS — device status + battery
 *   0x03: CAL    — calibration data
 */

#include "uart_protocol.h"
#include "ble_service.h"
#include "wifi_server.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "uart_proto";

static uint8_t s_uart_port;
static uint8_t s_rx_buf[256];
static int s_rx_idx = 0;
static int s_frame_len = 0;
static int s_payload_len = 0;
static enum { RX_SYNC1, RX_SYNC2, RX_CMD, RX_LEN_HI, RX_LEN_LO, RX_PAYLOAD, RX_CRC } s_rx_state = RX_SYNC1;
static uint8_t s_current_cmd = 0;

/* CRC-8 (poly 0x07) — must match the STM32 side */
static uint8_t crc8(const uint8_t *data, int len) {
    uint8_t crc = 0;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) crc = (crc << 1) ^ 0x07;
            else crc <<= 1;
        }
    }
    return crc;
}

void uart_protocol_init(uint8_t uart_port) {
    s_uart_port = uart_port;
    s_rx_state = RX_SYNC1;
    s_rx_idx = 0;
}

void uart_protocol_process(const uint8_t *data, int len) {
    for (int i = 0; i < len; i++) {
        uint8_t byte = data[i];

        switch (s_rx_state) {
        case RX_SYNC1:
            if (byte == 0xAA) s_rx_state = RX_SYNC2;
            break;

        case RX_SYNC2:
            if (byte == 0x55) s_rx_state = RX_CMD;
            else s_rx_state = RX_SYNC1;
            break;

        case RX_CMD:
            s_current_cmd = byte;
            s_rx_state = RX_LEN_HI;
            break;

        case RX_LEN_HI:
            s_payload_len = byte << 8;
            s_rx_state = RX_LEN_LO;
            break;

        case RX_LEN_LO:
            s_payload_len |= byte;
            s_rx_idx = 0;
            if (s_payload_len == 0) {
                s_rx_state = RX_CRC;
            } else if (s_payload_len > 250) {
                ESP_LOGE(TAG, "Frame too large: %d", s_payload_len);
                s_rx_state = RX_SYNC1;
            } else {
                s_rx_state = RX_PAYLOAD;
            }
            break;

        case RX_PAYLOAD:
            s_rx_buf[s_rx_idx++] = byte;
            if (s_rx_idx >= s_payload_len) {
                s_rx_state = RX_CRC;
            }
            break;

        case RX_CRC: {
            uint8_t expected_crc = crc8(s_rx_buf, s_payload_len);
            if (byte == expected_crc) {
                /* Valid frame — dispatch */
                uart_protocol_dispatch(s_current_cmd, s_rx_buf, s_payload_len);
            } else {
                ESP_LOGW(TAG, "CRC mismatch: expected %02X, got %02X", expected_crc, byte);
            }
            s_rx_state = RX_SYNC1;
            break;
        }
        }
    }
}

void uart_protocol_dispatch(uint8_t cmd, const uint8_t *payload, int len) {
    switch (cmd) {
    case CMD_RESULT: {
        /* Parse the measurement result from the payload */
        if (len < 80) {
            ESP_LOGW(TAG, "Result payload too short: %d", len);
            return;
        }

        ri_result_t result;
        int idx = 0;

        /* RI values (4 × float32) */
        memcpy(result.n, &payload[idx], 16); idx += 16;

        /* n_D, n_F, n_C, dispersion, abbe_vd */
        memcpy(&result.n_D, &payload[idx], 4); idx += 4;
        memcpy(&result.n_F, &payload[idx], 4); idx += 4;
        memcpy(&result.n_C, &payload[idx], 4); idx += 4;
        memcpy(&result.dispersion, &payload[idx], 4); idx += 4;
        memcpy(&result.abbe_vd, &payload[idx], 4); idx += 4;

        /* Derived quantities */
        memcpy(&result.brix, &payload[idx], 4); idx += 4;
        memcpy(&result.specific_grav, &payload[idx], 4); idx += 4;
        memcpy(&result.abv, &payload[idx], 4); idx += 4;
        memcpy(&result.freeze_point, &payload[idx], 4); idx += 4;

        /* Temperatures */
        memcpy(&result.t_prism, &payload[idx], 4); idx += 4;
        memcpy(&result.t_ambient, &payload[idx], 4); idx += 4;

        /* Compound */
        result.compound_id = (int8_t)payload[idx++];
        memcpy(&result.confidence, &payload[idx], 4); idx += 4;
        memcpy(result.compound_name, &payload[idx], 16);
        result.compound_name[15] = '\0';

        ESP_LOGI(TAG, "Result: n_D=%.4f V_D=%.1f %s (%.0f%%)",
                 result.n_D, result.abbe_vd,
                 result.compound_name, result.confidence * 100);

        /* Relay to BLE and Wi-Fi clients */
        ble_service_notify_result(&result);
        wifi_server_notify_result(&result);
        break;
    }

    case CMD_STATUS: {
        if (len >= 2) {
            uint8_t status = payload[0];
            uint8_t battery = payload[1];
            ESP_LOGI(TAG, "Status: %d, Battery: %d%%", status, battery);
            ble_service_notify_status(status, battery);
        }
        break;
    }

    default:
        ESP_LOGW(TAG, "Unknown command: 0x%02X", cmd);
        break;
    }
}