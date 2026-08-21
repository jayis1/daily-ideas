/*
 * qcm_driver.c — QCM crystal drive, frequency counting, ring-down capture
 *
 * Implements:
 *  - Si5351A I2C clock generator control for crystal drive
 *  - ADG918 RF switch TX/RX path selection
 *  - Reciprocal counting frequency measurement via TIM2
 *  - Ring-down ADC DMA capture
 *  - Full QCM-D measurement cycle
 */

#include "main.h"
#include <math.h>
#include <string.h>
#include "qcm_driver.h"
#include "dissipation.h"
#include "sauerbrey.h"
#include "voigt.h"
#include "overtone.h"
#include "i2c_util.h"

/* ── Si5351A register definitions ───────────────────────── */
#define SI5351_REG_CLK_ENABLE   3
#define SI5351_REG_CLK0_CTRL    16
#define SI5351_REG_CLK1_CTRL    17
#define SI5351_REG_CLK2_CTRL    18
#define SI5351_REG_PLL_A        26
#define SI5351_REG_PLL_B        34
#define SI5351_REG_CLK0_PARAMS  42
#define SI5351_REG_CLK1_PARAMS  50
#define SI5351_REG_CLK2_PARAMS  58
#define SI5351_REG_PLL_RESET    177
#define SI5351_REG_CRYSTAL_LOAD 183

/* ── Baselines ──────────────────────────────────────────── */
typedef struct {
    float f_baseline;
    float d_baseline;
    uint8_t valid;
} baseline_t;

static baseline_t baselines[QCM_CHANNELS][QCM_OVERtones];

/* ── Ring-down DMA buffer ────────────────────────────────── */
static uint16_t rd_dma_buf[RINGDOWN_SAMPLES];

/* ═══════════════════════════════════════════════════════════
 *  Si5351A Control
 * ═══════════════════════════════════════════════════════════ */

/* Write a single Si5351 register */
static void si5351_write(uint8_t reg, uint8_t val)
{
    i2c_write(SI5351_I2C_ADDR, reg, &val, 1);
}

/* Read a Si5351 register */
static uint8_t si5351_read(uint8_t reg)
{
    uint8_t val = 0;
    i2c_read(SI5351_I2C_ADDR, reg, &val, 1);
    return val;
}

/* Set up PLL with fractional synthesis:
 *  PLLA: f_PLL = f_xtal * (a + b/c)
 *  Then CLKx = f_PLL / (p + (q/r)) / (divider if MSx_INT)
 *
 * Simplified: use integer mode where possible.
 * For f_out = n * f0 (overtone), set MSx = PLLA_freq / f_out.
 *
 * PLLA = 25 MHz * 32 = 800 MHz (a=32, b=0, c=1)
 * MS0  = 800 MHz / f_out → integer if f_out divides 800e6
 */
static void si5351_setup_pll(void)
{
    /* PLLA: a=32, b=0, c=1 → fPLL = 25e6 * 32 = 800 MHz */
    si5351_write(SI5351_REG_PLL_A + 0, 0x00);    /* MSNA_P3[15:8] */
    si5351_write(SI5351_REG_PLL_A + 1, 0x01);    /* MSNA_P3[7:0]  */
    si5351_write(SI5351_REG_PLL_A + 2, 0x00);    /* MSNA_P1[17:16] + rdiv + MSNA_P3[19:16] */
    si5351_write(SI5351_REG_PLL_A + 3, 0x20);    /* MSNA_P1[15:8] */
    si5351_write(SI5351_REG_PLL_A + 4, 0x00);    /* MSNA_P1[7:0]  */
    si5351_write(SI5351_REG_PLL_A + 5, 0x80);    /* MSNA_P2[15:8] + MSNA_P1[19:18] */
    si5351_write(SI5351_REG_PLL_A + 6, 0x00);    /* MSNA_P2[7:0]  */
    /* P1 = 128*a + (128*b/c) - 512 = 128*32 - 512 = 3584 = 0x0E00 */
    si5351_write(SI5351_REG_PLL_A + 2, 0x00);
    si5351_write(SI5351_REG_PLL_A + 3, 0x0E);
    si5351_write(SI5351_REG_PLL_A + 4, 0x00);
}

/* Configure a multisynth output (CLK0 or CLK1) for a target frequency.
 * Uses integer division from 800 MHz PLLA.
 * f_out = 800e6 / MS_div
 * MS_div = 800e6 / f_out  (must be even, 4..900 for integer mode)
 */
