/* adc_ads122.c — ADS122U04 24-bit ADC interface over I2C1.
 *
 * Reads the mirror thermistor (T_m) and reference thermistor (T_r) via
 * a half-bridge with precision 100 kΩ reference resistor.
 * Differential mode for ΔT; single-ended for absolute T_m.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "adc_ads122.h"
#include <math.h>

extern I2C_HandleTypeDef hi2c1;

#define ADS122_REG_CFG0   0x00
#define ADS122_REG_CFG1   0x01
#define ADS122_REG_CFG2   0x02
#define ADS122_REG_CFG3   0x03

static int ads_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = { reg | 0x40, val };  /* write single reg */
    return HAL_I2C_Master_Transmit(&hi2c1, ADC_I2C_ADDR, buf, 2, I2C1_TIMEOUT_MS) == HAL_OK;
}

static int ads_read_reg(uint8_t reg, uint8_t *val)
{
    uint8_t cmd = reg | 0x20;  /* read single reg */
    HAL_I2C_Master_Transmit(&hi2c1, ADC_I2C_ADDR, &cmd, 1, I2C1_TIMEOUT_MS);
    return HAL_I2C_Master_Receive(&hi2c1, ADC_I2C_ADDR, val, 1, I2C1_TIMEOUT_MS) == HAL_OK;
}

static int ads_start_conv(void)
{
    uint8_t cmd = 0x08;  /* START/SYNC */
    return HAL_I2C_Master_Transmit(&hi2c1, ADC_I2C_ADDR, &cmd, 1, I2C1_TIMEOUT_MS) == HAL_OK;
}

static int ads_read_data(int32_t *val)
{
    uint8_t cmd = 0x10;  /* RDATA */
    uint8_t buf[3];
    HAL_I2C_Master_Transmit(&hi2c1, ADC_I2C_ADDR, &cmd, 1, I2C1_TIMEOUT_MS);
    if (HAL_I2C_Master_Receive(&hi2c1, ADC_I2C_ADDR, buf, 3, I2C1_TIMEOUT_MS) != HAL_OK)
        return 0;
    *val = ((int32_t)buf[0] << 16) | ((int32_t)buf[1] << 8) | buf[2];
    if (*val & 0x800000L) *val |= 0xFF000000L;  /* sign extend */
    return 1;
}

int ads122_init(void)
{
    /* Configure: PGA gain 8, 20 SPS, single-shot, internal reference.
     * Differential mode on AIN0-AIN1 for ΔT measurement. */
    ads_write_reg(ADS122_REG_CFG0, 0x00 | 0x01 /* AIN0-AIN1 */ | 0x20 /*PGA*/);
    /* CFG1: data rate 20 SPS = 0x04, single shot */
    ads_write_reg(ADS122_REG_CFG1, 0x04);
    /* CFG2: internal Vref, gain 8 (PGA_G=0x00), normal mode */
    ads_write_reg(ADS122_REG_CFG2, 0x00);
    /* CFG3: no IDAC */
    ads_write_reg(ADS122_REG_CFG3, 0x00);
    return 1;
}

/* Convert raw ADC code to thermistor resistance.
 * Bridge: V_excitation -- R_ref -- NTC -- GND
 *          └─ ADS diff AIN0 (mid node) vs AIN1 (ref node)
 * Code is proportional to (V_ref - V_ntc), with full-scale = Vref/PGA.
 * R_ntc = R_ref * code / (full_scale - code)
 */
static float code_to_resistance(int32_t code, float r_ref)
{
    /* ADS122U04: full-scale = ±Vref/PGA, 24-bit signed.
     * For single-supply with mid-supply reference, the relationship
     * simplifies to: R_ntc = R_ref * (1 + code/fs) / (1 - code/fs)
     * For small signals around mid-supply this reduces to a linear
     * ratio. We use the direct form.
     */
    float fs = 8388607.0f;  /* 2^23 - 1 */
    float f = (float)code / fs;
    if (f >= 0.999f) f = 0.999f;
    if (f <= -0.999f) f = -0.999f;
    return r_ref * (1.0f + f) / (1.0f - f);
}

/* β-parameter equation → temperature [°C] from resistance. */
static float res_to_temp_c(float r)
{
    float inv_t = 1.0f / 298.15f + (1.0f / NTC_B) * logf(r / NTC_R_REF);
    return 1.0f / inv_t - 273.15f;
}

/* Read both thermistors. For differential ΔT, we use the ADS differential
 * mode. For absolute temperature, we switch to single-ended. To keep
 * things simple, here we read the two single-ended channels sequentially.
 */
int ads122_read_mirror(float *t_mirror, float *t_ref, float *dt)
{
    int32_t code_m, code_r;

    /* Read AIN0 single-ended (mirror thermistor) */
    ads_write_reg(ADS122_REG_CFG0, 0x08 /* AIN0 */);
    ads_start_conv();
    HAL_Delay(60);  /* conversion time at 20 SPS ≈ 50 ms */
    if (!ads_read_data(&code_m)) return 0;
    float r_m = code_to_resistance(code_m, NTC_REF_RES);
    *t_mirror = res_to_temp_c(r_m);

    /* Read AIN1 single-ended (reference thermistor) */
    ads_write_reg(ADS122_REG_CFG0, 0x09 /* AIN1 */);
    ads_start_conv();
    HAL_Delay(60);
    if (!ads_read_data(&code_r)) return 0;
    float r_r = code_to_resistance(code_r, NTC_REF_RES);
    *t_ref = res_to_temp_c(r_r);

    *dt = *t_mirror - *t_ref;
    return 1;
}

/* Fault detection: open/short. */
int ads122_fault(float t_mirror)
{
    if (t_mirror > 150.0f || t_mirror < -80.0f) return 1;
    return 0;
}