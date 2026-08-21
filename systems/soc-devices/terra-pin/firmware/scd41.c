/**
 * terra_pin/scd41.c — Sensirion SCD41 NDIR CO2 sensor driver
 *
 * Dual SCD41 sensors are on the same I2C address (0x62) behind a TCA9548A
 * multiplexer. This driver manages mux channel selection and provides
 * separate API calls for the chamber and ambient sensors.
 *
 * I2C bus: GPIO6 (SCL), GPIO7 (SDA), 100 kHz
 */

#include "scd41.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

static const char *TAG = "SCD41";

/* ── Low-level I2C helpers ────────────────────────────────────────── */

static esp_err_t i2c_write_cmd(uint8_t addr, uint16_t cmd)
{
    uint8_t buf[2] = { (cmd >> 8) & 0xFF, cmd & 0xFF };
    i2c_cmd_handle_t cmd_handle = i2c_cmd_link_create();
    i2c_master_start(cmd_handle);
    i2c_master_write_byte(cmd_handle, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(cmd_handle, buf, 2, true);
    i2c_master_stop(cmd_handle);
    esp_err_t ret = i2c_master_cmd_begin(SCD41_I2C_PORT, cmd_handle,
                                         pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd_handle);
    return ret;
}

static esp_err_t i2c_read_words(uint8_t addr, uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_READ, true);
    for (size_t i = 0; i < len; i++) {
        i2c_master_read_byte(cmd, &data[i],
                             (i == len - 1) ? I2C_MASTER_LAST_NACK
                                            : I2C_MASTER_ACK);
    }
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(SCD41_I2C_PORT, cmd,
                                         pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret;
}

/* CRC-8 as per Sensirion specification: poly 0x31, init 0xFF */
static uint8_t scd41_crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0xFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x31;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* ── TCA9548A mux channel selection ───────────────────────────────── */

static esp_err_t tca9548a_select(uint8_t channel)
{
    uint8_t mask = (1 << channel);
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (TCA9548A_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, mask, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(SCD41_I2C_PORT, cmd,
                                         pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(cmd);
    if (ret != ESP_OK)
        ESP_LOGE(TAG, "TCA9548A select ch%d failed: %s", channel,
                 esp_err_to_name(ret));
    return ret;
}

esp_err_t scd41_select_channel(uint8_t ch)
{
    return tca9548a_select(ch);
}

/* ── SCD41 public API ─────────────────────────────────────────────── */

static esp_err_t scd41_read_raw(uint16_t *co2, float *temp, float *rh)
{
    esp_err_t ret = i2c_write_cmd(SCD41_I2C_ADDR, SCD41_CMD_READ_MEASUREMENT);
    if (ret != ESP_OK) return ret;

    vTaskDelay(pdMS_TO_TICKS(SCD41_MEASURE_DELAY_MS));

    /* 3 words × (2 data + 1 CRC) = 9 bytes */
    uint8_t buf[9];
    ret = i2c_read_words(SCD41_I2C_ADDR, buf, sizeof(buf));
    if (ret != ESP_OK) return ret;

    /* Validate CRC for each word */
    for (int i = 0; i < 3; i++) {
        if (scd41_crc8(&buf[i * 3], 2) != buf[i * 3 + 2]) {
            ESP_LOGE(TAG, "CRC error word %d", i);
            return ESP_ERR_INVALID_CRC;
        }
    }

    *co2 = (buf[0] << 8) | buf[1];
    /* T = -45 + 175 * (raw / 2^16) */
    uint16_t t_raw = (buf[3] << 8) | buf[4];
    *temp = -45.0f + 175.0f * (float)t_raw / 65536.0f;
    /* RH = 100 * (raw / 2^16) */
    uint16_t rh_raw = (buf[6] << 8) | buf[7];
    *rh = 100.0f * (float)rh_raw / 65536.0f;

    return ESP_OK;
}

esp_err_t scd41_init(void)
{
    ESP_LOGI(TAG, "Initializing SCD41 dual sensors via TCA9548A");

    /* Configure I2C master */
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = SCD41_I2C_FREQ,
    };
    esp_err_t ret = i2c_param_config(SCD41_I2C_PORT, &conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C config failed: %s", esp_err_to_name(ret));
        return ret;
    }
    i2c_driver_install(SCD41_I2C_PORT, I2C_MODE_MASTER, 0, 0, 0);

    /* Reset both SCD41 sensors */
    gpio_set_direction(PIN_SCD41_RESET, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_SCD41_RESET, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(PIN_SCD41_RESET, 1);
    vTaskDelay(pdMS_TO_TICKS(100));

    /* Reinit each sensor */
    for (uint8_t ch = 0; ch < 2; ch++) {
        tca9548a_select(ch == 0 ? TCA9548A_CH_CHAMBER : TCA9548A_CH_AMBIENT);
        vTaskDelay(pdMS_TO_TICKS(5));
        i2c_write_cmd(SCD41_I2C_ADDR, SCD41_CMD_REINIT);
        vTaskDelay(pdMS_TO_TICKS(20));
    }

    /* Deselect mux (no channel active to save power) */
    tca9548a_select(0);

    ESP_LOGI(TAG, "SCD41 init complete");
    return ESP_OK;
}

esp_err_t scd41_measure_chamber(uint16_t *co2, float *temp, float *rh)
{
    xSemaphoreTake(g_i2c_mutex, portMAX_DELAY);
    tca9548a_select(TCA9548A_CH_CHAMBER);
    vTaskDelay(pdMS_TO_TICKS(5));
    esp_err_t ret = scd41_read_raw(co2, temp, rh);
    tca9548a_select(0);
    xSemaphoreGive(g_i2c_mutex);
    return ret;
}

esp_err_t scd41_measure_ambient(uint16_t *co2, float *temp, float *rh)
{
    xSemaphoreTake(g_i2c_mutex, portMAX_DELAY);
    tca9548a_select(TCA9548A_CH_AMBIENT);
    vTaskDelay(pdMS_TO_TICKS(5));
    esp_err_t ret = scd41_read_raw(co2, temp, rh);
    tca9548a_select(0);
    xSemaphoreGive(g_i2c_mutex);
    return ret;
}

esp_err_t scd41_start_periodic_chamber(void)
{
    xSemaphoreTake(g_i2c_mutex, portMAX_DELAY);
    tca9548a_select(TCA9548A_CH_CHAMBER);
    vTaskDelay(pdMS_TO_TICKS(5));
    esp_err_t ret = i2c_write_cmd(SCD41_I2C_ADDR, SCD41_CMD_START_PERIODIC);
    tca9548a_select(0);
    xSemaphoreGive(g_i2c_mutex);
    /* First measurement available after 5 s */
    vTaskDelay(pdMS_TO_TICKS(5000));
    return ret;
}

esp_err_t scd41_stop_periodic_chamber(void)
{
    xSemaphoreTake(g_i2c_mutex, portMAX_DELAY);
    tca9548a_select(TCA9548A_CH_CHAMBER);
    esp_err_t ret = i2c_write_cmd(SCD41_I2C_ADDR, SCD41_CMD_STOP_PERIODIC);
    tca9548a_select(0);
    xSemaphoreGive(g_i2c_mutex);
    /* Wait for stop to take effect */
    vTaskDelay(pdMS_TO_TICKS(500));
    return ret;
}