/**
 * terra_pin/ezo_orp.c — Atlas Scientific EZO-ORP redox sensor driver
 *
 * UART interface at 9600 baud. Atlas EZO protocol:
 *   - Command: ASCII + '\r' (0x0D)
 *   - Response: status_byte + data_string + '\r'
 *   - Status: 1=success, 2=failed, 254=pending, 255=no_data
 *
 * ORP command set:
 *   "R"         — single reading → returns "ORP_value_in_mV"
 *   "Cal,228"   — calibrate to 228 mV (ZoBell's solution)
 *   "Cal,?"     — read calibration state
 *   "Cal,clear" — clear calibration
 *   "I"         — device info
 *   "Sleep"     — enter sleep mode
 */

#include "ezo_orp.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <stdlib.h>

static const char *TAG = "EZO-ORP";

esp_err_t ezo_orp_init(void)
{
    ESP_LOGI(TAG, "Initializing EZO-ORP on UART%d (TX=GPIO%d, RX=GPIO%d)",
             UART_ORP_NUM, PIN_UART_ORP_TX, PIN_UART_ORP_RX);

    uart_config_t uart_cfg = {
        .baud_rate  = EZO_BAUD,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_NONE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t ret = uart_param_config(UART_ORP_NUM, &uart_cfg);
    if (ret != ESP_OK) return ret;

    ret = uart_set_pin(UART_ORP_NUM, PIN_UART_ORP_TX, PIN_UART_ORP_RX,
                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (ret != ESP_OK) return ret;

    ret = uart_driver_install(UART_ORP_NUM, EZO_ORP_BUF_SIZE * 2, 0, 0, NULL, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "EZO-ORP initialized");
    return ESP_OK;
}

static esp_err_t ezo_send_cmd(const char *cmd, char *response, size_t resp_len)
{
    /* Flush RX buffer */
    uart_flush_input(UART_ORP_NUM);

    /* Send command + CR */
    uart_write_bytes(UART_ORP_NUM, cmd, strlen(cmd));
    uint8_t cr = 0x0D;
    uart_write_bytes(UART_ORP_NUM, &cr, 1);

    /* Read response — wait up to 900 ms for reading commands */
    int len = uart_read_bytes(UART_ORP_NUM, (uint8_t *)response, resp_len - 1,
                              pdMS_TO_TICKS(EZO_TIMEOUT_MS));
    if (len <= 0) {
        ESP_LOGE(TAG, "No response from EZO-ORP");
        return ESP_ERR_TIMEOUT;
    }
    response[len] = '\0';

    /* First byte is status code */
    if (response[0] != 1) {
        ESP_LOGE(TAG, "EZO-ORP error status: %d", response[0]);
        return ESP_ERR_INVALID_RESPONSE;
    }

    /* Shift past status byte */
    memmove(response, response + 1, len - 1);
    response[len - 1] = '\0';

    return ESP_OK;
}

esp_err_t ezo_orp_read(int16_t *orp_mv)
{
    char response[EZO_ORP_BUF_SIZE];
    esp_err_t ret = ezo_send_cmd("R", response, sizeof(response));
    if (ret != ESP_OK) return ret;

    /* Response is like "?22.3" or "421.5" — parse float */
    char *p = response;
    if (*p == '?') p++;  /* some firmware prefixes with ? */

    float val = strtof(p, NULL);
    *orp_mv = (int16_t)(val + (val >= 0 ? 0.5f : -0.5f));

    ESP_LOGI(TAG, "ORP: %d mV", *orp_mv);
    return ESP_OK;
}