/*
 * imu.c — ICM-42688-P 6-axis IMU driver + Mahony attitude filter
 *
 * Reads accel + gyro over I²C, runs a lightweight Mahony complementary
 * filter to produce a stable attitude quaternion. The quaternion is
 * used to map muon tracks onto the celestial sphere.
 */
#include "imu.h"
#include "sky_lens.h"
#include <math.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "driver/i2c.h"
#include "esp_log.h"
static const char *TAG = "imu";
#define I2C_PORT   I2C_NUM_0
#define IMU_ADDR   0x69   /* ICM-42688-P SA0=GND */
#endif

/* ── Mahony filter state ──────────────────────────────────────────────── */
static float q_w = 1.0f, q_x = 0.0f, q_y = 0.0f, q_z = 0.0f;
static float v0_integral[3] = {0,0,0};   /* integral term */
static float s_last_dt = 0.002f;        /* 500 Hz sample rate */

void imu_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("imu init (sim)");
#else
    /* I²C config + ICM-42688-P register init (PWR_MGMT0, GYRO_CONFIG0,
     * ACCEL_CONFIG0, etc.) omitted for brevity. */
    ESP_LOGI(TAG, "ICM-42688-P init (I²C @ 400 kHz)");
#endif
    q_w = 1.0f; q_x = q_y = q_z = 0.0f;
    v0_integral[0] = v0_integral[1] = v0_integral[2] = 0.0f;
}

/* ── Mahony quaternion update ───────────────────────────────────────────
 * Standard Mahony filter: gravity reference from accel, gyro rate
 * integration, with PI feedback. Two-K gain for gyro rates in rad/s.
 */
static void mahony_update(float ax, float ay, float az,
                          float gx, float gy, float gz, float dt)
{
    /* Normalize accel */
    float norm = sqrtf(ax*ax + ay*ay + az*az);
    if (norm < 1e-6f) return;
    ax /= norm; ay /= norm; az /= norm;

    /* Estimated gravity direction from q (rotate [0,0,1] by q) */
    float gx_est = 2.0f * (q_x*q_z - q_w*q_y);
    float gy_est = 2.0f * (q_w*q_x + q_y*q_z);
    float gz_est = q_w*q_w - q_x*q_x - q_y*q_y + q_z*q_z;

    /* Error is cross product between measured and estimated gravity */
    float ex = ay * gz_est - az * gy_est;
    float ey = az * gx_est - ax * gz_est;
    float ez = ax * gy_est - ay * gx_est;

    /* PI feedback */
    const float Kp = 0.8f, Ki = 0.002f;
    v0_integral[0] += ex * Ki * dt;
    v0_integral[1] += ey * Ki * dt;
    v0_integral[2] += ez * Ki * dt;

    gx += Kp * ex + v0_integral[0];
    gy += Kp * ey + v0_integral[1];
    gz += Kp * ez + v0_integral[2];

    /* Integrate quaternion rate: q̇ = 0.5 * q ⊗ [gx,gy,gz] */
    float dqw = 0.5f * (-q_x*gx - q_y*gy - q_z*gz) * dt;
    float dqx = 0.5f * ( q_w*gx + q_y*gz - q_z*gy) * dt;
    float dqy = 0.5f * ( q_w*gy - q_x*gz + q_z*gx) * dt;
    float dqz = 0.5f * ( q_w*gz + q_x*gy - q_y*gx) * dt;

    q_w += dqw; q_x += dqx; q_y += dqy; q_z += dqz;

    /* Normalize q */
    norm = sqrtf(q_w*q_w + q_x*q_x + q_y*q_y + q_z*q_z);
    if (norm > 1e-6f) {
        q_w /= norm; q_x /= norm; q_y /= norm; q_z /= norm;
    }
}

void imu_read_quat(float *w, float *x, float *y, float *z)
{
#ifdef SKY_LENS_SIM
    /* Sim provides a slowly-varying quaternion via the port shim */
    port_sim_imu_quat(w, x, y, z);
    /* Update internal state to match (so subsequent accel/gyro reads
     * are consistent) */
    q_w = *w; q_x = *x; q_y = *y; q_z = *z;
#else
    float ax, ay, az, gx, gy, gz;
    imu_read_accel(&ax, &ay, &az);
    imu_read_gyro(&gx, &gy, &gz);
    mahony_update(ax, ay, az, gx, gy, gz, s_last_dt);
    *w = q_w; *x = q_x; *y = q_y; *z = q_z;
#endif
}

void imu_read_accel(float *ax, float *ay, float *az)
{
#ifdef SKY_LENS_SIM
    port_sim_imu_accel(ax, ay, az);
#else
    /* Read ACCEL_DATA_XYZ from ICM-42688-P (registers 0x0B-0x0D, big-endian) */
    uint8_t buf[6] = {0};
    uint8_t reg = 0x0B;
    i2c_master_write_read_device(I2C_PORT, IMU_ADDR, &reg, 1, buf, 6, pdMS_TO_TICKS(10));
    int16_t rx = (buf[0] << 8) | buf[1];
    int16_t ry = (buf[2] << 8) | buf[3];
    int16_t rz = (buf[4] << 8) | buf[5];
    /* ±4g range: 1 g = 8192 LSB → m/s² = raw / 8192 * 9.81 */
    *ax = (float)rx / 8192.0f * 9.81f;
    *ay = (float)ry / 8192.0f * 9.81f;
    *az = (float)rz / 8192.0f * 9.81f;
#endif
}

void imu_read_gyro(float *gx, float *gy, float *gz)
{
#ifdef SKY_LENS_SIM
    port_sim_imu_gyro(gx, gy, gz);
#else
    uint8_t buf[6] = {0};
    uint8_t reg = 0x11;
    i2c_master_write_read_device(I2C_PORT, IMU_ADDR, &reg, 1, buf, 6, pdMS_TO_TICKS(10));
    int16_t rx = (buf[0] << 8) | buf[1];
    int16_t ry = (buf[2] << 8) | buf[3];
    int16_t rz = (buf[4] << 8) | buf[5];
    /* ±2000 dps: 1 dps = 16.4 LSB → rad/s = raw / 16.4 * π/180 */
    *gx = (float)rx / 16.4f * 0.0174533f;
    *gy = (float)ry / 16.4f * 0.0174533f;
    *gz = (float)rz / 16.4f * 0.0174533f;
#endif
}

#ifndef SKY_LENS_SIM
#include "freertos/FreeRTOS.h"
#endif