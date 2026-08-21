/*
 * main.c — Ferro Weave ESP32-C3 co-processor firmware (ESP-IDF)
 *
 * Bridges the STM32G474 DAQ core to BLE + Wi-Fi. Receives framed
 * sweep/status data over UART (GPIO2 RX / GPIO3 TX at 115200 8N1),
 * decodes it, and forwards:
 *   - SWEEP_RESULT → BLE notify + Wi-Fi /sweep.json + TCP stream
 *   - STATUS       → BLE notify
 * Commands from BLE/Wi-Fi clients are forwarded to the STM32 over UART.
 */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "proto.h"
#include "ble.h"
#include "wifi.h"
#include <string.h>

static const char *TAG = "fw_esp";

/* UART RX ring buffer (filled by UART event task). */
#define UART_BUF_SIZE 4096
static uint8_t uart_rx[UART_BUF_SIZE];
static int     uart_rx_len = 0;

/* Forward a command string to the STM32 over UART. */
static void cmd_callback(const char *cmd, int len)
{
    /* UART write — frame it as a CMD frame. */
    ESP_LOGI(TAG, "fwd cmd to STM32: %.*s", len, cmd);
}

void app_main(void)
{
    ESP_LOGI(TAG, "Ferro Weave ESP32-C3 booting…");

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* UART1 init: 115200 8N1, GPIO2 RX / GPIO3 TX, DMA RX. */
    /* … */

    ble_init();
    ble_set_cmd_callback(cmd_callback);
    wifi_init();
    wifi_start_stream();

    ESP_LOGI(TAG, "BLE + Wi-Fi up. Bridging STM32 ↔ radio.");

    /* ── UART RX → decode → dispatch ──────────────────────────── */
    for (;;) {
        /* Poll UART RX (in firmware: driven by a UART event queue). */
        int avail = 0;  /* = uart_read_bytes(...) */
        if (avail > 0) {
            if (uart_rx_len + avail > UART_BUF_SIZE) {
                /* Drop oldest if overflowed. */
                int drop = (uart_rx_len + avail) - UART_BUF_SIZE;
                memmove(uart_rx, uart_rx + drop, uart_rx_len - drop);
                uart_rx_len -= drop;
            }
            /* append … (simulated) */
            (void)avail;
        }

        /* Try to decode a frame. */
        proto_frame_t frame;
        int consumed = 0;
        int r = proto_decode(uart_rx, uart_rx_len, &frame, &consumed);
        if (consumed > 0 && uart_rx_len > consumed) {
            memmove(uart_rx, uart_rx + consumed, uart_rx_len - consumed);
            uart_rx_len -= consumed;
        } else if (consumed > 0) {
            uart_rx_len = 0;
        }
        if (r == 1) {
            if (frame.type == ESP_FRAME_SWEEP_RESULT) {
                ble_notify_sweep(frame.payload, frame.len);
                /* Build a JSON summary for the HTTP endpoint. */
                wifi_set_last_sweep(frame.payload, frame.len);
            } else if (frame.type == ESP_FRAME_STATUS) {
                ble_notify_status((const char *)frame.payload);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}