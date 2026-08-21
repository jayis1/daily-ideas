/*
 * Flux Ring — mag_sensor.h
 * MMC5983MA 3-axis AMR magnetometer driver.
 * I2C address: 0x30 (default)
 */

#ifndef MAG_SENSOR_H_
#define MAG_SENSOR_H_

#include <zephyr/drivers/i2c.h>
#include <stdint.h>
#include <stdbool.h>

/* I2C address when A0=0, A1=0 */
#define MMC5983MA_I2C_ADDR    0x30

/* Register map */
#define MMC5983MA_REG_INT_STATUS   0x00
#define MMC5983MA_REG_XOUT_23_16   0x01
#define MMC5983MA_REG_XOUT_15_8    0x02
#define MMC5983MA_REG_XOUT_7_0     0x03
#define MMC5983MA_REG_YOUT_23_16   0x04
#define MMC5983MA_REG_YOUT_15_8    0x05
#define MMC5983MA_REG_YOUT_7_0     0x06
#define MMC5983MA_REG_ZOUT_23_16   0x07
#define MMC5983MA_REG_ZOUT_15_8    0x08
#define MMC5983MA_REG_ZOUT_7_0     0x09
#define MMC5983MA_REG_XOUT_17_16   0x0A  /* 2-bit LSBs for X */
#define MMC5983MA_REG_YOUT_17_16   0x0B  /* 2-bit LSBs for Y */
#define MMC5983MA_REG_ZOUT_17_16   0x0C  /* 2-bit LSBs for Z */
#define MMC5983MA_REG_STATUS        0x0D
#define MMC5983MA_REG_CONTROL0      0x0E
#define MMC5983MA_REG_CONTROL1      0x0F
#define MMC5983MA_REG_CONTROL2      0x10
#define MMC5983MA_REG_PRODUCT_ID    0x20

/* Control0 bits */
#define CTRL0_AUTO_SR_EN    (1 << 7)
#define CTRL0_NORMAL_OP     (1 << 6)

/* Control1 bits */
#define CTRL1_BW_100HZ      (0x00 << 0)
#define CTRL1_BW_200HZ      (0x01 << 0)
#define CTRL1_BW_400HZ      (0x02 << 0)
#define CTRL1_BW_800HZ      (0x03 << 0)

/* Control2 bits */
#define CTRL2_SET           (1 << 0)
#define CTRL2_RESET         (1 << 1)
#define CTRL2_TM_M         (1 << 2)  /* Trigger mag measurement */

/* Scale: ±8 Gauss full range, 18-bit unsigned = 262144 counts */
#define MMC5983MA_FULL_SCALE_GAUSS  8.0f
#define MMC5983MA_18BIT_MAX         262143.0f
#define MMC5983MA_OFFSET            131072.0f  /* 2^17, zero-field code */

/* Calibration structure */
typedef struct {
    float offset_x, offset_y, offset_z;
    float scale_x,  scale_y,  scale_z;
} mag_calibration_t;

/* Raw magnetometer reading (Gauss) */
typedef struct {
    float x, y, z;
} mag_data_t;

/**
 * Initialize MMC5983MA over I2C.
 * Configures: continuous mode, 100Hz BW, auto set/reset.
 */
int mag_sensor_init(const struct device *i2c_dev);

/**
 * Perform SET/RESET cycle to cancel sensor offset.
 * Call periodically (every ~10s) for best accuracy.
 */
int mag_sensor_set_reset(void);

/**
 * Read 3-axis magnetic field (Gauss).
 * Applies sensitivity conversion but NOT calibration offsets.
 */
int mag_sensor_read(mag_data_t *data);

/**
 * Perform figure-8 calibration over duration_ms.
 * Records min/max per axis and computes offset + scale.
 * Returns 0 on success, negative on error.
 */
int mag_sensor_calibrate(mag_calibration_t *cal, uint32_t duration_ms);

#endif /* MAG_SENSOR_H_ */