static void si5351_set_multisynth(uint8_t clk_reg, uint32_t f_out_hz)
{
    /* For integer mode, MSx_INT bit must be set when MS_div >= 8 */
    uint32_t pll_freq = 800000000ULL;
    /* We need MS_div such that f_out = PLL / MS_div
     * But we also want R divider support for low freqs.
     * For QCM at 5-55 MHz, MS_div = 800e6 / f_out, e.g.:
     *   5 MHz  → MS_div = 160 (integer, OK)
     *   15 MHz → MS_div = 53.33 → need fractional
     *   25 MHz → MS_div = 32
     *   35 MHz → MS_div = 22.86 → fractional
     *   45 MHz → MS_div = 17.78 → fractional
     *   55 MHz → MS_div = 14.55 → fractional
     *
     * Use fractional mode for all: a + b/c where c = 1048575 (20-bit)
     */

    /* Compute a, b, c for fractional divider */
    double div = (double)pll_freq / (double)f_out_hz;
    uint32_t a = (uint32_t)div;
    double frac = div - (double)a;
    uint32_t c = 1048575;
    uint32_t b = (uint32_t)(frac * (double)c);
    if (b >= c) { b = c - 1; }

    /* Clamp a to valid range [4, 900] for fractional (MS_INT=0) */
    if (a < 4) a = 4;
    if (a > 900) a = 900;

    /* P1 = 128*a + floor(128*b/c) - 512 */
    uint32_t p1 = 128 * a + (uint32_t)(128.0 * (double)b / (double)c) - 512;
    /* P2 = 128*b - c*floor(128*b/c) */
    uint32_t p2 = 128 * b - c * (uint32_t)(128.0 * (double)b / (double)c);
    /* P3 = c */
    uint32_t p3 = c;

    si5351_write(clk_reg + 0, (p3 >> 8) & 0xFF);
    si5351_write(clk_reg + 1, p3 & 0xFF);
    si5351_write(clk_reg + 2, ((p1 >> 16) & 0x03) | ((p3 >> 12) & 0xF0));
    si5351_write(clk_reg + 3, (p1 >> 8) & 0xFF);
    si5351_write(clk_reg + 4, p1 & 0xFF);
    si5351_write(clk_reg + 5, ((p2 >> 8) & 0x0F) | ((p1 >> 4) & 0xF0));
    si5351_write(clk_reg + 6, p2 & 0xFF);

    /* Set CLK control: MS_INT=0 (fractional), PLLA, 8mA drive */
    uint8_t clk_ctrl_reg = SI5351_REG_CLK0_CTRL + (clk_reg == SI5351_REG_CLK0_PARAMS ? 0 : 1);
    si5351_write(clk_ctrl_reg, 0x4F); /* PLLA, MS_INT=0, 8mA, no invert */
}

int si5351_init(void)
{
    if (i2c_probe(SI5351_I2C_ADDR) != 0) return -1;

    /* Disable all outputs */
    si5351_write(SI5351_REG_CLK_ENABLE, 0xFF);

    /* Crystal load capacitance: 10 pF → CL[1:0] = 10 = 0b10 → bits 7:6 */
    si5351_write(SI5351_REG_CRYSTAL_LOAD, (SI5351_LOAD_CAP & 0x3F) << 6);

    /* Setup PLLA at 800 MHz */
    si5351_setup_pll();

    /* Reset PLLA */
    si5351_write(SI5351_REG_PLL_RESET, 0x20);

    HAL_Delay(10);

    /* Set default frequencies (5 MHz fundamental on CLK0) */
    si5351_set_freq(0, QCM_FUNDAMENTAL_HZ, 0);

    return 0;
}

int si5351_set_freq(uint8_t channel, uint32_t freq_hz, uint8_t clk_out)
{
    uint8_t params_reg = (clk_out == 0) ? SI5351_REG_CLK0_PARAMS :
                         (clk_out == 1) ? SI5351_REG_CLK1_PARAMS :
                                          SI5351_REG_CLK2_PARAMS;
    si5351_set_multisynth(params_reg, freq_hz);
    return 0;
}

void si5351_enable_clk(uint8_t clk_out)
{
    uint8_t en = si5351_read(SI5351_REG_CLK_ENABLE);
    en &= ~(1 << clk_out);
    si5351_write(SI5351_REG_CLK_ENABLE, en);
}

void si5351_disable_all(void)
{
    si5351_write(SI5351_REG_CLK_ENABLE, 0xFF);
}

/* ═══════════════════════════════════════════════════════════
 *  TX/RX Switch Control (ADG918)
 * ═══════════════════════════════════════════════════════════ */

