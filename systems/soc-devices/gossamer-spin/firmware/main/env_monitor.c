/*
 * gossamer-spin / firmware / env_monitor.c
 * BME280 temperature/humidity sensor via I2C1.
 *
 * Fiber morphology is strongly humidity-dependent, so the chamber
 * environment is monitored. Recipes include target RH ranges and
 * the firmware warns if out of range.
 */
#include "main.h"

static void *h_i2c1 = (void *)1;

/* BME280 I2C address (SDO tied low → 0x76) */
#define BME280_ADDR  0x76

/* Calibration coefficients (read from BME280 registers at init) */
static struct {
    uint16_t dig_T1;
    int16_t  dig_T2, dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2, dig_P3, dig_P4, dig_P5;
    int16_t  dig_P6, dig_P7, dig_P8, dig_P9;
    uint8_t  dig_H1, dig_H3;
    int16_t  dig_H2, dig_H4, dig_H5;
    int8_t   dig_H6;
    int32_t  t_fine;
} bme = { 0 };

static void bme_read_calibration(void)
{
    /* In real build: I2C read from registers 0x88–0xA1 and 0xE1–0xE7.
       Placeholder: leave zeros (will use default values). */
}

static int32_t compensate_temp(int32_t adc_T)
{
    int32_t var1, var2;
    var1 = ((((adc_T >> 3) - ((int32_t)bme.dig_T1 << 1))) *
            ((int32_t)bme.dig_T2)) >> 11;
    var2 = (((((adc_T >> 4) - ((int32_t)bme.dig_T1)) *
              ((adc_T >> 4) - ((int32_t)bme.dig_T1))) >> 12) *
            ((int32_t)bme.dig_T3)) >> 14;
    bme.t_fine = var1 + var2;
    return (bme.t_fine * 5 + 128) >> 8;  /* °C × 100 */
}

static uint32_t compensate_humidity(int32_t adc_H)
{
    int32_t v_x1 = bme.t_fine - 76800;
    v_x1 = (((((adc_H << 14) - ((int32_t)bme.dig_H4 << 20) -
                ((int32_t)bme.dig_H5 * v_x1)) + 16384) >> 15) *
            (((((((v_x1 * ((int32_t)bme.dig_H6)) >> 10) *
                 (((v_x1 * ((int32_t)bme.dig_H3)) >> 11) + 32768)) >> 10) +
              2097152) * ((int32_t)bme.dig_H2) + 8192) >> 14));
    v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) *
                    ((int32_t)bme.dig_H1)) >> 4);
    if (v_x1 < 0) v_x1 = 0;
    if (v_x1 > 419430400) v_x1 = 419430400;
    return (uint32_t)(v_x1 >> 12);  /* % RH × 1024 */
}

void env_monitor_init(void)
{
    /* I2C1 init at 100 kHz
       BME280 soft-reset (write 0xB6 to reg 0xE0)
       Read calibration coefficients
       Set humidity oversampling ×1, temp ×1, pressure ×1
       Set mode = normal */
    (void)h_i2c1;
    bme_read_calibration();
}

void env_read(float *temp_c, float *rh_pct)
{
    /* In real build:
       - I2C read 8 bytes from BME280 registers 0xF7–0xFE
       - Parse raw T, P, H
       - Apply compensation

       Placeholder: return realistic room conditions. */
    static uint32_t seed = 11111;
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF;

    *temp_c = 23.0f + (float)(seed % 20 - 10) * 0.1f;  /* ~23°C ±1°C */
    *rh_pct = 35.0f + (float)(seed % 30 - 15) * 0.2f;  /* ~35% ±3% RH */

    (void)compensate_temp;
    (void)compensate_humidity;
}