/*
 * ble_bridge.c — UART protocol to ESP32-C3 BLE GATT server
 *
 * USART1 (PA9=TX, PA10=RX) at 921600 baud connects to the ESP32-C3,
 * which runs a BLE GATT server exposing 5 characteristics:
 *   - 0xRTH (R, Θ, X, Y, noise)         — notify @ 100 Hz
 *   - 0xSWP (sweep point)                — notify per point
 *   - 0xSTA (status string)             — notify
 *   - 0xCMD (command from host)         — write
 *   - 0xFMT (config: freq, TC, slope)   — write
 *
 * The STM32 sends framed packets; the ESP32-C3 repackages them into
 * BLE notifications. A simple SLIP-like frame: [0xAA][len][payload][crc].
 */

#include "stm32g491_conf.h"
#include "ble_bridge.h"
#include <string.h>

#define USART1_UART USART1

void ble_bridge_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    /* PA9 = TX (AF7), PA10 = RX (AF7) */
    GPIOA->MODER = (GPIOA->MODER & ~(0x3U << (2*9)))  | (0x2U << (2*9));
    GPIOA->MODER = (GPIOA->MODER & ~(0x3U << (2*10))) | (0x2U << (2*10));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFU << (4*(9-8))))  | (0x7U << (4*(9-8)));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFU << (4*(10-8))))| (0x7U << (4*(10-8)));

    USART1_UART->BRR = (SYSCLK_FREQ / USART1_BAUD);
    USART1_UART->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

static void uart_putc(uint8_t c)
{
    while (!(USART1_UART->ISR & USART_ISR_TXE)) ;
    USART1_UART->TDR = c;
}

static void uart_send(const uint8_t *data, size_t len)
{
    uart_putc(0xAA);                /* frame sync */
    uart_putc((uint8_t)len);
    uint8_t crc = 0;
    for (size_t i = 0; i < len; ++i) {
        uart_putc(data[i]);
        crc ^= data[i];
    }
    uart_putc(crc);
}

void ble_bridge_push_demod(const demod_result_t *r, float freq, float gain)
{
    #pragma pack(push, 1)
    struct {
        uint8_t  tag;       /* 1 = demod */
        float    freq;
        float    gain;
        float    R, theta, X, Y, noise;
    } pkt = { 1, freq, gain, r->R, r->theta, r->X, r->Y, r->noise };
    #pragma pack(pop)
    uart_send((uint8_t*)&pkt, sizeof(pkt));
}

void ble_bridge_push_sweep(const sweep_point_t *p)
{
    #pragma pack(push, 1)
    struct {
        uint8_t  tag;       /* 2 = sweep */
        float    f, a, R, theta, X, Y, noise;
        uint32_t ts;
    } pkt = { 2, p->f, p->a, p->R, p->theta, p->X, p->Y, p->noise, p->ts_ms };
    #pragma pack(pop)
    uart_send((uint8_t*)&pkt, sizeof(pkt));
}

void ble_bridge_push_status(const char *msg)
{
    uint8_t buf[1 + 32];
    buf[0] = 3;   /* tag = status */
    strncpy((char*)buf + 1, msg, 31);
    buf[31 + 1] = 0;
    uart_send(buf, 1 + 32);
}

bool ble_bridge_poll_cmd(char *cmd, size_t len)
{
    if (!(USART1_UART->ISR & USART_ISR_RXNE)) return false;
    static uint8_t rxbuf[64];
    static int rxlen = 0;
    uint8_t c = (uint8_t)USART1_UART->RDR;
    if (rxlen == 0 && c != 0xAA) return false;
    rxbuf[rxlen++] = c;
    if (rxlen >= 2 && rxlen == 2 + rxbuf[1] + 1) {
        if (rxlen - 1 < len) {
            memcpy(cmd, rxbuf + 2, rxbuf[1]);
            cmd[rxbuf[1]] = 0;
        }
        rxlen = 0;
        return true;
    }
    if (rxlen >= (int)sizeof(rxbuf)) rxlen = 0;
    return false;
}