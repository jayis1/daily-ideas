/*
 * Flux Ring — mag_sensor.c
 * MMC5983MA 3-axis AMR magnetometer driver implementation.
 *
 * SPDX-License-Identifier: MIT
 */

#include "mag_sensor.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(mag_sensor, LOG_LEVEL_INF);

static const struct device *i2c_dev;
static uint8_t i2c_addr = MMC5983MA_I2C_ADDR;

/* Write a single register */
static int reg_write(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = { reg, val };
    return i2c_write(i2c_dev, buf, 2, i2c_addr);
}

/* Read single register */
static int reg_read(uint8_t reg, uint8_t *val)
{
    return i2c_reg_read_byte(i2c_dev, i2c_addr, reg, val);
}

/* Read multiple registers */
static int reg_read_burst(uint8_t start_reg, uint8_t *buf, uint16_t len)
{
    return i2c_burst_read(i2c_dev, i2c_addr, start_reg, buf, len);
}

int mag_sensor_init(const struct device *dev)
{
    i2c_dev = dev;

    if (!device_is_ready(i2c_dev)) {
        LOG_ERR("I2C device not ready");
        return -1;
    }

    /* Verify product ID */
    uint8_t prod_id;
    int rc = reg_read(MMC5983MA_REG_PRODUCT_ID, &prod_id);
    if (rc != 0 || prod_id != 0x30) {
        LOG_ERR("MMC5983MA not found (prod_id=0x%02X, expected 0x30)", prod_id);
        return -1;
    }
    LOG_INF("MMC5983MA found, product ID: 0x%02X", prod_id);

    /* Software reset */
    rc = reg_write(MMC5983MA_REG_CONTROL0, 0x80); /* Reset bit */
    if (rc != 0) {
        LOG_ERR("MMC5983MA software reset failed");
        return -1;
    }
    k_msleep(20); /* Wait for reset */

    /* Configure:
     * Control0: Normal operation, no auto-SR yet
     * Control1: BW = 100Hz (suitable for most modes)
     * Control2: No set/reset yet
     */
    rc = reg_write(MMC5983MA_REG_CONTROL0, CTRL0_NORMAL_OP);
    if (rc != 0) return -1;

    rc = reg_write(MMC5983MA_REG_CONTROL1, CTRL1_BW_100HZ);
    if (rc != 0) return -1;

    /* Perform initial SET then RESET for offset cancellation */
    mag_sensor_set_reset();

    /* Enable continuous measurement mode (auto-set/reset every 100ms) */
    rc = reg_write(MMC5983MA_REG_CONTROL0,
                   CTRL0_NORMAL_OP | CTRL0_AUTO_SR_EN);
    if (rc != 0) return -1;

    LOG_INF("MMC5983MA initialized: BW=100Hz, auto SR enabled");
    return 0;
}

int mag_sensor_set_reset(void)
{
    int rc;

    /* SET pulse — align magnetic domains */
    rc = reg_write(MMC5983MA_REG_CONTROL2, CTRL2_SET);
    if (rc != 0) return -1;
    k_msleep(1);

    /* Wait for SET to complete */
    uint8_t status = 0;
    int timeout = 100;
    while (--timeout > 0) {
        rc = reg_read(MMC5983MA_REG_STATUS, &status);
        if (rc == 0 && (status & 0x01)) break;
        k_msleep(1);
    }

    /* RESET pulse — flip domains */
    rc = reg_write(MMC5983MA_REG_CONTROL2, CTRL2_RESET);
    if (rc != 0) return -1;
    k_msleep(1);

    /* Wait for RESET to complete */
    timeout = 100;
    while (--timeout > 0) {
        rc = reg_read(MMC5983MA_REG_STATUS, &status);
        if (rc == 0 && (status & 0x01)) break;
        k_msleep(1);
    }

    /* Trigger a magnetic measurement */
    rc = reg_write(MMC5983MA_REG_CONTROL2, CTRL2_TM_M);
    if (rc != 0) return -1;

    /* Wait for measurement ready */
    timeout = 100;
    while (--timeout > 0) {
        rc = reg_read(MMC5983MA_REG_STATUS, &status);
        if (rc == 0 && (status & 0x01)) break;
        k_msleep(1);
    }

    LOG_INF("MMC5983MA SET/RESET cycle complete");
    return 0;
}

