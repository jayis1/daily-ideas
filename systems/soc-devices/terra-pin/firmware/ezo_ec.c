/**
 * terra_pin/ezo_ec.c — Atlas Scientific EZO-EC conductivity sensor driver
 *
 * UART interface at 9600 baud. Atlas EZO protocol (same as ORP):
 *   - Command: ASCII + '\r'
 *   - Response: status_byte + data + '\r'
 *
 * EC command set:
 *   "R"           — single reading → "EC_value,TDS,salinity,SG"
 *   "Cal,dry"     — calibrate dry probe (0 µS)
 *   "Cal,low,1413"— calibrate with 1413 µS/cm KCl standard
 *   "Cal,?"       — read calibration state
 *   "K,?"         — read probe K value
 *   "T,?"         — read temp compensation value
 *   "Sleep"       — enter sleep mode
 */

#include "ezo_ec.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <stdlib.h>

static const char *TAG = "EZO-EC";

esp_err_t ezo_ec_init(void)
{
    ESP_LOGI(TAG, "Initializing EZO-EC on UART%d (TX=GPIO%d, RX=GPIO%d)",
             UART_EC_NUM, PIN_UART_EC_TX, PIN_UART_EC_RX);

    uart_config_t uart_cfg = {
        .baud_rate  = EZO_BAUD,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_NONE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t ret = uart_param_config(UART_EC_NUM, &uart_cfg);
    if (ret != ESP_OK) return ret;

    ret = uart_set_pin(UART_EC_NUM, PIN_UART_EC_TX, PIN_UART_EC_RX,
                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (ret != ESP_OK) return ret;

    ret = uart_driver_install(UART_EC_NUM, EZO_EC_BUF_SIZE * 2, 0, 0, NULL, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "EZO-EC initialized");
    return ESP_OK;
}

static esp_err_t ezo_ec_send(const char *cmd, char *response, size_t resp_len)
{
    uart_flush_input(UART_EC_NUM);

    uart_write_bytes(UART_EC_NUM, cmd, strlen(cmd));
    uint8_t cr = 0x0D;
    uart_write_bytes(UART_EC_NUM, &cr, 1);

    int len = uart_read_bytes(UART_EC_NUM, (uint8_t *)response, resp_len - 1,
                              pdMS_TO_TICKS(EZO_TIMEOUT_MS));
    if (len <= 0) {
        ESP_LOGE(TAG, "No response from EZO-EC");
        return ESP_ERR_TIMEOUT;
    }
    response[len] = '\0';

    if (response[0] != 1) {
        ESP_LOGE(TAG, "EZO-EC error status: %d", response[0]);
        return ESP_ERR_INVALID_RESPONSE;
    }

    memmove(response, response + 1, len - 1);
    response[len - 1] = '\0';
    return ESP_OK;
}

esp_err_t ezo_ec_read(uint16_t *ec_us, float *temp_comp)
{
    char response[EZO_EC_BUF_SIZE];
    esp_err_t ret = ezo_ec_send("R", response, sizeof(response));
    if (ret != ESP_OK) return ret;

    /* Response format: "EC,TDS,salinity,SG" (comma-separated) */
    char *p = response;
    if (*p == '?') p++;

    /* Parse EC value (first field) */
    char *comma = strchr(p, ',');
    if (comma) *comma = '\0';
    float ec_val = strtof(p, NULL);
    *ec_us = (uint16_t)(ec_val + 0.5f);

    /* Temperature compensation from DS18B20 is handled in main task
       by sending "T,<temp>" command before reading */

    ESP_LOGI(TAG, "EC: %u µS/cm", *ec_us);
    return ESP_OK;
}