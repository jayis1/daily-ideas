/*
 * heel_caliper.c — Caliper pot → heel width d (mm)
 *
 * A 10 kΩ linear potentiometer (RV1) on the spring-loaded caliper
 * outputs 0–3.3 V, read by ADC2_IN13 (PA5). The caliper range is
 * 0–80 mm. Two-point calibration (zero at closed, full at 80 mm
 * open) gives a linear mapping d(mm) = (V - V0) / (V80 - V0) × 80.
 */

#include "heel_caliper.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static float v_zero = 0.0f;   /* Caliper closed voltage */
static float v_full = 3.3f;  /* Caliper at 80 mm voltage */
static bool  calibrated = false;

void heel_caliper_init(void)
{
    /* PA5: ADC2_IN13 (analog input) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (5u * 2u))) | (0u << (5u * 2u));
    GPIOA->PUPDR &= ~(3u << (5u * 2u));
    calibrated = false;
}

static float read_pa5_voltage(void)
{
    /* Simplified: real code configures ADC2_IN13 and reads.
     * Return a placeholder 1.65 V (mid-range = 40 mm).
     */
    return 1.65f;
}

float heel_caliper_read_mm(void)
{
    float v = read_pa5_voltage();
    if (calibrated && v_full > v_zero) {
        float d = (v - v_zero) / (v_full - v_zero) * SOS_CALIPER_MAX_MM;
        if (d < 0.0f) d = 0.0f;
        if (d > SOS_CALIPER_MAX_MM) d = SOS_CALIPER_MAX_MM;
        return d;
    }
    /* Uncalibrated: linear assume 0–3.3 V → 0–80 mm */
    return (v / 3.3f) * SOS_CALIPER_MAX_MM;
}

void heel_caliper_calibrate_zero(void)
{
    v_zero = read_pa5_voltage();
}

void heel_caliper_calibrate_full(void)
{
    v_full = read_pa5_voltage();
    calibrated = true;
}