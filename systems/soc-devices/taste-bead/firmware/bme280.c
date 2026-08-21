/* bme280.c — BME280 temperature/humidity/pressure sensor driver
 *
 * Minimal I2C driver for the Bosch BME280. Reads raw ADC values and
 * applies the factory calibration coefficients stored in the sensor.
 */

#include "bme280.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include "driver/i2c.h"
#include <string.h>

static const char *TAG = "bme280";

/* BME280 register addresses */
#define BME280_REG_ID           0xD0
#define BME280_REG_RESET       0xE0
#define BME280_REG_CTRL_HUM    0xF2
#define BME280_REG_STATUS      0xF3
#define BME280_REG_CTRL_MEAS   0xF4
#define BME280_REG_CONFIG      0xF5
#define BME280_REG_CALIB00     0x88
#define BME280_REG_CALIB26     0xE1
#define BME280_REG_DATA        0xF7

/* Calibration coefficients */
static struct {
    uint16_t dig_T1;
    int16_t  dig_T2, dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2, dig_P3, dig_P4, dig_P5;
    int16_t  dig_P6, dig_P7, dig_P8, dig_P9;
    uint8_t  dig_H1;
    int16_t  dig_H2;
    uint8_t  dig_H3;
    int16_t  dig_H4, dig_H5;
    int8_t   dig_H6;
} cal;

static int32_t t_fine;

static esp_err_t i2c_read(uint8_t reg, uint8_t *data, int len)
{
    return i2c_master_write_read_device(I2C_NUM_0, BME280_I2C_ADDR,
                                          &reg, 1, data, len,
                                          pdMS_TO_TICKS(100));
}

static esp_err_t i2c_write(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    return i2c_master_write_to_device(I2C_NUM_0, BME280_I2C_ADDR,
                                        buf, 2, pdMS_TO_TICKS(100));
}

esp_err_t bme280_init(int sda_pin, int scl_pin)
{
    /* I2C bus should already be initialized by display_init() */
    /* Verify sensor ID */
    uint8_t id;
    esp_err_t ret = i2c_read(BME280_REG_ID, &id, 1);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BME280 not found: %s", esp_err_to_name(ret));
        return ret;
    }
    if (id != 0x60) {
        ESP_LOGE(TAG, "BME280 wrong ID: 0x%02X (expected 0x60)", id);
        return ESP_ERR_NOT_FOUND;
    }

    /* Read calibration coefficients */
    uint8_t calib[32];
    i2c_read(BME280_REG_CALIB00, calib, 24);
    i2c_read(BME280_REG_CALIB26, calib + 24, 7);

    /* Parse calibration data */
    cal.dig_T1 = (calib[1] << 8) | calib[0];
    cal.dig_T2 = (calib[3] << 8) | calib[2];
    cal.dig_T3 = (calib[5] << 8) | calib[4];
    cal.dig_P1 = (calib[7] << 8) | calib[6];
    cal.dig_P2 = (calib[9] << 8) | calib[8];
    cal.dig_P3 = (calib[11] << 8) | calib[10];
    cal.dig_P4 = (calib[13] << 8) | calib[12];
    cal.dig_P5 = (calib[15] << 8) | calib[14];
    cal.dig_P6 = (calib[17] << 8) | calib[16];
    cal.dig_P7 = (calib[19] << 8) | calib[18];
    cal.dig_P8 = (calib[21] << 8) | calib[20];
    cal.dig_P9 = (calib[23] << 8) | calib[22];
    cal.dig_H1 = calib[24];
    cal.dig_H2 = (calib[26] << 8) | calib[25];
    cal.dig_H3 = calib[27];
    cal.dig_H4 = ((int16_t)calib[28] << 4) | (calib[29] & 0x0F);
    cal.dig_H5 = ((int16_t)calib[30] << 4) | (calib[29] >> 4);
    cal.dig_H6 = (int8_t)calib[31];

    /* Configure sensor: humidity x1, temp/press x1, normal mode */
    i2c_write(BME280_REG_CTRL_HUM, 0x01);  /* humidity oversampling x1 */
    i2c_write(BME280_REG_CONFIG, 0xA0);    /* 1000ms standby, filter off */
    i2c_write(BME280_REG_CTRL_MEAS, 0x27); /* temp/press x1, normal mode */

    ESP_LOGI(TAG, "BME280 initialized (ID=0x60)");
    return ESP_OK;
}

esp_err_t bme280_read(bme280_data_t *data)
{
    uint8_t raw[8];
    esp_err_t ret = i2c_read(BME280_REG_DATA, raw, 8);
    if (ret != ESP_OK) return ret;

    /* Parse raw values */
    int32_t adc_T = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4);
    int32_t adc_P = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4);
    int32_t adc_H = (raw[6] << 8) | raw[7];

    /* Temperature compensation (Bosch datasheet algorithm) */
    int32_t var1 = (((adc_T >> 3) - ((int32_t)cal.dig_T1 << 1)) *
                     ((int32_t)cal.dig_T2)) >> 11;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)cal.dig_T1)) *
                       ((adc_T >> 4) - ((int32_t)cal.dig_T1))) >> 12) *
                     ((int32_t)cal.dig_T3)) >> 14;
    t_fine = var1 + var2;
    data->temperature = (t_fine * 5 + 128) >> 8;
    data->temperature /= 100.0f;

    /* Pressure compensation (simplified) */
    int64_t p_var = ((int64_t)t_fine) - 128000;
    p_var = (((((p_var >> 2) * ((int64_t)cal.dig_P6)) >> 11) +
              (((p_var * ((int64_t)cal.dig_P5)) >> 2) << 13)) * 65536) +
            (((((p_var >> 2) * ((int64_t)cal.dig_P4)) << 3) +
              ((p_var * ((int64_t)cal.dig_P3)) << 1) + 4096) << 12) /
            (((((p_var >> 2) * ((int64_t)cal.dig_P3)) >> 3) +
              (((((int64_t)t_fine) - 128000) * 4096) << 4) + 8192) >> 13);
    int32_t p = (int32_t)(1048576 - adc_P);
    p = (p - (p_var >> 12)) * 6250;
    p = p / ((((((p_var * ((int64_t)cal.dig_P9)) + 8192) >> 12) * 3) >> 1) +
              ((int64_t)cal.dig_P8));
    p = p << 10;
    p >>= 10;
    data->pressure = (float)p / 100.0f; /* Pa → hPa */

    /* Humidity compensation */
    int32_t h_var = ((int32_t)t_fine) - 76800;
    int32_t h = ((((adc_H << 14) - (((int32_t)cal.dig_H4) << 20) -
                   (((int32_t)cal.dig_H5) * h_var)) + 16384) >> 15) *
                 ((((((((h_var * ((int32_t)cal.dig_H6)) >> 10) *
                       (((h_var * ((int32_t)cal.dig_H3)) >> 11) + 32768)) >> 10) +
                    2097152) * ((int32_t)cal.dig_H2)) + 8192) >> 12));
    h = h - (((((h >> 15) * (h >> 15)) >> 7) * cal.dig_H1) >> 4);
    h = (h < 0) ? 0 : (h > 419430400) ? 419430400 : h;
    data->humidity = (float)(h >> 12) / 1024.0f;

    return ESP_OK;
}