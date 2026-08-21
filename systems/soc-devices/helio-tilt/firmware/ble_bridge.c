/*
 * ble_bridge.c — UART protocol to ESP32-C3 BLE bridge
 *
 * UART1 (PA9=TX, PA10=RX) at 921600 baud.
 * Binary packet format:
 *   [START 0xAA] [TYPE] [LEN_H] [LEN_L] [PAYLOAD...] [CRC8]
 *
 * Packet types:
 *   0x01 — Measurement (DNI + AOD + PWV + Angstrom)
 *   0x02 — Langley progress
 *   0x03 — Error
 *   0x04 — Status (state, sun position, battery, GPS fix)
 */

#include "ble_bridge.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>
#include <stdio.h>

#define PKT_START   0xAA
#define PKT_MEAS    0x01
#define PKT_LANGLEY 0x02
#define PKT_ERROR   0x03
#define PKT_STATUS  0x04

static uint8_t crc8(const uint8_t *data, uint16_t len)
{
    uint8_t crc = 0;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (uint8_t)((crc << 1) ^ 0x07);
            else
                crc = (uint8_t)(crc << 1);
        }
    }
    return crc;
}

static void uart1_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    /* PA9=TX, PA10=RX: AF7 */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (9u * 2u)))  | (2u << (9u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (10u * 2u))) | (2u << (10u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 4))  | (7u << 4);
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 8))  | (7u << 8);

    USART1->BRR = SYSCLK_FREQ / BLE_BAUD;
    USART1->CR1 = USART_CR1_TE | USART_CR1_UE;
}

static void uart1_send(const uint8_t *data, uint16_t len)
{
    for (uint16_t i = 0; i < len; i++) {
        while (!(USART1->ISR & USART_ISR_TXE)) ;
        USART1->TDR = data[i];
    }
}

static void send_packet(uint8_t type, const uint8_t *payload, uint16_t len)
{
    uint8_t header[4];
    header[0] = PKT_START;
    header[1] = type;
    header[2] = (uint8_t)(len >> 8);
    header[3] = (uint8_t)(len & 0xFF);

    uint8_t crc = crc8(payload, len);

    uart1_send(header, 4);
    if (len > 0) uart1_send(payload, len);
    uart1_send(&crc, 1);
}

/* Helper: pack float into 4 bytes (little-endian) */
static void pack_float(uint8_t *buf, float val)
{
    memcpy(buf, &val, 4);
}

void ble_bridge_init(void)
{
    uart1_init();
}

void ble_bridge_send_measurement(const radiometry_result_t *result,
                                  const solar_pos_t *pos,
                                  float bat_v, const char *state)
{
    uint8_t payload[128];
    uint16_t idx = 0;

    /* Pack: sun_az(4) + sun_el(4) + zenith(4) + air_mass(4) */
    pack_float(&payload[idx], (float)pos->azimuth);   idx += 4;
    pack_float(&payload[idx], (float)pos->elevation); idx += 4;
    pack_float(&payload[idx], (float)pos->zenith);    idx += 4;
    pack_float(&payload[idx], (float)pos->air_mass);  idx += 4;

    /* Pack: 6× DNI (24 bytes) */
    for (int i = 0; i < 6; i++) {
        pack_float(&payload[idx], result->dni[i]);    idx += 4;
    }
    /* Pack: 6× AOD (24 bytes) */
    for (int i = 0; i < 6; i++) {
        pack_float(&payload[idx], result->aod[i]);    idx += 4;
    }
    /* Pack: angstrom(4) + pwv(4) + bat_v(4) */
    pack_float(&payload[idx], result->angstrom_alpha); idx += 4;
    pack_float(&payload[idx], result->pwv_cm);        idx += 4;
    pack_float(&payload[idx], bat_v);                  idx += 4;

    send_packet(PKT_MEAS, payload, idx);
}

void ble_bridge_send_langley(uint16_t points, float r2, float v0_870)
{
    uint8_t payload[12];
    payload[0] = (uint8_t)(points >> 8);
    payload[1] = (uint8_t)(points & 0xFF);
    pack_float(&payload[2], r2);
    pack_float(&payload[6], v0_870);
    send_packet(PKT_LANGLEY, payload, 10);
}

void ble_bridge_send_status(const char *state, float sun_az, float sun_el,
                             float bat_v, bool gps_fix)
{
    uint8_t payload[20];
    uint16_t idx = 0;
    uint16_t state_len = strlen(state);
    if (state_len > 12) state_len = 12;
    payload[idx++] = (uint8_t)state_len;
    memcpy(&payload[idx], state, state_len);
    idx += state_len;
    pack_float(&payload[idx], sun_az);  idx += 4;
    pack_float(&payload[idx], sun_el);  idx += 4;
    pack_float(&payload[idx], bat_v);   idx += 4;
    payload[idx++] = gps_fix ? 1 : 0;
    send_packet(PKT_STATUS, payload, idx);
}

void ble_bridge_send_error(const char *msg)
{
    uint16_t len = strlen(msg);
    if (len > BLE_MAX_PACKET - 5) len = BLE_MAX_PACKET - 5;
    send_packet(PKT_ERROR, (const uint8_t *)msg, len);
}