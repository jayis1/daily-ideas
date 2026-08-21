/*
 * Flux Ring — accel_sensor.h
 * LIS2DH12 3-axis accelerometer driver.
 * I2C address: 0x19 (SA0=1)
 */

#ifndef ACCEL_SENSOR_H_
#define ACCEL_SENSOR_H_

#include <zephyr/drivers/i2c.h>
#include <stdint.h>

#define LIS2DH12_I2C_ADDR   0x19

/* Key registers */
#define LIS2DH12_REG_WHO_AM_I   0x0F
#define LIS2DH12_REG_CTRL1      0x20
#define LIS2DH12_REG_CTRL2      0x21
#define LIS2DH12_REG_CTRL3      0x22
#define LIS2DH12_REG_CTRL4      0x23
#define LIS2DH12_REG_CTRL5      0x24
#define LIS2DH12_REG_OUT_X_L    0x28
#define LIS2DH12_REG_OUT_X_H    0x29
#define LIS2DH12_REG_OUT_Y_L    0x2A
#define LIS2DH12_REG_OUT_Y_H    0x2B
#define LIS2DH12_REG_OUT_Z_L    0x2C
#define LIS2DH12_REG_OUT_Z_H    0x2D
#define LIS2DH12_REG_INT1_CFG   0x30
#define LIS2DH12_REG_INT1_SRC   0x31
#define LIS2DH12_REG_INT1_THS   0x32
#define LIS2DH12_REG_INT1_DUR   0x33

#define LIS2DH12_WHO_AM_I_VAL  0x33

typedef struct {
    float x, y, z;  /* Acceleration in g */
} accel_data_t;

/**
 * Initialize LIS2DH12 over I2C.
 * Configures: ±2g range, 100Hz ODR, high-resolution mode,
 *             wake-on-motion interrupt on INT2.
 */
int accel_sensor_init(const struct device *i2c_dev);

/**
 * Read 3-axis acceleration (g).
 */
int accel_sensor_read(accel_data_t *data);

/**
 * Configure wake-on-motion threshold.
 * @param threshold_mg  Threshold in milli-g (default: 32mg)
 */
int accel_sensor_set_wom_threshold(uint16_t threshold_mg);

#endif /* ACCEL_SENSOR_H_ */