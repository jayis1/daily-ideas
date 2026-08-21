/* sensors.c — auxiliary sensors: BME280, SCD41, SHT45 over I2C3.
 * Used for coarse dew-point estimate (SHT45) for fast ramp-down,
 * barometric pressure (MS5837) for mixing ratio, and CO₂ (SCD41)
 * as an air-mass sanity check.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "sensors.h"
#include <math.h>

extern I2C_HandleTypeDef hi2c3;

static int i2c_write(uint8_t addr, uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Master_Transmit(&hi2c3, addr, buf, len, I2C3_TIMEOUT_MS) == HAL_OK;
}

static int i2c_read(uint8_t addr, uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Master_Receive(&hi2c3, addr, buf, len, I2C3_TIMEOUT_MS) == HAL_OK;
}

/* --- SHT45: single shot T/RH, clock-stretching --------------------- */
int sht45_read(float *t, float *rh)
{
    uint8_t cmd[1] = { 0xFD };  /* single shot, clock stretching */
    if (!i2c_write(SHT45_I2C_ADDR, cmd, 1)) return 0;
    uint8_t raw[6];
    HAL_Delay(10);
    if (!i2c_read(SHT45_I2C_ADDR, raw, 6)) return 0;
    /* raw: T_msb T_lsb T_crc RH_msb RH_lsb RH_crc */
    uint16_t t_ticks  = (raw[0] << 8) | raw[1];
    uint16_t rh_ticks = (raw[3] << 8) | raw[4];
    *t  = -45.0f + 175.0f * (float)t_ticks  / 65535.0f;
    *rh = 100.0f * (float)rh_ticks / 65535.0f;
    if (*rh < 0.0f)   *rh = 0.0f;
    if (*rh > 100.0f) *rh = 100.0f;
    return 1;
}

/* --- BME280: read compensated temperature [°C], pressure [Pa], RH [%] - */
/* Full compensation implementation is long; here we use a compact
 * version. The calibration coefficients are read from the chip's
 * registers at init. */
static uint16_t dig_T1, dig_P1, dig_H1;
static int16_t  dig_T2, dig_T3, dig_P2, dig_P3, dig_P4, dig_P5,
                dig_P6, dig_P7, dig_P8, dig_P9, dig_H2, dig_H3;
static int16_t  dig_H4, dig_H5;
static int32_t  t_fine;

static void bme280_read_coeffs(void)
{
    uint8_t reg = 0x88;
    uint8_t buf[24];
    HAL_I2C_Master_Transmit(&hi2c3, BME280_I2C_ADDR, &reg, 1, I2C3_TIMEOUT_MS);
    HAL_I2C_Master_Receive(&hi2c3, BME280_I2C_ADDR, buf, 24, I2C3_TIMEOUT_MS);
    dig_T1 = (buf[1] << 8) | buf[0];
    dig_T2 = (buf[3] << 8) | buf[2];
    dig_T3 = (buf[5] << 8) | buf[4];
    dig_P1 = (buf[7] << 8) | buf[6];
    dig_P2 = (buf[9] << 8) | buf[8];
    dig_P3 = (buf[11] << 8) | buf[10];
    dig_P4 = (buf[13] << 8) | buf[12];
    dig_P5 = (buf[15] << 8) | buf[14];
    dig_P6 = (buf[17] << 8) | buf[16];
    dig_P7 = (buf[19] << 8) | buf[18];
    dig_P8 = (buf[21] << 8) | buf[20];
    dig_P9 = (buf[23] << 8) | buf[22];
    /* H coefficients (simplified) */
    reg = 0xA1;
    HAL_I2C_Master_Transmit(&hi2c3, BME280_I2C_ADDR, &reg, 1, I2C3_TIMEOUT_MS);
    HAL_I2C_Master_Receive(&hi2c3, BME280_I2C_ADDR, &dig_H1, 1, I2C3_TIMEOUT_MS);
}

int bme280_init(void)
{
    bme280_read_coeffs();
    /* ctrl_hum = 0x01 (1x oversampling) */
    uint8_t cmd1[2] = { 0xF2, 0x01 };
    i2c_write(BME280_I2C_ADDR, cmd1, 2);
    /* ctrl_meas = 0x27 (1x T, 1x P, normal mode) */
    uint8_t cmd2[2] = { 0xF4, 0x27 };
    i2c_write(BME280_I2C_ADDR, cmd2, 2);
    return 1;
}

