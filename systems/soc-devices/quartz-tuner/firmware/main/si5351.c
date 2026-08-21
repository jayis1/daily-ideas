/*
 * si5351.c — Si5351A I2C clock generator driver implementation
 *
 * Implements fractional-N PLL synthesis for fine frequency resolution
 * across the 1 kHz – 30 MHz range used for crystal characterization.
 */

#include "si5351.h"
#include "stm32g4xx_hal.h"

/* Si5351A register map (simplified) */
#define SI5351_REG_DEVICE_STATUS   0
#define SI5351_REG_INTERRUPT_STATUS 1
#define SI5351_REG_INTERRUPT_MASK   2
#define SI5351_REG_OEB_PIN_CTRL    3
#define SI5351_REG_PLL_RESET       177
#define SI5351_REG_CRYSTAL_LOAD    183
#define SI5351_REG_CLK0_CTRL       16
#define SI5351_REG_CLK1_CTRL       17
#define SI5351_REG_CLK2_CTRL       18
#define SI5351_REG_PLLA_PARAMS     26   /* MSNA_P1[17:0] */
#define SI5351_REG_PLLB_PARAMS     34   /* MSNB_P1[17:0] */
#define SI5351_REG_MS0_PARAMS      52   /* MS0_P1[17:0] */
#define SI5351_REG_MS1_PARAMS      60   /* MS1_P1[17:0] */

/* I2C handle (external, initialized in main) */
extern I2C_HandleTypeDef hi2c1;

static uint32_t sweep_f_start = 0;
static uint32_t sweep_f_stop = 0;
static uint16_t sweep_n_steps = 0;
static uint16_t sweep_step = 0;
static uint32_t sweep_current_freq = 0;

/* Write a single register */
static int si5351_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c1, SI5351_ADDR << 1,
                                                    buf, 2, 100);
    return (rc == HAL_OK) ? 0 : -1;
}

/* Read a single register */
static int si5351_read_reg(uint8_t reg, uint8_t *val)
{
    HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c1, SI5351_ADDR << 1,
                                                    &reg, 1, 100);
    if (rc != HAL_OK) return -1;
    rc = HAL_I2C_Master_Receive(&hi2c1, SI5351_ADDR << 1, val, 1, 100);
    return (rc == HAL_OK) ? 0 : -1;
}

/* Write multiple registers sequentially */
static int si5351_write_burst(uint8_t start_reg, const uint8_t *data, uint8_t len)
{
    uint8_t buf[32];
    buf[0] = start_reg;
    memcpy(&buf[1], data, len);
    HAL_StatusTypeDef rc = HAL_I2C_Master_Transmit(&hi2c1, SI5351_ADDR << 1,
                                                    buf, len + 1, 200);
    return (rc == HAL_OK) ? 0 : -1;
}

/* Set PLL parameters (MSNA or MSNB) from a + b/c fractional value */
static int si5351_set_pll(uint8_t pll_reg_base, uint32_t a, uint32_t b, uint32_t c)
{
    /* P1 = 128 * a + floor(128 * b / c) - 512 */
    /* P2 = 128 * b - c * floor(128 * b / c) */
    /* P3 = c */
    uint32_t p1 = 128 * a + (128 * b / c) - 512;
    uint32_t p2 = 128 * b - c * (128 * b / c);
    uint32_t p3 = c;

    uint8_t regs[8];
    regs[0] = (p3 >> 8) & 0xFF;    /* P3[15:8] */
    regs[1] = p3 & 0xFF;           /* P3[7:0] */
    regs[2] = (p1 >> 16) & 0x03;   /* P1[17:16] */
    regs[3] = (p1 >> 8) & 0xFF;    /* P1[15:8] */
    regs[4] = p1 & 0xFF;           /* P1[7:0] */
    regs[5] = ((p3 & 0x0F) << 4) | ((p2 >> 16) & 0x0F);
    regs[6] = (p2 >> 8) & 0xFF;    /* P2[15:8] */
    regs[7] = p2 & 0xFF;           /* P2[7:0] */

    return si5351_write_burst(pll_reg_base, regs, 8);
}

/* Set multisynth parameters (MS0, MS1, etc.) from a + b/c fractional value */
static int si5351_set_ms(uint8_t ms_reg_base, uint32_t a, uint32_t b, uint32_t c,
                          uint8_t rdiv)
{
    uint32_t p1 = 128 * a + (128 * b / c) - 512;
    uint32_t p2 = 128 * b - c * (128 * b / c);
    uint32_t p3 = c;

    uint8_t regs[8];
    regs[0] = (p3 >> 8) & 0xFF;
    regs[1] = p3 & 0xFF;
    regs[2] = ((p1 >> 16) & 0x03) | ((rdiv & 0x03) << 4);  /* includes R_DIV */
    regs[3] = (p1 >> 8) & 0xFF;
    regs[4] = p1 & 0xFF;
    regs[5] = ((p3 & 0x0F) << 4) | ((p2 >> 16) & 0x0F);
    regs[6] = (p2 >> 8) & 0xFF;
    regs[7] = p2 & 0xFF;

    return si5351_write_burst(ms_reg_base, regs, 8);
}

