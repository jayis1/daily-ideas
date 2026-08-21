/*
 * bme280.c — BME280 environmental sensor (I2C)
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#include "bme280.h"
#include "main.h"
#include <string.h>

extern I2C_HandleTypeDef hi2c1;

#define BME280_ADDR  0x76

/* Calibration data registers */
static uint16_t dig_T1, dig_P1;
static int16_t  dig_T2, dig_T3, dig_P2, dig_P3, dig_P4, dig_P5;
static int16_t  dig_P6, dig_P7, dig_P8, dig_P9;
static uint8_t  dig_H1, dig_H3;
static int8_t   dig_H2, dig_H4, dig_H5, dig_H6;
static int32_t  t_fine;

static void read_regs(uint8_t reg, uint8_t *buf, int len)
{
    HAL_I2C_Master_Transmit(&hi2c1, BME280_ADDR << 1, &reg, 1, 10);
    HAL_I2C_Master_Receive(&hi2c1, BME280_ADDR << 1, buf, len, 10);
}

static void write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    HAL_I2C_Master_Transmit(&hi2c1, BME280_ADDR << 1, buf, 2, 10);
}

int bme280_init(void)
{
    uint8_t id;
    read_regs(0xD0, &id, 1);
    if (id != 0x60) return -1;  /* BME280 chip ID */

    /* Read calibration data */
    uint8_t calib[33];
    read_regs(0x88, calib, 26);
    read_regs(0xE1, calib + 26, 7);

    dig_T1 = (calib[1] << 8) | calib[0];
    dig_T2 = (calib[3] << 8) | calib[2];
    dig_T3 = (calib[5] << 8) | calib[4];
    dig_P1 = (calib[7] << 8) | calib[6];
    dig_P2 = (calib[9] << 8) | calib[8];
    dig_P3 = (calib[11] << 8) | calib[10];
    dig_P4 = (calib[13] << 8) | calib[12];
    dig_P5 = (calib[15] << 8) | calib[14];
    dig_P6 = (calib[17] << 8) | calib[16];
    dig_P7 = (calib[19] << 8) | calib[18];
    dig_P8 = (calib[21] << 8) | calib[20];
    dig_P9 = (calib[23] << 8) | calib[22];
    dig_H1 = calib[25];
    dig_H2 = (int16_t)((calib[27] << 8) | calib[26]);
    dig_H3 = calib[28];
    dig_H4 = (int16_t)((calib[29] << 4) | (calib[29] >> 4));
    dig_H5 = (int16_t)((calib[30] << 4) | (calib[29] & 0x0F));
    dig_H6 = (int8_t)calib[32];

    /* Configure: humidity ×1, temp/press ×1, normal mode */
    write_reg(0xF2, 0x01);  /* humidity oversampling ×1 */
    write_reg(0xF4, 0x27);  /* temp/press oversampling ×1, normal mode */
    write_reg(0xF5, 0xA0);  /* standby 1000 ms, filter off */

    HAL_Delay(100);
    return 0;
}

static int32_t compensate_temperature(int32_t adc_T)
{
    int32_t var1 = (((adc_T >> 3) - ((int32_t)dig_T1 << 1))) *
                   ((int32_t)dig_T2) >> 11;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)dig_T1)) *
                     ((adc_T >> 4) - ((int32_t)dig_T1))) >> 12) *
                    ((int32_t)dig_T3)) >> 14;
    t_fine = var1 + var2;
    return (t_fine * 5 + 128) >> 8;
}

static uint32_t compensate_pressure(int32_t adc_P)
{
    int64_t var1, var2, p;
    var1 = ((int64_t)t_fine) - 128000;
    var2 = var1 * var1 * (int64_t)dig_P6;
    var2 = var2 + ((var1 * (int64_t)dig_P5) << 17);
    var2 = var2 + (((int64_t)dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)dig_P3) >> 8) +
           ((var1 * (int64_t)dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)dig_P1) >> 33;
    if (var1 == 0) return 0;
    p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)dig_P7) << 4);
    return (uint32_t)(p >> 8) / 100;  /* hPa */
}

static uint32_t compensate_humidity(int32_t adc_H)
{
    int32_t v_x1 = t_fine - 76800;
    v_x1 = (((((adc_H << 14) - ((int32_t)dig_H4) << 20) -
              ((int32_t)dig_H5 * v_x1)) + 16384) >> 15) *
           (((((((v_x1 * (int32_t)dig_H6) >> 10) *
                (((v_x1 * (int32_t)dig_H3) >> 11) + 32768)) >> 10) +
               2097152) * ((int32_t)dig_H2) + 8192) >> 14));
    v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) *
                    (int32_t)dig_H1) >> 4);
    if (v_x1 < 0) v_x1 = 0;
    if (v_x1 > 419430400) v_x1 = 419430400;
    return (uint32_t)(v_x1 >> 12) / 1024;  /* % */
}

int bme280_read(bme280_data_t *data)
{
    uint8_t raw[8];
    read_regs(0xF7, raw, 8);

    int32_t adc_P = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4);
    int32_t adc_T = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4);
    int32_t adc_H = (raw[6] << 8) | raw[7];

    data->temperature = compensate_temperature(adc_T) / 100.0f;
    data->pressure = compensate_pressure(adc_P);
    data->humidity = compensate_humidity(adc_H);

    return 0;
}