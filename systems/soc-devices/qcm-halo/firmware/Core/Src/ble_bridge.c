/*
 * ble_bridge.c — UART protocol to ESP32-C3 for BLE + Wi-Fi streaming
 *
 * Protocol: simple binary frames with CRC
 *   [SYNC0][SYNC1][CMD][LEN][DATA...][CRC8]
 *
 * Commands from STM32 → ESP32-C3:
 *   0x01 RESULT  — QCM result packet (for BLE GATT notify)
 *   0x02 SWEEP   — overtone sweep data
 *   0x03 VOIGT   — Voigt fit results
 *   0x04 STATUS  — device status (temp, battery, state)
 *   0x05 RAW     — raw text line
 *   0x06 QUERY   — query BLE connection status
 *
 * Commands from ESP32-C3 → STM32:
 *   0x81 START   — start measurement
 *   0x82 STOP    — stop
 *   0x83 SET_CH  — set channel
 *   0x84 SET_OV  — set overtone
 *   0x85 SET_TMP — set temperature
 *   0x86 SET_PMP — set pump rate
 *   0x87 SET_VLV — set valve position
 *   0x88 CALIB   — calibrate
 *   0x89 EXP     — start experiment
 *   0x8A GETSTAT — get status
 *   0x8B SETPARM — set all params
 *   0x8C CONN    — BLE connection status reply
 */

#include "main.h"
#include <string.h>
#include <stdio.h>
#include "ble_bridge.h"
#include "overtone.h"

extern UART_HandleTypeDef huart2;

#define SYNC0 0xA5
#define SYNC1 0x5A

/* RX buffer */
#define RX_BUF_SIZE 256
static uint8_t rx_buf[RX_BUF_SIZE];
static uint16_t rx_idx = 0;
static uint8_t ble_connected = 0;

/* TX buffer */
static uint8_t tx_buf[BLE_MAX_PAYLOAD + 10];

