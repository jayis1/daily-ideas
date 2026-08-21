/*
 * hall-puck / firmware / Core / Src / magnet.c
 * Magnetic field reversal mechanism (28BYJ-48 stepper + DRV5053)
 *
 * Rotates N52 neodymium magnet 180° for Hall field reversal.
 *
 * MIT License.
 */
#include "magnet.h"
#include "main.h"

/* 28BYJ-48 sequence: 8-step half-step sequence */
static const uint8_t step_sequence[8] = {
    0x01, 0x03, 0x02, 0x06, 0x04, 0x0C, 0x08, 0x09
};

static magnet_state_t magnet_state = MAGNET_OFF;
static int current_step = 0;
static float b_field_calibration = MAGNETIC_FIELD_T;

/* DRV5053 ADC reading → B-field conversion
 * DRV5053-A1: 1.8 mV/mT at 5V → 1.8 V/T
 * With 12-bit ADC at 3.3V: raw/4095 × 3.3 / 1.8 = B [T]
 * (Simplified — actual calibration stored in flash)
 */
#define DRV5053_SENSITIVITY  1.8f   /* V/T */

static void set_stepper_pins(uint8_t state)
{
    /* PC0-PC3: STEP_IN1 through IN4 */
    if (state & 0x01) GPIOC->BSRR = (1 << STEP_IN1_PIN);
    else GPIOC->BSRR = (1 << STEP_IN1_PIN) << 16;

    if (state & 0x02) GPIOC->BSRR = (1 << STEP_IN2_PIN);
    else GPIOC->BSRR = (1 << STEP_IN2_PIN) << 16;

    if (state & 0x04) GPIOC->BSRR = (1 << STEP_IN3_PIN);
    else GPIOC->BSRR = (1 << STEP_IN3_PIN) << 16;

    if (state & 0x08) GPIOC->BSRR = (1 << STEP_IN4_PIN);
    else GPIOC->BSRR = (1 << STEP_IN4_PIN) << 16;
}

static void step_motor(int direction)
{
    current_step = (current_step + direction + 8) % 8;
    set_stepper_pins(step_sequence[current_step]);
    delay_ms(2);  /* 2ms per step ≈ 500 steps/s ≈ 0.25 rev/s */
}

static void rotate_steps(int steps)
{
    int dir = (steps > 0) ? 1 : -1;
    int count = (steps > 0) ? steps : -steps;
    for (int i = 0; i < count; i++) {
        step_motor(dir);
    }
}

static float read_drv5053(void)
{
    /* Read ADC channel for MAGNET_POS_PIN (PC5 = ADC_IN14) */
    ADC1->SQR1 = 0;
    ADC1->SQR1 = (14 << 6);  /* channel 14 */
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC));
    uint16_t raw = ADC1->DR;

    float voltage = (raw / 4095.0f) * 3.3f;
    /* DRV5053 quiescent output ~2.5V, B=0 → voltage=2.5V
     * B = (voltage - 2.5) / sensitivity
     * Positive B = field in one direction, negative = reversed
     */
    float b_field = (voltage - 2.5f) / DRV5053_SENSITIVITY;
    return b_field;
}

void magnet_init(void)
{
    /* Configure PC0-PC3 as outputs */
    GPIOC->MODER &= ~(0xFFFF << (STEP_IN1_PIN * 2));
    GPIOC->MODER |= (0x55 << (STEP_IN1_PIN * 2));  /* 01 for each pin = output */

    /* Configure PC5 as analog input (ADC) */
    GPIOC->MODER &= ~(3 << (MAGNET_POS_PIN * 2));
    GPIOC->MODER |= (3 << (MAGNET_POS_PIN * 2));  /* 11 = analog */

    /* Enable ADC clock if not already */
    RCC->AHB2ENR |= RCC_AHB2ENR_ADCEN;

    /* Power off coils */
    set_stepper_pins(0);
    current_step = 0;
    magnet_state = MAGNET_OFF;
}

void magnet_set_b_plus(void)
{
    if (magnet_state == MAGNET_B_PLUS) return;

    if (magnet_state == MAGNET_B_MINUS) {
        /* Rotate 180° (1024 steps) */
        rotate_steps(HALF_REV_STEPS);
    } else if (magnet_state == MAGNET_PARKED) {
        /* Rotate from parked to B+ (assume 90° = 512 steps) */
        rotate_steps(HALF_REV_STEPS / 2);
    } else {
        /* From unknown: rotate to B+ by checking DRV5053 */
        /* Step until we get positive B reading */
        for (int i = 0; i < STEPS_PER_REV; i++) {
            float b = read_drv5053();
            if (b > 0.1f) break;
            rotate_steps(1);
        }
    }

    /* Verify with DRV5053 */
    float b = read_drv5053();
    if (b > 0.0f) {
        magnet_state = MAGNET_B_PLUS;
    }

    /* Power off stepper coils (hold position mechanically) */
    set_stepper_pins(0);
}

void magnet_set_b_minus(void)
{
    if (magnet_state == MAGNET_B_MINUS) return;

    if (magnet_state == MAGNET_B_PLUS) {
        rotate_steps(HALF_REV_STEPS);
    } else if (magnet_state == MAGNET_PARKED) {
        /* Rotate from parked to B- (270° = 1536 steps) */
        rotate_steps(HALF_REV_STEPS * 3 / 2);
    } else {
        for (int i = 0; i < STEPS_PER_REV; i++) {
            float b = read_drv5053();
            if (b < -0.1f) break;
            rotate_steps(1);
        }
    }

    float b = read_drv5053();
    if (b < 0.0f) {
        magnet_state = MAGNET_B_MINUS;
    }

    set_stepper_pins(0);
}

void magnet_park(void)
{
    if (magnet_state == MAGNET_B_PLUS) {
        rotate_steps(-HALF_REV_STEPS / 2);  /* 90° away */
    } else if (magnet_state == MAGNET_B_MINUS) {
        rotate_steps(HALF_REV_STEPS / 2);
    }

    magnet_state = MAGNET_PARKED;
    set_stepper_pins(0);
}

magnet_state_t magnet_get_state(void)
{
    return magnet_state;
}

float magnet_get_b_field(void)
{
    float b = read_drv5053();
    /* Return signed B-field, scaled by calibration factor */
    return b * (b_field_calibration / MAGNETIC_FIELD_T);
}

void magnet_set_calibration(float b_field_t)
{
    b_field_calibration = b_field_t;
}

float magnet_get_calibration(void)
{
    return b_field_calibration;
}

void magnet_step(int steps)
{
    rotate_steps(steps);
    set_stepper_pins(0);
}