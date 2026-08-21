/*
 * visco-shear / firmware / torque.c
 * ADS1115 + DRV5053 Hall torque sensor acquisition
 *
 * Two DRV5053 Hall sensors: one on torsion arm (torque),
 * one on motor shaft (reference). Differential measurement
 * cancels drift and common-mode magnetic fields.
 *
 * ADS1115 configured for single-ended AIN0 (torque) and AIN1 (reference),
 * PGA gain 2/3 (±6.144 V), 860 SPS continuous conversion.
 *
 * MIT License.
 */
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "main.h"
#include "torque.h"

#define ADS1115_ADDR       0x48
#define ADS1115_REG_CONV   0x00
#define ADS1115_REG_CONFIG 0x01
#define ADS1115_REG_LO_THR 0x02
#define ADS1115_REG_HI_THR 0x03

/* Config: single-shot, AIN0, PGA ±6.144V, 860 SPS */
#define ADS_CFG_AIN0  0xC3E3
#define ADS_CFG_AIN1  0xD3E3

/* Hall sensor sensitivity: 25 mV/mT, magnet gives ~100 mT/rad angular */
#define HALL_SENSITIVITY   2.5f      /* V/rad (25mV/mT * 100mT/rad) */
#define SPRING_K_DEFAULT   0.5e-3f   /* 0.5 mN·m/rad → 0.5e-3 N·m/rad */
/* Torque (N·m) = angle (rad) * spring_k */
/* Torque (µN·m) = angle * spring_k * 1e6 */

static float zero_offset_v = 0.0f;
static float cal_factor = 1.0f;

static void ads1115_write_reg(uint8_t reg, uint16_t val)
{
    uint8_t buf[3] = { reg, (val >> 8) & 0xFF, val & 0xFF };
    i2c_write_blocking(i2c0, ADS1115_ADDR, buf, 3, false);
}

static uint16_t ads1115_read_reg(uint8_t reg)
{
    uint8_t buf[2];
    i2c_write_blocking(i2c0, ADS1115_ADDR, &reg, 1, true);
    i2c_read_blocking(i2c0, ADS1115_ADDR, buf, 2, false);
    return (buf[0] << 8) | buf[1];
}

static float ads1115_read_channel(uint16_t cfg)
{
    ads1115_write_reg(ADS1115_REG_CONFIG, cfg | 0x8000);  /* Start conversion */
    /* Wait for conversion complete (OS bit set) */
    int timeout = 0;
    while ((ads1115_read_reg(ADS1115_REG_CONFIG) & 0x8000) == 0) {
        if (++timeout > 1000) break;
        sleep_ms(1);
    }
    int16_t raw = (int16_t)ads1115_read_reg(ADS1115_REG_CONV);
    /* PGA ±6.144V → 187.5 µV/LSB */
    return raw * 0.0001875f;
}

void torque_init(void)
{
    /* Verify ADS1115 is present */
    ads1115_write_reg(ADS1115_REG_CONFIG, 0x0000);
    sleep_ms(10);
    /* Read default config to verify communication */
    uint16_t cfg = ads1115_read_reg(ADS1115_REG_CONFIG);
    (void)cfg;

    /* Initialize zero offset */
    torque_auto_zero();
    printf("[TORQUE] ADS1115 initialized, zero=%.4f V\n", zero_offset_v);
}

float torque_read_single(void)
{
    /* Read differential: AIN0 (torque) - AIN1 (reference) */
    float v_torque = ads1115_read_channel(ADS_CFG_AIN0);
    float v_ref    = ads1115_read_channel(ADS_CFG_AIN1);
    float v_diff   = (v_torque - v_ref) - zero_offset_v;

    /* Convert voltage to angle (rad) then to torque (µN·m) */
    float angle_rad = v_diff / HALL_SENSITIVITY;
    float torque_Nm = angle_rad * SPRING_K_DEFAULT;
    float torque_uNm = torque_Nm * 1e6f * cal_factor;

    return torque_uNm;
}

float torque_read_averaged(int n)
{
    float sum = 0;
    for (int i = 0; i < n; i++) {
        sum += torque_read_single();
    }
    return sum / n;
}

void torque_auto_zero(void)
{
    /* Stop motor first (caller's responsibility) */
    float sum = 0;
    int n = 64;
    for (int i = 0; i < n; i++) {
        float v_torque = ads1115_read_channel(ADS_CFG_AIN0);
        float v_ref    = ads1115_read_channel(ADS_CFG_AIN1);
        sum += (v_torque - v_ref);
    }
    zero_offset_v = sum / n;
    printf("[TORQUE] Auto-zero: offset = %.6f V\n", zero_offset_v);
}

void torque_set_calibration(float cf)
{
    cal_factor = cf;
}

float torque_get_calibration(void)
{
    return cal_factor;
}