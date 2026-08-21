/*
 * heater.c — Dual PID heater control for Thermo Trace DSC
 *
 * Two independent PID loops control the sample and reference heater cells.
 * Each heater is a Kapton thin-film 50Ω resistor driven by a MOSFET via
 * TIM1 PWM channels 1 (PA8) and 2 (PA9).
 *
 * The PID loop maintains the cell temperature at the programmed setpoint
 * (from ramp.c temperature profile). The heater power (used for heat-flow
 * computation) is:
 *
 *   P = (V_supply² / R_heater) × duty
 *
 * In power-compensation DSC:
 *   Φ = P_sample - P_reference
 */

#include "stm32g491_conf.h"
#include "heater.h"

static float duty_sample = 0.0f;
static float duty_ref    = 0.0f;
static float v_supply_val = 5.0f;

void heater_init(void) {
    /* TIM1: 10 kHz PWM on CH1 (PA8) and CH2 (PA9) */

    /* Enable TIM1 clock */
    RCC_APB2ENR |= (1U << 11);  /* TIM1EN */

    /* Configure PA8, PA9 as AF2 (TIM1 CH1/CH2) */
    GPIO_MODER(GPIOA_BASE) &= ~((3U << (8*2)) | (3U << (9*2)));
    GPIO_MODER(GPIOA_BASE) |=  (2U << (8*2)) | (2U << (9*2));
    GPIO_AFRL(GPIOA_BASE) = (GPIO_AFRL(GPIOA_BASE) & ~((0xF << (8*4)) | (0xF << (9*4))))
                           | (2U << (8*4)) | (2U << (9*4));

    /* PB9 = heater enable (active LOW = cutoff). Default HIGH = enabled */
    GPIO_MODER(GPIOB_BASE) |= (1U << (9*2));
    GPIO_SET(HEATER_EN_PORT, HEATER_EN_PIN);

    /* TIM1: PWM mode 1 on both channels */
    TIM1_PSC = 0;             /* no prescaler, 170 MHz timer */
    TIM1_ARR = PWM_PERIOD - 1; /* auto-reload = period */
    TIM1_CCMR1 = (6U << 4)     /* OC1M = PWM mode 1 */
               | (1U << 3)     /* OC1PE: preload enable */
               | (6U << 12)    /* OC2M = PWM mode 1 */
               | (1U << 11);   /* OC2PE: preload enable */
    TIM1_CCER = (1U << 0)      /* CC1E: CH1 output enable */
              | (1U << 4);     /* CC2E: CH2 output enable */
    TIM1_BDTR = (1U << 15);    /* MOE: main output enable */
    TIM1_CCR1 = 0;             /* 0% duty initially */
    TIM1_CCR2 = 0;
    TIM1_CR1 = (1U << 7)       /* ARPE: auto-reload preload */
             | (1U << 0);     /* CEN: enable timer */
}

void heater_set_pwm(uint8_t channel, float duty) {
    /* Clamp duty to safe range */
    if (duty < 0.0f) duty = 0.0f;
    if (duty > HEATER_MAX_DUTY) duty = HEATER_MAX_DUTY;

    uint32_t ccr = (uint32_t)(duty * (float)PWM_PERIOD);

    if (channel == 0) {
        TIM1_CCR1 = ccr;
        duty_sample = duty;
    } else {
        TIM1_CCR2 = ccr;
        duty_ref = duty;
    }
}

void heater_enable(bool on) {
    if (on) {
        GPIO_SET(HEATER_EN_PORT, HEATER_EN_PIN);
    } else {
        GPIO_CLR(HEATER_EN_PORT, HEATER_EN_PIN);
        /* Also set PWM to 0 immediately */
        TIM1_CCR1 = 0;
        TIM1_CCR2 = 0;
        duty_sample = 0.0f;
        duty_ref = 0.0f;
    }
}

void heater_off(void) {
    heater_enable(false);
}

float heater_compute_power(float v_supply, float duty, float r_heater) {
    if (r_heater <= 0.0f) return 0.0f;
    return (v_supply * v_supply / r_heater) * duty;
}

float heater_get_power(uint8_t channel) {
    float duty = (channel == 0) ? duty_sample : duty_ref;
    return heater_compute_power(v_supply_val, duty, HEATER_R_OHM);
}

void pid_init(pid_t *pid, float kp, float ki, float kd,
              float max_out, float max_int) {
    pid->setpoint    = 0.0f;
    pid->kP          = kp;
    pid->kI          = ki;
    pid->kD          = kd;
    pid->integral    = 0.0f;
    pid->prev_error  = 0.0f;
    pid->output      = 0.0f;
    pid->max_output  = max_out;
    pid->max_integral = max_int;
}

void pid_reset(pid_t *pid) {
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->output = 0.0f;
}

float pid_update(pid_t *pid, float measured, float setpoint, float dt) {
    float error = setpoint - measured;

    /* Proportional */
    float p_term = pid->kP * error;

    /* Integral with anti-windup */
    pid->integral += error * dt;
    if (pid->integral > pid->max_integral) pid->integral = pid->max_integral;
    if (pid->integral < -pid->max_integral) pid->integral = -pid->max_integral;
    float i_term = pid->kI * pid->integral;

    /* Derivative (on measurement to avoid derivative kick) */
    float d_term = pid->kD * (error - pid->prev_error) / dt;
    pid->prev_error = error;

    /* Sum and clamp */
    float output = p_term + i_term + d_term;
    if (output > pid->max_output) output = pid->max_output;
    if (output < 0.0f) output = 0.0f;

    pid->output = output;
    return output;
}