/**
 * spiro_flow/ble_bridge.c — UART protocol bridge to ESP32-C3 for BLE/WiFi
 *
 * The CH32V203 handles real-time spirometry, then sends results to an
 * ESP32-C3 module over USART1 (115200 baud). The ESP32-C3 runs a simple
 * BLE GATT server + WiFi client that relays data to a phone app or
 * cloud EHR system.
 *
 * Protocol format (binary frames):
 *   [SYNC1][SYNC2][TYPE][LEN_LO][LEN_HI][PAYLOAD...][CRC8]
 *
 * Frame types:
 *   0x01 — RESULT (spirometry results struct, packed)
 *   0x02 — FLOW_DATA (maneuver buffer, compressed: flow samples at 250Hz)
 *   0x03 — AMBIENT (BME280 readings)
 *   0x04 — PATIENT (patient profile)
 *   0x05 — DEVICE_INFO (firmware version, battery, session count)
 *   0x06 — TIME_SYNC (NTP time from ESP32-C3 → CH32V203)
 *
 * The ESP32-C3 firmware is a separate component (see firmware/esp32_c3_bridge/)
 */

#include "main.h"
#include "ble_bridge.h"
#include <string.h>

#define TAG "BLE"

#define SYNC1  0xAA
#define SYNC2  0x55

#define FRAME_RESULT     0x01
#define FRAME_FLOW_DATA  0x02
#define FRAME_AMBIENT    0x03
#define FRAME_PATIENT    0x04
#define FRAME_DEVICE_INFO 0x05
#define FRAME_TIME_SYNC  0x06

/* ── UART helpers (CH32V203 HAL) ───────────────────────────────────── */

static void uart1_send_byte(uint8_t b)
{
    /* CH32V203 HAL:
     * USART_SendData(USART1, b);
     * while(USART_GetFlagStatus(USART1, USART_FLAG_TXE) == RESET);
     */
    (void)b;
}

static void uart1_send(const uint8_t *data, int len)
{
    for (int i = 0; i < len; i++)
        uart1_send_byte(data[i]);
}

static int uart1_rx_available(void)
{
    /* CH32V203 HAL:
     * return USART_GetFlagStatus(USART1, USART_FLAG_RXNE) ? 1 : 0;
     */
    return 0;
}

static uint8_t uart1_read_byte(void)
{
    /* return USART_ReceiveData(USART1); */
    return 0;
}

/* ── CRC-8 (0x07 polynomial) ───────────────────────────────────────── */

static uint8_t crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* ── Frame sender ──────────────────────────────────────────────────── */

static void send_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    uint8_t header[5] = {SYNC1, SYNC2, type, (uint8_t)(len & 0xFF), (uint8_t)(len >> 8)};
    uart1_send(header, 5);
    if (len > 0 && payload)
        uart1_send(payload, len);
    uint8_t crc = crc8(header + 2, 3);  /* CRC over type+len */
    if (len > 0 && payload)
        crc ^= crc8(payload, len);
    uart1_send_byte(crc);
}

/* ── Packed result structure for transmission ──────────────────────── */

/* Pack spiro_result_t into a compact binary format for BLE transfer */
#pragma pack(push, 1)
typedef struct {
    float    fvc_liters;
    float    fev1_liters;
    float    fev1_fvc_ratio;
    float    pef_lps;
    float    fef2575_lps;
    float    fet_sec;
    float    back_extrap_ml;
    float    fev1_pred;
    float    fvc_pred;
    float    fev1_pct_pred;
    float    fvc_pct_pred;
    uint8_t  grade;
    uint8_t  pattern;
    uint16_t session_id;
    uint8_t  maneuver_count;
    float    btps_factor;
    float    ambient_temp;
    float    ambient_pressure;
} packed_result_t;
#pragma pack(pop)

/* ── Public API ────────────────────────────────────────────────────── */

int ble_bridge_init(void)
{
    /* USART1 init: 115200 baud, 8N1
     * CH32V203 HAL:
     *   USART_InitTypeDef usart;
     *   usart.USART_BaudRate = 115200;
     *   usart.USART_WordLength = USART_WordLength_8b;
     *   usart.USART_StopBits = USART_StopBits_1;
     *   usart.USART_Parity = USART_Parity_No;
     *   usart.USART_Mode = USART_Mode_Tx | USART_Mode_Rx;
     *   USART_Init(USART1, &usart);
     *   USART_Cmd(USART1, ENABLE);
     */
    ESP_LOGI(TAG, "BLE bridge UART initialized (USART1 @ 115200)");
    return 0;
}

