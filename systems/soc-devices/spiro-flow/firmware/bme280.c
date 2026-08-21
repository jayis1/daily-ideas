/**
 * spiro_flow/bme280.c — Bosch BME280 ambient conditions sensor
 *
 * Reads ambient temperature, pressure, and humidity for BTPS correction.
 * I2C address: 0x76 (SDO pin to GND)
 *
 * The BME280 sits in the device handle, open to ambient air.
 * Pressure is reported in mmHg (converted from Pa) for BTPS computation.
 */

#include "main.h"
#include "bme280.h"
#include <string.h>

#define TAG "BME280"

#define BME280_ADDR          0x76

/* BME280 register addresses */
#define BME280_REG_ID        0xD0
#define BME280_REG_RESET     0xE0
#define BME280_REG_CTRL_HUM  0xF2
#define BME280_REG_CTRL_MEAS 0xF4
#define BME280_REG_CONFIG    0xF5
#define BME280_REG_PRESS_MSB 0xF7
#define BME280_REG_CALIB00   0x88  /* dig_P1 */
#define BME280_REG_CALIB26   0xE1  /* dig_H1 */

/* Calibration data */
typedef struct {
    uint16_t dig_T1;
    int16_t  dig_T2;
    int16_t  dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2;
    int16_t  dig_P3;
    int16_t  dig_P4;
    int16_t  dig_P5;
    int16_t  dig_P6;
    int16_t  dig_P7;
    int16_t  dig_P8;
    int16_t  dig_P9;
    uint8_t  dig_H1;
    int16_t  dig_H2;
    uint8_t  dig_H3;
    int16_t  dig_H4;
    int16_t  dig_H5;
    int8_t   dig_H6;
} bme280_calib_t;

static bme280_calib_t s_cal;
static int32_t s_t_fine;

/* ── I2C helpers ───────────────────────────────────────────────────── */

static int i2c_write(uint8_t addr, uint8_t reg, uint8_t val)
{
    (void)addr; (void)reg; (void)val;
    return 0;
}

static int i2c_read(uint8_t addr, uint8_t reg, uint8_t *buf, int len)
{
    (void)addr; (void)reg;
    memset(buf, 0, len);
    return 0;
}

/* ── BME280 driver ─────────────────────────────────────────────────── */

int bme280_init(void)
{
    uint8_t id;
    i2c_read(BME280_ADDR, BME280_REG_ID, &id, 1);
    if (id != 0x60) {
        ESP_LOGW(TAG, "BME280 ID mismatch: 0x%02X (expected 0x60)", id);
        /* continue anyway for simulation */
    }

    /* Read calibration data (26 bytes from 0x88, 7 bytes from 0xE1) */
    uint8_t cal1[26];
    i2c_read(BME280_ADDR, BME280_REG_CALIB00, cal1, 26);

    s_cal.dig_T1 = (uint16_t)((cal1[1] << 8) | cal1[0]);
    s_cal.dig_T2 = (int16_t)((cal1[3] << 8) | cal1[2]);
    s_cal.dig_T3 = (int16_t)((cal1[5] << 8) | cal1[4]);
    s_cal.dig_P1 = (uint16_t)((cal1[7] << 8) | cal1[6]);
    s_cal.dig_P2 = (int16_t)((cal1[9] << 8) | cal1[8]);
    s_cal.dig_P3 = (int16_t)((cal1[11] << 8) | cal1[10]);
    s_cal.dig_P4 = (int16_t)((cal1[13] << 8) | cal1[12]);
    s_cal.dig_P5 = (int16_t)((cal1[15] << 8) | cal1[14]);
    s_cal.dig_P6 = (int16_t)((cal1[17] << 8) | cal1[16]);
    s_cal.dig_P7 = (int16_t)((cal1[19] << 8) | cal1[18]);
    s_cal.dig_P8 = (int16_t)((cal1[21] << 8) | cal1[20]);
    s_cal.dig_P9 = (int16_t)((cal1[23] << 8) | cal1[22]);
    s_cal.dig_H1 = cal1[25];

    uint8_t cal2[7];
    i2c_read(BME280_ADDR, BME280_REG_CALIB26, cal2, 7);
    s_cal.dig_H2 = (int16_t)((cal2[1] << 8) | cal2[0]);
    s_cal.dig_H3 = cal2[2];
    s_cal.dig_H4 = (int16_t)((cal2[3] << 4) | (cal2[4] & 0x0F));
    s_cal.dig_H5 = (int16_t)((cal2[5] << 4) | (cal2[4] >> 4));
    s_cal.dig_H6 = (int8_t)cal2[6];

    /* Configure: humidity x1, temp/pressure x1, normal mode, 500ms standby */
    i2c_write(BME280_ADDR, BME280_REG_CTRL_HUM, 0x01);   /* humidity oversampling x1 */
    i2c_write(BME280_ADDR, BME280_REG_CONFIG, 0xA0);     /* 1000ms standby, IIR off */
    i2c_write(BME280_ADDR, BME280_REG_CTRL_MEAS, 0x27);  /* temp x1, press x1, normal */

    ESP_LOGI(TAG, "BME280 initialized (addr 0x76)");
    return 0;
}

