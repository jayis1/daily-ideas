/*
 * dent-scope / Core/Src/stepper.c
 * Dent Scope — 28BYJ-48 geared stepper + DRV8833 driver
 *
 * The 28BYJ-48 is a 5V unipolar stepper with 1/64 internal gearbox:
 *   64 steps/rev × 64 gear ratio = 4096 steps/rev
 * With 8-step (half-step) drive sequence → 4096 half-steps/rev.
 * M4×0.35 leadscrew: 0.35 mm pitch → 4096 half-steps = 0.35 mm
 *   → 1 half-step ≈ 0.0854 µm per half-step
 * We use 8-step half-step sequence via DRV8833.
 *
 * "step_down" = push indenter toward sample (increase depth/force)
 * "step_up"   = retract indenter away from sample (decrease depth/force)
 *
 * MIT License.
 */
#include "stepper.h"

/* 28BYJ-48 8-step half-step sequence (DRV8833 dual H-bridge: IN1-IN4) */
static const uint8_t step_seq[8][4] = {
    {1, 0, 0, 0},
    {1, 0, 1, 0},
    {0, 0, 1, 0},
    {0, 1, 1, 0},
    {0, 1, 0, 0},
    {0, 1, 0, 1},
    {0, 0, 0, 1},
    {1, 0, 0, 1},
};

static int   step_idx     = 0;
static int   approach_dir = 1;   /* 1 = toward sample (down) */
static bool  stepping     = false;
static bool  retracting   = false;
static int   retract_remaining = 0;
static uint32_t last_step_us = 0;
static uint32_t step_period_us = 2000; /* 2 ms = 500 steps/s = ~43 µm/s */

static void set_outputs(const uint8_t *s)
{
    HAL_GPIO_WritePin(STEP_IN1_PORT, STEP_IN1_PIN, s[0] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEP_IN2_PORT, STEP_IN2_PIN, s[1] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEP_IN3_PORT, STEP_IN3_PIN, s[2] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEP_IN4_PORT, STEP_IN4_PIN, s[3] ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void step_one(int dir)
{
    step_idx = (step_idx + dir + 8) % 8;
    set_outputs(step_seq[step_idx]);
}

void stepper_init(void)
{
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_SET); /* disabled (active low) */
    set_outputs(step_seq[0]);
}

void stepper_approach(void)
{
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_RESET); /* enable */
    stepping = true;
    approach_dir = 1; /* down (toward sample) */
    step_period_us = 1500; /* approach speed: ~57 µm/s */
    last_step_us = 0;
}

void stepper_tick_approach(void)
{
    uint32_t now = DWT->CYCCNT / (SystemCoreClock / 1000000); /* µs */
    if (now - last_step_us >= step_period_us) {
        last_step_us = now;
        step_one(approach_dir);
    }
}

void stepper_step_down(void)
{
    /* one step toward sample (increase force) */
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_RESET);
    step_one(1);
}

void stepper_step_up(void)
{
    /* one step away from sample (decrease force) */
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_RESET);
    step_one(-1);
}

void stepper_stop(void)
{
    stepping = false;
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_SET); /* disable */
}

void stepper_hold_position(void)
{
    /* keep stepper energized to hold position, but don't step */
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_RESET); /* enabled, coils energized */
}

void stepper_retract(void)
{
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_RESET);
    retracting = true;
    retract_remaining = 3000; /* ~256 µm fast retract */
    step_period_us = 800;       /* fast retract: ~107 µm/s */
    last_step_us = 0;
}

void stepper_tick_retract(void)
{
    if (retract_remaining <= 0) {
        retracting = false;
        HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_SET);
        return;
    }
    uint32_t now = DWT->CYCCNT / (SystemCoreClock / 1000000);
    if (now - last_step_us >= step_period_us) {
        last_step_us = now;
        step_one(-1); /* retract */
        retract_remaining--;
    }
}

bool stepper_is_retracted(void)
{
    return !retracting;
}

void stepper_emergency_stop(void)
{
    stepping = false;
    retracting = false;
    HAL_GPIO_WritePin(STEP_EN_PORT, STEP_EN_PIN, GPIO_PIN_SET);
    /* de-energize all coils */
    HAL_GPIO_WritePin(STEP_IN1_PORT, STEP_IN1_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEP_IN2_PORT, STEP_IN2_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEP_IN3_PORT, STEP_IN3_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEP_IN4_PORT, STEP_IN4_PIN, GPIO_PIN_RESET);
}