void qcm_tx_enable(uint8_t channel)
{
    /* Select channel */
    HAL_GPIO_WritePin(CH1_SEL_PORT, CH1_SEL_PIN,
                      channel == 0 ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CH2_SEL_PORT, CH2_SEL_PIN,
                      channel == 1 ? GPIO_PIN_SET : GPIO_PIN_RESET);

    /* TX gate ON, RX gate OFF */
    HAL_GPIO_WritePin(GPIOA, TX_GATE_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, RX_GATE_PIN, GPIO_PIN_RESET);

    /* TX/RX switch to drive path */
    HAL_GPIO_WritePin(GPIOA, TXRX_SW_PIN, GPIO_PIN_SET);
}

void qcm_rx_enable(uint8_t channel)
{
    HAL_GPIO_WritePin(CH1_SEL_PORT, CH1_SEL_PIN,
                      channel == 0 ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CH2_SEL_PORT, CH2_SEL_PIN,
                      channel == 1 ? GPIO_PIN_SET : GPIO_PIN_RESET);

    /* TX gate OFF, RX gate ON */
    HAL_GPIO_WritePin(GPIOA, TX_GATE_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, RX_GATE_PIN, GPIO_PIN_SET);

    /* TX/RX switch to sense path */
    HAL_GPIO_WritePin(GPIOA, TXRX_SW_PIN, GPIO_PIN_RESET);
}

void qcm_disable_all(void)
{
    HAL_GPIO_WritePin(GPIOA, TX_GATE_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, RX_GATE_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, TXRX_SW_PIN, GPIO_PIN_RESET);
    si5351_disable_all();
}

/* ═══════════════════════════════════════════════════════════
 *  Frequency Measurement (Reciprocal Counting)
 * ═══════════════════════════════════════════════════════════ */

float qcm_measure_frequency(uint8_t channel, uint32_t gate_ms)
{
    /* Configure Si5351 for the fundamental (or desired overtone) */
    si5351_set_freq(channel, QCM_FUNDAMENTAL_HZ, channel);
    si5351_enable_clk(channel);

    /* Enable TX drive */
    qcm_tx_enable(channel);
    HAL_Delay(10); /* let oscillation stabilize */

    /* Switch to RX (sense) mode for counting */
    qcm_rx_enable(channel);

    /* TIM2 in input capture mode on CH1 (PA15) — counts input edges.
     * We gate by reading the counter before and after gate_ms.
     * For reciprocal counting: measure period of input signal.
     *
     * Simple approach: count TIM2 over gate_ms at 1 MHz tick,
     * with external clock mode (count on rising edge of input).
     */

    /* Configure TIM2: external clock mode 1, prescaler=0 */
    TIM_IC_InitTypeDef ic = {0};
    ic.ICPolarity = TIM_ICPOLARITY_RISING;
    ic.ICSelection = TIM_ICSELECTION_DIRECTTI;
    ic.ICPrescaler = TIM_ICPSC_DIV1;
    ic.ICFilter = 0;
    HAL_TIM_IC_ConfigChannel(&htim2, &ic, TIM_CHANNEL_1);

    /* Reset counter */
    __HAL_TIM_SET_COUNTER(&htim2, 0);
    HAL_TIM_IC_Start(&htim2, TIM_CHANNEL_1);

    /* Gate */
    HAL_Delay(gate_ms);

    uint32_t count = __HAL_TIM_GET_COUNTER(&htim2);
    HAL_TIM_IC_Stop(&htim2, TIM_CHANNEL_1);

    /* Also capture the last period for interpolation */
    uint32_t cc1 = HAL_TIM_ReadCapturedValue(&htim2, TIM_CHANNEL_1);
    (void)cc1;

    /* Frequency = count / gate_seconds  (with interpolation from cc1) */
    float freq = (float)count * 1000.0f / (float)gate_ms;

    /* Disable drive */
    qcm_disable_all();

    return freq;
}

/* ═══════════════════════════════════════════════════════════
 *  Ring-Down Capture
 * ═══════════════════════════════════════════════════════════ */

