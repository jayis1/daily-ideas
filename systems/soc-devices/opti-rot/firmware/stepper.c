/*
 * stepper.c — 28BYJ-48 stepper motor driver via ULN2003
 * Opti Rot — Pocket Digital Polarimeter
 *
 * The 28BYJ-48 is a 5V unipolar stepper with a 64:1 gearbox, giving
 * 4096 half-steps per revolution (0.08789°/step). Four GPIO pins drive
 * the ULN2003 Darlington array which energizes coils A, B, C, D.
 *
 * Half-step sequence (8 states):
 *   Step  A   B   C   D
 *    0    1   0   0   0
 *    1    1   1   0   0
 *    2    0   1   0   0
 *    3    0   1   1   0
 *    4    0   0   1   0
 *    5    0   0   1   1
 *    6    0   0   0   1
 *    7    1   0   0   1
 *
 * The analyzer polarizer is coupled to the motor shaft through a 1:1
 * coupling. We track absolute position in steps from power-on home (0°).
 */
#include "stm32g4xx_hal.h"
#include "sdkconfig.h"
#include "stepper.h"

/* GPIO pin mapping (PA5..PA8 → ULN2003 IN1..IN4) */
#define STEPPER_PORT       GPIOA
#define COIL_A_PIN         GPIO_PIN_5
#define COIL_B_PIN         GPIO_PIN_6
#define COIL_C_PIN         GPIO_PIN_7
#define COIL_D_PIN         GPIO_PIN_8

/* Half-step excitation table */
static const uint8_t half_step_seq[STEPPER_SEQ_LEN][4] = {
    {1, 0, 0, 0},
    {1, 1, 0, 0},
    {0, 1, 0, 0},
    {0, 1, 1, 0},
    {0, 0, 1, 0},
    {0, 0, 1, 1},
    {0, 0, 0, 1},
    {1, 0, 0, 1},
};

static int32_t current_step = 0;        /* absolute step position */
static uint8_t  seq_index   = 0;        /* current position in sequence */
static bool     energized   = false;

/* ---- Low-level coil write ---- */

static void write_coils(uint8_t a, uint8_t b, uint8_t c, uint8_t d)
{
    HAL_GPIO_WritePin(STEPPER_PORT, COIL_A_PIN, a ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_PORT, COIL_B_PIN, b ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_PORT, COIL_C_PIN, c ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_PORT, COIL_D_PIN, d ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void apply_seq_state(uint8_t idx)
{
    write_coils(
        half_step_seq[idx][0],
        half_step_seq[idx][1],
        half_step_seq[idx][2],
        half_step_seq[idx][3]
    );
}

/* ---- Public API ---- */

void stepper_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    GPIO_InitStruct.Pin   = COIL_A_PIN | COIL_B_PIN | COIL_C_PIN | COIL_D_PIN;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(STEPPER_PORT, &GPIO_InitStruct);

    /* Start de-energized (save power) */
    write_coils(0, 0, 0, 0);
    energized = false;
    current_step = 0;
    seq_index = 0;
}

void stepper_step(int16_t steps)
{
    int32_t target = current_step + (int32_t)steps;

    /* Energize if not already */
    if (!energized) {
        energized = true;
        apply_seq_state(seq_index);
        HAL_DelayUs(1000);
    }

    int16_t dir = (steps > 0) ? 1 : -1;
    int16_t remaining = (steps >= 0) ? steps : -steps;

    for (int16_t i = 0; i < remaining; i++) {
        seq_index = (uint8_t)((seq_index + dir + STEPPER_SEQ_LEN) % STEPPER_SEQ_LEN);
        apply_seq_state(seq_index);
        current_step += dir;
        HAL_DelayUs(STEPPER_STEP_DELAY_US);
    }
}

void stepper_move_to(double angle_deg)
{
    /* Convert absolute angle to steps from current position */
    double target_step_d = angle_deg / STEPPER_STEP_ANGLE;
    int32_t target_step = (int32_t)lround(target_step_d);
    int16_t delta = (int16_t)(target_step - current_step);
    stepper_step(delta);
}

void stepper_deenergize(void)
{
    write_coils(0, 0, 0, 0);
    energized = false;
}

double stepper_get_angle(void)
{
    return (double)current_step * STEPPER_STEP_ANGLE;
}

bool stepper_is_moving(void)
{
    return energized;
}

void stepper_home(void)
{
    /*
     * Mechanical homing: rotate until the photodiode reading peaks
     * (analyzer aligned with polarizer → maximum transmission).
     * The caller (polarimeter) handles the optical search; here we
     * just reset the position counter at the current location.
     */
    current_step = 0;
    seq_index = 0;
}