/**
 * bme280_driver.c — BME280 T/H/P sensor driver
 *
 * I²C address: 0x76
 * Used for air-density compensation (speed of sound varies with temperature).
 */

#include "bme280_driver.h"
#include "esp_log.h"
#include "driver/i2c.h"

static const char *TAG = "bme280";

#define I2C_SDA     15
#define I2C_SCL     16
#define I2C_PORT    I2C_NUM_0
#define BME280_ADDR 0x76

/* BME280 registers */
#define REG_CTRL_HUM   0xF2
#define REG_CTRL_MEAS  0xF4
#define REG_CONFIG     0xF5
#define REG_PRESS_MSB  0xF7
#define REG_TEMP_MSB   0xFA
#define REG_HUM_MSB    0xFD
#define REG_CHIP_ID   0xD0

/* Calibration data (read at init) */
static uint16_t dig_T1;
static int16_t  dig_T2, dig_T3;
static uint16_t dig_P1;
static int16_t  dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
static uint8_t  dig_H1, dig_H3;
static int16_t  dig_H2, dig_H4, dig_H5, dig_H6;

static int32_t t_fine;

static int i2c_write(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = {reg, val};
    return i2c_master_write_to_device(I2C_PORT, BME280_ADDR, buf, 2, 100);
}

static int i2c_read(uint8_t reg, uint8_t *buf, uint8_t len) {
    return i2c_master_write_read_device(I2C_PORT, BME280_ADDR, &reg, 1, buf, len, 100);
}

int bme280_init(void) {
    ESP_LOGI(TAG, "Initializing BME280");

    /* Configure I²C bus */
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA,
        .scl_io_num = I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 100000,
    };
    i2c_param_config(I2C_PORT, &conf);
    i2c_driver_install(I2C_PORT, I2C_MODE_MASTER, 0, 0, 0);

    /* Check chip ID */
    uint8_t chip_id = 0;
    i2c_read(REG_CHIP_ID, &chip_id, 1);
    if (chip_id != 0x60) {
        ESP_LOGE(TAG, "BME280 not found (chip_id=0x%02X)", chip_id);
        return -1;
    }

    /* Read calibration data */
    uint8_t cal[24];
    i2c_read(0x88, cal, 24);
    dig_T1 = (cal[1] << 8) | cal[0];
    dig_T2 = (cal[3] << 8) | cal[2];
    dig_T3 = (cal[5] << 8) | cal[4];
    dig_P1 = (cal[7] << 8) | cal[6];
    dig_P2 = (cal[9] << 8) | cal[8];
    dig_P3 = (cal[11] << 8) | cal[10];
    dig_P4 = (cal[13] << 8) | cal[12];
    dig_P5 = (cal[15] << 8) | cal[14];
    dig_P6 = (cal[17] << 8) | cal[16];
    dig_P7 = (cal[19] << 8) | cal[18];
    dig_P8 = (cal[21] << 8) | cal[20];
    dig_P9 = (cal[23] << 8) | cal[22];

    uint8_t cal_h[7];
    i2c_read(0xA1, cal_h, 1);
    dig_H1 = cal_h[0];
    i2c_read(0xE1, cal_h, 7);
    dig_H2 = (cal_h[1] << 8) | cal_h[0];
    dig_H3 = cal_h[2];
    dig_H4 = (cal_h[3] << 4) | (cal_h[4] & 0x0F);
    dig_H5 = (cal_h[5] << 4) | (cal_h[4] >> 4);
    dig_H6 = cal_h[6];

    /* Configure: oversampling ×1, normal mode */
    i2c_write(REG_CTRL_HUM, 0x01);   /* Humidity oversampling ×1 */
    i2c_write(REG_CTRL_MEAS, 0x27);  /* Temp ×1, Press ×1, Normal mode */
    i2c_write(REG_CONFIG, 0x00);     /* Standby 0.5ms */

    ESP_LOGI(TAG, "BME280 initialized (chip_id=0x60)");
    return 0;
}

/* BME280 compensation functions (from datasheet) */
static int32_t compensate_temp(int32_t adc_T) {
    double var1 = (((double)adc_T) / 16384.0 - ((double)dig_T1) / 1024.0) *
                  ((double)dig_T2);
    double var2 = ((((double)adc_T) / 131072.0 - ((double)dig_T1) / 8192.0) *
                  (((double)adc_T) / 131072.0 - ((double)dig_T1) / 8192.0)) *
                  ((double)dig_T3);
    t_fine = (int32_t)(var1 + var2);
    return (int32_t)((var1 + var2) / 5120.0);
}

static uint32_t compensate_press(int32_t adc_P) {
    double var1 = ((double)t_fine / 2.0) - 64000.0;
    double var2 = var1 * var1 * ((double)dig_P6) / 32768.0;
    var2 += var1 * ((double)dig_P5) * 2.0;
    var2 = (var2 / 4.0) + (((double)dig_P4) * 65536.0);
    var1 = (((double)dig_P3) * var1 * var1 / 524288.0 +
            ((double)dig_P2) * var1) / 524288.0;
    var1 = (1.0 + var1 / 32768.0) * ((double)dig_P1);
    if (var1 < 0.0000001) return 0;
    double p = 1048576.0 - (double)adc_P;
    p = (p - (var2 / 4096.0)) * 6250.0 / var1;
    var1 = ((double)dig_P9) * p * p / 2147483648.0;
    var2 = p * ((double)dig_P8) / 32768.0;
    p += (var1 + var2 + ((double)dig_P7)) / 16.0;
    return (uint32_t)p;
}

static uint32_t compensate_hum(int32_t adc_H) {
    double v_x1 = t_fine - 76800.0;
    v_x1 = ((((adc_H << 14) - (((double)dig_H4) << 20) -
              (((double)dig_H5) * v_x1) + ((double)(1 << 14))) / 16384.0) *
             (((((v_x1 * ((double)dig_H6)) / 100.0) *
                (((v_x1 * ((double)dig_H3)) / 2048.0 + 1.0)) / 4096.0) + 1.0) / 2.0)) *
             ((((1.0 << 14) - ((double)adc_H)) - (((v_x1 * ((double)dig_H2)) / 100.0)) + 1.0) / 2.0) / 4096.0;
    v_x1 *= 100.0;
    if (v_x1 > 100.0) v_x1 = 100.0;
    if (v_x1 < 0.0) v_x1 = 0.0;
    return (uint32_t)v_x1;
}

int bme280_read(float *temp, float *hum, float *pres) {
    uint8_t data[8];
    i2c_read(REG_PRESS_MSB, data, 8);

    int32_t adc_P = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4);
    int32_t adc_T = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4);
    int32_t adc_H = (data[6] << 8) | data[7];

    if (temp) *temp = (float)compensate_temp(adc_T) / 100.0f;
    if (pres) *pres = (float)compensate_press(adc_P) / 100.0f;
    if (hum)  *hum  = (float)compensate_hum(adc_H);

    return 0;
}