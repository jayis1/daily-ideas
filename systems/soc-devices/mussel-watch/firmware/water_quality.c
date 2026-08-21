/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * water_quality.c — DS18B20, MS5837, Atlas DO, BME280 drivers
 *
 * Implements:
 *  - DS18B20 1-Wire temperature probe (waterproof, submersible)
 *  - MS5837-02BA I²C pressure/depth sensor (0–30 m, 24-bit ADC)
 *  - Atlas Scientific DO EZO (galvanic dissolved O₂, I²C)
 *  - BME280 I²C barometric pressure (in air, for depth compensation)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "water_quality.h"
#include "config.h"
#include <string.h>
#include <math.h>

/* ---- Platform HAL stubs ---- */
extern void i2c_init(int port, int sda, int scl, int freq_hz);
extern int  i2c_write(uint8_t addr, const uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len);
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern void onewire_reset(void);
extern void onewire_write_byte(uint8_t b);
extern uint8_t onewire_read_byte(void);
extern void delay_ms(uint32_t ms);
extern void delay_us(uint32_t us);
extern void gpio_set(int pin, int val);

/* ============================================================
 * DS18B20 — 1-Wire waterproof temperature probe
 * ============================================================ */

/* DS18B20 commands */
#define DS18B20_CMD_SKIP_ROM    0xCC
#define DS18B20_CMD_CONVERT_T   0x44
#define DS18B20_CMD_READ_SCRATCH 0xBE

int water_quality_init(void)
{
    /* BME280 soft-reset */
    uint8_t reset_cmd = 0xB6;
    i2c_write_reg(I2C_ADDR_BME280, 0xE0, &reset_cmd, 1);
    delay_ms(10);
    return 0;
}

float water_temp_read_c(void)
{
    /* Issue 1-Wire reset, SKIP_ROM, CONVERT_T */
    onewire_reset();
    onewire_write_byte(DS18B20_CMD_SKIP_ROM);
    onewire_write_byte(DS18B20_CMD_CONVERT_T);

    /* DS18B20 12-bit conversion takes ~750 ms; we wait 800 ms */
    delay_ms(800);

    /* Read scratchpad (9 bytes) */
    onewire_reset();
    onewire_write_byte(DS18B20_CMD_SKIP_ROM);
    onewire_write_byte(DS18B20_CMD_READ_SCRATCH);

    uint8_t scratch[9];
    for (int i = 0; i < 9; i++)
        scratch[i] = onewire_read_byte();

    /* Temperature: bytes 0 (LSB) and 1 (MSB), 12-bit signed, 0.0625 °C/LSB */
    int16_t raw = (int16_t)((scratch[1] << 8) | scratch[0]);
    return (float)raw * 0.0625f;
}

/* ============================================================
 * Atlas Scientific DO EZO — I²C galvanic dissolved O₂
 * ============================================================ */

float water_do_read_mgl(void)
{
    /* Power on the DO probe */
    gpio_set(PIN_DO_PWR, 1);
    delay_ms(1000); /* probe warmup */

    /* Send "R" read command */
    const char *cmd = ATLAS_CMD_READ;
    i2c_write(I2C_ADDR_ATLAS_DO, (const uint8_t *)cmd, (uint8_t)strlen(cmd));

    /* Atlas EZO needs ~600 ms to process a read */
    delay_ms(600);

    /* Read response: status byte + data string + null */
    uint8_t resp[32];
    memset(resp, 0, sizeof(resp));
    /* Read without register (I²C master read) */
    extern int i2c_read_direct(uint8_t addr, uint8_t *data, uint8_t len);
    i2c_read_direct(I2C_ADDR_ATLAS_DO, resp, 32);

    /* Response format: [status_code][data_string][null]
     * status: 1=success, 2=fail, 254=pending, 255=no_data
     * data: floating-point string like "7.85" */
    if (resp[0] != 1)
        return -1.0f;

    /* Parse the ASCII float after the status byte */
    float value = 0.0f;
    int sign = 1;
    int i = 1;
    if (resp[i] == '-') { sign = -1; i++; }
    int int_part = 0;
    while (resp[i] >= '0' && resp[i] <= '9') {
        int_part = int_part * 10 + (resp[i] - '0');
        i++;
    }
    float frac_part = 0.0f;
    if (resp[i] == '.') {
        i++;
        float div = 10.0f;
        while (resp[i] >= '0' && resp[i] <= '9') {
            frac_part += (resp[i] - '0') / div;
            div *= 10.0f;
            i++;
        }
    }
    value = sign * (int_part + frac_part);

    /* Power off the DO probe to save energy */
    gpio_set(PIN_DO_PWR, 0);
    return value;
}

/* ============================================================
 * MS5837-02BA — I²C pressure/depth sensor (submersible)
 * ============================================================ */

static int ms5837_read_prom(uint8_t offset, uint16_t *val)
{
    uint8_t data[2];
    if (i2c_read_reg(I2C_ADDR_MS5837, MS5837_CMD_PROM_READ + offset, data, 2) < 0)
        return -1;
    *val = (uint16_t)((data[0] << 8) | data[1]);
    return 0;
}

