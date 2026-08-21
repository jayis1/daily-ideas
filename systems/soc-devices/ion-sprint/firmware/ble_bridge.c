/*
 * ble_bridge.c — UART1 protocol to ESP32-C3 BLE/Wi-Fi bridge
 *
 * USART1 (PA9=TX, PA10=RX) at 921600 baud.
 * Protocol: binary framed packets with CRC-8.
 * Packet types:
 *   0x01 EPH_CHUNK — live electropherogram data
 *   0x02 RESULTS   — peak table (final)
 *   0x03 ERROR     — error message
 *   0x04 STATUS    — status update
 *
 * The ESP32-C3 firmware (separate) receives these and exposes them
 * via BLE GATT characteristics for a phone app to read/subscribe.
 */

#include "ble_bridge.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>

/* Packet format: [START 0xAA][TYPE][LEN_H][LEN_L][PAYLOAD...][CRC8] */
#define PKT_START   0xAAu
#define PKT_EPH     0x01u
#define PKT_RESULTS 0x02u
#define PKT_ERROR   0x03u
#define PKT_STATUS  0x04u

static void uart1_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    /* PA9=TX (AF7), PA10=RX (AF7) */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (9u * 2u))) | (2u << (9u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (10u * 2u))) | (2u << (10u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 4)) | (7u << 4);
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 8)) | (7u << 8);

    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    USART1->BRR = (SYSCLK_FREQ / BLE_BAUD);
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

static void uart_tx_byte(uint8_t b)
{
    while (!(USART1->ISR & USART_ISR_TXE)) ;
    USART1->TDR = b;
}

static uint8_t crc8(const uint8_t *data, uint32_t len)
{
    uint8_t crc = 0;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) crc = (crc << 1) ^ 0x07;
            else           crc <<= 1;
        }
    }
    return crc;
}

static void send_packet(uint8_t type, const uint8_t *payload, uint16_t len)
{
    uart_tx_byte(PKT_START);
    uart_tx_byte(type);
    uart_tx_byte((uint8_t)(len >> 8));
    uart_tx_byte((uint8_t)(len & 0xFF));
    for (uint16_t i = 0; i < len; i++) {
        uart_tx_byte(payload[i]);
    }
    uart_tx_byte(crc8(payload, len));
}

void ble_bridge_init(void)
{
    uart1_init();
}

void ble_bridge_send_eph_chunk(const float *eph, uint32_t count,
                               float hv_kv, float current_ua)
{
    /* Send up to 50 samples per chunk (50 × 4 bytes = 200 bytes + 8 header) */
    uint32_t to_send = count > 50 ? 50 : count;
    if (to_send == 0) return;

    /* Build packet payload: [hv_kv float][current float][sample_count u16][floats...] */
    uint8_t buf[BLE_MAX_PACKET];
    uint16_t pos = 0;
    memcpy(&buf[pos], &hv_kv, 4);      pos += 4;
    memcpy(&buf[pos], &current_ua, 4); pos += 4;
    uint16_t sc = (uint16_t)to_send;
    memcpy(&buf[pos], &sc, 2);         pos += 2;
    memcpy(&buf[pos], &eph[count - to_send], to_send * 4);
    pos += (uint16_t)(to_send * 4);

    send_packet(PKT_EPH, buf, pos);
}

void ble_bridge_send_results(const ion_result_t *results, uint8_t count,
                             uint16_t run_id)
{
    /* Build results packet: [run_id u16][count u8][ion results...] */
    uint8_t buf[BLE_MAX_PACKET];
    uint16_t pos = 0;
    memcpy(&buf[pos], &run_id, 2); pos += 2;
    buf[pos++] = count;
    for (uint8_t i = 0; i < count && pos < BLE_MAX_PACKET - 40; i++) {
        memcpy(&buf[pos], &results[i].ion_id, 1);    pos += 1;
        memcpy(&buf[pos], results[i].ion_name, 12);   pos += 12;
        memcpy(&buf[pos], &results[i].migration_time, 4); pos += 4;
        memcpy(&buf[pos], &results[i].area, 4);       pos += 4;
        memcpy(&buf[pos], &results[i].concentration_mM, 4); pos += 4;
    }
    send_packet(PKT_RESULTS, buf, pos);
}

void ble_bridge_send_error(const char *msg, float current_ua, float voltage_kv)
{
    uint8_t buf[128];
    uint16_t pos = 0;
    uint8_t len = (uint8_t)strlen(msg);
    if (len > 80) len = 80;
    buf[pos++] = len;
    memcpy(&buf[pos], msg, len); pos += len;
    memcpy(&buf[pos], &current_ua, 4); pos += 4;
    memcpy(&buf[pos], &voltage_kv, 4); pos += 4;
    send_packet(PKT_ERROR, buf, pos);
}