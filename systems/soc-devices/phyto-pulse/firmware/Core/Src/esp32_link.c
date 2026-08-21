/*
 * esp32_link.c — UART protocol to ESP32-C3
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Protocol: simple framed JSON packets over USART1 @ 460800 baud.
 * Each packet: {len_hi, len_lo, JSON...}
 */

#include "esp32_link.h"
#include "main.h"
#include <string.h>
#include <stdio.h>

extern UART_HandleTypeDef huart1;

#define TX_BUF_SIZE 256
#define RX_BUF_SIZE 128

static char g_tx_buf[TX_BUF_SIZE];
static uint8_t g_rx_buf[RX_BUF_SIZE];
static esp32_cmd_callback_t g_cmd_cb = NULL;
static bool g_esp_enabled = false;
static int  g_rx_idx = 0;

int esp32_link_init(void)
{
    /* Enable ESP32-C3 */
    esp32_link_enable(true);
    HAL_Delay(100);

    /* Start receiving UART */
    HAL_UART_Receive_IT(&huart1, g_rx_buf, 1);
    g_rx_idx = 0;
    return 0;
}

void esp32_link_enable(bool enable)
{
    HAL_GPIO_WritePin(ESP_EN_GPIO_Port, ESP_EN_Pin,
                      enable ? GPIO_PIN_SET : GPIO_PIN_RESET);
    g_esp_enabled = enable;
}

static void send_packet(const char *json, int len)
{
    if (!g_esp_enabled) return;
    if (len > TX_BUF_SIZE - 4) len = TX_BUF_SIZE - 4;

    /* Frame: [0xAA] [len_hi] [len_lo] [json...] [0x55] */
    uint8_t header[3] = { 0xAA, (uint8_t)(len >> 8), (uint8_t)(len & 0xFF) };
    HAL_UART_Transmit(&huart1, header, 3, 10);
    HAL_UART_Transmit(&huart1, (uint8_t *)json, len, 20);
    uint8_t trailer = 0x55;
    HAL_UART_Transmit(&huart1, &trailer, 1, 10);
}

int esp32_link_send_sample(float voltage_mv, uint32_t timestamp_ms, float gain)
{
    int len = snprintf(g_tx_buf, TX_BUF_SIZE,
        "{\"t\":\"s\",\"ts\":%lu,\"v\":%.3f,\"g\":%.0f}",
        (unsigned long)timestamp_ms, voltage_mv, gain);
    send_packet(g_tx_buf, len);
    return 0;
}

int esp32_link_send_event(const spike_event_t *event)
{
    const char *cls = (event->classification == EVENT_AP) ? "AP" :
                      (event->classification == EVENT_VP) ? "VP" : "ART";
    int len = snprintf(g_tx_buf, TX_BUF_SIZE,
        "{\"t\":\"e\",\"ts\":%lu,\"c\":\"%s\",\"a\":%.2f,\"d\":%.0f,\"conf\":%.2f}",
        (unsigned long)event->timestamp_ms, cls,
        event->amplitude_mv, event->duration_ms, event->confidence);
    send_packet(g_tx_buf, len);
    return 0;
}

int esp32_link_send_swp(const swp_result_t *result)
{
    int len = snprintf(g_tx_buf, TX_BUF_SIZE,
        "{\"t\":\"swp\",\"ts\":%lu,\"mean\":%.3f,\"pp\":%.3f,\"slope\":%.3f}",
        (unsigned long)result->timestamp_ms,
        result->mean_mv, result->peak_to_peak, result->slope_mV_per_min);
    send_packet(g_tx_buf, len);
    return 0;
}

int esp32_link_send_status(float battery_v, float gain, const char *state)
{
    int len = snprintf(g_tx_buf, TX_BUF_SIZE,
        "{\"t\":\"stat\",\"bat\":%.2f,\"g\":%.0f,\"st\":\"%s\"}",
        battery_v, gain, state);
    send_packet(g_tx_buf, len);
    return 0;
}

void esp32_link_set_cmd_callback(esp32_cmd_callback_t cb)
{
    g_cmd_cb = cb;
}

void esp32_link_process(void)
{
    /* Check for complete received command (terminated by '\n') */
    /* In a full implementation, this parses incoming JSON commands
     * like {"cmd":"start"}, {"cmd":"stop"}, {"cmd":"stim"}, {"cmd":"exp","id":0} */
    /* Simplified: just reset rx index periodically */
    if (g_rx_idx >= RX_BUF_SIZE - 1) {
        g_rx_idx = 0;
    }
}

/* UART RX callback */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart1) {
        if (g_rx_idx < RX_BUF_SIZE - 1) {
            g_rx_buf[g_rx_idx++] = 0;  /* placeholder; real impl captures byte */
        }
        HAL_UART_Receive_IT(&huart1, g_rx_buf, 1);
    }
}