/*
 * trajectory_recon.c — 3D trajectory reconstruction from IMU data
 *
 * Implements Madgwick orientation filter + double integration
 * for pen position tracking. Projects 3D path onto 2D writing plane.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "trajectory_recon.h"
#include <math.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "traj_recon";

/* Madgwick filter beta parameter (tradeoff: noise vs response) */
#define MADGWICK_BETA  0.04f

/* High-pass filter cutoff for drift correction */
#define HPF_ALPHA      0.995f

/* Quaternion: q = {w, x, y, z} */
typedef struct {
    float w, x, y, z;
} quaternion_t;

static quaternion_t q = {1.0f, 0.0f, 0.0f, 0.0f};
static float position_x = 0.0f;
static float position_y = 0.0f;
static float position_z = 0.0f;
static float prev_lin_accel_x = 0.0f;
static float prev_lin_accel_y = 0.0f;
static float prev_lin_accel_z = 0.0f;
static float dt = 0.005f;  /* 200Hz → 5ms */
static bool initialized = false;

/* Magnetometer heading reference (for yaw correction) */
static float mag_heading = 0.0f;

/* ---- Quaternion helpers ---- */

static float quat_norm(quaternion_t *q)
{
    return sqrtf(q->w * q->w + q->x * q->x + q->y * q->y + q->z * q->z);
}

static void quat_normalize(quaternion_t *q)
{
    float n = quat_norm(q);
    if (n > 0.0001f) {
        q->w /= n;
        q->x /= n;
        q->y /= n;
        q->z /= n;
    }
}

static quaternion_t quat_multiply(const quaternion_t *a, const quaternion_t *b)
{
    quaternion_t r;
    r.w = a->w*b->w - a->x*b->x - a->y*b->y - a->z*b->z;
    r.x = a->w*b->x + a->x*b->w + a->y*b->z - a->z*b->y;
    r.y = a->w*b->y - a->x*b->z + a->y*b->w + a->z*b->x;
    r.z = a->w*b->z + a->x*b->y - a->y*b->x + a->z*b->w;
    return r;
}

/* Rotate a vector by quaternion: v' = q * v * q_conjugate */
static void quat_rotate_vector(const quaternion_t *q, float vx, float vy, float vz,
                                float *out_x, float *out_y, float *out_z)
{
    quaternion_t v = {0, vx, vy, vz};
    quaternion_t q_conj = {q->w, -q->x, -q->y, -q->z};
    quaternion_t result = quat_multiply(quat_multiply(q, &v), &q_conj);
    *out_x = result.x;
    *out_y = result.y;
    *out_z = result.z;
}

/* ---- Madgwick MIMU filter update ---- */

