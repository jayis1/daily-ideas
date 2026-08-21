/**
 * uart_protocol.h — Binary frame parser for STM32 → ESP32-C3 link
 */
#ifndef UART_PROTOCOL_H
#define UART_PROTOCOL_H

#include <stdint.h>

/* Result structure (mirrors the STM32 side) */
typedef struct {
    float n[4];          /* RI at 589, 525, 470, 655 nm */
    float n_D;
    float n_F;
    float n_C;
    float dispersion;
    float abbe_vd;
    float brix;
    float specific_grav;
    float abv;
    float freeze_point;
    float t_prism;
    float t_ambient;
    int8_t  compound_id;
    char    compound_name[16];
    float   confidence;
} ri_result_t;

/* Frame commands */
#define CMD_RESULT  0x01
#define CMD_STATUS  0x02
#define CMD_CAL     0x03

void uart_protocol_init(uint8_t uart_port);
void uart_protocol_process(const uint8_t *data, int len);
void uart_protocol_dispatch(uint8_t cmd, const uint8_t *payload, int len);

#endif /* UART_PROTOCOL_H */