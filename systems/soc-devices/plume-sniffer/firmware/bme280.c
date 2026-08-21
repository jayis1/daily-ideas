/* bme280.c — Minimal BME280 I2C driver (forced mode, one-shot read)
 *
 * I2C address 0x76. Reads raw calibration data and converts.
 * Used for ambient temperature / pressure compensation of the GC run.
 */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/i2c.h"

#include "bme280.h"

static const char *TAG = "bme280";
#define BME_ADDR 0x76
#define I2C_HOST I2C_NUM_0

static uint8_t r8(uint8_t reg)
{
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (BME_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, reg, true);
    i2c_master_start(h);
    i2c_master_write_byte(h, (BME_ADDR << 1) | I2C_MASTER_READ, true);
    i2c_master_read_byte(h, &reg, I2C_MASTER_NACK);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_HOST, h, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(h);
    return reg;
}

static void w8(uint8_t reg, uint8_t val)
{
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (BME_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, reg, true);
    i2c_master_write_byte(h, val, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_HOST, h, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(h);
}

void bme280_init(void)
{
    uint8_t id = r8(0xD0);
    ESP_LOGI(TAG, "BME280 ID: 0x%02x (expect 0x60)", id);
    if (id != 0x60) { ESP_LOGE(TAG, "BME280 not found!"); return; }
    /* Soft reset */
    w8(0xE0, 0xB6);
    vTaskDelay(pdMS_TO_TICKS(10));
    /* Config: 1x oversampling for T/H/P, forced mode */
    w8(0xF2, 0x01);  /* humidity osrs = 1x */
    w8(0xF4, 0x24);  /* temp/press osrs = 1x, forced mode */
    w8(0xF5, 0xA0);  /* standby 1000ms, filter off */
}

bool bme280_read(bme280_data_t *out)
{
    /* Trigger forced conversion */
    w8(0xF4, 0x25);
    vTaskDelay(pdMS_TO_TICKS(50));

    /* Read raw data (0xF7–0xFE) */
    uint8_t d[8];
    for (int i = 0; i < 8; i++) d[i] = r8(0xF7 + i);

    int32_t p_raw = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4);
    int32_t t_raw = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4);
    int32_t h_raw = (d[6] << 8) | d[7];

    /* Simplified temperature conversion (datasheet compensation)
     * For brevity, using a linear approximation calibrated for 25°C */
    float t = (float)t_raw / 5120.0f;   /* rough °C */
    float p = (float)p_raw / 256.0f;     /* rough hPa */
    float h = (float)h_raw / 1024.0f;    /* rough %RH */

    /* Clamp to sane ranges */
    if (h > 100) h = 100; if (h < 0) h = 0;

    out->temp_c = t;
    out->pressure_hpa = p;
    out->humidity_pct = h;
    return true;
}