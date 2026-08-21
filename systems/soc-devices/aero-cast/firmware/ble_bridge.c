/* ble_bridge.c — UART protocol to ESP32-C3 BLE/Wi-Fi bridge
 *
 * Binary packet protocol over UART at 1 Mbps:
 *
 * Packet format:
 *   [0xAA] [type] [len_lo] [len_hi] [payload...] [crc8]
 *
 * Types:
 *   0x01 = wind data (RP2040 → ESP32-C3 → phone)
 *   0x02 = status string
 *   0x03 = command (phone → ESP32-C3 → RP2040)
 *   0x04 = ack
 *   0x05 = raw TOF data
 *
 * The ESP32-C3 firmware (separate) handles BLE GATT and Wi-Fi socket
 * to relay these packets transparently.
 */

#include <string.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "ble_bridge.h"
#include "sdkconfig.h"

#define BLE_UART uart1
#define BLE_BAUD 1000000

/* CRC-8 (polynomial 0x07, init 0x00) */
static uint8_t crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0x00;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc = crc << 1;
        }
    }
    return crc;
}

static void send_packet(uint8_t type, const uint8_t *payload, uint8_t len)
{
    uint8_t header[4];
    header[0] = 0xAA;
    header[1] = type;
    header[2] = len & 0xFF;
    header[3] = (len >> 8) & 0xFF;

    uart_write_blocking(BLE_UART, header, 4);
    if (len > 0)
        uart_write_blocking(BLE_UART, payload, len);

    uint8_t crc = crc8(payload, len);
    /* CRC over header+payload for integrity */
    uint8_t crc_buf[5];
    crc_buf[0] = 0xAA; crc_buf[1] = type; crc_buf[2] = len & 0xFF;
    crc_buf[3] = (len >> 8) & 0xFF;
    crc_buf[4] = crc8(payload, len);
    uint8_t full_crc = crc8(crc_buf, 4);
    /* simplified: just append crc8 of payload */
    uart_write_blocking(BLE_UART, &crc, 1);
}

void ble_bridge_init(void)
{
    uart_init(BLE_UART, BLE_BAUD);
    uart_set_format(BLE_UART, 8, 1, UART_PARITY_NONE);
    gpio_set_function(PIN_UART_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_UART_RX, GPIO_FUNC_UART);

    /* Enable UART FIFO for efficient RX */
    uart_set_fifo_enabled(BLE_UART, true);

    printf("[ble] UART bridge initialized at %u baud\n", BLE_BAUD);
}

/* Wind data packet payload: 28 bytes
 * 0-3:   timestamp (uint32, µs, low 32 bits)
 * 4-7:   speed (float)
 * 8-11:  direction (float)
 * 12-15: u (float)
 * 16-19: v (float)
 * 20-23: w (float)
 * 24-27: t_sonic (float)
 */
void ble_send_wind(const wind_vector_t *wind, const bme280_data_t *atm, uint32_t timestamp)
{
    uint8_t payload[40];
    int pos = 0;

    memcpy(&payload[pos], &timestamp, 4); pos += 4;
    memcpy(&payload[pos], &wind->speed, 4); pos += 4;
    memcpy(&payload[pos], &wind->direction, 4); pos += 4;
    memcpy(&payload[pos], &wind->u, 4); pos += 4;
    memcpy(&payload[pos], &wind->v, 4); pos += 4;
    memcpy(&payload[pos], &wind->w, 4); pos += 4;
    memcpy(&payload[pos], &wind->t_sonic, 4); pos += 4;

    if (atm) {
        memcpy(&payload[pos], &atm->temperature, 4); pos += 4;
        memcpy(&payload[pos], &atm->pressure, 4); pos += 4;
        memcpy(&payload[pos], &atm->humidity, 4); pos += 4;
    } else {
        memset(&payload[pos], 0, 12); pos += 4;
    }

    send_packet(BLE_MSG_WIND, payload, pos);
}

/* Turbulence packet: 44 bytes */
void ble_send_turbulence(const turbulence_stats_t *stats, uint32_t elapsed_s)
{
    uint8_t payload[48];
    int pos = 0;
    memcpy(&payload[pos], &stats->u_mean, 4); pos += 4;
    memcpy(&payload[pos], &stats->v_mean, 4); pos += 4;
    memcpy(&payload[pos], &stats->w_mean, 4); pos += 4;
    memcpy(&payload[pos], &stats->sigma_u, 4); pos += 4;
    memcpy(&payload[pos], &stats->sigma_v, 4); pos += 4;
    memcpy(&payload[pos], &stats->sigma_w, 4); pos += 4;
    memcpy(&payload[pos], &stats->u_w_cov, 4); pos += 4;
    memcpy(&payload[pos], &stats->v_w_cov, 4); pos += 4;
    memcpy(&payload[pos], &stats->tke, 4); pos += 4;
    memcpy(&payload[pos], &stats->u_star, 4); pos += 4;
    memcpy(&payload[pos], &stats->turb_intensity, 4); pos += 4;
    memcpy(&payload[pos], &elapsed_s, 4); pos += 4;

    send_packet(BLE_MSG_STATUS, payload, pos);
}

void ble_send_status(const char *msg)
{
    uint8_t len = strlen(msg);
    if (len > 200) len = 200;
    send_packet(BLE_MSG_STATUS, (const uint8_t *)msg, len);
}

void ble_send_raw(const sonic_sample_t *sample)
{
    uint8_t payload[28];
    int pos = 0;
    for (int i = 0; i < NUM_PATHS; i++) {
        memcpy(&payload[pos], &sample->paths[i].t_forward_us, 4); pos += 4;
        memcpy(&payload[pos], &sample->paths[i].t_reverse_us, 4); pos += 4;
    }
    memcpy(&payload[pos], &sample->timestamp_us, 4); pos += 4;
    send_packet(BLE_MSG_RAW, payload, pos);
}

/* Poll for commands. Returns true if a complete command was received. */
bool ble_poll_command(uint8_t *cmd, uint8_t *arg, uint8_t *arg_len)
{
    /* Non-blocking read: look for 0xAA header */
    static enum { ST_SYNC, ST_TYPE, ST_LEN, ST_PAYLOAD, ST_CRC } state = ST_SYNC;
    static uint8_t rtype, rlen, rcv_len;
    static uint8_t rpayload[64];
    static int rpos = 0;

    while (uart_is_readable(BLE_UART)) {
        uint8_t byte = uart_getc(BLE_UART);

        switch (state) {
        case ST_SYNC:
            if (byte == 0xAA) state = ST_TYPE;
            break;
        case ST_TYPE:
            rtype = byte;
            state = ST_LEN;
            break;
        case ST_LEN:
            rcv_len = byte;
            rpos = 0;
            if (rcv_len == 0) {
                state = ST_CRC;
            } else {
                state = ST_PAYLOAD;
            }
            break;
        case ST_PAYLOAD:
            rpayload[rpos++] = byte;
            if (rpos >= rcv_len) state = ST_CRC;
            break;
        case ST_CRC: {
            uint8_t expected = crc8(rpayload, rcv_len);
            if (byte == expected) {
                *cmd = rtype;
                *arg_len = rcv_len;
                if (arg && rcv_len <= 64) memcpy(arg, rpayload, rcv_len);
                state = ST_SYNC;
                return true;
            }
            state = ST_SYNC;
            break;
        }
        }
    }
    return false;
}