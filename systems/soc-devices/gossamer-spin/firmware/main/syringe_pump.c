/*
 * gossamer-spin / firmware / syringe_pump.c
 * NEMA8 stepper + A4988 driver + M4×0.35 leadscrew syringe pump.
 *
 * Flow rate is controlled by the TIM1 step pulse frequency.
 * The A4988 driver is set to 1/16 microstepping.
 *
 * Flow rate (mL/h) = (π × r² × pitch × step_rate) /
 *                    (steps_per_rev × microsteps × 3600)
 *
 * For a 5 mL syringe (r = 6 mm, pitch = 0.35 mm):
 *   flow = π × 36 × 0.35 × step_rate / (200 × 16 × 3600)
 *   flow = 39.584 × step_rate / 11520000
 *   flow = step_rate × 3.436e-6 mL/s
 *   flow_mlh = step_rate × 3.436e-6 × 3600 = step_rate × 0.01237
 *
 * So for 1.0 mL/h: step_rate = 1.0 / 0.01237 ≈ 80.8 steps/s
 *     for 0.1 mL/h: step_rate ≈ 8.1 steps/s
 *     for 10 mL/h:  step_rate ≈ 808 steps/s
 */
#include "main.h"

static struct {
    float target_mlh;
    float syringe_r_mm;
    bool  running;
} pump = { 0 };

static void *h_tim1 = (void *)1;

/* Compute step rate (steps/s) for a given flow rate (mL/h) */
static float flow_to_step_rate(float mlh)
{
    /* flow_mlh = step_rate × π × r² × pitch / (steps × microsteps × 3600) */
    /* step_rate = flow_mlh × steps × microsteps × 3600 / (π × r² × pitch) */
    float r = pump.syringe_r_mm;
    float area = M_PI * r * r;           /* mm² */
    float num = mlh * SYRINGE_STEPS_PER_REV * SYRINGE_MICROSTEPS * 3600.0f;
    float den = area * SYRINGE_LEAD_MM;
    return num / den;                     /* steps/s */
}

void syringe_pump_init(void)
{
    pump.target_mlh = 0.0f;
    pump.syringe_r_mm = SYRINGE_DEFAULT_R_MM;
    pump.running = false;

    /* Configure TIM1 for step pulse generation:
       - Output compare, toggle mode on CH1 (step)
       - CH2 as GPIO direction output
       - Start with frequency = 0 (disabled) */
    (void)h_tim1;
}

void syringe_set_flow(float mlh)
{
    if (mlh < 0.0f) mlh = 0.0f;
    if (mlh > SYRINGE_MAX_MLH) mlh = SYRINGE_MAX_MLH;
    pump.target_mlh = mlh;

    if (pump.running) {
        float step_rate = flow_to_step_rate(mlh);
        /* Update TIM1 auto-reload register for new frequency:
           ARR = SYS_CLK_HZ / (2 * step_rate) - 1  (toggle mode) */
        (void)step_rate;
    }
}

void syringe_start(void)
{
    pump.running = true;
    float step_rate = flow_to_step_rate(pump.target_mlh);
    /* Set DIR pin high (forward)
       Set TIM1 ARR for step_rate
       Enable TIM1 */
    (void)step_rate;
}

void syringe_stop(void)
{
    pump.running = false;
    /* Disable TIM1 */
}

bool syringe_empty(void)
{
    /* Read SYR_LIMIT GPIO (PA14). Returns true if carriage is at the
       forward limit (syringe plunger fully depressed = empty).
       In a real build: return gpio_read(PA14) == 0; */
    return false;
}