/**
 * lumen_cast/firmware/color.c — TCS34725 color sensor + CCT/Duv computation
 *
 * AMS TCS34725 RGB + Clear color sensor
 *   I2C address: 0x29 (fixed)
 *   16-bit per channel (R, G, B, C)
 *   Integrated IR blocking filter
 *   Programmable gain (1×, 4×, 16×, 60×) and integration time
 *
 * CCT computation: McCamy's approximation from CIE 1931 (x, y)
 * Duv computation: distance from Planckian locus in CIE 1960 uv
 */

#include "main.h"
#include <math.h>

#define TAG "COLOR"

/* TCS34725 registers (command byte: 0x80 | reg) */
#define TCS34725_REG_ENABLE    0x00
#define TCS34725_REG_ATIME     0x01
#define TCS34725_REG_WTIME     0x03
#define TCS34725_REG_AILT      0x04
#define TCS34725_REG_AIHT      0x06
#define TCS34725_REG_ID        0x12
#define TCS34725_REG_CDATAL    0x14
#define TCS34725_REG_RDATAL    0x16
#define TCS34725_REG_GDATAL    0x18
#define TCS34725_REG_BDATAL    0x1A
#define TCS34725_REG_PPCOUNT   0x0E
#define TCS34725_REG_CONTROL   0x0F

#define TCS34725_ENABLE_PON    0x01
#define TCS34725_ENABLE_AEN    0x02
#define TCS34725_ENABLE_WEN    0x08

#define TCS34725_ID_TCS34725   0x44  /* ID register = 0x44 */
#define TCS34725_ID_TCS34727   0x4D

/* Gain values */
#define TCS34725_GAIN_1X       0x00
#define TCS34725_GAIN_4X       0x01
#define TCS34725_GAIN_16X      0x02
#define TCS34725_GAIN_60X      0x03

/* Integration time: 256 − ATIME counts × 2.4ms
 * ATIME=0x00 → 612ms (max integration, best SNR)
 * ATIME=0xFF → 2.4ms
 */
#define TCS34725_ATIME_154MS   0x9B  /* 154ms */
#define TCS34725_ATIME_614MS   0x00  /* 614ms (max) */

int tcs34725_init(void)
{
    uint8_t id = i2c_read8(TCS34725_I2C_ADDR, TCS34725_REG_ID);
    if (id != TCS34725_ID_TCS34725 && id != TCS34725_ID_TCS34727) {
        LOGE(TAG, "TCS34725 not found (ID=0x%02X)", id);
        return -1;
    }
    LOGI(TAG, "TCS34725 detected (ID=0x%02X)", id);

    /* Set integration time to 154ms */
    i2c_write8(TCS34725_I2C_ADDR, TCS34725_REG_ATIME, TCS34725_ATIME_154MS);

    /* Set gain to 4× */
    i2c_write8(TCS34725_I2C_ADDR, TCS34725_REG_CONTROL, TCS34725_GAIN_4X);

    /* Enable: power on + RGBC ADC enable */
    i2c_write8(TCS34725_I2C_ADDR, TCS34725_REG_ENABLE,
               TCS34725_ENABLE_PON | TCS34725_ENABLE_AEN);
    delay_ms(10);

    /* Re-enable after power-on */
    i2c_write8(TCS34725_I2C_ADDR, TCS34725_REG_ENABLE,
               TCS34725_ENABLE_PON | TCS34725_ENABLE_AEN);

    delay_ms(200);  /* wait for first integration */
    return 0;
}

int tcs34725_read_rgbc(uint16_t *r, uint16_t *g, uint16_t *b, uint16_t *c)
{
    /* Read 8 bytes: C, R, G, B (each 16-bit little-endian) */
    uint8_t buf[8];
    int rc = i2c_read_burst(TCS34725_I2C_ADDR, TCS34725_REG_CDATAL, buf, 8);
    if (rc != 0) {
        LOGE(TAG, "TCS34725 read failed");
        return -1;
    }

    *c = (uint16_t)(buf[1] << 8 | buf[0]);
    *r = (uint16_t)(buf[3] << 8 | buf[2]);
    *g = (uint16_t)(buf[5] << 8 | buf[4]);
    *b = (uint16_t)(buf[7] << 8 | buf[6]);

    /* Check for saturation (clear channel maxed out) */
    if (*c == 0xFFFF) {
        LOGW(TAG, "TCS34725 saturated (C=0xFFFF)");
    }

    return 0;
}

/* ── CCT and Duv computation ───────────────────────────────────────── */
/*
 * The TCS34725 has a specific spectral response for R, G, B channels.
 * To convert to CIE 1931 XYZ, we use an approximation matrix calibrated
 * for typical white LEDs. This is not spectrally accurate for all sources
 * but gives reasonable CCT/Duv for white/near-white light.
 *
 * Approximate conversion (for 4× gain, 154ms integration):
 *   X = 1.850×R − 0.715×G − 0.195×B
 *   Y = 0.395×R + 1.295×G − 0.290×B  (≈ luminance)
 *   Z = −0.275×R − 0.475×G + 1.985×B  (≈ blue)
 *
 * Then: x = X/(X+Y+Z), y = Y/(X+Y+Z)
 * CCT via McCamy: n = (x-0.3320)/(0.1858-y)
 *                 CCT = 449n³ + 3525n² + 6823.3n + 5520.33
 *
 * Duv: convert (x,y) → (u,v) in CIE 1960:
 *   u = 4x/(-2x+12y+3)
 *   v = 6y/(-2x+12y+3)
 * Then find nearest point on Planckian locus and compute distance.
 */