int mag_sensor_read(mag_data_t *data)
{
    uint8_t buf[9];
    int rc = reg_read_burst(MMC5983MA_REG_XOUT_23_16, buf, 9);
    if (rc != 0) {
        LOG_WRN("MMC5983MA read failed");
        return -1;
    }

    /* Parse 24-bit values for X, Y, Z (3 bytes each, big-endian) */
    /* 24-bit unsigned: 0 = -8 Gauss, 2^23 = 0 Gauss, 2^24-1 = +8 Gauss */
    /* We use the 18-bit version for simplicity (most significant 18 bits) */
    uint32_t x_raw = ((uint32_t)buf[0] << 10) | ((uint32_t)buf[1] << 2) | ((uint32_t)buf[6] >> 6);
    uint32_t y_raw = ((uint32_t)buf[2] << 10) | ((uint32_t)buf[3] << 2) | ((uint32_t)buf[7] >> 6);
    uint32_t z_raw = ((uint32_t)buf[4] << 10) | ((uint32_t)buf[5] << 2) | ((uint32_t)buf[8] >> 6);

    /* Convert 18-bit unsigned to signed Gauss:
     * 0 = -8G, 131072 (2^17) = 0G, 262143 = +8G
     */
    data->x = ((float)x_raw - MMC5983MA_OFFSET) *
              (MMC5983MA_FULL_SCALE_GAUSS / MMC5983MA_OFFSET);
    data->y = ((float)y_raw - MMC5983MA_OFFSET) *
              (MMC5983MA_FULL_SCALE_GAUSS / MMC5983MA_OFFSET);
    data->z = ((float)z_raw - MMC5983MA_OFFSET) *
              (MMC5983MA_FULL_SCALE_GAUSS / MMC5983MA_OFFSET);

    return 0;
}

int mag_sensor_calibrate(mag_calibration_t *cal, uint32_t duration_ms)
{
    mag_data_t min_vals = { 1e6f, 1e6f, 1e6f };
    mag_data_t max_vals = { -1e6f, -1e6f, -1e6f };
    mag_data_t sample;

    int64_t start = k_uptime_get();
    int sample_count = 0;

    while (k_uptime_get() - start < duration_ms) {
        if (mag_sensor_read(&sample) == 0) {
            if (sample.x < min_vals.x) min_vals.x = sample.x;
            if (sample.y < min_vals.y) min_vals.y = sample.y;
            if (sample.z < min_vals.z) min_vals.z = sample.z;
            if (sample.x > max_vals.x) max_vals.x = sample.x;
            if (sample.y > max_vals.y) max_vals.y = sample.y;
            if (sample.z > max_vals.z) max_vals.z = sample.z;
            sample_count++;
        }
        k_msleep(10); /* ~100 samples/sec during calibration */
    }

    if (sample_count < 100) {
        LOG_ERR("Calibration: not enough samples (%d)", sample_count);
        return -1;
    }

    /* Compute offset (hard iron) and scale */
    cal->offset_x = (max_vals.x + min_vals.x) / 2.0f;
    cal->offset_y = (max_vals.y + min_vals.y) / 2.0f;
    cal->offset_z = (max_vals.z + min_vals.z) / 2.0f;

    float avg_delta = ((max_vals.x - min_vals.x) +
                       (max_vals.y - min_vals.y) +
                       (max_vals.z - min_vals.z)) / 3.0f;

    cal->scale_x = avg_delta / (max_vals.x - min_vals.x + 1e-6f);
    cal->scale_y = avg_delta / (max_vals.y - min_vals.y + 1e-6f);
    cal->scale_z = avg_delta / (max_vals.z - min_vals.z + 1e-6f);

    LOG_INF("Calibration: %d samples, offset=(%.2f, %.2f, %.2f)",
            sample_count, cal->offset_x, cal->offset_y, cal->offset_z);
    LOG_INF("  scale=(%.3f, %.3f, %.3f)",
            cal->scale_x, cal->scale_y, cal->scale_z);

    return 0;
}