/* Compensate temperature (Bosch reference implementation) */
static float compensate_temperature(int32_t adc_T)
{
    int32_t var1 = ((((adc_T >> 3) - ((int32_t)s_cal.dig_T1 << 1))) *
                    ((int32_t)s_cal.dig_T2)) >> 11;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)s_cal.dig_T1)) *
                      ((adc_T >> 4) - ((int32_t)s_cal.dig_T1))) >> 12) *
                    ((int32_t)s_cal.dig_T3)) >> 14;
    s_t_fine = var1 + var2;
    return (s_t_fine * 5 + 128) >> 8;  /* 0.01°C units */
}

/* Compensate pressure (returns Pa) */
static float compensate_pressure(int32_t adc_P)
{
    int64_t var1, var2, p;
    var1 = ((int64_t)s_t_fine) - 128000;
    var2 = var1 * var1 * (int64_t)s_cal.dig_P6;
    var2 = var2 + ((var1 * (int64_t)s_cal.dig_P5) << 17);
    var2 = var2 + (((int64_t)s_cal.dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)s_cal.dig_P3) >> 8) +
           ((var1 * (int64_t)s_cal.dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)s_cal.dig_P1) >> 33;
    if (var1 == 0) return 0;
    p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)s_cal.dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)s_cal.dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)s_cal.dig_P7) << 4);
    return (float)p / 256.0f;  /* Pa */
}

/* Compensate humidity (returns %RH) */
static float compensate_humidity(int32_t adc_H)
{
    int32_t v_x1 = (s_t_fine - 76800);
    v_x1 = (((((adc_H << 14) - ((int32_t)s_cal.dig_H4 << 20) -
               ((int32_t)s_cal.dig_H5 * v_x1)) + 16384) >> 15) *
            (((((((v_x1 * ((int32_t)s_cal.dig_H6)) >> 10) *
                 (((v_x1 * ((int32_t)s_cal.dig_H3)) >> 11) + 32768)) >> 10) +
              2097152) * ((int32_t)s_cal.dig_H2) + 8192) >> 14));
    v_x1 = (v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) *
                     ((int32_t)s_cal.dig_H1)) >> 4));
    if (v_x1 < 0) v_x1 = 0;
    if (v_x1 > 419430400) v_x1 = 419430400;
    return (float)(v_x1 >> 12) / 1024.0f;
}

int bme280_read(float *temp_c, float *pressure_mmhg, float *humidity_pct)
{
    uint8_t data[8];
    i2c_read(BME280_ADDR, BME280_REG_PRESS_MSB, data, 8);

    int32_t adc_P = ((int32_t)data[0] << 12) | ((int32_t)data[1] << 4) | (data[2] >> 4);
    int32_t adc_T = ((int32_t)data[3] << 12) | ((int32_t)data[4] << 4) | (data[5] >> 4);
    int32_t adc_H = ((int32_t)data[6] << 8) | data[7];

    /* Compensate */
    int32_t T_int = compensate_temperature(adc_T);
    *temp_c = (float)T_int / 100.0f;

    float pressure_pa = compensate_pressure(adc_P);
    /* Convert Pa to mmHg: 1 mmHg = 133.322 Pa */
    *pressure_mmhg = pressure_pa / 133.322f;

    *humidity_pct = compensate_humidity(adc_H);

    return 0;
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#define ESP_LOGW(tag, fmt, ...) do { printf("[%s W] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif