/*
 * ad5933.c — AD5933 impedance analyzer driver implementation
 *
 * Uses the AD5933 in external MCLK mode (clocked by Si5351A CLK1)
 * for maximum frequency flexibility. At each sweep point, the
 * Si5351A CLK0 provides the stimulus and the AD5933 measures the
 * response DFT.
 */

#include "ad5933.h"
#include "stm32g4xx_hal.h"
#include <math.h>

extern I2C_HandleTypeDef hi2c1;

static uint16_t settling_cycles = 10;
static uint16_t dft_points = 1024;
static uint8_t gain_range = 1;  /* default: ±2.56 V */
static bool pga_5x = false;

/* Write a block to AD5933 registers */
static int ad5933_write_block(uint8_t start_reg, const uint8_t *data, uint8_t len)
{
    uint8_t buf[16];
    for (uint8_t i = 0; i < len; i++) {
        buf[0] = start_reg + i;
        buf[1] = data[i];
        HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1,
                                                        buf, 2, 100);
        if (rc != HAL_OK) return -1;
    }
    return 0;
}

/* Read a block from AD5933 registers */
static int ad5933_read_block(uint8_t start_reg, uint8_t *data, uint8_t len)
{
    for (uint8_t i = 0; i < len; i++) {
        uint8_t reg = start_reg + i;
        HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1,
                                                        &reg, 1, 100);
        if (rc != HAL_OK) return -1;
        rc = HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1,
                                    &data[i], 1, 100);
        if (rc != HAL_OK) return -1;
    }
    return 0;
}

/* Wait for DFT valid bit in status register */
static int ad5933_wait_dft(uint32_t timeout_ms)
{
    uint8_t status;
    uint32_t start = HAL_GetTick();
    do {
        uint8_t reg = AD5933_REG_STATUS;
        HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
        HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &status, 1, 100);
        if (status & 0x01) return 0;  /* DFT valid */
    } while ((HAL_GetTick() - start) < timeout_ms);
    return -1;  /* timeout */
}

int ad5933_init(void)
{
    uint8_t ctrl[2];

    /* Power-up with external MCLK, gain range 1, PGA 1x */
    ctrl[0] = AD5933_CTRL_STANDBY;  /* standby mode, no output */
    ctrl[1] = 0x00;  /* range 1 (±2.56 V), PGA 1x */
    ad5933_write_block(AD5933_REG_CTRL_H, ctrl, 2);

    /* Set settling time: 10 cycles * 1024 DFT points */
    uint8_t settle[2];
    settle[0] = (settling_cycles >> 8) & 0x03;  /* settle cycles [9:8] + DFT points */
    settle[1] = settling_cycles & 0xFF;           /* settle cycles [7:0] */
    ad5933_write_block(AD5933_REG_SETTLE_H, settle, 2);

    /* Number of increments: 0 (single frequency mode) */
    uint8_t num_inc[2] = {0x00, 0x00};
    ad5933_write_block(AD5933_REG_NUM_INC_H, num_inc, 2);

    return 0;
}

int ad5933_measure_at_freq(uint32_t freq_hz, complex_t *result)
{
    (void)freq_hz;  /* frequency is set externally by Si5351A */

    /* Initiate with start frequency command (uses current setting) */
    uint8_t ctrl[2];
    ctrl[0] = AD5933_CTRL_INIT_START_FREQ | (gain_range << 1) | (pga_5x ? 0x01 : 0x00);
    ctrl[1] = 0x00;
    ad5933_write_block(AD5933_REG_CTRL_H, ctrl, 2);

    /* Wait for settling */
    HAL_Delay(1 + settling_cycles);  /* ~1 ms per settling cycle */

    /* Start sweep (actually just starts DFT at current frequency) */
    ctrl[0] = AD5933_CTRL_START_SWEEP | (gain_range << 1) | (pga_5x ? 0x01 : 0x00);
    ad5933_write_block(AD5933_REG_CTRL_H, ctrl, 2);

    /* Wait for DFT to complete */
    if (ad5933_wait_dft(100) != 0) return -1;

    /* Read DFT result */
    return ad5933_read_dft(result);
}

int ad5933_read_dft(complex_t *result)
{
    uint8_t real_h, real_l, imag_h, imag_l;

    uint8_t reg = AD5933_REG_REAL_H;
    HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &real_h, 1, 100);

    reg = AD5933_REG_REAL_L;
    HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &real_l, 1, 100);

    reg = AD5933_REG_IMAG_H;
    HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &imag_h, 1, 100);

    reg = AD5933_REG_IMAG_L;
    HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &imag_l, 1, 100);

    /* Convert 16-bit signed values */
    int16_t real_val = (int16_t)((real_h << 8) | real_l);
    int16_t imag_val = (int16_t)((imag_h << 8) | imag_l);

    result->re = (float)real_val;
    result->im = (float)imag_val;

    return 0;
}

void ad5933_set_settling(uint16_t cycles)
{
    settling_cycles = cycles;
}

void ad5933_set_dft_points(uint16_t points)
{
    dft_points = points;
}

void ad5933_set_range(uint8_t range)
{
    gain_range = range & 0x03;
}

void ad5933_set_pga_gain(bool gain_5x)
{
    pga_5x = gain_5x;
}

void ad5933_to_admittance(const complex_t *raw, const calibration_t *cal,
                           complex_t *admittance)
{
    /* Apply calibration correction:
     * Y_cal = (Y_raw - offset) * gain
     * where gain and offset are determined from OSLT calibration */
    float re_cal = (raw->re - cal->offset.re) * cal->system_gain;
    float im_cal = (raw->im - cal->offset.im) * cal->system_gain;

    /* Rotate by system phase offset */
    float cos_p = cosf(cal->system_phase);
    float sin_p = sinf(cal->system_phase);
    admittance->re = re_cal * cos_p - im_cal * sin_p;
    admittance->im = re_cal * sin_p + im_cal * cos_p;
}

float ad5933_read_temp(void)
{
    /* Initiate temperature measurement */
    uint8_t ctrl[2] = {AD5933_CTRL_TEMP_MEASURE, 0x00};
    ad5933_write_block(AD5933_REG_CTRL_H, ctrl, 2);

    /* Wait for valid (bit 0 of status) */
    ad5933_wait_dft(100);

    /* Read temperature registers (0x92, 0x93) */
    uint8_t temp_h, temp_l;
    uint8_t reg = 0x92;
    HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &temp_h, 1, 100);
    reg = 0x93;
    HAL_I2C_Master_Transmit(&hi2c1, AD5933_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, AD5933_ADDR << 1, &temp_l, 1, 100);

    int16_t raw = (int16_t)((temp_h << 8) | temp_l);
    return (float)raw / 32.0f;  /* AD5933 temp: 0.03125 °C/LSB */
}

void ad5933_sleep(void)
{
    uint8_t ctrl[2] = {AD5933_CTRL_POWER_DOWN, 0x00};
    ad5933_write_block(AD5933_REG_CTRL_H, ctrl, 2);
}

void ad5933_wake(void)
{
    ad5933_init();
}