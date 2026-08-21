/** neom9n.h — u-blox NEO-M9N GPS packet protocol (via ESP32-C3) */
#ifndef NEOM9N_H
#define NEOM9N_H
#include "stm32g4xx_hal.h"

typedef struct {
    double  lat;         /* degrees        */
    double  lon;         /* degrees        */
    double  alt;         /* metres         */
    uint32_t unix_time;  /* seconds        */
    uint8_t fix;         /* 0=none, 2=2D, 3=3D */
    uint8_t sats;        /* satellite count */
} neom9n_packet_t;

int neom9n_uart_recv(UART_HandleTypeDef *uart, neom9n_packet_t *pkt, uint32_t timeout_ms);

#endif