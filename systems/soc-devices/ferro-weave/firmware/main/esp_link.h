/*
 * esp_link.h — UART protocol to the ESP32-C3 co-processor
 */
#ifndef FERRO_WEAVE_ESP_LINK_H
#define FERRO_WEAVE_ESP_LINK_H

#include <stddef.h>
#include "bh.h"
#include "sweep.h"

/* Frame types for the STM32↔ESP32-C3 UART protocol. */
#define ESP_FRAME_SWEEP_RESULT 0x01   /* STM→ESP: result + arrays */
#define ESP_FRAME_STATUS       0x02   /* STM→ESP: status string    */
#define ESP_FRAME_CMD          0x03   /* ESP→STM: command          */
#define ESP_FRAME_ACK          0x04

/* Push a complete sweep to the ESP32-C3 (chunked over UART). */
int esp_link_send_sweep(const sweep_params_t *sp, const geom_t *g,
                        const float *H, const float *B, int n,
                        const bh_result_t *r);

/* Send a one-line status string. */
int esp_link_send_status(const char *s);

/* Poll for an incoming command from the ESP32-C3 (non-blocking).
 * Returns 0 + fills cmd[] if a full command line is available. */
int esp_link_poll_cmd(char *cmd, size_t maxlen);

/* Initialise the UART. */
void esp_link_init(void);

#endif /* FERRO_WEAVE_ESP_LINK_H */