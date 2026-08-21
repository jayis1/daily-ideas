/*
 * sonar-cast / firmware / hrtim_drv.c
 * HRTIM + HV H-bridge drive, T/R switch timing, TGC ramp via DAC.
 *
 * The HRTIM (high-resolution timer, 184 ps) drives the H-bridge MOSFETs
 * with a bipolar ±100 V square wave whose frequency is swept through the
 * chirp LUT via DMA into the period register.
 */
#include "main.h"

/* Placeholder HAL handles — in a real build these map to STM32 HAL structs. */
static void *h_hrtim1 = (void *)1;
static void *h_dac1   = (void *)2;

extern const uint16_t *chirp_get_freq_lut(void);

/* ---- HRTIM config for center-aligned PWM on CHA + CHB (H-bridge) ---- */
static void hrtim_config_pwm(void)
{
    /* In a real implementation:
       - HRTIM Timer A → CHA1/CHA2 (H-bridge leg A, complementary + deadtime)
       - HRTIM Timer B → CHB1/CHB2 (H-bridge leg B, complementary + deadtime)
       - Center-aligned PWM, period loaded from chirp_freq_lut[] via DMA
       - Deadtime ~50 ns (IRFH7440 gate charge)
       - Burst mode: enabled only for CHIRP_DURATION_US, then T/R switch flips to RX
    */
    (void)h_hrtim1;
}

/* ---- DAC1 ramp for TGC ---- */
static void dac_tgc_init(void)
{
    /* DAC1 channel 1 on PA0, 12-bit, triggered by HRTIM at ping start.
       DMA loads an exponential 0→1.6 V ramp (0→48 dB gain) over the
       echo window (16 ms) — compensates 1/R² spreading. */
    (void)h_dac1;
}

void hrtim_drv_init(void)
{
    hrtim_config_pwm();
    dac_tgc_init();
}

/*
 * Fire one CHIRP ping:
 *   1. Set T/R switch to TX (PA8 high)
 *   2. Enable H-bridge, DMA-load chirp freq LUT into HRTIM period
 *   3. After CHIRP_DURATION_US, disable H-bridge
 *   4. Set T/R switch to RX (PA8 low)
 *   5. Start DAC TGC ramp + ADC capture (triggered by HRTIM)
 */
void chirp_fire(void)
{
    /* 1. TX mode */
    /* gpio_set(PA8, 1) */

    /* 2. Start H-bridge with chirp DMA */
    /* HAL_HRTIM_PWM_Start_DMA(CHA, chirp_get_freq_lut(), CHIRP_SAMPLES) */

    /* 3. Wait for chirp to complete (0.5 ms — done by HRTIM burst count) */
    /* delay_us(CHIRP_DURATION_US); — actually HRTIM IRQ */

    /* 4. RX mode */
    /* gpio_set(PA8, 0) */

    /* 5. Start TGC ramp + ADC (ADC capture called by caller) */
    /* HAL_DAC_Start_DMA(DAC1_CH1, tgc_ramp_lut, ECHO_WINDOW_SAMPLES) */
}

/* ---- HV rail safety monitor ---- */
bool hrtim_hv_safe(void)
{
    /* Read PA1 (ADC1_IN1) = HV rail ÷ 11.
       If > 3.0 V (33 V on 12 V rail — fault) abort ping. */
    return true;  /* placeholder */
}