static int ms5837_read_adc(uint8_t cmd, uint32_t *val)
{
    /* Send conversion command */
    uint8_t buf[1] = { cmd };
    i2c_write(I2C_ADDR_MS5837, buf, 1);
    delay_ms(20); /* OSR 256 → ~0.5 ms, pad to 20 ms */

    /* Read ADC result (3 bytes, big-endian) */
    uint8_t data[3];
    extern int i2c_read_direct(uint8_t addr, uint8_t *data, uint8_t len);
    i2c_read_direct(I2C_ADDR_MS5837, data, 3);
    *val = ((uint32_t)data[0] << 16) | ((uint32_t)data[1] << 8) | data[2];
    return 0;
}

void ms5837_convert(const uint16_t prom[8], uint32_t d1, uint32_t d2,
                    float *pressure_mbar, float *temp_c)
{
    /* Per MS5837-02BA datasheet, second-order temperature compensation.
     * PROM coefficients: C1..C6 at indices 1..6. Index 0 = factory, 7 = CRC. */
    int32_t C1 = prom[1];
    int32_t C2 = prom[2];
    int32_t C3 = prom[3];
    int32_t C4 = prom[4];
    int32_t C5 = prom[5];
    int32_t C6 = prom[6];

    /* Calculate 1st order pressure and temperature (OSR=256) */
    int32_t dT = (int32_t)d2 - (C5 * 256);  /* dT = D2 - C5 * 2^8 for 02BA */
    int64_t OFF = (int64_t)C2 * (1 << 16) + ((int64_t)dT * C6) / (1 << 7);
    int64_t SENS = (int64_t)C1 * (1 << 14) + ((int64_t)dT * C3) / (1 << 8);

    int32_t T = (int32_t)(2000 + ((int64_t)dT * C6) / (1 << 23));
    int32_t P = (int32_t)((((int64_t)d1 * SENS) / (1 << 21) - OFF) / (1 << 13));

    /* Second-order temperature compensation (datasheet §2) */
    int32_t T2 = 0;
    int64_t OFF2 = 0;
    int64_t SENS2 = 0;

    if (T < 2000) {
        /* Low temperature (< 20 °C) */
        T2 = 3 * dT * dT / (1 << 23);
        OFF2 = 3 * ((int64_t)(T - 2000) * (T - 2000)) / (1 << 1);
        SENS2 = 5 * ((int64_t)(T - 2000) * (T - 2000)) / (1 << 3);
    }

    T -= T2;
    OFF -= OFF2;
    SENS -= SENS2;

    P = (int32_t)((((int64_t)d1 * SENS) / (1 << 21) - OFF) / (1 << 13));

    *temp_c = T / 100.0f;
    *pressure_mbar = P / 100.0f;
}

float water_depth_read_m(float baro_hpa)
{
    /* Reset MS5837 */
    uint8_t reset_cmd = MS5837_CMD_RESET;
    i2c_write(I2C_ADDR_MS5837, &reset_cmd, 1);
    delay_ms(10);

    /* Read PROM calibration coefficients */
    uint16_t prom[8];
    for (int i = 0; i < 8; i++) {
        if (ms5837_read_prom((uint8_t)(i * 2), &prom[i]) < 0)
            return -999.0f;
    }

    /* Read D1 (pressure) and D2 (temperature) at OSR 256 */
    uint32_t d1, d2;
    if (ms5837_read_adc(MS5837_CMD_CONV_D1_256, &d1) < 0)
        return -999.0f;
    if (ms5837_read_adc(MS5837_CMD_CONV_D2_256, &d2) < 0)
        return -999.0f;

    float p_mbar, t_c;
    ms5837_convert(prom, d1, d2, &p_mbar, &t_c);

    /* Convert mbar → hPa (1 mbar = 1 hPa) */
    float water_hpa = p_mbar;
    if (baro_hpa < 1.0f)
        baro_hpa = 1013.25f;  /* fallback standard atmosphere */

    /* Gauge pressure = water pressure - atmospheric pressure */
    float gauge_hpa = water_hpa - baro_hpa;
    if (gauge_hpa < 0)
        gauge_hpa = 0;  /* above water surface */

    /* Depth = gauge_pressure / (ρ × g)
     * ρ (freshwater) ≈ 997 kg/m³, g = 9.80665 m/s²
     * 1 hPa = 100 Pa → depth_m = gauge_hpa * 100 / (ρ * g)
     */
    float depth_m = gauge_hpa * 100.0f / (997.0f * 9.80665f);
    return depth_m;
}

/* ============================================================
 * BME280 — I²C barometric pressure (in air pod)
 * ============================================================ */

