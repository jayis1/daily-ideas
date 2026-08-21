/*
 * dent-scope / Core/Src/displacement.c
 * Dent Scope — AD7746 24-bit capacitive sensor driver for depth measurement
 *
 * The AD7746 is a 24-bit capacitance-to-digital converter (CDC) with
 * I²C interface. It measures capacitance between two plates with
 * ±4pF range and 4aF resolution (0.000004 pF).
 *
 * Our depth sensor is a parallel-plate capacitor:
 *   C = ε₀·ε_r·A / d
 * where A = plate area (π × 5² = 78.5 mm²), d = gap (~1 mm nominal)
 *
 * A 1 µm change in gap produces ~0.09 pF change → ~11 nm resolution
 * with 4 aF CDC resolution. We calibrate with gauge blocks to get
 * a polynomial fit of µm vs. pF.
 *
 * MIT License.
 */
#include "displacement.h"

#define AD7746_ADDR         0x48  /* I2C 7-bit address (shifted <<1 = 0x90) */
#define AD7746_REG_CAP_SETUP 0x0A
#define AD7746_REG_VT_SETUP  0x0B
#define AD7746_REG_CAP_DATA  0x00 /* 3 bytes MSB-first */
#define AD7746_REG_STATUS    0x00 /* read status via bit check */
#define AD7746_REG_EXC_SETUP 0x09
#define AD7746_REG_CONFIG    0x0C
#define AD7746_REG_CAP_GAIN  0x0E
#define AD7746_REG_CAP_OFFSET 0x0D

static float last_um = 0.0f;
static float last_pf = 0.0f;

static void i2c_write(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    HAL_I2C_Master_Transmit(&hi2c1, (AD7746_ADDR << 1), buf, 2, 50);
}

static uint32_t i2c_read3(uint8_t reg)
{
    uint8_t buf[3] = {0,0,0};
    HAL_I2C_Master_Transmit(&hi2c1, (AD7746_ADDR << 1), &reg, 1, 50);
    HAL_I2C_Master_Receive(&hi2c1, (AD7746_ADDR << 1), buf, 3, 50);
    return ((uint32_t)buf[0] << 16) | ((uint32_t)buf[1] << 8) | buf[2];
}

void displacement_init(void)
{
    /* continuous conversion, channel A */
    i2c_write(AD7746_REG_EXC_SETUP, 0x0E); /* exc A on, 3.3 V */
    i2c_write(AD7746_REG_CAP_SETUP, 0x80); /* CAPEN=1, CEN=1 continuous */
    i2c_write(AD7746_REG_CONFIG, 0x01);   /* default config */
    HAL_Delay(20);
}

void displacement_read_um(void)
{
    /* read 24-bit capacitance data from channel A */
    uint32_t raw = i2c_read3(AD7746_REG_CAP_DATA);

    /* AD7746 output: 24-bit, full scale = ±4pF
     * mid-scale 0x800000 = 0 pF differential
     * 1 count ≈ 4pF / 2^23 = 0.4768 fF */
    float pf = ((int32_t)raw - (int32_t)0x800000) * 4.0f / 8388608.0f;
    last_pf = pf;

    /* convert pF to µm using calibrated polynomial:
     * µm = cap_offset + cap_scale * pf + cap_quad * pf²
     * (calibration stored in flash, e.g. 0 µm at initial contact) */
    last_um = g_cfg.cap_offset + g_cfg.cap_scale * pf + g_cfg.cap_quad * pf * pf;
}

float displacement_last_um(void) { return last_um; }
float displacement_raw_pf(void) { return last_pf; }