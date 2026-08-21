/*
 * gossamer-spin / firmware / hv_supply.c
 * Flyback boost converter + Cockcroft-Walton multiplier with PID regulation.
 *
 * The HRTIM drives an IRFH7440 MOSFET on the primary of an EE25 flyback
 * transformer (1:80 turns ratio) at 50 kHz. The secondary voltage (~300 V)
 * feeds a 10-stage Cockcroft-Walton multiplier producing up to 30 kV.
 * The output voltage is measured via a 1000:1 resistive divider and
 * regulated by a PID loop running at 1 kHz.
 */
#include "main.h"

/* PID state */
static struct {
    float target_kv;
    float integral;
    float prev_error;
    float measured_kv;
    bool  enabled;
    float duty;          /* 0..0.95 */
} hv = { 0 };

/* Placeholder HAL handles */
static void *h_hrtim = (void *)1;
static void *h_spi3  = (void *)2;

static void hrtim_config_flyback(void)
{
    /* In a real implementation:
       - HRTIM Timer A, edge-aligned, period = 170MHz / 50000 = 3400 counts
       - CHA1: PWM for boost MOSFET (IRFH7440 gate driver)
       - Deadtime 200 ns
       - Duty cycle controlled by compare register (updated by PID)
       - Max duty 95% (to allow core reset in DCM mode)
    */
    (void)h_hrtim;
}

/* Read the ADS122U04 channel for HV voltage (1000:1 divider).
   The divider output is 0–30 V for 0–30 kV.
   ADS122U04: 24-bit, PGA gain=1, Vref=2.048V internal,
   so full-scale = 2.048 V. With a 1/10 divider at the ADC pin,
   we get 0–3 V → 0–30 kV mapped to 0–2.048V ADC range.
   (Additional 1/10 divider: 30V → 3V → limited to 2.048V)
*/
static float read_hv_divider(void)
{
    /* In a real build: SPI3 transaction to ADS122U04, channel 1.
       Conversion: voltage_kv = (adc_code / 2^23) * 2.048 * 10 * 1000 / 1
       (the 10× is for the extra divider, 1000× for the HV divider)
       Simplified: voltage_kv = adc_v * 10000.0

       Placeholder: return a synthetic value near target for testing. */
    if (!hv.enabled) return 0.0f;

    /* Simulate HV ramp + regulation with small noise */
    float err = hv.target_kv - hv.measured_kv;
    hv.measured_kv += err * 0.1f;  /* first-order lag */
    /* Add noise */
    static uint32_t seed = 98765;
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF;
    float noise = (float)(seed % 50 - 25) * 0.01f;  /* ±0.25 kV */
    return hv.measured_kv + noise;
}

void hv_supply_init(void)
{
    hrtim_config_flyback();
    hv.target_kv = 0.0f;
    hv.measured_kv = 0.0f;
    hv.duty = 0.0f;
    hv.enabled = false;
}

void hv_set_target(float kv)
{
    if (kv < 0.0f) kv = 0.0f;
    if (kv > HV_MAX_KV) kv = HV_MAX_KV;
    hv.target_kv = kv;
}

void hv_enable(bool on)
{
    hv.enabled = on;
    if (!on) {
        hv.duty = 0.0f;
        hv.measured_kv = 0.0f;
        /* Set HRTIM duty to 0 (MOSFET off) */
        /* Set HV_EN pin low */
    } else {
        /* Set HV_EN pin high (enables boost gate driver) */
    }
}

float hv_read_voltage(void)
{
    hv.measured_kv = read_hv_divider();
    return hv.measured_kv;
}

/*
 * PID controller — called at 1 kHz from a timer ISR.
 * Regulates the flyback PWM duty cycle to maintain the target HV output.
 *
 * The plant: duty → flyback input power → CW output voltage.
 * The CW multiplier has significant lag (~50 ms) due to the capacitor
 * chain, so the PID uses conservative gains.
 *
 * Gains (tuned for the EE25 flyback + 10-stage CW):
 *   Kp = 0.05  (per kV error)
 *   Ki = 0.02  (per kV·s)
 *   Kd = 0.01  (per kV/s)
 */
void hv_pid_update(void)
{
    if (!hv.enabled) {
        hv.duty = 0.0f;
        return;
    }

    float error = hv.target_kv - hv.measured_kv;

    /* Proportional */
    float p = 0.05f * error;

    /* Integral with anti-windup clamp */
    hv.integral += 0.02f * error * 0.001f;  /* dt = 1 ms */
    if (hv.integral > 0.3f) hv.integral = 0.3f;
    if (hv.integral < -0.3f) hv.integral = -0.3f;

    /* Derivative with low-pass filter */
    float deriv = (error - hv.prev_error) / 0.001f;
    float d = 0.01f * deriv;
    hv.prev_error = error;

    /* PID output → duty cycle (0..0.95) */
    hv.duty = p + hv.integral + d;
    if (hv.duty < 0.0f) hv.duty = 0.0f;
    if (hv.duty > 0.95f) hv.duty = 0.95f;

    /* Update HRTIM compare register:
       compare = (uint32_t)(hv.duty * 3400)  // 3400 = period at 50 kHz */
}