/*
 * Hive Mind — BME280 Driver (ambient T/H/P)
 * I2C at 0x76 or 0x77
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "bme280_driver.h"
#include "main.h"

#define BME280_ADDR          0x76 << 1  /* Default I2C address */
#define BME280_CHIP_ID       0x60

/* Registers */
#define BME280_REG_CHIP_ID   0xD0
#define BME280_REG_RESET     0xE0
#define BME280_REG_CTRL_HUM  0xF2
#define BME280_REG_CTRL_MEAS 0xF4
#define BME280_REG_CONFIG    0xF5
#define BME280_REG_DATA      0xF7

/* Calibration data registers */
#define BME280_REG_DIG_T1    0x88
#define BME280_REG_DIG_P1    0x8E
#define BME280_REG_DIG_H1    0xA1
#define BME280_REG_DIG_H2    0xE1

/* Oversampling settings */
#define BME280_OS_SKIP       0
#define BME280_OS_1X         1
#define BME280_OS_2X         2
#define BME280_OS_4X         3
#define BME280_OS_8X         4
#define BME280_OS_16X        5

/* Mode */
#define BME280_MODE_SLEEP    0
#define BME280_MODE_FORCED   1
#define BME280_MODE_NORMAL   3

extern I2C_HandleTypeDef hi2c1;

/* Calibration coefficients */
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

static bme280_calib_t calib;
static int32_t t_fine;

/* ------------------------------------------------------------------ */
/* I2C helpers                                                         */
/* ------------------------------------------------------------------ */

static HAL_StatusTypeDef bme280_read(uint8_t reg, uint8_t *data, uint16_t len)
{
    return HAL_I2C_Mem_Read(&hi2c1, BME280_ADDR, reg, I2C_MEMADD_SIZE_8BIT,
                            data, len, 100);
}

static HAL_StatusTypeDef bme280_write(uint8_t reg, uint8_t val)
{
    return HAL_I2C_Mem_Write(&hi2c1, BME280_ADDR, reg, I2C_MEMADD_SIZE_8BIT,
                             &val, 1, 100);
}

/* ------------------------------------------------------------------ */
/* Calibration                                                         */
/* ------------------------------------------------------------------ */

static void read_calibration(void)
{
    uint8_t buf[24];

    /* Temperature and pressure calibration */
    bme280_read(BME280_REG_DIG_T1, buf, 24);
    calib.dig_T1 = (uint16_t)(buf[1] << 8 | buf[0]);
    calib.dig_T2 = (int16_t)(buf[3] << 8 | buf[2]);
    calib.dig_T3 = (int16_t)(buf[5] << 8 | buf[4]);
    calib.dig_P1 = (uint16_t)(buf[7] << 8 | buf[6]);
    calib.dig_P2 = (int16_t)(buf[9] << 8 | buf[8]);
    calib.dig_P3 = (int16_t)(buf[11] << 8 | buf[10]);
    calib.dig_P4 = (int16_t)(buf[13] << 8 | buf[12]);
    calib.dig_P5 = (int16_t)(buf[15] << 8 | buf[14]);
    calib.dig_P6 = (int16_t)(buf[17] << 8 | buf[16]);
    calib.dig_P7 = (int16_t)(buf[19] << 8 | buf[18]);
    calib.dig_P8 = (int16_t)(buf[21] << 8 | buf[20]);
    calib.dig_P9 = (int16_t)(buf[23] << 8 | buf[22]);

    /* Humidity calibration */
    uint8_t h_buf[7];
    bme280_read(BME280_REG_DIG_H2, h_buf, 7);
    calib.dig_H1 = bme280_read_8bit(BME280_REG_DIG_H1);
    calib.dig_H2 = (int16_t)(h_buf[1] << 8 | h_buf[0]);
    calib.dig_H3 = h_buf[2];
    calib.dig_H4 = (int16_t)((h_buf[3] << 4) | (h_buf[4] & 0x0F));
    calib.dig_H5 = (int16_t)((h_buf[5] << 4) | (h_buf[4] >> 4));
    calib.dig_H6 = (int8_t)h_buf[6];
}

static uint8_t bme280_read_8bit(uint8_t reg)
{
    uint8_t val;
    bme280_read(reg, &val, 1);
    return val;
}

