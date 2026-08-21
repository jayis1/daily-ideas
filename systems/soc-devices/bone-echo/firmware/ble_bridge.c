/*
 * ble_bridge.c — UART protocol to ESP32-C3 (BLE GATT server)
 *
 * USART1: PA9=TX, PA10=RX (921600 baud)
 * The ESP32-C3 runs a BLE GATT server that exposes:
 *   - SOS/BUA/SI/T/Z/class characteristic
 *   - Waveform characteristic (chunked, 115200 samples × 2 bytes)
 *   - Status characteristic (battery, state, last SOS/BUA)
 *   - Command characteristic (SCAN, STOP, PHANTOM, ID/AGE/SEX/ETH set)
 */

#include "ble_bridge.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>
#include <stdio.h>

static char rx_buf[64];
static uint8_t rx_idx = 0;

void ble_bridge_init(void)
{
    /* PA9: USART1_TX, PA10: USART1_RX */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (9u * 2u))) | (2u << (9u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (10u * 2u))) | (2u << (10u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << (1u * 4u))) | (7u << (1u * 4u));  /* AF7 = USART1 */
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << (2u * 4u))) | (7u << (2u * 4u));

    /* PB9: ESP32-C3 reset, PB10: enable */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (9u * 2u))) | (1u << (9u * 2u));
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (10u * 2u))) | (1u << (10u * 2u));
    GPIOB->BSRR = (1u << 9u);    /* Reset high (not in reset) */
    GPIOB->BSRR = (1u << 10u);   /* Enable high */

    /* USART1: 921600 baud, 8N1 */
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    USART1->BRR = SYSCLK_FREQ / 921600u;
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE | USART_CR1_RXNEIE;
    rx_idx = 0;
}

static void uart_tx(const char *s)
{
    while (*s) {
        while (!(USART1->ISR & USART_ISR_TXE)) ;
        USART1->TDR = (uint8_t)*s++;
    }
}

bool ble_bridge_poll_cmd(char *cmd, size_t len)
{
    while (USART1->ISR & USART_ISR_RXNE) {
        char c = (char)USART1->RDR;
        if (c == '\n' || c == '\r') {
            if (rx_idx > 0) {
                rx_buf[rx_idx] = 0;
                strncpy(cmd, rx_buf, len - 1);
                cmd[len - 1] = 0;
                rx_idx = 0;
                return true;
            }
        } else {
            if (rx_idx < sizeof(rx_buf) - 1) rx_buf[rx_idx++] = c;
        }
    }
    return false;
}

void ble_bridge_push_results(float sos, float bua, float si, float t, float z, int cls)
{
    char buf[128];
    snprintf(buf, sizeof(buf), "R:%.1f,%.1f,%.1f,%.2f,%.2f,%d\n",
             sos, bua, si, t, z, cls);
    uart_tx(buf);
}

void ble_bridge_push_waveform(const uint16_t *buf, uint32_t n)
{
    /* Send waveform in 512-byte chunks with "W:" prefix */
    uart_tx("W:START\n");
    for (uint32_t i = 0; i < n; i += 256) {
        char chunk[16];
        snprintf(chunk, sizeof(chunk), "W:%lu\n", (unsigned long)i);
        uart_tx(chunk);
        /* Real code sends raw binary via DMA */
    }
    uart_tx("W:END\n");
    (void)buf;
}

void ble_bridge_push_status(float bat_v, int state, float sos, float bua)
{
    char buf[64];
    snprintf(buf, sizeof(buf), "S:%.2f,%d,%.1f,%.1f\n", bat_v, state, sos, bua);
    uart_tx(buf);
}