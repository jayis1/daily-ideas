/*
 * dent-scope / Core/Src/esp32_link.c
 * Dent Scope — UART protocol to ESP32-C3 for BLE/Wi-Fi streaming
 *
 * Protocol: simple binary frames
 *   Frame: [0xAA][0x55][type][len_lo][len_hi][payload...][crc_lo][crc_hi]
 *   type 0x01: data point (force_mN:float, depth_um:float, t_ms:u32)
 *   type 0x02: result (HV:float, E:float, eta:float, Pmax:float, material:i8)
 *   type 0x03: status (state:u8, force:float, depth:float, tilt:float)
 *
 * MIT License.
 */
#include "esp32_link.h"

#define FRAME_SYNC1 0xAA
#define FRAME_SYNC2 0x55

static uint8_t tx_buf[256];
static uint8_t rx_buf[64];
static uint8_t rx_idx = 0;

static uint16_t crc16(const uint8_t *data, int len)
{
    uint16_t crc = 0xFFFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1) crc = (crc >> 1) ^ 0xA001;
            else crc >>= 1;
        }
    }
    return crc;
}

static void send_frame(uint8_t type, const uint8_t *payload, int len)
{
    int p = 0;
    tx_buf[p++] = FRAME_SYNC1;
    tx_buf[p++] = FRAME_SYNC2;
    tx_buf[p++] = type;
    tx_buf[p++] = (uint8_t)(len & 0xFF);
    tx_buf[p++] = (uint8_t)(len >> 8);
    memcpy(&tx_buf[p], payload, len); p += len;
    uint16_t crc = crc16(tx_buf, p);
    tx_buf[p++] = (uint8_t)(crc & 0xFF);
    tx_buf[p++] = (uint8_t)(crc >> 8);
    HAL_UART_Transmit(&huart1, tx_buf, p, 100);
}

void esp32_link_init(void)
{
    /* reset ESP32-C3 */
    HAL_GPIO_WritePin(ESP_RST_PORT, ESP_RST_PIN, GPIO_PIN_RESET);
    HAL_Delay(10);
    HAL_GPIO_WritePin(ESP_RST_PORT, ESP_RST_PIN, GPIO_PIN_SET);
    HAL_Delay(500);
    rx_idx = 0;
}

void esp32_link_poll(void)
{
    /* poll UART RX (simplified: check for incoming commands from phone app) */
    uint8_t byte;
    if (HAL_UART_Receive(&huart1, &byte, 1, 1) == HAL_OK) {
        if (rx_idx < sizeof(rx_buf))
            rx_buf[rx_idx++] = byte;
        if (rx_idx >= 4 && rx_buf[0] == FRAME_SYNC1 && rx_buf[1] == FRAME_SYNC2) {
            uint8_t type = rx_buf[2];
            uint16_t len = rx_buf[3] | (rx_buf[4] << 8);
            if (rx_idx >= len + 6) {
                /* handle command (type): */
                /* 0x10 = START, 0x11 = STOP, 0x12 = SET_PARAMS */
                if (type == 0x10) {
                    /* simulate START button */
                    HAL_GPIO_WritePin(BTN_START_PORT, BTN_START_PIN, GPIO_PIN_RESET);
                    HAL_Delay(10);
                    HAL_GPIO_WritePin(BTN_START_PORT, BTN_START_PIN, GPIO_PIN_SET);
                } else if (type == 0x11) {
                    HAL_GPIO_WritePin(BTN_STOP_PORT, BTN_STOP_PIN, GPIO_PIN_RESET);
                    HAL_Delay(10);
                    HAL_GPIO_WritePin(BTN_STOP_PORT, BTN_STOP_PIN, GPIO_PIN_SET);
                }
                rx_idx = 0;
            }
        } else if (rx_idx > 0 && rx_buf[0] != FRAME_SYNC1) {
            rx_idx = 0;
        }
    }
}

void esp32_send_point(float force_mN, float depth_um, uint32_t t_ms)
{
    uint8_t payload[12];
    memcpy(&payload[0], &force_mN, 4);
    memcpy(&payload[4], &depth_um, 4);
    memcpy(&payload[8], &t_ms, 4);
    send_frame(0x01, payload, 12);
}

void esp32_send_result(ds_status_t *st)
{
    uint8_t payload[21];
    memcpy(&payload[0],  &st->hardness_HV, 4);
    memcpy(&payload[4],  &st->modulus_E_GPa, 4);
    memcpy(&payload[8],  &st->elastic_ratio, 4);
    memcpy(&payload[12], &st->peak_force_mN, 4);
    memcpy(&payload[16], &st->peak_depth_um, 4);
    payload[20] = (uint8_t)st->matched_material;
    send_frame(0x02, payload, 21);
}