int si5351_init(void)
{
    /* Disable all outputs */
    si5351_write_reg(SI5351_REG_CLK0_CTRL, 0x80);
    si5351_write_reg(SI5351_REG_CLK1_CTRL, 0x80);
    si5351_write_reg(SI5351_REG_CLK2_CTRL, 0x80);

    /* Crystal load capacitance: 10 pF */
    si5351_write_reg(SI5351_REG_CRYSTAL_LOAD, (SI5351_XTAL_CL << 6) | 0x12);

    /* PLLA: VCO = 800 MHz (XTAL=25, a=32, integer mode) */
    si5351_set_pll(SI5351_REG_PLLA_PARAMS, 32, 0, 1);

    /* CLK0: initially 10 MHz (VCO/80 = 800/80 = 10 MHz, integer mode) */
    si5351_set_ms(SI5351_REG_MS0_PARAMS, 80, 0, 1, 0);
    si5351_write_reg(SI5351_REG_CLK0_CTRL, 0x4F); /* PLLA, integer mode, enable */

    /* CLK1: 16.776 MHz for AD5933 MCLK (VCO/47.64 ≈ 16.776) */
    si5351_set_ms(SI5351_REG_MS1_PARAMS, 47, 32, 50, 0);
    si5351_write_reg(SI5351_REG_CLK1_CTRL, 0x4F); /* PLLA, fractional mode */

    /* PLL reset */
    si5351_write_reg(SI5351_REG_PLL_RESET, 0xA0); /* reset PLLA */

    /* Enable CLK0 output */
    si5351_write_reg(SI5351_REG_CLK0_CTRL, 0x4F);

    return 0;
}

int si5351_set_frequency(uint32_t freq_hz)
{
    if (freq_hz < 1000 || freq_hz > 30000000) return -1;

    /* Choose VCO frequency and divider to achieve target frequency.
     * VCO range: 600–900 MHz. We use PLLA VCO = 800 MHz.
     * CLK0 = VCO / (a + b/c) where a >= 4 (Si5351 constraint).
     *
     * For f < 500 kHz, use R_DIV to further divide.
     * For f > 30 MHz, not supported (Si5351 max with PLLA). */

    uint32_t vco = 800000000UL;
    uint32_t rdiv = 0;
    uint32_t actual_freq = freq_hz;

    /* Apply R_DIV for very low frequencies */
    while (actual_freq < 500000 && rdiv < 7) {
        actual_freq *= 2;
        rdiv++;
    }

    /* MS divider: a + b/c = VCO / actual_freq */
    /* We need a >= 4 for the Si5351 */
    uint32_t a = vco / actual_freq;
    uint32_t rem = vco % actual_freq;

    if (a < 4) {
        /* Adjust VCO to make a >= 4 */
        /* Use PLLB with different multiplier */
        a = 4;
        rem = 0;  /* fall back to integer mode with a=4 */
    }

    /* b/c = rem / actual_freq (simplified fraction) */
    uint32_t b = rem;
    uint32_t c = actual_freq;

    /* Reduce fraction b/c */
    if (b == 0) {
        c = 1;
    }

    si5351_set_ms(SI5351_REG_MS0_PARAMS, a, b, c, rdiv);
    si5351_write_reg(SI5351_REG_PLL_RESET, 0xA0);

    sweep_current_freq = freq_hz;
    return 0;
}

int si5351_sweep_start(uint32_t f_start_hz, uint32_t f_stop_hz, uint16_t n_steps)
{
    sweep_f_start = f_start_hz;
    sweep_f_stop = f_stop_hz;
    sweep_n_steps = n_steps;
    sweep_step = 0;
    sweep_current_freq = f_start_hz;
    return si5351_set_frequency(f_start_hz);
}

uint32_t si5351_sweep_next(void)
{
    sweep_step++;
    if (sweep_step >= sweep_n_steps) return 0;

    uint32_t freq = sweep_f_start +
        (uint32_t)((uint64_t)(sweep_f_stop - sweep_f_start) * sweep_step / sweep_n_steps);

    si5351_set_frequency(freq);
    return freq;
}

void si5351_reset(void)
{
    si5351_write_reg(SI5351_REG_PLL_RESET, 0xA0);
}

void si5351_output_enable(bool enable)
{
    if (enable) {
        si5351_write_reg(SI5351_REG_CLK0_CTRL, 0x4F);
    } else {
        si5351_write_reg(SI5351_REG_CLK0_CTRL, 0x80);
    }
}

int si5351_set_mclk(uint32_t mclk_hz)
{
    /* Set CLK1 to mclk_hz using PLLA VCO */
    uint32_t vco = 800000000UL;
    uint32_t a = vco / mclk_hz;
    uint32_t rem = vco % mclk_hz;
    uint32_t b = rem;
    uint32_t c = (b == 0) ? 1 : mclk_hz;

    si5351_set_ms(SI5351_REG_MS1_PARAMS, a, b, c, 0);
    si5351_write_reg(SI5351_REG_PLL_RESET, 0xA0);
    return 0;
}

uint32_t si5351_get_actual_frequency(void)
{
    return sweep_current_freq;
}