/*
 * imu.c — ICM-42688-P 6-axis IMU driver + self-motion compensation
 *
 * Samples accel + gyro at 1 kHz. Low-frequency device sway (< 20 Hz)
 * is estimated from the accelerometer along the beam axis and subtracted
 * from the measured target velocity, enabling handheld operation.
 */

#include "imu.h"
#include "i2c_util.h"
#include "config.h"
#include <math.h>

/* ICM-42688-P register map (key registers) */
#define ICM_REG_WHOAMI        0x75
#define ICM_REG_PWR_MGMT0     0x4D
#define ICM_REG_GYRO_CONFIG0  0x4F
#define ICM_REG_ACCEL_CONFIG0 0x50
#define ICM_REG_ACCEL_DATA    0x1F  /* X high byte */
#define ICM_REG_GYRO_DATA     0x25  /* X high byte */
#define ICM_WHOAMI_VAL        0x47

static float s_accel_scale = 9.81f / 32768.0f;   /* ±8 g default → m/s²/LSB */
static float s_gyro_scale  = (float)(M_PI / 180.0) / 32768.0f; /* ±2000 dps → rad/s/LSB */

void imu_init(void)
{
    uint8_t whoami;
    if (i2c_read_reg(CONFIG_IMU_I2C_ADDR, ICM_REG_WHOAMI, &whoami, 1) != 0
        || whoami != ICM_WHOAMI_VAL) {
        return;  /* IMU not present — compensation disabled silently */
    }

    /* Reset + power on */
    uint8_t rst = 0x20;  /* SOFT_RESET_CONFIG */
    i2c_write_reg(CONFIG_IMU_I2C_ADDR, ICM_REG_PWR_MGMT0, &rst, 1);
    HAL_Delay(2);

    /* Accel: ±8 g, ODR 1 kHz (LN mode) */
    uint8_t accel_cfg = 0x06;  /* FS=±8g, ODR=1kHz */
    i2c_write_reg(CONFIG_IMU_I2C_ADDR, ICM_REG_ACCEL_CONFIG0, &accel_cfg, 1);

    /* Gyro: ±2000 dps, ODR 1 kHz */
    uint8_t gyro_cfg = 0x06;
    i2c_write_reg(CONFIG_IMU_I2C_ADDR, ICM_REG_GYRO_CONFIG0, &gyro_cfg, 1);

    /* Enable gyro + accel in low-noise mode */
    uint8_t pwr = 0x0F;
    i2c_write_reg(CONFIG_IMU_I2C_ADDR, ICM_REG_PWR_MGMT0, &pwr, 1);
    HAL_Delay(2);
}

void imu_read(imu_sample_t *s)
{
    uint8_t buf[12];
    if (i2c_read_reg(CONFIG_IMU_I2C_ADDR, ICM_REG_ACCEL_DATA, buf, 12) != 0) {
        memset(s, 0, sizeof(*s));
        s->t_ms = HAL_GetTick();
        return;
    }
    int16_t ax = (int16_t)((buf[0]  << 8) | buf[1]);
    int16_t ay = (int16_t)((buf[2]  << 8) | buf[3]);
    int16_t az = (int16_t)((buf[4]  << 8) | buf[5]);
    int16_t gx = (int16_t)((buf[6]  << 8) | buf[7]);
    int16_t gy = (int16_t)((buf[8]  << 8) | buf[9]);
    int16_t gz = (int16_t)((buf[10] << 8) | buf[11]);

    s->ax = ax * s_accel_scale;
    s->ay = ay * s_accel_scale;
    s->az = az * s_accel_scale;
    s->gx = gx * s_gyro_scale;
    s->gy = gy * s_gyro_scale;
    s->gz = gz * s_gyro_scale;
    s->t_ms = HAL_GetTick();
}

/* Low-pass filter: returns sway velocity (mm/s) along beam axis (X) */
float imu_compensate_velocity(const imu_sample_t *s, float t_ms)
{
    /* Integrate accel-X with one-pole HPF to remove DC gravity bias */
    static float v_sway = 0.0f;
    static float v_hp = 0.0f;
    static float t_prev = 0.0f;
    float dt = (t_ms - t_prev) / 1000.0f;
    if (dt <= 0.0f || dt > 0.1f) dt = 1.0f / (float)CONFIG_IMU_SAMPLE_RATE_HZ;
    t_prev = t_ms;

    /* Remove gravity projection (low-pass) */
    static float a_dc = 0.0f;
    float alpha_dc = 0.001f;
    a_dc = a_dc * (1.0f - alpha_dc) + s->ax * alpha_dc;
    float a_hp = s->ax - a_dc;

    /* Integrate to velocity */
    v_sway += a_hp * dt * 1000.0f;  /* m/s² → mm/s */

    /* High-pass to kill drift */
    float alpha_hp = 2.0f * (float)M_PI * CONFIG_IMU_COMPENSATE_FC_HZ * dt;
    if (alpha_hp > 1.0f) alpha_hp = 1.0f;
    v_hp = v_hp * (1.0f - alpha_hp) + v_sway * alpha_hp;

    return v_hp;
}