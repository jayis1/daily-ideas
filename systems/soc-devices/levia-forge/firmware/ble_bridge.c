/*
 * Levia Forge — BLE Bridge (UART to ESP32-C3)
 * Sends state to ESP32-C3 and receives remote commands.
 *
 * Protocol:
 *   PC → ESP: "STATE,<x>,<y>,<z>,<pattern>,<particle>,<bat>,<safety>\n"
 *   ESP → PC: "CMD,<type>,<arg1>,<arg2>,...\n"
 *     CMD types: SET_XYZ, SET_PATTERN, SET_ACTIVE, SET_PARAM
 *
 * SPDX-License-Identifier: MIT
 */
#include "ble_bridge.h"
#include "sdkconfig.h"
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define UART_BAUD   921600
#define RX_BUF_SIZE 256

static char rx_buffer[RX_BUF_SIZE];
static int rx_len = 0;

/* State struct (same layout as in main.c) */
typedef struct {
    float target_x, target_y, target_z;
    float actual_x, actual_y, actual_z;
    int pattern;
    int vortex_charge;
    float twin_delta;
    float bend_gradient;
    float transport_progress;
    float transport_speed;
    bool active;
    bool particle_detected;
    float particle_height_mm;
    int battery_mv;
    float temp_c;
    int safety;
    uint32_t uptime_ms;
    bool auto_track_z;
} bridge_state_t;

void ble_bridge_init(void)
{
    uart_init(uart1, UART_BAUD);
    uart_set_format(uart1, 8, 1, UART_PARITY_NONE);
    gpio_set_function(PIN_UART_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_UART_RX, GPIO_FUNC_UART);

    /* Enable UART RX interrupt */
    uart_set_fifo_enabled(uart1, true);
    rx_len = 0;
}

void ble_bridge_send_state(void *state_ptr)
{
    bridge_state_t *s = (bridge_state_t *)state_ptr;
    char buf[128];
    int len = snprintf(buf, sizeof(buf),
        "STATE,%.2f,%.2f,%.2f,%d,%d,%d,%d\n",
        s->actual_x, s->actual_y, s->actual_z,
        s->pattern,
        s->particle_detected ? 1 : 0,
        s->battery_mv,
        s->safety);
    uart_write_blocking(uart1, (uint8_t *)buf, len);
}

/* Parse a received command line and apply it to state */
static void parse_command(const char *cmd, void *state_ptr)
{
    bridge_state_t *s = (bridge_state_t *)state_ptr;

    if (strncmp(cmd, "CMD,SET_XYZ,", 12) == 0) {
        float x, y, z;
        if (sscanf(cmd + 12, "%f,%f,%f", &x, &y, &z) == 3) {
            s->target_x = x;
            s->target_y = y;
            s->target_z = z;
        }
    } else if (strncmp(cmd, "CMD,SET_PATTERN,", 16) == 0) {
        int pat;
        if (sscanf(cmd + 16, "%d", &pat) == 1 && pat >= 0 && pat < 6) {
            s->pattern = pat;
        }
    } else if (strncmp(cmd, "CMD,SET_ACTIVE,", 15) == 0) {
        int active;
        if (sscanf(cmd + 15, "%d", &active) == 1) {
            s->active = active ? true : false;
        }
    } else if (strncmp(cmd, "CMD,SET_PARAM,", 14) == 0) {
        char param[16];
        float value;
        if (sscanf(cmd + 14, "%[^,],%f", param, &value) == 2) {
            if (strcmp(param, "vortex_charge") == 0)
                s->vortex_charge = (int)value;
            else if (strcmp(param, "twin_delta") == 0)
                s->twin_delta = value;
            else if (strcmp(param, "bend_gradient") == 0)
                s->bend_gradient = value;
            else if (strcmp(param, "transport_speed") == 0)
                s->transport_speed = value;
            else if (strcmp(param, "auto_track") == 0)
                s->auto_track_z = (bool)value;
        }
    }
}

void ble_bridge_poll(void *state_ptr)
{
    /* Read available UART data */
    while (uart_is_readable(uart1)) {
        char ch = uart_getc(uart1);
        if (ch == '\n' || ch == '\r') {
            if (rx_len > 0) {
                rx_buffer[rx_len] = '\0';
                parse_command(rx_buffer, state_ptr);
                rx_len = 0;
            }
        } else {
            if (rx_len < RX_BUF_SIZE - 1) {
                rx_buffer[rx_len++] = ch;
            }
        }
    }

    /* Send current state to ESP32-C3 (every poll = 10 Hz) */
    ble_bridge_send_state(state_ptr);
}