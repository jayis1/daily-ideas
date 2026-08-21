/**
 * bme280.c — BME280 ambient sensor driver (I2C, address 0x76)
 *
 * Provides ambient temperature/humidity/pressure for reference and
 * air-density compensation. The prism temperature comes from the
 * DS18B20 (more accurate); BME280 is for ambient conditions.
 */

#include "bme280.h"

extern I2C_HandleTypeDef hi2c1;

#define BME280_ADDR    0x76 << 1  /* I2C 7-bit address, shifted for HAL */

/* BME280 registers */
#define BME280_REG_ID          0xD0
#define BME280_REG_RESET       0xE0
#define BME280_REG_CTRL_HUM    0xF2
#define BME280_REG_STATUS      0xF3
#define BME280_REG_CTRL_MEAS   0xF4
#define BME280_REG_CONFIG      0xF5
#define BME280_REG_PRESS_MSB   0xF7
#define BME280_REG_TEMP_MSB    0xFA
#define BME280_REG_HUM_MSB     0xFD

/* Calibration data registers */
#define BME280_REG_CALIB00     0x88
#define BME280_REG_CALIB26     0xE1

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

static bme280_calib_t s_cal;
static int32_t s_t_fine;

static uint8_t read_reg8(uint8_t reg) {
    uint8_t val;
    HAL_I2C_Mem_Read(&hi2c1, BME280_ADDR, reg, 1, &val, 1, 100);
    return val;
}

static uint16_t read_reg16(uint8_t reg) {
    uint8_t buf[2];
    HAL_I2C_Mem_Read(&hi2c1, BME280_ADDR, reg, 1, buf, 2, 100);
    return (buf[1] << 8) | buf[0];
}

static void write_reg8(uint8_t reg, uint8_t val) {
    HAL_I2C_Mem_Write(&hi2c1, BME280_ADDR, reg, 1, &val, 1, 100);
}

static void load_calibration(void) {
    s_cal.dig_T1 = read_reg16(0x88);
    s_cal.dig_T2 = (int16_t)read_reg16(0x8A);
    s_cal.dig_T3 = (int16_t)read_reg16(0x8C);
    s_cal.dig_P1 = read_reg16(0x8E);
    s_cal.dig_P2 = (int16_t)read_reg16(0x90);
    s_cal.dig_P3 = (int16_t)read_reg16(0x92);
    s_cal.dig_P4 = (int16_t)read_reg16(0x94);
    s_cal.dig_P5 = (int16_t)read_reg16(0x96);
    s_cal.dig_P6 = (int16_t)read_reg16(0x98);
    s_cal.dig_P7 = (int16_t)read_reg16(0x9A);
    s_cal.dig_P8 = (int16_t)read_reg16(0x9C);
    s_cal.dig_P9 = (int16_t)read_reg16(0x9E);
    s_cal.dig_H1 = read_reg8(0xA1);
    s_cal.dig_H2 = (int16_t)read_reg16(0xE1);
    s_cal.dig_H3 = read_reg8(0xE3);
    int8_t e4 = (int8_t)read_reg8(0xE4);
    int8_t e5 = (int8_t)read_reg8(0xE5);
    s_cal.dig_H4 = (e4 << 4) | (e5 & 0x0F);
    s_cal.dig_H5 = ((e5 >> 4) & 0x0F) | (read_reg8(0xE6) << 4);
    s_cal.dig_H6 = (int8_t)read_reg8(0xE7);
}

/* Compensate temperature (from datasheet) */
static float compensate_temperature(int32_t adc_T) {
    int32_t var1 = (((adc_T >> 3) - ((int32_t)s_cal.dig_T1 << 1)) *
                    ((int32_t)s_cal.dig_T2)) >> 11;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)s_cal.dig_T1)) *
                      ((adc_T >> 4) - ((int32_t)s_cal.dig_T1))) >> 12) *
                    ((int32_t)s_cal.dig_T3)) >> 14;
    s_t_fine = var1 + var2;
    return (s_t_fine * 5 + 128) >> 8;
}

/* Compensate pressure (from datasheet) */
static float compensate_pressure(int32_t adc_P) {
    int64_t var1 = ((int64_t)s_t_fine) - 128000;
    int64_t var2 = var1 * var1 * (int64_t)s_cal.dig_P6;
    var2 = var2 + ((var1 * (int64_t)s_cal.dig_P5) << 17);
    var2 = var2 + (((int64_t)s_cal.dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)s_cal.dig_P3) >> 8) +
           ((var1 * (int64_t)s_cal.dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)s_cal.dig_P1) >> 33;
    if (var1 == 0) return 0;
    int64_t p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)s_cal.dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)s_cal.dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)s_cal.dig_P7) << 4);
    return (float)p / 256.0f;
}

/* Compensate humidity (from datasheet) */
static float compensate_humidity(int32_t adc_H) {
    int32_t v_x1 = s_t_fine - 76800;
    v_x1 = (((((adc_H << 14) - ((int32_t)s_cal.dig_H4) << 20) -
              (((int32_t)s_cal.dig_H5) * v_x1)) + 16384) >> 15) *
           (((((((v_x1 * ((int32_t)s_cal.dig_H6)) >> 10) *
                (((v_x1 * ((int32_t)s_cal.dig_H3)) >> 11) + 32768)) >> 10) +
              2097152) * ((int32_t)s_cal.dig_H2) + 8192) >> 14);
    v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) *
                    ((int32_t)s_cal.dig_H1)) >> 4);
    if (v_x1 < 0) v_x1 = 0;
    if (v_x1 > 419430400) v_x1 = 419430400;
    return (float)(v_x1 >> 12) / 1024.0f;
}

void bme280_init(void) {
    /* Check chip ID */
    uint8_t id = read_reg8(BME280_REG_ID);
    if (id != 0x60) return;  /* BME280 ID = 0x60 */

    /* Load calibration data */
    load_calibration();

    /* Configure: humidity x1, temperature x1, pressure x1, normal mode */
    write_reg8(BME280_REG_CTRL_HUM, 0x01);   /* humidity oversampling x1 */
    write_reg8(BME280_REG_CTRL_MEAS, 0x27);  /* temp x1, press x1, normal */
    write_reg8(BME280_REG_CONFIG, 0xA0);     /* 1000ms standby, IIR off */
}

void bme280_read(float *temp, float *humidity, float *pressure) {
    uint8_t data[8];
    HAL_I2C_Mem_Read(&hi2c1, BME280_ADDR, BME280_REG_PRESS_MSB, 1, data, 8, 100);

    int32_t adc_P = ((int32_t)data[0] << 12) | ((int32_t)data[1] << 4) | (data[2] >> 4);
    int32_t adc_T = ((int32_t)data[3] << 12) | ((int32_t)data[4] << 4) | (data[5] >> 4);
    int32_t adc_H = ((int32_t)data[6] << 8) | data[7];

    float t = compensate_temperature(adc_T) / 100.0f;

    if (temp) *temp = t;
    if (humidity) *humidity = compensate_humidity(adc_H);
    if (pressure) *pressure = compensate_pressure(adc_P) / 100.0f;  /* hPa */
}