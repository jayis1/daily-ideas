/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * pulser.c — High-voltage pulser control (HRTIM-driven)
 *
 * Drives the LMG1210 GaN driver + SCT2H12NZ (or IRF830) FET via HRTIM_CHA1
 * on PA8, synchronized with the ADC for jitter-free acquisition.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "pulser.h"

static pulser_config_t g_pulser;
static volatile uint8_t g_firing = 0;
static volatile uint32_t g_shot_count = 0;

/* ---- HRTIM registers — simplified direct access ----
 * HRTIM1 Master and Timer A (TA) drive the pulser output.
 */

void pulser_init(void)
{
    /* Enable HRTIM clock */
    RCC->APB2ENR |= RCC_APB2ENR_HRTIM1EN;

    /* Enable GPIOA clock (already on, but ensure) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;

    /* PA8 → HRTIM CHA1 output (alternate function) */
    GPIOA->MODER = (GPIOA->MODER & ~GPIO_MODER_MODE8) |
                   (2U << GPIO_MODER_MODE8_Pos);   /* AF */
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xF << 0)) |
                    (13U << 0);                     /* AF13 = HRTIM_CHA1 */

    /* Configure HRTIM Master + Timer A
     * We use a high-resolution PWM: period = PRF interval, compare = width_ns.
     */
    HRTIM1_COMMON->CR1 = 0;
    HRTIM1_COMMON->CR2 = 0;

    /* Master period (in HRTIM ticks). HRTIM tick = 184 ps.
     * For PRF=100 Hz → period = 1/100 = 10 ms = 10e6 ns
     * ticks = 10e6 / 0.184 = 54347821 (fits in 32-bit). */
    uint32_t period_ticks = (uint32_t)((1000000.0f / g_pulser.prf_hz) / 0.184f);

    HRTIM1_MASTER->MCMP1R = (uint32_t)(g_pulser.width_ns / 0.184f);  /* pulse width */
    HRTIM1_MASTER->MPER   = period_ticks;
    HRTIM1_MASTER->MREP    = 0;
    HRTIM1_MASTER->MCR    = HRTIM1_MASTER->MCR;   /* default */

    /* Timer A for the pulse output (CHA1) */
    HRTIM1_TIMA->CMP1xR = (uint32_t)(g_pulser.width_ns / 0.184f);
    HRTIM1_TIMA->PERxR  = period_ticks;
    HRTIM1_TIMA->TIMA_CR = 0;

    /* Defaults */
    g_pulser.mode            = PULSE_MODE_NEG_SPIKE;
    g_pulser.width_ns         = PULSE_WIDTH_NS_DEFAULT;
    g_pulser.hv_voltage_mv    = HV_VOLTAGE_DEFAULT_MV;
    g_pulser.prf_hz           = PRF_HZ_DEFAULT;
    g_pulser.burst_cycles     = 1;
    g_pulser.armed            = 0;

    /* DAC2 (PA1) setup for HV boost setpoint (LM5022 FB divider) */
    /* Enable DAC1 channel 2 */
    RCC->AHB2ENR |= RCC_AHB2ENR_DAC1EN;
    DAC1->CR |= DAC_CR_EN2;
    /* Initial HV setpoint = 0 (HV off) */
    DAC1->DHR12R2 = 0;
}

void pulser_configure(const pulser_config_t *cfg)
{
    /* Clamp values to safe ranges */
    g_pulser = *cfg;
    if (g_pulser.width_ns < PULSE_WIDTH_NS_MIN) g_pulser.width_ns = PULSE_WIDTH_NS_MIN;
    if (g_pulser.width_ns > PULSE_WIDTH_NS_MAX) g_pulser.width_ns = PULSE_WIDTH_NS_MAX;
    if (g_pulser.hv_voltage_mv < HV_VOLTAGE_MIN_MV) g_pulser.hv_voltage_mv = HV_VOLTAGE_MIN_MV;
    if (g_pulser.hv_voltage_mv > HV_VOLTAGE_MAX_MV) g_pulser.hv_voltage_mv = HV_VOLTAGE_MAX_MV;
    if (g_pulser.prf_hz < PRF_HZ_MIN) g_pulser.prf_hz = PRF_HZ_MIN;
    if (g_pulser.prf_hz > PRF_HZ_MAX) g_pulser.prf_hz = PRF_HZ_MAX;
    if (g_pulser.burst_cycles < 1) g_pulser.burst_cycles = 1;
    if (g_pulser.burst_cycles > 16) g_pulser.burst_cycles = 16;

    /* Update HRTIM compare/period (only if timer stopped) */
    uint32_t period_ticks = (uint32_t)((1000000.0f / g_pulser.prf_hz) / 0.184f);
    uint32_t width_ticks  = (uint32_t)(g_pulser.width_ns / 0.184f);

    HRTIM1_MASTER->MCMP1R = width_ticks;
    HRTIM1_MASTER->MPER   = period_ticks;
    HRTIM1_TIMA->CMP1xR   = width_ticks;
    HRTIM1_TIMA->PERxR    = period_ticks;

    /* Set HV boost voltage via DAC2 */
    pulser_set_hv(g_pulser.hv_voltage_mv);
}