static void madgwick_update(float gx, float gy, float gz,
                              float ax, float ay, float az,
                              float mx, float my, float mz)
{
    float recip_norm;
    float s0, s1, s2, s3;
    float q_dot1, q_dot2, q_dot3, q_dot4;
    float _2qw, _2qx, _2qy, _2qz;
    float hx, hy, _2bx, _2bz;
    float _8bx, _2by;

    /* Rate of change of quaternion from gyroscope */
    q_dot1 = 0.5f * (-q.x * gx - q.y * gy - q.z * gz);
    q_dot2 = 0.5f * (q.w * gx + q.y * gz - q.z * gy);
    q_dot3 = 0.5f * (q.w * gy - q.x * gz + q.z * gx);
    q_dot4 = 0.5f * (q.w * gz + q.x * gy - q.y * gx);

    /* Normalize accelerometer */
    recip_norm = sqrtf(ax * ax + ay * ay + az * az);
    if (recip_norm > 0.0001f) {
        ax /= recip_norm;
        ay /= recip_norm;
        az /= recip_norm;
    } else {
        return;
    }

    /* Normalize magnetometer */
    recip_norm = sqrtf(mx * mx + my * my + mz * mz);
    if (recip_norm > 0.0001f) {
        mx /= recip_norm;
        my /= recip_norm;
        mz /= recip_norm;
    } else {
        /* Fallback: no magnetometer, use gravity-only */
        goto gravity_only;
    }

    /* Reference direction of earth's magnetic field */
    _2qw = 2.0f * q.w;
    _2qx = 2.0f * q.x;
    _2qy = 2.0f * q.y;
    _2qz = 2.0f * q.z;

    hx = mx * _2qw + my * _2qz - mz * _2qy;
    hy = mx * _2qx + my * _2qy + mz * _2qw;
    _2bx = sqrtf(hx * hx + hy * hy);
    _2bz = -mx * _2qy + my * _2qx - mz * (q.w * q.w - q.x * q.x - q.y * q.y + q.z * q.z);
    _2by = _2bz;

    /* Gradient descent corrective step */
    _8bx = 2.0f * _2bx;
    _2by = 2.0f * _2by;

    s0 = _2qy * (2.0f * q.x * q.z - _2qw * q.y) - _2qx * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f)
         + _8bx * q.y * (_2bz + _2qw * q.x - _2qy * q.z)
         - _2by * q.x * (_2bx - q.w * q.w + q.x * q.x - q.y * q.y + q.z * q.z);
    s1 = -_2qz * (2.0f * q.x * q.z - _2qw * q.y) - _2qy * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f)
         + _8bx * q.x * (_2bz + _2qw * q.x - _2qy * q.z)
         + _2by * q.w * (_2bx - q.w * q.w + q.x * q.x - q.y * q.y + q.z * q.z);
    s2 = _2qw * (2.0f * q.x * q.z - _2qw * q.y) + _2qz * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f)
         + _8bx * q.z * (_2bz - _2qw * q.y - _2qx * q.z)
         - _2by * q.z * (_2bx - q.w * q.w + q.x * q.x - q.y * q.y + q.z * q.z);
    s3 = _2qx * (2.0f * q.x * q.z - _2qw * q.y) + _2qw * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f)
         + _8bx * q.w * (_2bz - _2qw * q.y - _2qx * q.z)
         + _2by * q.y * (_2bx - q.w * q.w + q.x * q.x - q.y * q.y + q.z * q.z);

    recip_norm = sqrtf(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
    if (recip_norm > 0.0001f) {
        s0 /= recip_norm;
        s1 /= recip_norm;
        s2 /= recip_norm;
        s3 /= recip_norm;
    }

    /* Apply feedback */
    q_dot1 -= MADGWICK_BETA * s0;
    q_dot2 -= MADGWICK_BETA * s1;
    q_dot3 -= MADGWICK_BETA * s2;
    q_dot4 -= MADGWICK_BETA * s3;

    goto integrate;

gravity_only:
    /* Simplified gravity-only correction */
    _2qw = 2.0f * q.w;
    _2qx = 2.0f * q.x;
    _2qy = 2.0f * q.y;
    _2qz = 2.0f * q.z;

    s0 = -_2qy * (2.0f * q.x * q.z - _2qw * q.y) + _2qx * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f);
    s1 = _2qz * (2.0f * q.x * q.z - _2qw * q.y) + _2qy * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f);
    s2 = -_2qw * (2.0f * q.x * q.z - _2qw * q.y) - _2qz * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f);
    s3 = _2qx * (2.0f * q.x * q.z - _2qw * q.y) - _2qw * (2.0f * q.w * q.w + 2.0f * q.z * q.z - 1.0f);

    recip_norm = sqrtf(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
    if (recip_norm > 0.0001f) {
        s0 /= recip_norm;
        s1 /= recip_norm;
        s2 /= recip_norm;
        s3 /= recip_norm;
    }

    q_dot1 -= MADGWICK_BETA * s0;
    q_dot2 -= MADGWICK_BETA * s1;
    q_dot3 -= MADGWICK_BETA * s2;
    q_dot4 -= MADGWICK_BETA * s3;

integrate:
    /* Integrate rate of change of quaternion */
    q.w += q_dot1 * dt;
    q.x += q_dot2 * dt;
    q.y += q_dot3 * dt;
    q.z += q_dot4 * dt;

    quat_normalize(&q);
}

/* ---- Public API ---- */

void trajectory_recon_init(void)
{
    q.w = 1.0f; q.x = 0.0f; q.y = 0.0f; q.z = 0.0f;
    position_x = position_y = position_z = 0.0f;
    initialized = true;
    ESP_LOGI(TAG, "Trajectory reconstructor initialized");
}

void trajectory_recon_set_dt(float sample_dt)
{
    dt = sample_dt;
}

void trajectory_recon_set_mag_heading(float heading_rad)
{
    mag_heading = heading_rad;
}

