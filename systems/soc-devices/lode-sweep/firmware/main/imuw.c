/*
 * lode-sweep / firmware / imuw.c
 * ICM-42688-P IMU read + coil tilt computation for depth correction.
 *
 * Computes the tilt angle of the search coil from horizontal. A level
 * coil (face parallel to ground) has tilt = 0°. The tilt is used to
 * correct the depth estimate for non-level sweeping.
 */
#include "main.h"
#include <math.h>

/* ICM-42688-P I2C address (SA0=0) */
#define IMU_ADDR 0x69

/* Registers */
#define REG_PWR_MGMT0  0x4C
#define REG_ACCEL_DATA 0x0B

static float ax_off = 0, ay_off = 0, az_off = 0;
static const float LSB_G = 1.0f / 2048.0f;   /* ±16g range → 2048 LSB/g */

static void i2c_read(uint8_t addr, uint8_t reg, uint8_t *buf, uint16_t len)
{
    (void)addr; (void)reg; (void)buf; (void)len;
    /* HAL_I2C_Master_Transmit then Receive — placeholder. */
}

void imuw_init(void)
{
    uint8_t cfg[2] = { REG_PWR_MGMT0, 0x0C };  /* LN mode accel */
    /* HAL_I2C_Master_Transmit(IMU_ADDR, cfg, 2, 100) */
    (void)cfg;

    /* Calibration: average 64 samples while stationary, level. */
    float sx = 0, sy = 0, sz = 0;
    for (int i = 0; i < 64; i++) {
        uint8_t d[6];
        i2c_read(IMU_ADDR, REG_ACCEL_DATA, d, 6);
        int16_t rx = (int16_t)((d[0] << 8) | d[1]);
        int16_t ry = (int16_t)((d[2] << 8) | d[3]);
        int16_t rz = (int16_t)((d[4] << 8) | d[5]);
        sx += rx * LSB_G; sy += ry * LSB_G; sz += rz * LSB_G;
    }
    ax_off = sx / 64.0f;
    ay_off = sy / 64.0f;
    /* When coil is level (face down), Z axis reads -1 g */
    az_off = sz / 64.0f + 1.0f;
}

void imuw_read_tilt(float *tilt_deg)
{
    uint8_t d[6];
    i2c_read(IMU_ADDR, REG_ACCEL_DATA, d, 6);
    int16_t rx = (int16_t)((d[0] << 8) | d[1]);
    int16_t ry = (int16_t)((d[2] << 8) | d[3]);
    int16_t rz = (int16_t)((d[4] << 8) | d[5]);

    float x = rx * LSB_G - ax_off;
    float y = ry * LSB_G - ay_off;
    float z = rz * LSB_G - az_off;

    /* Tilt from horizontal = angle between the coil face normal (Z axis)
       and the gravity vector (0, 0, -1).
       When level: z = -1 g, tilt = 0°.
       cos(θ) = |z| / |(x,y,z)| */
    float mag = sqrtf(x*x + y*y + z*z);
    if (mag < 0.01f) { *tilt_deg = 0; return; }
    float cos_t = fabsf(z) / mag;
    if (cos_t > 1.0f) cos_t = 1.0f;
    *tilt_deg = acosf(cos_t) * 180.0f / (float)M_PI;
}