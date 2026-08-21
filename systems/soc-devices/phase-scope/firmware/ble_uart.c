/*
 * Phase Scope — BLE UART transport (via nRF52810 module)
 * Sends power quality data to smartphone app using Nordic UART Service
 */

#include "ble_uart.h"
#include "main.h"
#include "power_quality.h"
#include <string.h>

/* ------------------------------------------------------------------ */
/* UART4 configuration for BLE module                                   */
/* ------------------------------------------------------------------ */

#define BLE_BAUD    115200

void ble_uart_init(void)
{
    /* Enable UART4 clock */
    RCC->APB1ENR1 |= RCC_APB1ENR1_UART4EN;

    /* Configure UART4: 115200 8N1 */
    float usartdiv = (float)SystemCoreClock / (BLE_BAUD * 16.0f);
    uint32_t mantissa = (uint32_t)usartdiv;
    uint32_t fraction = (uint32_t)((usartdiv - (float)mantissa) * 16.0f + 0.5f);

    UART4->BRR = (mantissa << USART_BRR_DIV_MANTISSA_Pos) |
                  (fraction << USART_BRR_DIV_FRACTION_Pos);

    UART4->CR1 = USART_CR1_TE |    /* Transmitter enable */
                  USART_CR1_RE |    /* Receiver enable */
                  USART_CR1_RXNEIE; /* RX interrupt enable */

    UART4->CR2 = 0;
    UART4->CR3 = 0;

    /* Enable UART */
    UART4->CR1 |= USART_CR1_UE;

    /* Enable RX interrupt */
    NVIC_SetPriority(UART4_IRQn, 2);
    NVIC_EnableIRQ(UART4_IRQn);
}

/* ------------------------------------------------------------------ */
/* Transmit byte via UART                                              */
/* ------------------------------------------------------------------ */

static void uart_tx_byte(uint8_t data)
{
    while (!(UART4->ISR & USART_ISR_TXE))
        ;
    UART4->TDR = data;
}

static void uart_tx_buf(const uint8_t *data, int len)
{
    for (int i = 0; i < len; i++) {
        uart_tx_byte(data[i]);
    }
}

/* ------------------------------------------------------------------ */
/* Send status packet (64 bytes every 500ms)                            */
/* ------------------------------------------------------------------ */

void ble_uart_send_status(const power_results_t *res)
{
    uint8_t pkt[64];
    memset(pkt, 0, sizeof(pkt));

    pkt[0] = 0x01; /* Status packet type */

    /* VRMS values (Q12.4, units: 0.1V) */
    for (int i = 0; i < 3; i++) {
        int16_t vrms_q = (int16_t)(res->vrms[i] * 10.0f);
        pkt[1 + i * 2]     = (uint8_t)(vrms_q & 0xFF);
        pkt[2 + i * 2]     = (uint8_t)((vrms_q >> 8) & 0xFF);
    }

    /* IRMS values (Q12.4, units: 0.01A) */
    for (int i = 0; i < 3; i++) {
        int16_t irms_q = (int16_t)(res->irms[i] * 100.0f);
        pkt[7 + i * 2]     = (uint8_t)(irms_q & 0xFF);
        pkt[8 + i * 2]     = (uint8_t)((irms_q >> 8) & 0xFF);
    }

    /* Active power (Q16.0, units: W) */
    for (int i = 0; i < 3; i++) {
        int32_t p_q = (int32_t)res->p[i];
        pkt[13 + i * 4]     = (uint8_t)(p_q & 0xFF);
        pkt[14 + i * 4]     = (uint8_t)((p_q >> 8) & 0xFF);
        pkt[15 + i * 4]     = (uint8_t)((p_q >> 16) & 0xFF);
        pkt[16 + i * 4]     = (uint8_t)((p_q >> 24) & 0xFF);
    }

    /* Power factor (Q1.15 fixed point) */
    for (int i = 0; i < 3; i++) {
        int16_t pf_q = (int16_t)(res->pf[i] * 32767.0f);
        pkt[25 + i * 2]    = (uint8_t)(pf_q & 0xFF);
        pkt[26 + i * 2]    = (uint8_t)((pf_q >> 8) & 0xFF);
    }

    /* Frequency (Q8.8, units: 0.01Hz) */
    int16_t freq_q = (int16_t)(res->frequency * 100.0f);
    pkt[31] = (uint8_t)(freq_q & 0xFF);
    pkt[32] = (uint8_t)((freq_q >> 8) & 0xFF);

    /* Timestamp (4 bytes) */
    pkt[33] = (uint8_t)(res->timestamp & 0xFF);
    pkt[34] = (uint8_t)((res->timestamp >> 8) & 0xFF);
    pkt[35] = (uint8_t)((res->timestamp >> 16) & 0xFF);
    pkt[36] = (uint8_t)((res->timestamp >> 24) & 0xFF);

    /* THD values (Q4.12, units: 0.01%) */
    for (int i = 0; i < 3; i++) {
        int16_t thd_q = (int16_t)(res->thd_v[i] * 100.0f);
        pkt[37 + i * 2]    = (uint8_t)(thd_q & 0xFF);
        pkt[38 + i * 2]    = (uint8_t)((thd_q >> 8) & 0xFF);
    }

    /* Phase angles */
    for (int i = 0; i < 3; i++) {
        int16_t phase_q = (int16_t)(res->phase_vi[i] * 100.0f);
        pkt[43 + i * 2]    = (uint8_t)(phase_q & 0xFF);
        pkt[44 + i * 2]    = (uint8_t)((phase_q >> 8) & 0xFF);
    }

    /* Flags */
    pkt[49] = (uint8_t)(res->flags & 0xFF);
    pkt[50] = (uint8_t)((res->flags >> 8) & 0xFF);

    /* Send packet with framing */
    uart_tx_byte(0xAA); /* Start byte */
    uart_tx_byte(0x55); /* Start byte */
    uart_tx_buf(pkt, 64);
    uart_tx_byte(0x0D); /* End byte */
    uart_tx_byte(0x0A); /* End byte */
}

/* ------------------------------------------------------------------ */
/* RX command handler                                                   */
/* ------------------------------------------------------------------ */

#define CMD_BUF_SIZE 64
static uint8_t cmd_buf[CMD_BUF_SIZE];
static uint8_t cmd_idx = 0;
static uint8_t cmd_ready = 0;

void UART4_IRQHandler(void)
{
    if (UART4->ISR & USART_ISR_RXNE) {
        uint8_t byte = (uint8_t)(UART4->RDR & 0xFF);

        if (byte == 0x0A) {
            /* End of command */
            cmd_ready = 1;
            cmd_idx = 0;
        } else if (cmd_idx < CMD_BUF_SIZE - 1) {
            cmd_buf[cmd_idx++] = byte;
        }
    }
}

uint8_t ble_uart_get_command(uint8_t *buf, uint8_t *len)
{
    if (!cmd_ready) return 0;

    memcpy(buf, cmd_buf, cmd_idx);
    *len = cmd_idx;
    cmd_ready = 0;
    return 1;
}