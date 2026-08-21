/*
 * gossamer-spin / firmware / uart_link.c
 * Binary framing protocol to/from ESP32-C3.
 *
 * Frame format:
 *   [0xAA][0x55][len_lo][len_hi][type][payload...]
 *
 * Types (STM32 → ESP32):
 *   0x01: Process data (voltage, current, flow, RPM, temp, RH, state, time)
 *   0x02: Safety alert (source code)
 *   0x03: Run status (state, recipe idx)
 *
 * Types (ESP32 → STM32):
 *   0x81: Start run (recipe idx)
 *   0x82: Stop run
 *   0x83: Set custom recipe (payload = recipe struct)
 *   0x84: Set target voltage (float)
 */
#include "main.h"

static void *h_usart2 = (void *)1;

#define UART_BAUD    460800
#define MAX_PAYLOAD  128

static uint8_t rx_buf[MAX_PAYLOAD + 6];
static int     rx_pos = 0;

void uart_link_init(void)
{
    /* USART2 init: 460800 baud, 8N1, TX=PA2, RX=PA3
       Enable RX interrupt */
    (void)h_usart2;
    rx_pos = 0;
}

/* Send a process data frame (type 0x01) */
void uart_link_send(process_t *p)
{
    uint8_t frame[64];
    int i = 0;
    frame[i++] = 0xAA;
    frame[i++] = 0x55;

    /* Payload: voltage(4) + current(4) + flow(4) + rpm(4) +
       temp(4) + rh(4) + jet_state(1) + jet_sigma(4) + elapsed(4) = 33 bytes */
    uint16_t len = 33;
    frame[i++] = len & 0xFF;
    frame[i++] = (len >> 8) & 0xFF;
    frame[i++] = 0x01;

    memcpy(&frame[i], &p->voltage_kv, 4); i += 4;
    memcpy(&frame[i], &p->current_na, 4); i += 4;
    memcpy(&frame[i], &p->flow_mlh, 4);   i += 4;
    memcpy(&frame[i], &p->drum_rpm, 4);   i += 4;
    memcpy(&frame[i], &p->temp_c, 4);     i += 4;
    memcpy(&frame[i], &p->rh_pct, 4);     i += 4;
    frame[i++] = (uint8_t)p->jet_state;
    memcpy(&frame[i], &p->jet_sigma_na, 4); i += 4;
    memcpy(&frame[i], &p->elapsed_s, 4);    i += 4;

    /* In real build: HAL_UART_Transmit(h_usart2, frame, i, 100) */
    (void)frame;
}

/* Poll for incoming commands from ESP32 */
void uart_link_poll(void)
{
    /* In real build: read bytes from USART2 RX interrupt buffer,
       parse frames, and execute commands:

       0x81 (start run): read recipe idx from payload, load recipe,
                          call start_run()
       0x82 (stop run):  call stop_run()
       0x83 (custom recipe): copy payload into recipe struct
       0x84 (set voltage): update HV target

       For now, placeholder frame parser: */
    (void)rx_buf;
    (void)rx_pos;
}