void trajectory_recon_project(const stroke_event_t *stroke, traj_2d_t *traj)
{
    if (!stroke || !traj || stroke->sample_count == 0) return;

    /* Reset position at start of each stroke (zero-velocity update) */
    position_x = 0.0f;
    position_y = 0.0f;
    position_z = 0.0f;
    q.w = 1.0f; q.x = 0.0f; q.y = 0.0f; q.z = 0.0f;

    int n = stroke->sample_count;
    traj->point_count = 0;

    float prev_vx = 0.0f, prev_vy = 0.0f, prev_vz = 0.0f;

    for (int i = 0; i < n && traj->point_count < MAX_TRAJ_POINTS; i++) {
        const imu_sample_t *s = &stroke->samples[i];
        dt = (i > 0) ?
            (s->timestamp_ms - stroke->samples[i-1].timestamp_ms) / 1000.0f :
            0.005f;
        if (dt <= 0.0f || dt > 0.1f) dt = 0.005f;

        /* Update orientation using Madgwick filter */
        /* Magnetometer: use stored heading as reference */
        float mx = cosf(mag_heading);
        float my = sinf(mag_heading);
        float mz = 0.0f;

        madgwick_update(s->gyro_x, s->gyro_y, s->gyro_z,
                        s->accel_x, s->accel_y, s->accel_z,
                        mx, my, mz);

        /* Remove gravity from accelerometer to get linear acceleration */
        float gravity_world[3] = {0.0f, 0.0f, 9.81f};
        float lin_x, lin_y, lin_z;
        /* Rotate gravity vector to sensor frame and subtract */
        quaternion_t q_conj = {q.w, -q.x, -q.y, -q.z};
        quaternion_t g_world = {0, 0, 0, 9.81f};
        quaternion_t g_sensor = quat_multiply(quat_multiply(&q_conj, &g_world), &q);

        lin_x = s->accel_x - g_sensor.x;
        lin_y = s->accel_y - g_sensor.y;
        lin_z = s->accel_z - g_sensor.z;

        /* High-pass filter on linear acceleration for drift suppression */
        lin_x = HPF_ALPHA * prev_lin_accel_x + (1.0f - HPF_ALPHA) * lin_x;
        lin_y = HPF_ALPHA * prev_lin_accel_y + (1.0f - HPF_ALPHA) * lin_y;
        lin_z = HPF_ALPHA * prev_lin_accel_z + (1.0f - HPF_ALPHA) * lin_z;
        prev_lin_accel_x = lin_x;
        prev_lin_accel_y = lin_y;
        prev_lin_accel_z = lin_z;

        /* Rotate linear acceleration to world frame */
        float world_x, world_y, world_z;
        quat_rotate_vector(&q, lin_x, lin_y, lin_z, &world_x, &world_y, &world_z);

        /* Double integration: acceleration → velocity → position */
        float vx = prev_vx + world_x * dt;
        float vy = prev_vy + world_y * dt;
        float vz = prev_vz + world_z * dt;

        /* Apply velocity damping to reduce drift */
        float damping = 0.98f;
        vx *= damping;
        vy *= damping;
        vz *= damping;

        position_x += vx * dt;
        position_y += vy * dt;
        position_z += vz * dt;

        prev_vx = vx;
        prev_vy = vy;
        prev_vz = vz;

        /* Project onto 2D writing plane (XY in world frame) */
        /* Sample every 5th point to reduce to ~32×32 grid input size */
        if (i % 5 == 0) {
            traj->points[traj->point_count].x = position_x;
            traj->points[traj->point_count].y = position_y;
            traj->point_count++;
        }
    }

    /* Normalize trajectory to 0.0..1.0 range for CNN input */
    if (traj->point_count > 1) {
        float min_x = traj->points[0].x, max_x = traj->points[0].x;
        float min_y = traj->points[0].y, max_y = traj->points[0].y;

        for (int i = 1; i < traj->point_count; i++) {
            if (traj->points[i].x < min_x) min_x = traj->points[i].x;
            if (traj->points[i].x > max_x) max_x = traj->points[i].x;
            if (traj->points[i].y < min_y) min_y = traj->points[i].y;
            if (traj->points[i].y > max_y) max_y = traj->points[i].y;
        }

        float range_x = max_x - min_x;
        float range_y = max_y - min_y;
        float scale = (range_x > range_y ? range_x : range_y);
        if (scale < 0.001f) scale = 1.0f;

        /* Center and scale to 0.1..0.9 (leaving margin for pen width in CNN) */
        for (int i = 0; i < traj->point_count; i++) {
            traj->points[i].x = 0.1f + 0.8f * (traj->points[i].x - min_x) / scale;
            traj->points[i].y = 0.1f + 0.8f * (1.0f - (traj->points[i].y - min_y) / scale);
            /* Note: Y inverted so up-stroke appears upward in rendered image */
        }
    }
}