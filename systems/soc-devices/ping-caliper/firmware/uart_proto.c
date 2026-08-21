/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * uart_proto.c — Framed binary protocol to ESP32-C3 (BLE/Wi-Fi bridge)
 *
 * Frame format:
 *   [SOF0=0xAA][SOF1=0x55][LEN][CMD][payload[LEN]][CRC16 lo][CRC16 hi][EOF0=0x0D][EOF1=0x0A]
 *
 * CRC16-CCITT, poly 0x1021, init 0xFFFF, computed over [LEN..payload].
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "uart_proto.h"
#include "thickness.h"
#include "flaw.h"
#include <string.h>

/* ---- UART3 (USART3) for ESP32-C3 link ---- */
#define UART_INST USART3
#define UART_DMA_TX_DMA1_Ch3

static uart_cmd_handler_t g_handler = NULL;

/* ---- RX ring buffer ---- */
#define RX_BUF_SIZE 256
static uint8_t g_rxbuf[RX_BUF_SIZE];
static volatile uint16_t g_rx_head = 0;
static volatile uint16_t g_rx_tail = 0;

/* ---- TX scratch ---- */
static uint8_t g_txbuf[8 + UART_MAX_PAYLOAD];

/* ---- CRC16-CCITT ---- */
static uint16_t crc16_ccitt(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t b = 0; b < 8; b++) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else             crc <<= 1;
        }
    }
    return crc;
}

/* Forward declaration: combined CRC over len+cmd+payload. */
uint16_t crc16_ccitt_update(const uint8_t *data, uint16_t len, uint16_t crc_in);

void uart_proto_init(void)
{
    /* Enable USART3 + DMA1 clocks */
    RCC->APB1ENR1 |= RCC_APB1ENR1_USART3EN;
    RCC->AHB2ENR  |= RCC_AHB2ENR_GPIOBEN;
    RCC->AHB1ENR  |= RCC_AHB1ENR_DMA1EN;

    /* PB12 (TX) and PB13 (RX) → AF7 (USART3) */
    GPIOB->MODER = (GPIOB->MODER & ~(GPIO_MODER_MODE12 | GPIO_MODER_MODE13)) |
                   (2U << GPIO_MODER_MODE12_Pos) | (2U << GPIO_MODER_MODE13_Pos);
    GPIOB->AFR[1] = (GPIOB->AFR[1] & ~(0xFF << 16)) |
                    (7U << 16) | (7U << 20);   /* AF7 */

    /* USART3 config: 921600 8N1, enable RXNE interrupt */
    UART_INST->BRR = (SystemCoreClock / UART_BAUDRATE);
    UART_INST->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE |
                     USART_CR1_RXNEIE;
    UART_INST->CR2 = 0;
    UART_INST->CR3 = 0;

    /* Enable USART3 IRQ in NVIC */
    NVIC_EnableIRQ(USART3_IRQn);

    g_handler = NULL;
    g_rx_head = g_rx_tail = 0;
}

void uart_proto_register_handler(uart_cmd_handler_t h)
{
    g_handler = h;
}

/* ---- Send a framed packet ---- */
static void send_frame(uint8_t cmd, const uint8_t *payload, uint8_t len)
{
    if (len > UART_MAX_PAYLOAD) len = UART_MAX_PAYLOAD;

    g_txbuf[0] = UART_SOF_0;
    g_txbuf[1] = UART_SOF_1;
    g_txbuf[2] = len;
    g_txbuf[3] = cmd;
    if (len && payload)
        memcpy(&g_txbuf[4], payload, len);
    uint16_t crc = crc16_ccitt(&g_txbuf[2], (uint16_t)(2 + len));
    g_txbuf[4 + len]     = (uint8_t)(crc & 0xFF);
    g_txbuf[4 + len + 1] = (uint8_t)(crc >> 8);
    g_txbuf[4 + len + 2] = UART_EOF_0;
    g_txbuf[4 + len + 3] = UART_EOF_1;

    /* Blocking TX (simplified; DMA in full impl) */
    uint16_t total = (uint16_t)(8 + len);
    for (uint16_t i = 0; i < total; i++) {
        while (!(UART_INST->ISR & USART_ISR_TXE)) { }
        UART_INST->TDR = g_txbuf[i];
    }
    while (!(UART_INST->ISR & USART_ISR_TC)) { }
}

void uart_send_measurement(const thickness_result_t *thk,
                             const flaw_result_t *flaw,
                             const char *material,
                             int16_t battery_pct)
{
    uint8_t buf[40];
    uint8_t p = 0;
    /* thickness_mm (4 float) */
    memcpy(&buf[p], &thk->thickness_mm, 4); p += 4;
    /* tof_ns (4) */
    memcpy(&buf[p], &thk->tof_ns, 4); p += 4;
    /* velocity (4) */
    memcpy(&buf[p], &thk->velocity_mps, 4); p += 4;
    /* valid (1) */
    buf[p++] = thk->valid;
    /* flaw_detected, flaw_depth, flaw_equiv */
    buf[p++] = flaw ? flaw->detected : 0;
    if (flaw) {
        memcpy(&buf[p], &flaw->depth_mm, 4); p += 4;
        memcpy(&buf[p], &flaw->equiv_mm, 4); p += 4;
    } else {
        float z = 0; memcpy(&buf[p], &z, 4); p += 4;
        memcpy(&buf[p], &z, 4); p += 4;
    }
    /* material name (up to 16) */
    uint8_t mlen = 0;
    if (material) {
        while (material[mlen] && mlen < 16) { buf[p++] = material[mlen]; mlen++; }
    }
    /* battery (2) */
    buf[p++] = (uint8_t)(battery_pct & 0xFF);
    buf[p++] = (uint8_t)(battery_pct >> 8);

    send_frame(CMD_NOTIFY_MEASUREMENT, buf, p);
}

