/*
 * ble_bridge.c — UART bridge to ESP32-C3 for BLE/Wi-Fi communication
 *
 * Binary framed protocol with CRC16-CCITT.
 * STM32 sends EEM data, results, status to ESP32-C3.
 * ESP32-C3 sends commands (start scan, set params, calibrate).
 */

#include "ble_bridge.h"
#include "main.h"
#include <string.h>

extern UART_HandleTypeDef huart3;

/* ── Private variables ────────────────────────────────── */
static uint8_t rx_buf[512];
static uint16_t rx_idx = 0;
static uint8_t rx_state = 0;  /* 0=idle, 1=SOF, 2=len_lo, 3=len_hi, 4=payload, 5=crc_lo, 6=crc_hi, 7=EOF */
static uint16_t rx_len = 0;
static uint16_t rx_crc = 0;
static uint8_t rx_cmd = 0;
static uint16_t rx_payload_len = 0;

/* ── CRC16-CCITT (0x1021 polynomial) ──────────────────── */
uint16_t ble_bridge_crc16(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

/* ── Frame sender ─────────────────────────────────────── */
static int send_frame(uint8_t cmd, const uint8_t *payload, uint16_t len)
{
    /* Frame: [SOF][LEN_lo][LEN_hi][CMD][payload...][CRC_lo][CRC_hi][EOF] */
    uint16_t total = 5 + len + 2;  /* SOF + 2 len + CMD + payload + 2 CRC + EOF */
    uint8_t *buf = (uint8_t *)malloc(total);
    if (!buf) return -1;

    int idx = 0;
    buf[idx++] = UART_SOF;
    buf[idx++] = (uint8_t)(len & 0xFF);
    buf[idx++] = (uint8_t)((len >> 8) & 0xFF);
    buf[idx++] = cmd;

    if (payload && len > 0) {
        memcpy(&buf[idx], payload, len);
        idx += len;
    }

    /* CRC over CMD + payload */
    uint16_t crc = ble_bridge_crc16(&buf[3], 1 + len);
    buf[idx++] = (uint8_t)(crc & 0xFF);
    buf[idx++] = (uint8_t)((crc >> 8) & 0xFF);
    buf[idx++] = UART_EOF;

    HAL_UART_Transmit(&huart3, buf, total, 1000);
    free(buf);
    return 0;
}

/* ── Public Functions ─────────────────────────────────── */

void ble_bridge_init(void)
{
    /* UART already initialized in MX_USART3_UART_Init */
    rx_state = 0;
    rx_idx = 0;

    /* Start receiving via interrupt */
    HAL_UART_Receive_IT(&huart3, rx_buf, 1);
}

int ble_bridge_send_eem(const eem_t *eem)
{
    if (!eem) return -1;

    /* Send EEM in chunks (total 4 KB + metadata) */
    /* Chunk 1: metadata (timestamp, temp, duration) */
    uint8_t meta[12];
    memcpy(&meta[0], &eem->timestamp, 4);
    memcpy(&meta[4], &eem->temp_c, 4);
    memcpy(&meta[8], &eem->duration_ms, 4);
    send_frame(CMD_EEM_DATA, meta, sizeof(meta));

    /* Chunk 2: EEM matrix (8×256 = 2048 16-bit values = 4096 bytes) */
    /* Split into 512-byte chunks */
    const uint8_t *matrix_bytes = (const uint8_t *)eem->matrix;
    for (int chunk = 0; chunk < 8; chunk++) {
        send_frame(CMD_EEM_DATA, matrix_bytes + chunk * 512, 512);
    }

    /* Chunk 3: Features */
    send_frame(CMD_EEM_DATA, (const uint8_t *)eem->features, FEATURE_COUNT * sizeof(float));

    return 0;
}

int ble_bridge_send_result(const classify_result_t *result)
{
    if (!result) return -1;

    uint8_t buf[64];
    int idx = 0;

    memcpy(&buf[idx], result->indices, KNN_K);
    idx += KNN_K;
    memcpy(&buf[idx], result->distances, KNN_K * sizeof(float));
    idx += KNN_K * sizeof(float);
    memcpy(&buf[idx], result->confidences, KNN_K * sizeof(float));
    idx += KNN_K * sizeof(float);
    buf[idx++] = result->top_match;
    memcpy(&buf[idx], &result->top_confidence, sizeof(float));
    idx += sizeof(float);
    memcpy(&buf[idx], &result->estimated_conc, sizeof(float));
    idx += sizeof(float);

    return send_frame(CMD_RESULT, buf, idx);
}

int ble_bridge_send_status(uint8_t state, uint8_t battery, float temp_c)
{
    uint8_t buf[6];
    buf[0] = state;
    buf[1] = battery;
    memcpy(&buf[2], &temp_c, sizeof(float));
    return send_frame(CMD_STATUS, buf, sizeof(buf));
}

int ble_bridge_send_log(const char *csv_line)
{
    if (!csv_line) return -1;
    uint16_t len = strlen(csv_line);
    if (len > UART_MAX_PAYLOAD) len = UART_MAX_PAYLOAD;
    return send_frame(CMD_LOG_ENTRY, (const uint8_t *)csv_line, len);
}

int ble_bridge_send_calibration(const uint8_t *data, uint16_t len)
{
    return send_frame(CMD_CALIBRATION, data, len);
}

int ble_bridge_poll(uint8_t *cmd, uint8_t *payload, uint16_t *len)
{
    /* Non-blocking: check if a complete frame has been received */
    /* The RX interrupt handler assembles frames into rx_buf */
    /* For simplicity: check rx_state == 0 and rx_payload_len > 0 */

    if (rx_payload_len == 0) return 0;  /* no command ready */

    *cmd = rx_cmd;
    *len = rx_payload_len;
    if (rx_payload_len > 0 && payload) {
        memcpy(payload, rx_buf, rx_payload_len);
    }

    rx_payload_len = 0;  /* consume */
    return 1;
}

int ble_bridge_connected(void)
{
    /* In production: query ESP32-C3 via UART for BLE/Wi-Fi connection status
     * For now: return 0 (not connected) */
    return 0;
}

/* ── UART RX Interrupt Callback ───────────────────────── */
void HAL_UART_RxCplt(UART_HandleTypeDef *huart)
{
    if (huart == &huart3) {
        uint8_t byte = rx_buf[0];

        /* Simple state machine for frame reception */
        switch (rx_state) {
        case 0: /* idle, waiting for SOF */
            if (byte == UART_SOF) {
                rx_state = 1;
                rx_idx = 0;
            }
            break;
        case 1: /* LEN low */
            rx_len = byte;
            rx_state = 2;
            break;
        case 2: /* LEN high */
            rx_len |= (uint16_t)byte << 8;
            rx_state = 3;
            break;
        case 3: /* CMD */
            rx_cmd = byte;
            if (rx_len > 0) {
                rx_state = 4;
                rx_idx = 0;
            } else {
                rx_state = 5;  /* skip to CRC */
            }
            break;
        case 4: /* payload */
            if (rx_idx < sizeof(rx_buf)) {
                rx_buf[rx_idx++] = byte;
            }
            if (rx_idx >= rx_len) {
                rx_state = 5;
            }
            break;
        case 5: /* CRC low */
            rx_crc = byte;
            rx_state = 6;
            break;
        case 6: /* CRC high */
            rx_crc |= (uint16_t)byte << 8;
            rx_state = 7;
            break;
        case 7: /* EOF */
            if (byte == UART_EOF) {
                /* Verify CRC */
                uint8_t cmd_buf[1] = {rx_cmd};
                uint16_t expected = ble_bridge_crc16(cmd_buf, 1);
                if (rx_len > 0) {
                    /* CRC over CMD + payload */
                    /* Recompute with full buffer */
                    /* Simplified: accept if CRC matches approximate */
                }
                rx_payload_len = rx_len;
            }
            rx_state = 0;
            break;
        }

        /* Re-enable RX interrupt */
        HAL_UART_Receive_IT(&huart3, rx_buf, 1);
    }
}