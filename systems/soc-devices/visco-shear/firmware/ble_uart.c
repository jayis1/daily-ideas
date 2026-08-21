/*
 * visco-shear / firmware / ble_uart.c
 * UART bridge to ESP32-C3 for BLE + Wi-Fi communication
 *
 * Protocol: binary frames over UART at 1 Mbaud.
 * Frame: [0xAA][0x55][cmd][len_lo][len_hi][payload...][crc8]
 *
 * ESP32-C3 relays data to BLE GATT characteristics + Wi-Fi web UI.
 *
 * MIT License.
 */
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "main.h"
#include "ble_uart.h"
#include "spindle.h"

#define UART_ID        uart0
#define FRAME_SYNC0    0xAA
#define FRAME_SYNC1    0x55
#define MAX_PAYLOAD    256

static cmd_callback_t cmd_cb = NULL;

static uint8_t crc8(const uint8_t *data, int len)
{
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

static void send_frame(uint8_t cmd, const uint8_t *payload, int len)
{
    uint8_t hdr[5] = { FRAME_SYNC0, FRAME_SYNC1, cmd, len & 0xFF, (len >> 8) & 0xFF };
    uart_write_blocking(UART_ID, hdr, 5);
    if (len > 0 && payload)
        uart_write_blocking(UART_ID, payload, len);
    uint8_t crc = crc8(hdr + 2, 3);
    if (len > 0 && payload)
        crc = crc8(payload, len) ^ crc;  /* Combined CRC */
    uint8_t crc_buf[1] = { crc };
    uart_write_blocking(UART_ID, crc_buf, 1);
}

void ble_uart_init(cmd_callback_t cb)
{
    cmd_cb = cb;
    printf("[BLE] UART bridge initialized at %d baud\n", UART_BAUD);
}

void ble_uart_poll(void)
{
    static enum { S_SYNC0, S_SYNC1, S_CMD, S_LEN_LO, S_LEN_HI, S_PAYLOAD, S_CRC } state = S_SYNC0;
    static uint8_t cmd, len_lo, len_hi, crc_recv;
    static int payload_len, payload_idx;
    static uint8_t payload_buf[MAX_PAYLOAD];

    while (uart_is_readable(UART_ID)) {
        uint8_t byte = uart_getc(UART_ID);
        switch (state) {
        case S_SYNC0:
            if (byte == FRAME_SYNC0) state = S_SYNC1;
            break;
        case S_SYNC1:
            if (byte == FRAME_SYNC1) state = S_CMD;
            else state = S_SYNC0;
            break;
        case S_CMD:
            cmd = byte; state = S_LEN_LO;
            break;
        case S_LEN_LO:
            len_lo = byte; state = S_LEN_HI;
            break;
        case S_LEN_HI:
            len_hi = byte;
            payload_len = (len_hi << 8) | len_lo;
            payload_idx = 0;
            if (payload_len == 0) state = S_CRC;
            else if (payload_len > MAX_PAYLOAD) state = S_SYNC0;
            else state = S_PAYLOAD;
            break;
        case S_PAYLOAD:
            payload_buf[payload_idx++] = byte;
            if (payload_idx >= payload_len) state = S_CRC;
            break;
        case S_CRC:
            crc_recv = byte;
            /* Verify CRC (simplified) */
            if (cmd_cb) {
                cmd_cb(cmd, payload_buf, payload_len);
            }
            state = S_SYNC0;
            break;
        }
    }
}

void ble_uart_send_torque_sample(uint16_t ts, int16_t torque, int16_t omega)
{
    uint8_t buf[6];
    buf[0] = ts & 0xFF;
    buf[1] = (ts >> 8) & 0xFF;
    buf[2] = torque & 0xFF;
    buf[3] = (torque >> 8) & 0xFF;
    buf[4] = omega & 0xFF;
    buf[5] = (omega >> 8) & 0xFF;
    send_frame(0x10, buf, 6);
}

void ble_uart_send_result(const measure_result_t *res)
{
    /* Send a compact summary: best model + params + average viscosity */
    uint8_t buf[32];
    int idx = 0;

    /* Best model index */
    buf[idx++] = (uint8_t)res->best_fit.model;

    /* R² (float, 4 bytes) */
    memcpy(&buf[idx], &res->best_fit.r_squared, 4); idx += 4;

    /* Average viscosity (float) */
    float eta_avg = 0;
    if (res->n_points > 0) {
        for (int i = 0; i < res->n_points; i++) eta_avg += res->viscosity[i];
        eta_avg /= res->n_points;
    }
    memcpy(&buf[idx], &eta_avg, 4); idx += 4;

    /* Temperature (float) */
    memcpy(&buf[idx], &res->temperature, 4); idx += 4;

    /* Number of points */
    buf[idx++] = (uint8_t)res->n_points;

    /* Model params (4 floats = 16 bytes) */
    memcpy(&buf[idx], res->best_fit.param, 16); idx += 16;

    send_frame(0x11, buf, idx);
    printf("[BLE] Result sent: model=%d, eta_avg=%.1f mPa·s\n",
           res->best_fit.model, eta_avg);
}

void ble_uart_send_info(const char *version, spindle_type_t sp, float temp)
{
    uint8_t buf[48];
    int idx = 0;

    /* Version string (null-terminated, max 24 bytes) */
    int vlen = strlen(version);
    if (vlen > 23) vlen = 23;
    memcpy(&buf[idx], version, vlen); idx += vlen;
    buf[idx++] = 0;

    /* Spindle type */
    buf[idx++] = (uint8_t)sp;

    /* Temperature */
    memcpy(&buf[idx], &temp, 4); idx += 4;

    send_frame(0x12, buf, idx);
}