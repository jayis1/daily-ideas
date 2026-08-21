/*
 * ble_bridge.c — UART to ESP32-C3 BLE module
 *
 * USART1: PA9=TX, PA10=RX, 921600 baud.
 * Simple text protocol; ESP32-C3 firmware parses and exposes GATT.
 */

#include "ble_bridge.h"
#include "stm32g474_conf.h"
#include <string.h>
#include <stdio.h>

#define UART_BUF_LEN  128

static char rx_buf[UART_BUF_LEN];
static uint32_t rx_pos = 0;

void ble_bridge_init(void)
{
    /* PA9=TX, PA10=RX → AF7 (USART1) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->AFR[1] &= ~(GPIO_AFRH_AFSEL9 | GPIO_AFRH_AFSEL10);
    GPIOA->AFR[1] |= (7u << GPIO_AFRH_AFSEL9_Pos) | (7u << GPIO_AFRH_AFSEL10_Pos);
    GPIOA->MODER = (GPIOA->MODER & ~(GPIO_MODER_MODE9 | GPIO_MODER_MODE10))
                 | (2u << GPIO_MODER_MODE9_Pos) | (2u << GPIO_MODER_MODE10_Pos);

    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    USART1->BRR = (SYSCLK_FREQ / 921600u);
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_RXNEIE | USART_CR1_UE;
    NVIC_EnableIRQ(USART1_IRQn);
}

void USART1_IRQHandler(void)
{
    if (USART1->ISR & USART_ISR_RXNE) {
        char c = (char)USART1->RDR;
        if (c == '\n' || c == '\r') {
            rx_buf[rx_pos] = '\0';
            rx_pos = 0;
            /* Command complete — main loop polls rx_buf */
            /* Set a flag to indicate new command */
        } else if (rx_pos < UART_BUF_LEN - 1) {
            rx_buf[rx_pos++] = c;
        }
    }
}

/* Simple: check if a complete command is available */
static volatile bool cmd_ready = false;

bool ble_bridge_poll_cmd(char *cmd, uint32_t maxlen)
{
    if (rx_pos > 0 && rx_buf[rx_pos - 1] == '\0') {
        strncpy(cmd, rx_buf, maxlen);
        cmd[maxlen - 1] = '\0';
        rx_pos = 0;
        return true;
    }
    return false;
}

static void uart_send(const char *s)
{
    while (*s) {
        while (!(USART1->ISR & USART_ISR_TXE)) ;
        USART1->TDR = *s++;
    }
}

void ble_bridge_push_status(float battery_v, int state, float flow,
                             float pm1, float pm25, float pm10,
                             const uint32_t *counts, uint8_t n)
{
    char buf[256];
    int pos = snprintf(buf, sizeof(buf),
                       "S:%d,B:%.2f,F:%.2f,1:%.1f,25:%.1f,10:%.1f,H:",
                       state, battery_v, flow, pm1, pm25, pm10);
    for (uint8_t i = 0; i < n && pos < (int)sizeof(buf) - 12; ++i)
        pos += snprintf(buf + pos, sizeof(buf) - pos, "%lu,", (unsigned long)counts[i]);
    buf[pos++] = '\n';
    buf[pos] = '\0';
    uart_send(buf);
}