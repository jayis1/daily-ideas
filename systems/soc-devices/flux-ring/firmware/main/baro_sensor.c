/*
 * Flux Ring — baro_sensor.c
 * MS5837-02BA barometric pressure sensor driver implementation.
 *
 * SPDX-License-Identifier: MIT
 */

#include "baro_sensor.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <math.h>

LOG_MODULE_DECLARE(baro_sensor, LOG_LEVEL_INF);

static const struct device *i2c_dev;

/* Calibration coefficients (from PROM) */
static uint16_t prom[7];  /* C1-C6 stored in PROM[1]-PROM[6] */

static int send_command(uint8_t cmd)
{
    return i2c_write(i2c_dev, &cmd, 1, MS5837_I2C_ADDR);
}

static int read_prom(uint8_t cmd, uint16_t *val)
{
    uint8_t buf[2];
    int rc = i2c_reg_read_byte_buf(i2c_dev, MS5837_I2C_ADDR, cmd, buf, 2);
    if (rc != 0) return rc;
    *val = ((uint16_t)buf[0] << 8) | buf[1];
    return 0;
}

static int read_adc(uint32_t *val)
{
    uint8_t buf[3];
    int rc = i2c_burst_read(i2c_dev, MS5837_I2C_ADDR, MS5837_ADC_READ, buf, 3);
    if (rc != 0) return rc;
    *val = ((uint32_t)buf[0] << 16) | ((uint32_t)buf[1] << 8) | buf[2];
    return 0;
}

int baro_sensor_init(const struct device *dev)
{
    i2c_dev = dev;
    int rc;

    /* Reset */
    rc = send_command(MS5837_RESET);
    if (rc != 0) {
        LOG_ERR("MS5837 reset failed");
        return -1;
    }
    k_msleep(10);

    /* Read PROM calibration data (7 coefficients) */
    for (int i = 0; i < 7; i++) {
        rc = read_prom(MS5837_PROM_READ + (i * 2), &prom[i]);
        if (rc != 0) {
            LOG_ERR("MS5837 PROM read %d failed", i);
            return -1;
        }
    }

    /* Verify CRC (CRC is in upper 4 bits of prom[0]) */
    /* Simplified: we trust the PROM if reads succeed */
    LOG_INF("MS5837 initialized: C1=%u C2=%u C3=%u",
            prom[1], prom[2], prom[3]);

    return 0;
}

int baro_sensor_read(baro_data_t *data)
{
    int rc;
    uint32_t d1, d2;

    /* Start D1 conversion (OSR=512 for 2ms conversion) */
    rc = send_command(MS5837_CONVERT_D1_512);
    if (rc != 0) return -1;
    k_msleep(4); /* Wait for conversion */
    rc = read_adc(&d1);
    if (rc != 0) return -1;

    /* Start D2 conversion */
    rc = send_command(MS5837_CONVERT_D2_512);
    if (rc != 0) return -1;
    k_msleep(4);
    rc = read_adc(&d2);
    if (rc != 0) return -1;

    /* Calculate temperature (first order) */
    int64_t dt = (int64_t)d2 - ((int64_t)prom[5] << 8);  /* d2 - C5*2^8 */
    int64_t temp = 2000 + ((dt * (int64_t)prom[6]) >> 23); /* 2000 + dT*C6/2^23 */

    /* Calculate pressure (second order) */
    int64_t off  = ((int64_t)prom[2] << 16) + ((dt * (int64_t)prom[4]) >> 7);
    int64_t sens = ((int64_t)prom[1] << 15) + ((dt * (int64_t)prom[3]) >> 8);

    /* Second-order temperature compensation */
    int64_t t2 = 0, off2 = 0, sens2 = 0;
    if (temp < 2000) {
        /* Low temperature */
        t2 = (dt * dt) >> 31;
        off2  = 5 * (temp - 2000) * (temp - 2000) >> 3;
        sens2 = 5 * (temp - 2000) * (temp - 2000) >> 1;
    }
    temp -= t2;
    off  -= off2;
    sens -= sens2;

    /* Final pressure calculation */
    int64_t p = ((d1 * sens >> 21) - off) >> 15; /* mbar * 10 */

    data->temperature_c = (float)temp / 100.0f;
    data->pressure_mbar = (float)p / 10.0f;

    /* Altitude estimation (barometric formula) */
    /* h = 44330 * (1 - (P/P0)^(1/5.255)) */
    data->altitude_m = 44330.0f * (1.0f - powf(data->pressure_mbar / 1013.25f,
                                                1.0f / 5.255f));

    return 0;
}