/* TCS34725 channel-to-XYZ matrix (approximate, for white LEDs) */
static const float M_R2X =  1.850f, M_G2X = -0.715f, M_B2X = -0.195f;
static const float M_R2Y =  0.395f, M_G2Y =  1.295f, M_B2Y = -0.290f;
static const float M_R2Z = -0.275f, M_G2Z = -0.475f, M_B2Z =  1.985f;

/* Planckian locus samples in CIE 1960 uv space (1000K – 40000K)
 * Used for Duv computation via table lookup + linear interpolation.
 * Each entry: {T(K), u, v} */
static const float planck_uv[][3] = {
    {1000, 0.4482, 0.3546},
    {1500, 0.3471, 0.3516},
    {2000, 0.3018, 0.3240},
    {2500, 0.2787, 0.3025},
    {3000, 0.2655, 0.2866},
    {3500, 0.2572, 0.2741},
    {4000, 0.2517, 0.2641},
    {4500, 0.2478, 0.2560},
    {5000, 0.2450, 0.2492},
    {5500, 0.2429, 0.2435},
    {6000, 0.2413, 0.2386},
    {6500, 0.2401, 0.2344},
    {7000, 0.2391, 0.2308},
    {8000, 0.2377, 0.2247},
    {10000, 0.2360, 0.2156},
    {15000, 0.2333, 0.2026},
    {20000, 0.2321, 0.1954},
    {40000, 0.2304, 0.1824},
};
#define N_PLANCK  (sizeof(planck_uv) / sizeof(planck_uv[0]))

void color_compute_cct_duv(uint16_t r, uint16_t g, uint16_t b, uint16_t c,
                            float *cct_k, float *duv, float *x_out, float *y_out)
{
    *cct_k = 0;
    *duv = 0;
    *x_out = 0;
    *y_out = 0;

    /* Avoid division by zero */
    if (c == 0) return;

    /* Normalize by clear channel to remove intensity dependence */
    float R = (float)r / (float)c;
    float G = (float)g / (float)c;
    float B = (float)b / (float)c;

    /* Convert to XYZ (normalized) */
    float X = M_R2X * R + M_G2X * G + M_B2X * B;
    float Y = M_R2Y * R + M_G2Y * G + M_B2Y * B;
    float Z = M_R2Z * R + M_G2Z * G + M_B2Z * B;

    float sum = X + Y + Z;
    if (sum < 0.0001f) return;

    /* CIE 1931 chromaticity */
    float x = X / sum;
    float y = Y / sum;
    *x_out = x;
    *y_out = y;

    /* McCamy's approximation for CCT */
    float n = (x - 0.3320f) / (0.1858f - y);
    float cct = 449.0f * n*n*n + 3525.0f * n*n + 6823.3f * n + 5520.33f;

    /* Clamp to reasonable range */
    if (cct < 1000.0f) cct = 1000.0f;
    if (cct > 40000.0f) cct = 40000.0f;
    *cct_k = cct;

    /* Convert (x,y) to CIE 1960 (u,v) */
    float denom = -2.0f * x + 12.0f * y + 3.0f;
    if (fabsf(denom) < 0.0001f) return;
    float u = 4.0f * x / denom;
    float v = 6.0f * y / denom;

    /* Find nearest point on Planckian locus */
    float min_dist = 1e9f;
    float best_u = 0, best_v = 0;

    for (int i = 0; i < (int)N_PLANCK - 1; i++) {
        float u0 = planck_uv[i][1], v0 = planck_uv[i][2];
        float u1 = planck_uv[i+1][1], v1 = planck_uv[i+1][2];

        /* Distance from (u,v) to segment (u0,v0)-(u1,v1) */
        float du = u1 - u0, dv = v1 - v0;
        float len2 = du*du + dv*dv;
        if (len2 < 1e-10f) continue;

        float t = ((u - u0) * du + (v - v0) * dv) / len2;
        if (t < 0) t = 0;
        if (t > 1) t = 1;

        float pu = u0 + t * du;
        float pv = v0 + t * dv;
        float dist = sqrtf((u - pu)*(u - pu) + (v - pv)*(v - pv));

        if (dist < min_dist) {
            min_dist = dist;
            best_u = pu;
            best_v = pv;
        }
    }

    /* Duv: signed distance from Planckian locus
     * Positive = above locus (greenward), negative = below (magenta) */
    float cross = (u - best_u) * (best_v + 0.5f) - (v - best_v) * (best_u + 0.2f);
    *duv = (cross > 0) ? min_dist : -min_dist;
}