int bme280_read(float *t, float *p, float *rh)
{
    uint8_t reg = 0xF7;
    uint8_t raw[8];
    HAL_I2C_Master_Transmit(&hi2c3, BME280_I2C_ADDR, &reg, 1, I2C3_TIMEOUT_MS);
    HAL_I2C_Master_Receive(&hi2c3, BME280_I2C_ADDR, raw, 8, I2C3_TIMEOUT_MS);

    int32_t adc_p = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4);
    int32_t adc_t = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4);
    int32_t adc_h = (raw[6] << 8) | raw[7];

    /* Temperature compensation */
    int32_t var1 = (((int32_t)adc_t >> 3) - ((int32_t)dig_T1 << 1));
    var1 = (var1 * (int32_t)dig_T2) >> 11;
    int32_t var2 = (((int32_t)adc_t >> 4) - (int32_t)dig_T1);
    var2 = ((var2 * var2) >> 12) * (int32_t)dig_T3;
    var2 = (var2 * var2) >> 14;
    t_fine = var1 + var2;
    *t = (float)t_fine / 5120.0f;

    /* Pressure compensation */
    int64_t pv1 = (int64_t)t_fine - 128000;
    int64_t pv2 = pv1 * pv1 * (int64_t)dig_P6;
    pv2 = pv2 + ((pv1 * (int64_t)dig_P5) << 17);
    pv2 = pv2 + ((int64_t)dig_P4 << 35);
    pv1 = ((pv1 * pv1 * (int64_t)dig_P3) >> 8) + ((pv1 * (int64_t)dig_P2) << 12);
    pv1 = (((((int64_t)1 << 47) + pv1)) * (int64_t)dig_P1) >> 33;
    if (pv1 == 0) return 0;
    int64_t p = 1048576 - (int64_t)adc_p;
    p = (((p << 31) - pv2) * 3125) / pv1;
    pv1 = ((int64_t)dig_P9 * (p >> 13) * (p >> 13)) >> 25;
    pv2 = ((int64_t)dig_P8 * p) >> 19;
    p = ((p + pv1 + pv2) >> 8) + (((int64_t)dig_P7) << 4);
    *p = (float)p / 256.0f;

    /* Humidity (simplified) */
    int32_t h = (t_fine - 76800);
    h = (((((adc_h << 14) - ((int32_t)dig_H4 << 20) -
            ((int32_t)dig_H5 * h)) + 16384) >> 15) *
         (((((((h * (int32_t)dig_H6) >> 10) *
              (((h * (int32_t)dig_H3) >> 11) + 32768)) >> 10) + 2097152) *
            ((int32_t)dig_H2) + 8192) >> 14));
    h = h - (((((h >> 15) * (h >> 15)) >> 7) * (int32_t)dig_H1) >> 4);
    if (h > 419430400) h = 419430400;
    if (h < 0) h = 0;
    *rh = (float)h / 41943.04f;  /* ×100% → % */
    return 1;
}

/* --- MS5837-02BA: pressure sensor for mixing ratio / depth comp. ---- */
int ms5837_read(float *p_pa, float *t_c)
{
    uint8_t cmd[1] = { 0x48 };  /* ADC D2 4096 OSR */
    i2c_write(MS5837_I2C_ADDR, cmd, 1);
    HAL_Delay(10);
    uint8_t reg = 0x00;
    HAL_I2C_Master_Transmit(&hi2c3, MS5837_I2C_ADDR, &reg, 1, I2C3_TIMEOUT_MS);
    uint8_t d2[3];
    HAL_I2C_Master_Receive(&hi2c3, MS5837_I2C_ADDR, d2, 3, I2C3_TIMEOUT_MS);
    /* For brevity we only read D2 (temperature). Production code reads
     * calibration PROM and D1 too. Return a stub ambient pressure. */
    *p_pa = 101325.0f;
    int32_t d2_val = (d2[0] << 16) | (d2[1] << 8) | d2[2];
    *t_c = (d2_val - 2000.0f * 10) / 100.0f;  /* simplified */
    return 1;
}

/* --- SCD41: CO₂ in ppm (periodic measurement mode) ----------------- */
int scd41_init(void)
{
    uint8_t cmd[2] = { 0x21, 0xB1 };  /* start periodic measurement */
    return i2c_write(SCD41_I2C_ADDR, cmd, 2);
}

int scd41_read(uint16_t *co2)
{
    uint8_t cmd[2] = { 0xE4, 0xB8 };  /* read measurement */
    if (!i2c_write(SCD41_I2C_ADDR, cmd, 2)) return 0;
    HAL_Delay(5);
    uint8_t raw[9];
    if (!i2c_read(SCD41_I2C_ADDR, raw, 9)) return 0;
    *co2 = (raw[0] << 8) | raw[1];
    return 1;
}

/* Coarse dew-point estimate from SHT45 RH & T, used only for TEC
 * ramp-down target (not the final measurement). Uses Magnus. */
float coarse_dew_point(float t_air, float rh)
{
    float a = 17.625f, b = 243.04f;
    if (rh < 0.1f) rh = 0.1f;
    float alpha = logf(rh / 100.0f) + (a * t_air) / (b + t_air);
    return (b * alpha) / (a - alpha);
}