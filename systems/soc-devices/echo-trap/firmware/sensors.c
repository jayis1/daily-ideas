/*
 * sensors.c — I2C sensor drivers (SHT40, TSL2591, MAX17048)
 *
 * All three sensors share the ESP32-S3 I2C bus (GPIO14 SDA / GPIO15 SCL)
 * with 4.7 kΩ pull-ups.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "sensors.h"
#include "esp_log.h"
#include "driver/i2c.h"
#include <string.h>

static const char *TAG = "sensors";

/* ---- I2C helpers ---- */
static esp_err_t i2c_write(uint8_t dev_addr, const uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(cmd, data, len, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret;
}

static esp_err_t i2c_read(uint8_t dev_addr, uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_READ, true);
    for (size_t i = 0; i < len; i++) {
        i2c_master_read_byte(cmd, data + i, (i == len - 1) ? true : false);
    }
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret;
}

/* ---- SHT40 (Sensirion) ---- */
static void sht40_read(float *temp_c, float *humidity_pct)
{
    uint8_t cmd = 0xFD;  /* high repeatability, clock stretching */
    i2c_write(SHT40_ADDR, &cmd, 1);
    vTaskDelay(pdMS_TO_TICKS(10));  /* measurement time ~8 ms */

    uint8_t data[6];
    if (i2c_read(SHT40_ADDR, data, 6) != ESP_OK) {
        *temp_c = -999.0f;
        *humidity_pct = -1.0f;
        return;
    }

    /* Convert raw to physical values */
    uint16_t t_raw = (data[0] << 8) | data[1];
    uint16_t rh_raw = (data[3] << 8) | data[4];
    *temp_c = -45.0f + 175.0f * (float)t_raw / 65535.0f;
    *humidity_pct = 100.0f * (float)rh_raw / 65535.0f;

    /* Clamp humidity */
    if (*humidity_pct > 100.0f) *humidity_pct = 100.0f;
    if (*humidity_pct < 0.0f) *humidity_pct = 0.0f;
}

/* ---- TSL2591 (AMS) ---- */
static void tsl2591_init(void)
{
    uint8_t cfg[2] = { 0xA1, 0x00 };  /* enable power + ALS */
    i2c_write(TSL2591_ADDR, cfg, 2);
    /* Integration time 600ms, gain 25x */
    uint8_t timing[2] = { 0xA1, 0x17 };
    i2c_write(TSL2591_ADDR, timing, 2);
}

static void tsl2591_read(float *lux)
{
    uint8_t reg = 0xB4;  /* CH0 data low */
    uint8_t data[2];
    if (i2c_write(TSL2591_ADDR, &reg, 1) != ESP_OK ||
        i2c_read(TSL2591_ADDR, data, 2) != ESP_OK) {
        *lux = -1.0f;
        return;
    }
    uint16_t ch0 = (data[1] << 8) | data[0];
    reg = 0xB6;  /* CH1 data low */
    i2c_write(TSL2591_ADDR, &reg, 1);
    i2c_read(TSL2591_ADDR, data, 2);
    uint16_t ch1 = (data[1] << 8) | data[0];

    /* Simplified lux calculation (TSL2591 package formula) */
    float cpl = 600.0f * 25.0f / 32768.0f;  /* integration × gain / 2^15 */
    float ratio = (ch0 > 0) ? (float)ch1 / (float)ch0 : 0.0f;
    float factor = (ratio < 0.5f) ? (0.0304f - 0.062f * ratio) :
                   (ratio < 0.61f) ? (0.0224f - 0.031f * ratio) :
                   0.0128f;
    *lux = (float)(ch0 - ch1) * cpl * factor;
    if (*lux < 0.0f) *lux = 0.0f;
}

/* ---- MAX17048 (fuel gauge) ---- */
static void max17048_read(uint8_t *battery_pct)
{
    uint8_t reg = 0x02;  /* SOC register */
    uint8_t data[2];
    if (i2c_write(MAX17048_ADDR, &reg, 1) != ESP_OK ||
        i2c_read(MAX17048_ADDR, data, 2) != ESP_OK) {
        *battery_pct = 0;
        return;
    }
    /* SOC is in 1/256 % per bit, upper byte = integer % */
    *battery_pct = data[0];
}

void sensors_init(void)
{
    ESP_LOGI(TAG, "Initializing I2C sensors (SHT40, TSL2591, MAX17048)");

    /* Configure I2C master */
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 100000,
    };
    i2c_param_config(I2C_NUM_0, &conf);
    i2c_driver_install(I2C_NUM_0, conf.mode, 0, 0, 0);

    tsl2591_init();
}

void sensors_read_all(float *temp_c, float *humidity_pct,
                      float *light_lux, uint8_t *battery_pct)
{
    sht40_read(temp_c, humidity_pct);
    tsl2591_read(light_lux);
    max17048_read(battery_pct);
}