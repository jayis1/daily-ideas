/*
 * phantom.c — Acrylic phantom reference measurement
 *
 * The 25 mm acrylic phantom (PMMA, SOS = 2700 m/s) is used to:
 *   1. Calibrate the transducer + cable probe delay.
 *   2. Capture the reference FFT |H_ref(f)| for BUA.
 *
 * The reed switch on PB12 detects the phantom's embedded magnet.
 */

#include "phantom.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>

#define REF_FFT_SIZE 512
static float ref_fft[REF_FFT_SIZE];
static float probe_delay_us = 0.0f;   /* Transducer + cable delay */
static bool  ref_fft_valid = false;

void phantom_init(void)
{
    /* PB12: phantom reed switch (input, pull-up) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER &= ~(3u << (12u * 2u));   /* Input */
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (12u * 2u))) | (1u << (12u * 2u)); /* Pull-up */

    probe_delay_us = 0.0f;
    ref_fft_valid = false;
    memset(ref_fft, 0, sizeof(ref_fft));
}

bool phantom_present(void)
{
    /* Reed switch: closed (low) when magnet (phantom) present */
    return (GPIOB->IDR & (1u << 12u)) == 0;
}

void phantom_update_probe_delay(float d_mm, float measured_sos)
{
    /* Expected t_f for phantom: d_phantom / SOS_phantom (in µs)
     *   t_f_expected = d_mm / 2700.0 × 1000 (to get µs from mm/m/ms)
     *   = (d_mm / 2700.0) * 1000.0 µs
     * Measured t_f = d_mm / measured_sos * 1000 µs
     * Probe delay = measured_t_f − expected_t_f
     */
    float t_expected = (d_mm / PHANTOM_SOS_MPS) * 1000.0f;
    float t_measured = (d_mm / measured_sos) * 1000.0f;
    probe_delay_us = t_measured - t_expected;
    if (probe_delay_us < 0.0f) probe_delay_us = 0.0f;
}

float phantom_get_probe_delay(void) { return probe_delay_us; }

void phantom_capture_ref_fft(const uint16_t *buf, uint32_t n)
{
    /* Compute FFT of the phantom signal and store as reference.
     * Reuses the same FFT logic as bua.c (simplified here).
     */
    /* For the firmware stub, store a flat reference (real code would FFT). */
    for (int i = 0; i < REF_FFT_SIZE; ++i) {
        ref_fft[i] = 1.0f;   /* Placeholder: real code computes FFT magnitude */
    }
    ref_fft_valid = true;
    (void)buf; (void)n;
}

const float* phantom_get_ref_fft(void)
{
    return ref_fft_valid ? ref_fft : (const float*)0;
}