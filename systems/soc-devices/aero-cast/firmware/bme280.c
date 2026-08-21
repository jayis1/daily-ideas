/* bme280.c — BME280 atmospheric sensor driver (I2C)
 *
 * Reads calibrated temperature, pressure, humidity and computes
 * mixing ratio and air density for sonic temperature correction.
 */

#include <stdio.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "bme280.h"
#include "sdkconfig.h"

/* BME280 registers */
#define BME280_REG_ID          0xD0
#define BME280_REG_RESET       0xE0
#define BME280_REG_CTRL_HUM    0xF2
#define BME280_REG_CTRL_MEAS   0xF4
#define BME280_REG_CONFIG      0xF5
#define BME280_REG_DATA        0xF7
#define BME280_REG_CALIB00     0x88
#define BME280_REG_CALIB26     0xE1

/* Calibration coefficients */
typedef struct {
    uint16_t dig_T1;
    int16_t  dig_T2, dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2, dig_P3, dig_P4, dig_P5;
    int16_t  dig_P6, dig_P7, dig_P8, dig_P9;
    uint8_t  dig_H1, dig_H3;
    int8_t   dig_H6;
    int16_t  dig_H2, dig_H4, dig_H5;
} bme280_calib_t;

static bme280_calib_t cal;
static int32_t t_fine;

static void i2c_write(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = { reg, val };
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 2, false);
}

static void i2c_read(uint8_t reg, uint8_t *buf, uint16_t len)
{
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, &reg, 1, true);
    i2c_read_blocking(i2c0, BME280_I2C_ADDR, buf, len, false);
}

static void read_calibration(void)
{
    uint8_t buf[26];
    i2c_read(BME280_REG_CALIB00, buf, 26);

    cal.dig_T1 = (buf[1] << 8) | buf[0];
    cal.dig_T2 = (buf[3] << 8) | buf[2];
    cal.dig_T3 = (buf[5] << 8) | buf[4];
    cal.dig_P1 = (buf[7] << 8) | buf[6];
    cal.dig_P2 = (buf[9] << 8) | buf[8];
    cal.dig_P3 = (buf[11] << 8) | buf[10];
    cal.dig_P4 = (buf[13] << 8) | buf[12];
    cal.dig_P5 = (buf[15] << 8) | buf[14];
    cal.dig_P6 = (buf[17] << 8) | buf[16];
    cal.dig_P7 = (buf[19] << 8) | buf[18];
    cal.dig_P8 = (buf[21] << 8) | buf[20];
    cal.dig_P9 = (buf[23] << 8) | buf[22];

    uint8_t h_buf[7];
    i2c_read(BME280_REG_CALIB26, h_buf, 7);
    cal.dig_H1 = buf[25];
    cal.dig_H2 = (h_buf[1] << 8) | h_buf[0];
    cal.dig_H3 = h_buf[2];
    cal.dig_H4 = (h_buf[3] << 4) | (h_buf[4] & 0x0F);
    cal.dig_H5 = (h_buf[5] << 4) | (h_buf[4] >> 4);
    cal.dig_H6 = (int8_t)h_buf[6];
}

bool bme280_init(void)
{
    /* Initialize I2C */
    i2c_init(i2c0, 400000);
    gpio_set_function(PIN_I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C_SDA);
    gpio_pull_up(PIN_I2C_SCL);

    /* Check chip ID */
    uint8_t id;
    i2c_read(BME280_REG_ID, &id, 1);
    if (id != 0x60) {
        printf("[bme280] wrong chip ID: 0x%02X\n", id);
        return false;
    }

    /* Soft reset */
    i2c_write(BME280_REG_RESET, 0xB6);
    sleep_ms(10);

    read_calibration();

    /* Configure: humidity x1, temp/press x1, normal mode, 500ms standby */
    i2c_write(BME280_REG_CTRL_HUM, 0x01);
    i2c_write(BME280_REG_CONFIG, 0x5C);  /* 1000ms standby, IIR off */
    i2c_write(BME280_REG_CTRL_MEAS, 0x27); /* x1 oversampling, normal mode */

    sleep_ms(50);
    printf("[bme280] initialized, cal T1=%u T2=%d T3=%d\n",
           cal.dig_T1, cal.dig_T2, cal.dig_T3);
    return true;
}

static int32_t compensate_temperature(int32_t adc_T)
{
    int32_t var1, var2;
    var1 = ((((adc_T >> 3) - ((int32_t)cal.dig_T1 << 1))) * ((int32_t)cal.dig_T2)) >> 11;
    var2 = (((((adc_T >> 4) - ((int32_t)cal.dig_T1)) * ((adc_T >> 4) - ((int32_t)cal.dig_T1))) >> 12) *
            ((int32_t)cal.dig_T3)) >> 14;
    t_fine = var1 + var2;
    return (t_fine * 5 + 128) >> 8;
}