void ble_bridge_send_result(const spiro_result_t *r)
{
    packed_result_t packed;
    memset(&packed, 0, sizeof(packed));

    packed.fvc_liters       = r->fvc_liters;
    packed.fev1_liters      = r->fev1_liters;
    packed.fev1_fvc_ratio   = r->fev1_fvc_ratio;
    packed.pef_lps          = r->pef_lps;
    packed.fef2575_lps     = r->fef2575_lps;
    packed.fet_sec          = r->fet_sec;
    packed.back_extrap_ml   = r->back_extrap_ml;
    packed.fev1_pred        = r->fev1_pred;
    packed.fvc_pred         = r->fvc_pred;
    packed.fev1_pct_pred    = r->fev1_pct_pred;
    packed.fvc_pct_pred     = r->fvc_pct_pred;
    packed.grade            = (uint8_t)r->grade;
    packed.pattern          = r->pattern;
    packed.session_id       = r->session_id;
    packed.maneuver_count   = r->maneuver_count;
    packed.btps_factor      = r->btps_factor;
    packed.ambient_temp     = r->ambient_temp_c;
    packed.ambient_pressure = r->ambient_pressure_mmhg;

    send_frame(FRAME_RESULT, (uint8_t *)&packed, sizeof(packed));
    ESP_LOGI(TAG, "Sent RESULT frame (%d bytes)", (int)sizeof(packed));
}

void ble_bridge_send_flow_data(const maneuver_buffer_t *m)
{
    /* Send flow data in chunks (each frame max ~200 bytes payload)
     * Flow samples are float (4 bytes) → 200/4 = 50 samples per frame
     * For 2000 samples → 40 frames
     * In production, would compress (delta encoding or int16 quantization)
     */
    int chunk_samples = 50;
    int offset = 0;

    while (offset < m->n_samples) {
        int n = m->n_samples - offset;
        if (n > chunk_samples) n = chunk_samples;

        /* Pack: [offset_lo][offset_hi][count][float flow[0..n-1]] */
        uint8_t buf[200];
        buf[0] = (uint8_t)(offset & 0xFF);
        buf[1] = (uint8_t)(offset >> 8);
        buf[2] = (uint8_t)n;
        memcpy(&buf[3], &m->flow_lps[offset], n * sizeof(float));

        send_frame(FRAME_FLOW_DATA, buf, 3 + n * sizeof(float));
        offset += n;
    }
}

void ble_bridge_poll(void)
{
    /* Check for incoming frames from ESP32-C3 (e.g., time sync, commands) */
    static uint8_t rx_buf[256];
    static int rx_len = 0;
    static bool in_frame = false;
    static uint8_t frame_type = 0;
    static uint16_t frame_len = 0;
    static int payload_count = 0;

    while (uart1_rx_available()) {
        uint8_t b = uart1_read_byte();

        if (!in_frame) {
            /* Looking for sync bytes */
            if (rx_len == 0 && b == SYNC1) {
                rx_buf[rx_len++] = b;
            } else if (rx_len == 1 && b == SYNC2) {
                rx_buf[rx_len++] = b;
            } else if (rx_len == 2) {
                frame_type = b;
                rx_buf[rx_len++] = b;
            } else if (rx_len == 3) {
                frame_len = b;
                rx_buf[rx_len++] = b;
            } else if (rx_len == 4) {
                frame_len |= (b << 8);
                rx_buf[rx_len++] = b;
                in_frame = true;
                payload_count = 0;
            } else {
                rx_len = 0;
            }
        } else {
            /* Receiving payload */
            if (payload_count < frame_len) {
                rx_buf[rx_len++] = b;
                payload_count++;
            } else {
                /* CRC byte */
                in_frame = false;
                rx_len = 0;

                /* Process frame based on type */
                if (frame_type == FRAME_TIME_SYNC) {
                    /* ESP32-C3 sends NTP-synced time */
                    if (frame_len >= 4) {
                        uint32_t epoch = 0;
                        /* would extract epoch from payload */
                        (void)epoch;
                        ESP_LOGI(TAG, "Received time sync from ESP32-C3");
                    }
                }
            }
        }
    }
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif