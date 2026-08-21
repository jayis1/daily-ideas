/**
 * neom9n.c — GPS packet receiver from ESP32-C3 bridge
 *
 * The ESP32-C3 parses NMEA from the NEO-M9N and sends a compact
 * 28-byte binary packet to the STM32 over UART2 at 1 Hz:
 *
 *   [0xAA][0x55][lat(8)][lon(8)][alt(8)][time(4)][fix(1)][sats(1)]
 *
 * This avoids the STM32 having to parse NMEA strings directly.
 */

#include "neom9n.h"
#include <string.h>

int neom9n_uart_recv(UART_HandleTypeDef *uart, neom9n_packet_t *pkt, uint32_t timeout_ms)
{
    uint8_t header[2];
    uint8_t body[26];

    /* Look for sync bytes 0xAA 0x55 */
    uint32_t start = HAL_GetTick();
    uint8_t found = 0;

    while ((HAL_GetTick() - start) < timeout_ms) {
        if (HAL_UART_Receive(uart, header, 1, 100) != HAL_OK) continue;
        if (header[0] == 0xAA) {
            if (HAL_UART_Receive(uart, &header[1], 1, 50) != HAL_OK) continue;
            if (header[1] == 0x55) { found = 1; break; }
        }
    }

    if (!found) return 0;

    if (HAL_UART_Receive(uart, body, 26, 200) != HAL_OK) return 0;

    memcpy(&pkt->lat,       &body[0],  8);
    memcpy(&pkt->lon,       &body[8],  8);
    memcpy(&pkt->alt,       &body[16], 8);
    memcpy(&pkt->unix_time, &body[24], 4);
    pkt->fix  = body[25] & 0x0F;
    pkt->sats = (body[25] >> 4) & 0x0F;

    return 28;
}