static uint32_t compensate_pressure(int32_t adc_P)
{
    int32_t var1, var2;
    uint32_t p;
    var1 = (((int32_t)t_fine) >> 1) - ((int32_t)64000);
    var2 = (((var1 >> 2) * (var1 >> 2)) >> 11) * ((int32_t)cal.dig_P6);
    var2 = var2 + ((var1 * ((int32_t)cal.dig_P5)) << 1);
    var2 = (var2 >> 2) + (((int32_t)cal.dig_P4) << 16);
    var1 = (((cal.dig_P3 * (((var1 >> 2) * (var1 >> 2)) >> 13)) >> 3) +
            ((((int32_t)cal.dig_P2) * var1) >> 1)) >> 18;
    var1 = ((((32768 + var1)) * ((int32_t)cal.dig_P1)) >> 15);
    if (var1 == 0) return 0;
    p = (((uint32_t)(((int32_t)1048576) - adc_P) - (var2 >> 12))) * 3125;
    p = (p << 1) / ((uint32_t)var1);
    var1 = (((int32_t)cal.dig_P9) * ((int32_t)((p >> 3) * (p >> 3)) >> 13)) >> 12;
    var2 = (((int32_t)(p >> 2)) * ((int32_t)cal.dig_P8)) >> 13;
    p = (uint32_t)((int32_t)p + ((var1 + var2 + cal.dig_P7) >> 4));
    return p;
}

static uint32_t compensate_humidity(int32_t adc_H)
{
    int32_t v_x1;
    v_x1 = (t_fine - ((int32_t)76800));
    v_x1 = (((((adc_H << 14) - (((int32_t)cal.dig_H4) << 20) -
              (((int32_t)cal.dig_H5) * v_x1)) + ((int32_t)16384)) >> 10) *
            (((((v_x1 * ((int32_t)cal.dig_H6)) >> 10) *
               (((v_x1 * ((int32_t)cal.dig_H3)) >> 11) + ((int32_t)32768))) >> 10) +
              ((int32_t)2097152)) >> 11) * (((((v_x1 * ((int32_t)cal.dig_H2)) >> 10) +
              ((int32_t)cal.dig_H1)) << 1) + ((int32_t)cal.dig_H7))) >> 11;
    v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) * ((int32_t)cal.dig_H8)) >> 12);
    if (v_x1 < 0) v_x1 = 0;
    if (v_x1 > 419430400) v_x1 = 419430400;
    return (uint32_t)(v_x1 >> 12);
}

bool bme280_read(bme280_data_t *data)
{
    uint8_t buf[8];
    i2c_read(BME280_REG_DATA, buf, 8);

    int32_t adc_P = ((int32_t)buf[0] << 12) | ((int32_t)buf[1] << 4) | (buf[2] >> 4);
    int32_t adc_T = ((int32_t)buf[3] << 12) | ((int32_t)buf[4] << 4) | (buf[5] >> 4);
    int32_t adc_H = ((int32_t)buf[6] << 8) | buf[7];

    int32_t T = compensate_temperature(adc_T);  /* sets t_fine */
    uint32_t P = compensate_pressure(adc_P);
    uint32_t H = compensate_humidity(adc_H);

    data->temperature = (float)T / 100.0f;
    data->pressure    = (float)P;
    data->humidity    = (float)H / 1024.0f;

    data->mixing_ratio = bme280_mixing_ratio(data->temperature, data->humidity, data->pressure);
    data->air_density  = bme280_air_density(data->temperature, data->humidity, data->pressure);

    return true;
}

float bme280_mixing_ratio(float temp_c, float rh_percent, float pressure_pa)
{
    /* Saturation vapor pressure (Magnus formula) */
    float T = temp_c;
    float es = 610.94f * expf((17.625f * T) / (T + 243.04f));  /* Pa */
    float e = (rh_percent / 100.0f) * es;
    /* Mixing ratio: w = 0.622 * e / (P - e) */
    float w = 0.622f * e / (pressure_pa - e);
    return w;
}

float bme280_air_density(float temp_c, float rh_percent, float pressure_pa)
{
    float T = temp_c + 273.15f;
    float w = bme280_mixing_ratio(temp_c, rh_percent, pressure_pa);
    /* Virtual temperature */
    float Tv = T * (1.0f + 0.608f * w);
    /* ρ = P / (R_d * Tv) */
    float Rd = 287.05f;
    return pressure_pa / (Rd * Tv);
}