/* ------------------------------------------------------------------ */
/* Compensation functions                                              */
/* ------------------------------------------------------------------ */

static float compensate_temperature(int32_t adc_T)
{
    float var1 = ((float)adc_T / 16384.0f - (float)calib.dig_T1 / 1024.0f) * (float)calib.dig_T2;
    float var2 = (((float)adc_T / 131072.0f - (float)calib.dig_T1 / 8192.0f) *
                  ((float)adc_T / 131072.0f - (float)calib.dig_T1 / 8192.0f)) *
                  (float)calib.dig_T3;
    t_fine = (int32_t)(var1 + var2);
    return (var1 + var2) / 5120.0f;
}

static float compensate_pressure(int32_t adc_P)
{
    float var1 = (float)t_fine / 2.0f - 64000.0f;
    float var2 = var1 * var1 * (float)calib.dig_P6 / 32768.0f;
    var2 = var2 + var1 * (float)calib.dig_P5 * 2.0f;
    var2 = var2 / 4.0f + (float)calib.dig_P4 * 65536.0f;
    var1 = ((float)calib.dig_P3 * var1 * var1 / 524288.0f +
            (float)calib.dig_P2 * var1) / 524288.0f;
    var1 = (1.0f + var1 / 32768.0f) * (float)calib.dig_P1;
    if (var1 < 1.0f) return 0;

    float p = 1048576.0f - (float)adc_P;
    p = (p - (var2 / 4096.0f)) * 6250.0f / var1;
    var1 = (float)calib.dig_P9 * p * p / 2147483648.0f;
    var2 = p * (float)calib.dig_P8 / 32768.0f;
    p = p + (var1 + var2 + (float)calib.dig_P7) / 16.0f;
    return p / 100.0f; /* Convert to hPa */
}

static float compensate_humidity(int32_t adc_H)
{
    float h = (float)t_fine - 76800.0f;
    h = (adc_H - ((float)calib.dig_H4 * 64.0f +
          (float)calib.dig_H5 / 16384.0f * h)) *
         ((float)calib.dig_H2 / 65536.0f *
          (1.0f + (float)calib.dig_H6 / 67108864.0f * h *
          (1.0f + (float)calib.dig_H3 / 67108864.0f * h)));
    h = h * (1.0f - (float)calib.dig_H1 * h / 524288.0f);
    if (h > 100.0f) h = 100.0f;
    if (h < 0.0f) h = 0.0f;
    return h;
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void bme280_init(void)
{
    uint8_t chip_id;
    bme280_read(BME280_REG_CHIP_ID, &chip_id, 1);

    if (chip_id != BME280_CHIP_ID) {
        /* BME280 not found, try alternate address */
        /* For now, just log error */
        return;
    }

    /* Soft reset */
    bme280_write(BME280_REG_RESET, 0xB6);
    HAL_Delay(2);

    /* Read calibration data */
    read_calibration();

    /* Configure: humidity oversampling x1 */
    bme280_write(BME280_REG_CTRL_HUM, BME280_OS_1X);

    /* Configure: temp oversampling x2, pressure oversampling x16, normal mode */
    bme280_write(BME280_REG_CTRL_MEAS, (BME280_OS_2X << 5) |
                                         (BME280_OS_16X << 2) |
                                         BME280_MODE_NORMAL);

    /* Configure: standby 500ms, filter off */
    bme280_write(BME280_REG_CONFIG, (5 << 5) | (0 << 2) | 0);

    /* Wait for first measurement */
    HAL_Delay(100);
}

void bme280_read(float *temperature, float *humidity, float *pressure)
{
    uint8_t data[8];
    bme280_read(BME280_REG_DATA, data, 8);

    int32_t adc_P = (int32_t)((uint32_t)data[0] << 12 | (uint32_t)data[1] << 4 | data[2] >> 4);
    int32_t adc_T = (int32_t)((uint32_t)data[3] << 12 | (uint32_t)data[4] << 4 | data[5] >> 4);
    int32_t adc_H = (int32_t)((uint16_t)data[6] << 8 | data[7]);

    *temperature = compensate_temperature(adc_T);
    *pressure = compensate_pressure(adc_P);
    *humidity = compensate_humidity(adc_H);
}