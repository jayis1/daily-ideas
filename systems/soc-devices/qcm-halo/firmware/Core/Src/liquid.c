/*
 * liquid.c — Peristaltic pump + rotary valve control
 */

#include "main.h"
#include "liquid.h"

extern TIM_HandleTypeDef htim2;

static float current_pump_rate = 0;
static uint8_t current_valve_pos = 0;

/* ── Pump ───────────────────────────────────────────────── */
void pump_init(void)
{
    /* TIM2 CH3 (PB10) for pump PWM */
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_3);
    pump_stop();
}

void pump_set_rate(float ml_per_min)
{
    if (ml_per_min <= 0) {
        pump_stop();
        return;
    }
    if (ml_per_min > PUMP_MAX_RATE) ml_per_min = PUMP_MAX_RATE;

    /* Map flow rate to PWM duty cycle.
     * Mini peristaltic pump: 0-5 mL/min at 0-100% PWM
     */
    float duty = (ml_per_min / PUMP_MAX_RATE) * 100.0f;

    /* TIM2 runs at 1 MHz, prescaler set for PWM at 1 kHz */
    uint32_t arr = 1000; /* 1 MHz / 1000 = 1 kHz */
    uint32_t ccr = (uint32_t)(duty * arr / 100.0f);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_3, ccr);

    current_pump_rate = ml_per_min;
}

void pump_stop(void)
{
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_3, 0);
    current_pump_rate = 0;
}

float pump_get_rate(void)
{
    return current_pump_rate;
}

/* ── Rotary Valve (28BYJ-48 via ULN2003) ────────────────── */
/* 28BYJ-48: 4096 steps per revolution (half-step, 64:1 gear ratio)
 * 6-way valve: 4096/6 ≈ 683 steps per position
 */
#define VALVE_STEPS_PER_POS  683

static void valve_step(uint8_t phase)
{
    /* ULN2003: 4 coils, half-step sequence */
    static const uint8_t half_step[8] = {
        0x01, 0x03, 0x02, 0x06, 0x04, 0x0C, 0x08, 0x09
    };
    uint8_t pat = half_step[phase & 0x07];

    HAL_GPIO_WritePin(VALVE_A_PORT, VALVE_A_PIN, (pat & 0x01) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(VALVE_B_PORT, VALVE_B_PIN, (pat & 0x02) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    /* VALVE_C and VALVE_D use the same port pins — simplified for 3-wire */
    /* In full design, 4 GPIOs drive ULN2003 inputs IN1-IN4 */
}

void valve_init(void)
{
    valve_home();
}

void valve_home(void)
{
    /* Rotate to position 0 (home). In practice, use a Hall sensor or
     * optical flag for homing. Here we assume starting from known position.
     */
    current_valve_pos = 0;
}

void valve_set_position(uint8_t pos)
{
    if (pos > 5) pos = 5;

    int8_t delta = (int8_t)pos - (int8_t)current_valve_pos;
    if (delta == 0) return;

    int total_steps = delta * VALVE_STEPS_PER_POS;
    int direction = (total_steps > 0) ? 1 : -1;
    int abs_steps = (total_steps >= 0) ? total_steps : -total_steps;

    uint8_t phase = 0;
    for (int i = 0; i < abs_steps; i++) {
        if (direction > 0) {
            phase = (phase + 1) & 0x07;
        } else {
            phase = (phase - 1) & 0x07;
        }
        valve_step(phase);
        HAL_Delay(2); /* ~500 steps/sec */
    }

    /* De-energize coils */
    HAL_GPIO_WritePin(VALVE_A_PORT, VALVE_A_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(VALVE_B_PORT, VALVE_B_PIN, GPIO_PIN_RESET);

    current_valve_pos = pos;
}

uint8_t valve_get_position(void)
{
    return current_valve_pos;
}

const char *valve_position_name(uint8_t pos)
{
    static const char *names[] = {
        "Buffer", "Sample", "Wash", "Rinse", "Waste", "Air"
    };
    if (pos > 5) return "?";
    return names[pos];
}