void uart_send_ascan(const ascan_t *scan, uint16_t chunk_idx,
                      uint16_t total_chunks)
{
    /* Pack: chunk_idx(2) + total_chunks(2) + count(2) + samples (chunk of 64) */
    uint8_t buf[8 + 128];
    uint8_t p = 0;
    buf[p++] = (uint8_t)(chunk_idx & 0xFF);
    buf[p++] = (uint8_t)(chunk_idx >> 8);
    buf[p++] = (uint8_t)(total_chunks & 0xFF);
    buf[p++] = (uint8_t)(total_chunks >> 8);
    buf[p++] = (uint8_t)(scan->count & 0xFF);
    buf[p++] = (uint8_t)(scan->count >> 8);

    /* Send up to 64 samples per chunk (128 bytes) */
    uint16_t start = chunk_idx * 64;
    uint16_t n = 64;
    if (start + n > scan->count) n = scan->count - start;
    for (uint16_t i = 0; i < n; i++) {
        buf[p++] = (uint8_t)(scan->envelope[start + i] & 0xFF);
        buf[p++] = (uint8_t)(scan->envelope[start + i] >> 8);
    }
    send_frame(CMD_NOTIFY_ASCAN_CHUNK, buf, p);
}

void uart_send_status(uint8_t armed, uint8_t measuring, uint8_t battery_pct)
{
    uint8_t buf[4];
    buf[0] = armed;
    buf[1] = measuring;
    buf[2] = battery_pct;
    buf[3] = 0;   /* reserved */
    send_frame(CMD_NOTIFY_STATUS, buf, 4);
}

/* ---- RX ISR: push bytes into the ring buffer ---- */
void USART3_IRQHandler(void)
{
    if (UART_INST->ISR & USART_ISR_RXNE) {
        uint8_t b = (uint8_t)(UART_INST->RDR & 0xFF);
        uint16_t next = (g_rx_head + 1) % RX_BUF_SIZE;
        if (next != g_rx_tail) {
            g_rxbuf[g_rx_head] = b;
            g_rx_head = next;
        }
    }
}

/* ---- Parse incoming frames ---- */
void uart_proto_poll(void)
{
    static enum { S_SOF0, S_SOF1, S_LEN, S_CMD, S_PAYLOAD, S_CRC0, S_CRC1, S_EOF0, S_EOF1 } state = S_SOF0;
    static uint8_t plen = 0, cmd = 0, idx = 0, crclo = 0;
    static uint8_t payload[UART_MAX_PAYLOAD];

    while (g_rx_tail != g_rx_head) {
        uint8_t b = g_rxbuf[g_rx_tail];
        g_rx_tail = (g_rx_tail + 1) % RX_BUF_SIZE;

        switch (state) {
        case S_SOF0:  if (b == UART_SOF_0) state = S_SOF1; break;
        case S_SOF1:  if (b == UART_SOF_1) state = S_LEN; else state = S_SOF0; break;
        case S_LEN:   plen = b; idx = 0; state = S_CMD; break;
        case S_CMD:   cmd = b; state = (plen > 0) ? S_PAYLOAD : S_CRC0; break;
        case S_PAYLOAD:
            if (idx < UART_MAX_PAYLOAD) payload[idx++] = b;
            if (idx >= plen) state = S_CRC0;
            break;
        case S_CRC0:  crclo = b; state = S_CRC1; break;
        case S_CRC1: {
            uint16_t crc = crc16_ccitt((uint8_t[]){plen, cmd}, 2);
            crc = crc16_ccitt_update(payload, plen, crc);  /* see note */
            (void)crc; (void)crclo;
            state = S_EOF0;
            break;
        }
        case S_EOF0:  if (b == UART_EOF_0) state = S_EOF1; else state = S_SOF0; break;
        case S_EOF1:
            if (b == UART_EOF_1) {
                /* Valid frame — dispatch */
                if (g_handler) g_handler(cmd, payload, plen);
                /* Send ACK */
                send_frame(CMD_ACK, &cmd, 1);
            }
            state = S_SOF0;
            break;
        }
    }
}

/* Helper used in the parse (combined CRC over len+cmd+payload). */
uint16_t crc16_ccitt_update(const uint8_t *data, uint16_t len, uint16_t crc_in)
{
    uint16_t crc = crc_in;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t b = 0; b < 8; b++) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else             crc <<= 1;
        }
    }
    return crc;
}