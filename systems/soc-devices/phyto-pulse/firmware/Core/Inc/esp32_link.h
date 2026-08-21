/*
 * esp32_link.h — UART protocol to ESP32-C3 connectivity MCU
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#ifndef ESP32_LINK_H
#define ESP32_LINK_H

#include <stdint.h>
#include <stdbool.h>
#include "spike_detect.h"
#include "slow_wave.h"

/* Initialize UART link to ESP32-C3 */
int esp32_link_init(void);

/* Send a live sample (called at 1 kHz, or decimated for display) */
int esp32_link_send_sample(float voltage_mv, uint32_t timestamp_ms, float gain);

/* Send an event notification */
int esp32_link_send_event(const spike_event_t *event);

/* Send a slow-wave result */
int esp32_link_send_swp(const swp_result_t *result);

/* Send status update (battery, gain, state) */
int esp32_link_send_status(float battery_v, float gain, const char *state);

/* Enable/disable the ESP32-C3 (power gate) */
void esp32_link_enable(bool enable);

/* Process incoming commands from ESP32-C3 (called in main loop) */
void esp32_link_process(void);

/* Callback when a command is received from ESP32 */
typedef void (*esp32_cmd_callback_t)(const char *cmd, int len);
void esp32_link_set_cmd_callback(esp32_cmd_callback_t cb);

#endif /* ESP32_LINK_H */