void pulser_get_config(pulser_config_t *cfg)
{
    *cfg = g_pulser;
}

void pulser_arm(uint8_t armed)
{
    g_pulser.armed = armed ? 1 : 0;
    /* Pulser inhibit pin (PC13) — active low: 0 = allow fire, 1 = inhibit */
    if (armed) {
        GPIOC->BSRR = (1U << (16 + 13));   /* PC13 low (allow) */
        GPIOA->BSRR = (1U << 7);            /* PA7 high (LMG1210 enable) */
        power_enable_hv(1);
    } else {
        GPIOC->BSRR = (1U << 13);           /* PC13 high (inhibit) */
        GPIOA->BSRR = (1U << (16 + 7));     /* PA7 low (disable) */
        power_enable_hv(0);
    }
}

void pulser_fire_single(void)
{
    if (!g_pulser.armed) return;

    g_firing = 1;

    /* Check probe coupling (safety interlock) */
    if (!pulser_probe_coupled()) {
        g_firing = 0;
        return;
    }

    /* Single shot: enable HRTIM Timer A, generate one pulse, then stop.
     * We use the repetition counter to fire exactly one event.
     */
    HRTIM1_TIMA->TIMA_CR |= (1U << 0);   /* enable Timer A */
    HRTIM1_COMMON->CR1 |= (1U << 0);     /* start master */

    /* Wait for one period (blocking; bounded by PRF period) */
    uint32_t timeout = (SystemCoreClock / g_pulser.prf_hz) + 100;
    while (timeout--) { __NOP(); }

    /* Stop */
    HRTIM1_COMMON->CR1 &= ~(1U << 0);
    HRTIM1_TIMA->TIMA_CR &= ~(1U << 0);

    g_shot_count++;
    g_firing = 0;
}

void pulser_start_continuous(void)
{
    if (!g_pulser.armed) return;
    g_firing = 1;
    HRTIM1_TIMA->TIMA_CR |= (1U << 0);
    HRTIM1_COMMON->CR1 |= (1U << 0);     /* start master */
}

void pulser_stop_continuous(void)
{
    HRTIM1_COMMON->CR1 &= ~(1U << 0);
    HRTIM1_TIMA->TIMA_CR &= ~(1U << 0);
    g_firing = 0;
}

void pulser_set_hv(uint16_t voltage_mv)
{
    /* DAC2 output (PA1) → LM5022 FB divider.
     * Map 0..200000 mV → 0..3300 mV DAC (12-bit).
     * voltage_mv = (dac_mv / 3300) * 200000 → dac_mv = voltage * 3300 / 200000
     */
    if (voltage_mv > HV_VOLTAGE_MAX_MV) voltage_mv = HV_VOLTAGE_MAX_MV;
    uint32_t dac_mv = (uint32_t)voltage_mv * 3300U / HV_VOLTAGE_MAX_MV;
    uint16_t dac_code = (uint16_t)(dac_mv * ADC_MAX / 3300U);
    DAC1->DHR12R2 = dac_code;
}

uint16_t pulser_read_hv(void)
{
    /* Read ADC1 channel 6 (PC0, HV monitor via 1:100 divider).
     * Actual HV = adc_mv * 100. */
    /* (In a full implementation this would configure ADC1 IN6 and read.) */
    /* Simplified: return setpoint. */
    return g_pulser.hv_voltage_mv;
}

uint8_t pulser_probe_coupled(void)
{
    /* Coupling test: a small bias is applied to the probe tip and the
     * probe-present detect (PC2) is sampled. If a probe is connected and
     * the coupling capacitor is present, the line is pulled in a known
     * direction; if not coupled (open), it floats.
     * Simplified: read PC2 and return 1 if asserted. */
    return (GPIOC->IDR & (1U << 2)) ? 1 : 0;
}