/*
 * ble_bridge.c — UART binary protocol bridge to ESP32-C3
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Implements a simple framed binary protocol over UART2 at 1 Mbps
 * between the STM32G491 and the ESP32-C3 companion module. The ESP32-C3
 * relays commands and results over BLE 5.0 and Wi-Fi.
 *
 * Frame format:
 *   [SYNC 0xA5] [VERSION] [LEN_LO] [LEN_HI] [CMD] [PAYLOAD...] [CHECKSUM]
 *   CHECKSUM = XOR of all bytes from VERSION through last PAYLOAD byte
 */
#include "stm32g4xx_hal.h"
#include <string.h>
#include "sdkconfig.h"
#include "ble_bridge.h"

extern UART_HandleTypeDef huart2;

static uint8_t rx_buffer[BLE_UART_BUFFER_SIZE];
static uint8_t rx_index = 0;
static uint8_t rx_state = 0;  /* 0=idle, 1=got_sync, 2=got_ver, 3=got_len_lo, 4=got_len_hi, 5=got_cmd, 6=payload */

/* External function declarations for command handling */
extern void polarimeter_auto_zero(void);
extern void polarimeter_set_wavelength(double nm);

static uint8_t checksum_calc(const uint8_t *data, int len)
{
    uint8_t cs = 0;
    for (int i = 0; i < len; i++)
        cs ^= data[i];
    return cs;
}

static void send_frame(uint8_t cmd, const uint8_t *payload, uint16_t len)
{
    uint8_t header[5];
    header[0] = BLE_FRAME_SYNC_BYTE;
    header[1] = BLE_FRAME_VERSION;
    header[2] = (uint8_t)(len & 0xFF);
    header[3] = (uint8_t)(len >> 8);
    header[4] = cmd;

    /* Compute checksum over version, len, cmd, payload */
    uint8_t cs = BLE_FRAME_VERSION;
    cs ^= header[2]; cs ^= header[3]; cs ^= cmd;
    for (int i = 0; i < len; i++)
        cs ^= payload[i];

    HAL_UART_Transmit(&huart2, header, 5, HAL_MAX_DELAY);
    if (len > 0)
        HAL_UART_Transmit(&huart2, (uint8_t *)payload, len, HAL_MAX_DELAY);
    HAL_UART_Transmit(&huart2, &cs, 1, HAL_MAX_DELAY);
}

void ble_bridge_init(void)
{
    rx_index = 0;
    rx_state = 0;
    /* Enable UART RX interrupt (in production: HAL_UART_Receive_IT) */
}

void ble_bridge_poll(void)
{
    /* In production, use HAL_UART_Receive_IT in interrupt mode and
     * process complete frames here. For simplicity, we poll the
     * UART RX flag. This is a simplified blocking check. */

    uint8_t byte;
    /* Check if data available (simplified — real implementation uses IRQ) */
    if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_RXNE)) {
        byte = (uint8_t)(huart2.Instance->RDR & 0xFF);

        switch (rx_state) {
        case 0: /* idle, waiting for sync */
            if (byte == BLE_FRAME_SYNC_BYTE)
                rx_state = 1;
            break;
        case 1: /* version */
            if (byte == BLE_FRAME_VERSION)
                rx_state = 2;
            else
                rx_state = 0;
            break;
        case 2: /* len low */
            rx_index = 0;
            rx_state = 3;
            break;
        case 3: /* len high — not used for small payloads */
            rx_state = 4;
            break;
        case 4: /* cmd */
            rx_state = 5;
            break;
        case 5: /* payload or end */
            /* Process command (simplified) */
            rx_state = 0;
            break;
        }
    }
}

void ble_bridge_send_result(const polarimeter_result_t *result,
                             double rotation, double concentration,
                             const char *compound, double confidence)
{
    /* Pack result into a binary payload:
     * [angle: float32] [rotation: float32] [concentration: float32]
     * [confidence: float32] [wavelength: float32] [temp: float32]
     * [compound: 24 bytes]
     * Total = 6*4 + 24 = 48 bytes
     */
    uint8_t payload[48];
    memset(payload, 0, sizeof(payload));

    /* Simple memcpy packing (little-endian, both STM32 and ESP32-C3 are LE) */
    memcpy(&payload[0],  &result->angle_deg, 4);
    memcpy(&payload[4],  &rotation, 4);
    memcpy(&payload[8],  &concentration, 4);
    memcpy(&payload[12], &confidence, 4);
    memcpy(&payload[16], &result->wavelength_nm, 4);
    memcpy(&payload[20], &result->temperature_c, 4);
    if (compound)
        strncpy((char *)&payload[24], compound, 24);

    send_frame(CMD_RESULT_SINGLE, payload, 48);
}

void ble_bridge_send_multi(const polarimeter_result_t results[3],
                            const double rotations[3],
                            const drude_result_t *drude,
                            const library_match_t *match)
{
    /* Pack 3-wavelength result + Drude + match:
     * [rot_405: f32] [rot_520: f32] [rot_589: f32]
     * [K: f32] [lambda0: f32] [drude_residual: f32]
     * [match_index: u8] [match_confidence: f32] [match_distance: f32]
     * [match_name: 24 bytes]
     * Total = 7*4 + 1 + 2*4 + 24 = 61 bytes
     */
    uint8_t payload[61];
    memset(payload, 0, sizeof(payload));

    memcpy(&payload[0],  &rotations[0], 4);
    memcpy(&payload[4],  &rotations[1], 4);
    memcpy(&payload[8],  &rotations[2], 4);
    memcpy(&payload[12], &drude->K, 4);
    memcpy(&payload[16], &drude->lambda0_nm, 4);
    memcpy(&payload[20], &drude->residual, 4);
    payload[24] = (uint8_t)match->best_index;
    memcpy(&payload[25], &match->confidence, 4);
    memcpy(&payload[29], &match->distance, 4);
    if (match->best_index >= 0) {
        const library_entry_t *e = library_get(match->best_index);
        if (e)
            strncpy((char *)&payload[33], e->name, 24);
    }

    send_frame(CMD_RESULT_MULTI, payload, 61);
}

void ble_bridge_send_status(const char *status)
{
    uint8_t len = (uint8_t)strlen(status);
    if (len > 32) len = 32;
    send_frame(CMD_STATUS, (const uint8_t *)status, len);
}