/* BME280 registers */
#define BME280_REG_ID       0xD0
#define BME280_REG_CTRL_HUM 0xF2
#define BME280_REG_STATUS   0xF3
#define BME280_REG_CTRL_MEAS 0xF4
#define BME280_REG_CONFIG    0xF5
#define BME280_REG_PRESS_MSB 0xF7
#define BME280_REG_TEMP_MSB  0xFA
#define BME280_REG_HUM_MSB   0xFD
#define BME280_REG_DIG_P     0x88  /* calibration coefficients start */

static int bme280_read24(uint8_t reg, int32_t *val)
{
    uint8_t data[3];
    if (i2c_read_reg(I2C_ADDR_BME280, reg, data, 3) < 0)
        return -1;
    *val = ((int32_t)data[0] << 12) | ((int32_t)data[1] << 4) | (data[2] >> 4);
    return 0;
}

static int bme280_read16s(uint8_t reg, int16_t *val)
{
    uint8_t data[2];
    if (i2c_read_reg(I2C_ADDR_BME280, reg, data, 2) < 0)
        return -1;
    *val = (int16_t)((data[0] << 8) | data[1]);
    return 0;
}

static int bme280_read16u(uint8_t reg, uint16_t *val)
{
    uint8_t data[2];
    if (i2c_read_reg(I2C_ADDR_BME280, reg, data, 2) < 0)
        return -1;
    *val = (uint16_t)((data[0] << 8) | data[1]);
    return 0;
}

float baro_read_hpa(void)
{
    /* Read calibration coefficients */
    uint16_t dig_P1;
    int16_t  dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
    bme280_read16u(BME280_REG_DIG_P,     &dig_P1);
    bme280_read16s(BME280_REG_DIG_P + 2, &dig_P2);
    bme280_read16s(BME280_REG_DIG_P + 4, &dig_P3);
    bme280_read16s(BME280_REG_DIG_P + 6, &dig_P4);
    bme280_read16s(BME280_REG_DIG_P + 8, &dig_P5);
    bme280_read16s(BME280_REG_DIG_P + 10, &dig_P6);
    bme280_read16s(BME280_REG_DIG_P + 12, &dig_P7);
    bme280_read16s(BME280_REG_DIG_P + 14, &dig_P8);
    bme280_read16s(BME280_REG_DIG_P + 16, &dig_P9);

    /* Temperature coefficients (for fine compensation of pressure) */
    uint16_t dig_T1;
    int16_t  dig_T2, dig_T3;
    bme280_read16u(0x88, &dig_T1);
    bme280_read16s(0x8A, &dig_T2);
    bme280_read16s(0x8C, &dig_T3);

    /* Set forced mode: temperature ×1, pressure ×1, forced */
    uint8_t ctrl = 0x25;  /* 001 001 01 → t×1, p×1, forced */
    i2c_write_reg(I2C_ADDR_BME280, BME280_REG_CTRL_MEAS, &ctrl, 1);
    delay_ms(10);

    /* Read raw pressure (20-bit) and temperature (20-bit) */
    int32_t raw_p, raw_t;
    if (bme280_read24(BME280_REG_PRESS_MSB, &raw_p) < 0)
        return -1.0f;
    if (bme280_read24(BME280_REG_TEMP_MSB, &raw_t) < 0)
        return -1.0f;

    /* BME280 compensation (per datasheet) */
    int32_t var1, var2;
    var1 = ((raw_t >> 3) - ((int32_t)dig_T1 << 1)) * ((int32_t)dig_T2) >> 11;
    var2 = (((((raw_t >> 4) - (int32_t)dig_T1) * ((raw_t >> 4) - (int32_t)dig_T1)) >> 12) * (int32_t)dig_T3) >> 14;
    int32_t t_fine = var1 + var2;
    /* t_fine in units of 0.01 °C */

    /* Pressure compensation */
    var1 = (int32_t)t_fine - 128000;
    var2 = var1 * var1 * (int32_t)dig_P6 >> 16;
    var2 = var2 + ((var1 * (int32_t)dig_P5) << 17);
    var2 = var2 + (((int64_t)dig_P4) << 35);
    var1 = ((var1 * var1 * (int32_t)dig_P3) >> 8) + ((var1 * (int32_t)dig_P2) << 12);
    var1 = (((var1 >> 19) + ((int32_t)1 << 16)) * (int32_t)dig_P1) >> 18;
    if (var1 == 0) return -1.0f; /* avoid division by zero */

    int32_t p = 1048576 - raw_p;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = ((int32_t)dig_P9 * (p >> 13) * (p >> 13)) >> 25;
    var2 = ((int32_t)dig_P8 * p) >> 19;
    p = ((p + var1 + var2) >> 8) + ((int32_t)dig_P7 << 4);

    /* p is in Pa (32-bit); convert to hPa */
    return (float)p / 100.0f;
}

/* ============================================================
 * Combined sampling
 * ============================================================ */

void water_quality_sample_all(mussel_watch_state_t *st)
{
    st->baro_hpa = baro_read_hpa();
    st->water_temp_c = water_temp_read_c();
    st->dissolved_o2_mgl = water_do_read_mgl();
    st->water_depth_m = water_depth_read_m(st->baro_hpa);
}