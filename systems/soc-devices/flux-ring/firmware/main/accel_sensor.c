/*
 * Flux Ring — accel_sensor.c
 * LIS2DH12 3-axis accelerometer driver implementation.
 *
 * SPDX-License-Identifier: MIT
 */

#include "accel_sensor.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <math.h>

LOG_MODULE_DECLARE(accel_sensor, LOG_LEVEL_INF);

static const struct device *i2c_dev;

static int reg_write(uint8_t reg, uint8_t val)
{
    return i2c_reg_write_byte(i2c_dev, LIS2DH12_I2C_ADDR, reg, val);
}

static int reg_read(uint8_t reg, uint8_t *val)
{
    return i2c_reg_read_byte(i2c_dev, LIS2DH12_I2C_ADDR, reg, val);
}

int accel_sensor_init(const struct device *dev)
{
    i2c_dev = dev;

    /* Verify WHO_AM_I */
    uint8_t who_am_i;
    int rc = reg_read(LIS2DH12_REG_WHO_AM_I, &who_am_i);
    if (rc != 0 || who_am_i != LIS2DH12_WHO_AM_I_VAL) {
        LOG_ERR("LIS2DH12 not found (who_am_i=0x%02X, expected 0x33)", who_am_i);
        return -1;
    }
    LOG_INF("LIS2DH12 found");

    /* Reboot */
    rc = reg_write(LIS2DH12_REG_CTRL5, 0x80); /* Boot */
    if (rc != 0) return -1;
    k_msleep(10);

    /* CTRL1: ODR = 100Hz (0x5F), all axes enabled, HR mode */
    rc = reg_write(LIS2DH12_REG_CTRL1, 0x5F);
    if (rc != 0) return -1;

    /* CTRL2: HP filter bypass for now */
    rc = reg_write(LIS2DH12_REG_CTRL2, 0x00);
    if (rc != 0) return -1;

    /* CTRL4: ±2g range, HR mode (12-bit) */
    rc = reg_write(LIS2DH12_REG_CTRL4, 0x08);
    if (rc != 0) return -1;

    /* CTRL5: No FIFO, 4D detection disabled */
    rc = reg_write(LIS2DH12_REG_CTRL5, 0x00);
    if (rc != 0) return -1;

    /* Configure wake-on-motion on INT2 */
    accel_sensor_set_wom_threshold(32); /* 32 mg */

    LOG_INF("LIS2DH12 initialized: ±2g, 100Hz, HR mode");
    return 0;
}

int accel_sensor_set_wom_threshold(uint16_t threshold_mg)
{
    /* INT1_CFG: OR of all axes, 0x2A = 6D movement detection */
    int rc = reg_write(LIS2DH12_REG_INT1_CFG, 0x2A);
    if (rc != 0) return -1;

    /* INT1_THS: threshold in mg / 16mg per LSB (±2g range) */
    uint8_t ths = (uint8_t)(threshold_mg / 16);
    if (ths < 1) ths = 1;
    rc = reg_write(LIS2DH12_REG_INT1_THS, ths);
    if (rc != 0) return -1;

    /* INT1_DUR: minimum duration = 0 (any duration) */
    rc = reg_write(LIS2DH12_REG_INT1_DUR, 0x00);
    if (rc != 0) return -1;

    /* CTRL3: INT1 interrupt enabled (AOI1 on INT1) */
    rc = reg_write(LIS2DH12_REG_CTRL3, 0x40);
    if (rc != 0) return -1;

    return 0;
}

int accel_sensor_read(accel_data_t *data)
{
    uint8_t buf[6];
    int rc = i2c_burst_read(i2c_dev, LIS2DH12_I2C_ADDR,
                             LIS2DH12_REG_OUT_X_L | 0x80, /* auto-increment */
                             buf, 6);
    if (rc != 0) {
        LOG_WRN("LIS2DH12 read failed");
        return -1;
    }

    /* 12-bit left-justified: upper 8 bits = integer, lower 4 bits = fraction */
    int16_t x_raw = (int16_t)((buf[1] << 8) | buf[0]) >> 4;
    int16_t y_raw = (int16_t)((buf[3] << 8) | buf[2]) >> 4;
    int16_t z_raw = (int16_t)((buf[5] << 8) | buf[4]) >> 4;

    /* Convert to g: ±2g range, 12-bit = 2048 LSB/g */
    data->x = (float)x_raw / 2048.0f;
    data->y = (float)y_raw / 2048.0f;
    data->z = (float)z_raw / 2048.0f;

    return 0;
}