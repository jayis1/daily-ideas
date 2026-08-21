/*
 * gossamer-spin / esp32c3 / main.c
 * ESP32-C3 radio relay firmware (ESP-IDF v5.2+).
 *
 * Receives process data from the STM32 over UART0 and:
 *   - Exposes a BLE GATT server (live process data stream)
 *   - Serves a Wi-Fi AP web dashboard (live charts)
 *   - Receives recipe selection and start/stop commands from phone
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/uart.h"

static const char *TAG = "gossamer-spin-radio";

#define UART_STM  UART_NUM_0    /* GPIO2 RX, GPIO3 TX @ 460800 */
#define BUF_SZ    2048

/* Latest process data (filled by link task, read by BLE/Wi-Fi) */
static struct {
    float voltage_kv;
    float current_na;
    float flow_mlh;
    float drum_rpm;
    float temp_c;
    float rh_pct;
    uint8_t jet_state;
    float jet_sigma_na;
    uint32_t elapsed_s;
} proc = {0};

/* Jet state names (must match firmware/main/main.h) */
static const char *const JET_STATE_NAMES[] = {
    "IDLE", "STABLE", "INTERRUPTED", "UNSTABLE", "DRIPPING"
};

static void link_task(void *arg)
{
    uint8_t buf[BUF_SZ];
    while (1) {
        int n = uart_read_bytes(UART_STM, buf, sizeof(buf), pdMS_TO_TICKS(50));
        if (n > 0) {
            /* Parse result frame: [0xAA][0x55][len_lo][len_hi][type][payload] */
            if (n >= 6 && buf[0] == 0xAA && buf[1] == 0x55) {
                uint16_t body_len = buf[2] | (buf[3] << 8);
                if (body_len >= 33 && buf[4] == 0x01 && n >= 5 + 33) {
                    uint8_t *p = &buf[5];
                    memcpy(&proc.voltage_kv, &p[0], 4);
                    memcpy(&proc.current_na, &p[4], 4);
                    memcpy(&proc.flow_mlh,   &p[8], 4);
                    memcpy(&proc.drum_rpm,   &p[12], 4);
                    memcpy(&proc.temp_c,     &p[16], 4);
                    memcpy(&proc.rh_pct,     &p[20], 4);
                    proc.jet_state = p[24];
                    memcpy(&proc.jet_sigma_na, &p[25], 4);
                    memcpy(&proc.elapsed_s,    &p[29], 4);

                    ESP_LOGI(TAG, "HV: %.1f kV, I: %.0f nA, %s, T: %.1f, RH: %.1f",
                             proc.voltage_kv, proc.current_na,
                             proc.jet_state < 5 ? JET_STATE_NAMES[proc.jet_state] : "?",
                             proc.temp_c, proc.rh_pct);
                }
            }
        }
        /* In a real build: forward to BLE notifications and Wi-Fi websocket */
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Gossamer Spin radio booting...");
    nvs_flash_init();

    /* UART0 @ 460800 (STM32 link) */
    uart_config_t u0 = { .baud_rate=460800, .data_bits=UART_DATA_8_BITS,
        .parity=UART_PARITY_DISABLE, .stop_bits=UART_STOP_BITS_1,
        .flow_ctrl=UART_HW_FLOWCTRL_DISABLE, .source_clk=UART_SCLK_APB };
    uart_driver_install(UART_STM, BUF_SZ*2, BUF_SZ*2, 0, NULL, 0);
    uart_param_config(UART_STM, &u0);
    uart_set_pin(UART_STM, 3, 2, -1, -1);

    xTaskCreate(link_task, "link", 6144, NULL, 5, NULL);

    /* BLE + Wi-Fi init would go here (see esp_wifi / esp_bt components).
       BLE GATT server:
         - Service UUID: 00009501-...
         - Process data characteristic: notify on new data
         - Command characteristic: write to start/stop/select recipe
       Wi-Fi AP + HTTP server:
         - Serve a web page with live Chart.js process graphs */

    ESP_LOGI(TAG, "Link task started. BLE/Wi-Fi placeholders ready.");
}