/* CRC-8 (poly 0x07, init 0x00) */
static uint8_t crc8(const uint8_t *data, uint16_t len)
{
    uint8_t crc = 0;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* Send a framed message to ESP32-C3 */
static void ble_send(uint8_t cmd, const uint8_t *data, uint16_t len)
{
    if (len > BLE_MAX_PAYLOAD) len = BLE_MAX_PAYLOAD;

    tx_buf[0] = SYNC0;
    tx_buf[1] = SYNC1;
    tx_buf[2] = cmd;
    tx_buf[3] = (uint8_t)len;
    if (data && len > 0)
        memcpy(&tx_buf[4], data, len);
    tx_buf[4 + len] = crc8(&tx_buf[2], 2 + len);

    HAL_UART_Transmit(&huart2, tx_buf, 5 + len, 200);
}

void ble_bridge_init(void)
{
    /* Enable UART RX via interrupt */
    HAL_UART_Receive_IT(&huart2, &rx_buf[rx_idx], 1);
}

uint8_t ble_service_is_connected(void)
{
    /* Query ESP32-C3 for connection status */
    ble_send(0x06, NULL, 0);
    return ble_connected;
}

/* Pack a qcm_result_t into a compact binary packet */
void ble_send_result(const qcm_result_t *r)
{
    /* Pack: channel(1) + overtone_n(1) + delta_f(4 float) + dissipation(4) +
     *       delta_d(4) + temp(4) + sauerbrey_mass(4) + timestamp(4) = 26 bytes
     */
    uint8_t pkt[26];
    uint16_t idx = 0;
    pkt[idx++] = r->channel;
    pkt[idx++] = r->overtone_n;
    memcpy(&pkt[idx], &r->delta_f, 4); idx += 4;
    memcpy(&pkt[idx], &r->dissipation, 4); idx += 4;
    memcpy(&pkt[idx], &r->delta_d, 4); idx += 4;
    memcpy(&pkt[idx], &r->temperature, 4); idx += 4;
    memcpy(&pkt[idx], &r->sauerbrey_mass, 4); idx += 4;
    uint32_t ts = r->timestamp_ms;
    memcpy(&pkt[idx], &ts, 4); idx += 4;

    ble_send(0x01, pkt, idx);
}

void ble_send_sweep(const overtone_sweep_t *s)
{
    /* Pack 6 overtones: 6 × (delta_f + delta_d) + temp + timestamp = 56 bytes */
    uint8_t pkt[56];
    uint16_t idx = 0;
    for (uint8_t i = 0; i < QCM_OVERtones; i++) {
        memcpy(&pkt[idx], &s->delta_f[i], 4); idx += 4;
        memcpy(&pkt[idx], &s->delta_d[i], 4); idx += 4;
    }
    memcpy(&pkt[idx], &s->temperature, 4); idx += 4;
    uint32_t ts = s->timestamp;
    memcpy(&pkt[idx], &ts, 4); idx += 4;

    ble_send(0x02, pkt, idx);
}

void ble_send_voigt(const voigt_params_t *v)
{
    uint8_t pkt[20];
    uint16_t idx = 0;
    memcpy(&pkt[idx], &v->thickness_nm, 4); idx += 4;
    memcpy(&pkt[idx], &v->viscosity_pa_s, 4); idx += 4;
    memcpy(&pkt[idx], &v->shear_mod_pa, 4); idx += 4;
    pkt[idx++] = v->converged;
    pkt[idx++] = v->iterations;
    uint32_t res = (uint32_t)v->residual;
    memcpy(&pkt[idx], &res, 4); idx += 4;

    ble_send(0x03, pkt, idx);
}

void ble_send_status(float temp, float vbat, const char *state)
{
    uint8_t pkt[12];
    uint16_t idx = 0;
    memcpy(&pkt[idx], &temp, 4); idx += 4;
    memcpy(&pkt[idx], &vbat, 4); idx += 4;
    uint8_t state_len = strlen(state);
    if (state_len > 4) state_len = 4;
    pkt[idx++] = state_len;
    memcpy(&pkt[idx], state, state_len); idx += state_len;

    ble_send(0x04, pkt, idx);
}

void ble_send_raw(const char *data, uint16_t len)
{
    ble_send(0x05, (const uint8_t *)data, len);
}

/* Parse an incoming command frame from ESP32-C3 */
static ble_cmd_t parse_frame(uint8_t cmd, const uint8_t *data, uint16_t len,
                             acq_params_t *params)
{
    switch (cmd) {
    case 0x81: /* START */
        if (params && len >= 1) {
            params->channel = data[0] & 1;
            if (len >= 2) params->overtone = data[1] % QCM_OVERtones;
            if (len >= 3) params->run_overtone_sweep = data[2] & 1;
        }
        return BLE_CMD_START_MEASURE;
    case 0x82:
        return BLE_CMD_STOP;
    case 0x83:
        if (params && len >= 1) params->channel = data[0] & 1;
        return BLE_CMD_SET_CHANNEL;
    case 0x84:
        if (params && len >= 1) params->overtone = data[0] % QCM_OVERtones;
        return BLE_CMD_SET_OVERTONE;
    case 0x85:
        if (params && len >= 4) {
            float t;
            memcpy(&t, data, 4);
            params->target_temp = t;
        }
        return BLE_CMD_SET_TEMP;
    case 0x86:
        if (params && len >= 4) {
            float r;
            memcpy(&r, data, 4);
            params->pump_rate = r;
        }
        return BLE_CMD_SET_PUMP;
    case 0x87:
        if (params && len >= 1) params->valve_pos = data[0] % 6;
        return BLE_CMD_SET_VALVE;
    case 0x88:
        return BLE_CMD_CALIBRATE;
    case 0x89:
        if (params && len >= 4) {
            uint32_t dur;
            memcpy(&dur, data, 4);
            params->duration_s = dur;
        }
        return BLE_CMD_START_EXPERIMENT;
    case 0x8A:
        return BLE_CMD_GET_STATUS;
    case 0x8B:
        if (params && len >= sizeof(acq_params_t)) {
            memcpy(params, data, sizeof(acq_params_t));
        }
        return BLE_CMD_SET_PARAMS;
    case 0x8C: /* BLE connection status */
        if (len >= 1) ble_connected = data[0];
        return BLE_CMD_NONE;
    default:
        return BLE_CMD_NONE;
    }
}

ble_cmd_t ble_get_command(acq_params_t *params)
{
    /* Check if we have a complete frame in the buffer.
     * Frame: [SYNC0][SYNC1][CMD][LEN][DATA...][CRC8]
     */
    if (rx_idx < 5) return BLE_CMD_NONE;

    /* Find sync bytes */
    uint16_t i = 0;
    while (i < rx_idx - 1) {
        if (rx_buf[i] == SYNC0 && rx_buf[i+1] == SYNC1) break;
        i++;
    }
    if (i >= rx_idx - 1) {
        /* Shift buffer to remove garbage */
        rx_buf[0] = rx_buf[rx_idx - 1];
        rx_idx = 1;
        return BLE_CMD_NONE;
    }

    uint8_t cmd = rx_buf[i + 2];
    uint8_t data_len = rx_buf[i + 3];
    uint16_t frame_len = 5 + data_len;

    if (i + frame_len > rx_idx) return BLE_CMD_NONE; /* incomplete */

    /* Verify CRC */
    uint8_t expected_crc = crc8(&rx_buf[i + 2], 2 + data_len);
    if (rx_buf[i + 4 + data_len] != expected_crc) {
        /* Bad CRC — shift past sync */
        i += 2;
        memmove(rx_buf, &rx_buf[i], rx_idx - i);
        rx_idx -= i;
        return BLE_CMD_NONE;
    }

    /* Parse frame */
    ble_cmd_t result = parse_frame(cmd, &rx_buf[i + 4], data_len, params);

    /* Remove processed frame */
    uint16_t remaining = rx_idx - (i + frame_len);
    if (remaining > 0) {
        memmove(rx_buf, &rx_buf[i + frame_len], remaining);
    }
    rx_idx = remaining;

    return result;
}

void ble_poll_commands(acq_params_t *params)
{
    ble_cmd_t cmd;
    while ((cmd = ble_get_command(params)) != BLE_CMD_NONE) {
        /* Handle in caller — for simplicity, just break after first */
        (void)cmd;
        break;
    }
}

/* UART RX callback — called on each byte received */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart2) {
        rx_idx++;
        if (rx_idx >= RX_BUF_SIZE) {
            /* Buffer overflow — reset */
            rx_idx = 0;
        }
        HAL_UART_Receive_IT(&huart2, &rx_buf[rx_idx], 1);
    }
}