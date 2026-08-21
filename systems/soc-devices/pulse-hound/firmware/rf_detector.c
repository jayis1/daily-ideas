/*
 * Pulse Hound — RF Signal Hunter
 * ESP32-S3 Firmware
 *
 * rf_detector.c — ADS1115 I2C driver, AD8318 VOUT->dBm conversion,
 *                 temperature compensation, power-gate control
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "rf_detector.h"
#include "config.h"
#include <math.h>
#include <string.h>

/* ---- Calibration (stored in NVS, loaded at init) ---- */
static float cal_slope_mv_per_db = AD8318_SLOPE_MV_PER_DB;
static float cal_intercept_v      = AD8318_INTERCEPT_V;
static float cal_temp_coeff_mv_per_c = AD8318_TEMP_COEFF_MV_PER_C;
static int   detector_powered = 0;

/* ---- I2C helpers (provided by platform HAL) ---- */
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len);
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);

/* ---- ADS1115 register read ---- */
static int ads1115_read_channel(uint16_t mux_config, int16_t *raw)
{
    uint8_t cfg[2];
    uint8_t result[2];

    /* Build config word:
     * OS=1 (start), MUX=mux_config, PGA=±6.144V (0x0000),
     * MODE=single-shot (0x0100), DR=860 SPS (0x00E0),
     * COMP disabled (0x0003)
     */
    uint16_t config = 0x8000U | mux_config | ADS1115_GAIN_6144
                      | 0x0100U | ADS1115_DR_860SPS | 0x0003U;

    cfg[0] = (uint8_t)(config >> 8);
    cfg[1] = (uint8_t)(config & 0xFF);

    if (i2c_write_reg(ADS1115_ADDR, ADS1115_REG_CONFIG, cfg, 2) != 0)
        return -1;

    /* Wait for conversion (860 SPS ≈ 1.2 ms, give 3 ms margin) */
    delay_ms(3);

    if (i2c_read_reg(ADS1115_ADDR, ADS1115_REG_CONVERSION, result, 2) != 0)
        return -1;

    *raw = (int16_t)((result[0] << 8) | result[1]);
    return 0;
}

/* ---- ADS1115 raw to voltage ---- */
/* Full-scale range ±6.144 V → 16-bit signed → LSB = 6.144/32768 = 187.5 µV */
#define ADS1115_LSB_V  (6.144f / 32768.0f)

static float ads1115_raw_to_v(int16_t raw)
{
    return (float)raw * ADS1115_LSB_V;
}

/* ---- AD8318 power-up / power-down ---- */
void rf_detector_power_on(void)
{
    gpio_set(AD8318_ANALOG_EN_GPIO, 1);   /* enable LDO for AFE */
    delay_ms(5);
    gpio_set(AD8318_PWDN_GPIO, 1);        /* PWDN active low → high = on */
    delay_ms(1);                          /* AD8318 wake-up < 1 ms */
    detector_powered = 1;
}

void rf_detector_power_off(void)
{
    gpio_set(AD8318_PWDN_GPIO, 0);        /* power down detector */
    gpio_set(AD8318_ANALOG_EN_GPIO, 0);   /* cut LDO */
    detector_powered = 0;
}

int rf_detector_is_powered(void)
{
    return detector_powered;
}

/* ---- Temperature read from AD8318 TEMP pin via ADS1115 AIN1 ---- */
float rf_detector_read_temp_c(void)
{
    int16_t raw;
    if (ads1115_read_channel(ADS1115_AIN_TEMP, &raw) != 0)
        return AD8318_TEMP_AT_CALIBRATION_C; /* fallback */

    float v = ads1115_raw_to_v(raw);
    /* TEMP pin: 10 mV/°C, nominally 0.8 V at 25 °C */
    float temp_c = (v - AD8318_TEMP_NOMINAL_V) / (AD8318_TEMP_MV_PER_C / 1000.0f)
                   + AD8318_TEMP_AT_CALIBRATION_C;
    return temp_c;
}

/* ---- RSSI read: VOUT -> dBm with temperature compensation ---- */
int rf_detector_read_rssi_dbm(float *rssi_dbm)
{
    if (!detector_powered)
        return -1;

    int16_t raw_rssi;
    if (ads1115_read_channel(ADS1115_AIN_RSSI, &raw_rssi) != 0)
        return -1;

    float v_out = ads1115_raw_to_v(raw_rssi);

    /* Temperature compensation */
    float temp_c = rf_detector_read_temp_c();
    float d_intercept = cal_temp_coeff_mv_per_c * (temp_c - AD8318_TEMP_AT_CALIBRATION_C);
    float v_intercept_comp = cal_intercept_v + d_intercept / 1000.0f;

    /* P_dBm = (V_OUT - V_intercept) / SLOPE
     * SLOPE is negative (stronger signal -> lower voltage) */
    float p_dbm = (v_out - v_intercept_comp) / (cal_slope_mv_per_db / 1000.0f);

    /* Clamp to valid range */
    if (p_dbm > RSSI_MAX_DBM) p_dbm = RSSI_MAX_DBM;
    if (p_dbm < RSSI_MIN_DBM) p_dbm = RSSI_MIN_DBM;

    *rssi_dbm = p_dbm;
    return 0;
}

/* ---- Bulk sample: read N RSSI samples into array ---- */
int rf_detector_sample_burst(float *samples, int count, uint32_t sample_interval_ms)
{
    if (!detector_powered)
        return -1;

    for (int i = 0; i < count; i++) {
        if (rf_detector_read_rssi_dbm(&samples[i]) != 0)
            return -1;
        if (i < count - 1)
            delay_ms(sample_interval_ms);
    }
    return count;
}

/* ---- Calibration accessors ---- */
void rf_detector_set_calibration(float slope, float intercept, float temp_coeff)
{
    cal_slope_mv_per_db   = slope;
    cal_intercept_v       = intercept;
    cal_temp_coeff_mv_per_c = temp_coeff;
}

void rf_detector_get_calibration(float *slope, float *intercept, float *temp_coeff)
{
    if (slope)      *slope = cal_slope_mv_per_db;
    if (intercept)  *intercept = cal_intercept_v;
    if (temp_coeff) *temp_coeff = cal_temp_coeff_mv_per_c;
}

/* ---- Median filter (for DF mode: robust against transient spikes) ---- */
static int cmp_float(const void *a, const void *b)
{
    float fa = *(const float *)a, fb = *(const float *)b;
    return (fa > fb) - (fa < fb);
}

float rf_detector_median_rssi(float *samples, int count)
{
    /* In-place sort copy */
    float tmp[256];
    int n = count < 256 ? count : 256;
    memcpy(tmp, samples, n * sizeof(float));
    qsort(tmp, n, sizeof(float), cmp_float);
    return tmp[n / 2];
}