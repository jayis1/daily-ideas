/* ble.c — UART-based BLE bridge to the ANNA-B112 module.
 * Implements a custom GATT profile via u-blox SPP-like service.
 * On the STM32 side we speak AT commands over LPUART1.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "ble.h"
#include "dewpoint.h"
#include <stdio.h>
#include <string.h>

extern UART_HandleTypeDef hlpuart1;

static uint8_t rx_buf[256];
static volatile uint16_t rx_len = 0;

void ble_init(void)
{
    /* Reset module */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);
    HAL_Delay(10);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET);
    HAL_Delay(500);

    /* Enable UART RX via interrupt */
    HAL_UART_Receive_IT(&hlpuart1, rx_buf, 1);
}

/* Send a BLE notification with the humidity measurement. */
void ble_notify(const humidity_t *h, float mirror_c, int state, int8_t tec_pct)
{
    char pkt[96];
    int n = snprintf(pkt, sizeof(pkt),
        "DEW %.2f RH %.2f AH %.2f W %.2f M %.2f S %d TEC %d P %d\r\n",
        h->dew_c, h->rh_pct, h->ah_gm3, h->w_gkg, mirror_c,
        state, (int)tec_pct, h->phase);
    HAL_UART_Transmit(&hlpuart1, (uint8_t *)pkt, n, 200);
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == LPUART1) {
        /* Echo to debug or handle command */
        rx_len = (rx_len + 1) % sizeof(rx_buf);
        HAL_UART_Receive_IT(&hlpuart1, &rx_buf[rx_len], 1);
    }
}