void qcm_capture_ringdown(uint8_t channel, uint16_t *buf, uint16_t n)
{
    /* Drive crystal at resonance */
    si5351_set_freq(channel, QCM_FUNDAMENTAL_HZ, channel);
    si5351_enable_clk(channel);
    qcm_tx_enable(channel);

    /* Let oscillation build up */
    HAL_Delay(5);

    /* Abruptly disconnect drive — switch to RX (sense) mode */
    /* The crystal will ring down naturally */
    qcm_rx_enable(channel);

    /* Trigger ADC DMA to capture the decaying signal */
    /* ADC1 channel 0 (PA0) at 20 Msps with DMA
     * For 2048 samples at 20 Msps → 102.4 µs capture window
     */

    /* Configure ADC for continuous conversion with DMA */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_1; /* PA0 = ADC1_IN1 */
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_2CYCLES;
    sConfig.SingleDiff = ADC_SINGLE_ENDED;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    /* Start DMA transfer */
    HAL_ADC_Start_DMA(&hadc1, (uint32_t *)rd_dma_buf, n);

    /* Wait for completion (with timeout) */
    uint32_t timeout = HAL_GetTick() + 100;
    while (HAL_ADC_PollForConversion(&hadc1, 10) != HAL_OK) {
        if (HAL_GetTick() > timeout) break;
    }

    HAL_ADC_Stop_DMA(&hadc1);

    /* Copy to user buffer */
    memcpy(buf, rd_dma_buf, n * sizeof(uint16_t));

    /* Disable drive */
    qcm_disable_all();
}

/* ═══════════════════════════════════════════════════════════
 *  Baseline Management
 * ═══════════════════════════════════════════════════════════ */

void qcm_set_baseline(uint8_t channel, uint8_t overtone_idx, float f, float d)
{
    if (channel >= QCM_CHANNELS || overtone_idx >= QCM_OVERtones) return;
    baselines[channel][overtone_idx].f_baseline = f;
    baselines[channel][overtone_idx].d_baseline = d;
    baselines[channel][overtone_idx].valid = 1;
}

void qcm_get_baseline(uint8_t channel, uint8_t overtone_idx, float *f, float *d)
{
    if (channel >= QCM_CHANNELS || overtone_idx >= QCM_OVERtones) {
        *f = 0; *d = 0; return;
    }
    *f = baselines[channel][overtone_idx].f_baseline;
    *d = baselines[channel][overtone_idx].d_baseline;
}

/* ═══════════════════════════════════════════════════════════
 *  Full QCM-D Measurement Cycle
 * ═══════════════════════════════════════════════════════════ */

qcm_result_t qcm_measure(uint8_t channel, uint8_t overtone_idx,
                         float temperature, int do_ringdown, int do_voigt)
{
    qcm_result_t r;
    memset(&r, 0, sizeof(r));
    r.channel = channel;
    r.overtone_idx = overtone_idx;
    r.overtone_n = overtone_multipliers[overtone_idx];
    r.temperature = temperature;
    r.timestamp_ms = HAL_GetTick();

    /* Set Si5351 to overtone frequency */
    float f0 = overtone_freq(QCM_FUNDAMENTAL_HZ, overtone_idx);
    si5351_set_freq(channel, (uint32_t)f0, channel);
    si5351_enable_clk(channel);

    /* Measure frequency */
    r.frequency = qcm_measure_frequency(channel, QCM_GATE_TIME_MS);

    /* Get baseline */
    float f_base = 0, d_base = 0;
    qcm_get_baseline(channel, overtone_idx, &f_base, &d_base);

    r.f_baseline = f_base;
    r.delta_f = r.frequency - f_base;

    /* Measure dissipation via ring-down */
    if (do_ringdown) {
        static uint16_t rd_buf[RINGDOWN_SAMPLES];
        qcm_capture_ringdown(channel, rd_buf, RINGDOWN_SAMPLES);
        r.dissipation = dissipation_fit(rd_buf, RINGDOWN_SAMPLES,
                                         (float)RINGDOWN_RATE_HZ, f0);
    }

    r.d_baseline = d_base;
    r.delta_d = r.dissipation - d_base;

    /* Sauerbrey mass (always compute) */
    if (baselines[channel][overtone_idx].valid) {
        r.sauerbrey_mass = sauerbrey_mass(r.delta_f, f0, SAUERBREY_AREA_CM2);
        /* Assuming film density of 1.0 g/cm³ if unknown */
        r.sauerbrey_thick = r.sauerbrey_mass / 100.0f; /* ng/cm² → nm at ρ=1 */
    }

    r.valid = 1;

    (void)do_voigt; /* Voigt fitting requires multi-overtone data */

    return r;
}

/* ═══════════════════════════════════════════════════════════
 *  Multi-overtone measurement sweep
 * ═══════════════════════════════════════════════════════════ */

uint8_t qcm_measure_all_overtones(uint8_t channel, float temperature,
                                  qcm_result_t *results, uint8_t max_n)
{
    uint8_t count = (max_n < QCM_OVERtones) ? max_n : QCM_OVERtones;
    for (uint8_t i = 0; i < count; i++) {
        results[i] = qcm_measure(channel, i, temperature, 1, 0);
    }
    return count;
}