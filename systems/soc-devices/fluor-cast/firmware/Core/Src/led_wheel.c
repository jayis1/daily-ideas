/*
 * led_wheel.c — Excitation LED wheel control
 *
 * 8 LEDs (255–525 nm) on a rotating wheel, selected by 28BYJ-48 stepper.
 * LED current is controlled via MCP4131 digital pot + OPA548 op-amp.
 * LED selection via 74HC138 3-to-8 decoder.
 * Reference photodiode (OPT101) monitors actual LED output.
 */

#include "led_wheel.h"
#include "main.h"
#include <math.h>

extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim2;

/* ── Private variables ────────────────────────────────── */
static ex_wavelength_t current_pos = EX_BLANK;
static uint8_t wheel_homed = 0;
static float current_led_ma = 50.0f;

/* 28BYJ-48 half-step sequence (8 steps) */
static const uint8_t half_steps[8][4] = {
    {1, 0, 0, 0},
    {1, 0, 1, 0},
    {0, 0, 1, 0},
    {0, 1, 1, 0},
    {0, 1, 0, 0},
    {0, 1, 0, 1},
    {0, 0, 0, 1},
    {1, 0, 0, 1},
};

/* ── Private helpers ──────────────────────────────────── */
static void stepper_step(int step)
{
    int idx = step & 7;
    HAL_GPIO_WritePin(STEPPER_IN1_GPIO, STEPPER_IN1_PIN, half_steps[idx][0] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_IN2_GPIO, STEPPER_IN2_PIN, half_steps[idx][1] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_IN3_GPIO, STEPPER_IN3_PIN, half_steps[idx][2] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_IN4_GPIO, STEPPER_IN4_PIN, half_steps[idx][3] ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_Delay(STEPPER_SPEED_MS);
}

static void stepper_off(void)
{
    HAL_GPIO_WritePin(STEPPER_IN1_GPIO, STEPPER_IN1_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_IN2_GPIO, STEPPER_IN2_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_IN3_GPIO, STEPPER_IN3_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(STEPPER_IN4_GPIO, STEPPER_IN4_PIN, GPIO_PIN_RESET);
}

static void select_led_channel(uint8_t channel)
{
    /* 74HC138: active low outputs, select via 3-bit input */
    HAL_GPIO_WritePin(LED_SEL0_GPIO, LED_SEL0_PIN, (channel & 1) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_SEL1_GPIO, LED_SEL1_PIN, (channel & 2) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_SEL2_GPIO, LED_SEL2_PIN, (channel & 4) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static uint16_t read_ref_adc(void)
{
    /* Read ADC1 channel 2 (PA1 - OPT101 reference) */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_2;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    return (uint16_t)HAL_ADC_GetValue(&hadc1);
}

static void mcp4131_write(uint8_t value)
{
    /* MCP4131 SPI digital potentiometer
     * Command: 0x00 (write wiper), data: 0-128
     * We use GPIO bit-banging since SPI is shared with SD/OLED */
    /* In production, use dedicated SPI or a separate CS.
     * For now, simplified: control LED current via PWM duty cycle instead */
    (void)value;
}

/* ── Public Functions ─────────────────────────────────── */

void led_wheel_init(void)
{
    /* All pins already initialized in MX_GPIO_Init */
    HAL_GPIO_WritePin(LED_DRV_EN_GPIO, LED_DRV_EN_PIN, GPIO_PIN_RESET);

    /* Disable all LED channels */
    select_led_channel(0);

    /* PWM off */
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);

    current_pos = EX_BLANK;
    wheel_homed = 0;
}

int led_wheel_home(void)
{
    /* Rotate until Hall sensor triggers, then back off one step */
    int timeout = 4096;  /* one full revolution max */

    while (timeout-- > 0) {
        if (HAL_GPIO_ReadPin(STEPPER_HOME_GPIO, STEPPER_HOME_PIN) == GPIO_PIN_RESET) {
            /* Hall sensor active (magnet near) → home position = blank */
            current_pos = EX_BLANK;
            wheel_homed = 1;
            stepper_off();
            return 0;
        }
        stepper_step(1);
    }

    stepper_off();
    return -1;  /* timeout */
}

int led_wheel_goto(ex_wavelength_t wavelength)
{
    if (!wheel_homed) {
        if (led_wheel_home() != 0) return -1;
    }

    int target = (int)wavelength;
    int current = (int)current_pos;

    /* Calculate shortest path (wheel has 9 positions: 0-8, 8=blank) */
    int diff = target - current;
    if (diff < 0) diff += 9;
    if (diff > 4) diff -= 9;  /* go other way if shorter */

    int direction = (diff >= 0) ? 1 : -1;
    int steps = abs(diff) * STEPS_PER_POSITION;

    for (int i = 0; i < steps; i++) {
        stepper_step(direction);
    }

    stepper_off();
    current_pos = wavelength;
    return 0;
}

void led_set_current(float current_ma)
{
    if (current_ma < 0) current_ma = 0;
    if (current_ma > 80) current_ma = 80;
    current_led_ma = current_ma;

    /* Convert to PWM duty cycle (0-8500) */
    /* OPA548 in current sink mode: I = V_set / R_sense
     * PWM → RC filter → V_set
     * Duty cycle proportional to current (0-80mA → 0-100% duty) */
    uint32_t duty = (uint32_t)((current_ma / 80.0f) * 8499);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, duty);
}

uint16_t led_on(float current_ma)
{
    /* Check safety interlock first */
    if (HAL_GPIO_ReadPin(LID_INTERLOCK_GPIO, LID_INTERLOCK_PIN) == GPIO_PIN_RESET) {
        /* Lid open — don't turn on LED */
        return 0;
    }

    led_set_current(current_ma);
    select_led_channel((uint8_t)current_pos);
    HAL_GPIO_WritePin(LED_DRV_EN_GPIO, LED_DRV_EN_PIN, GPIO_PIN_SET);

    /* Wait for LED to stabilize */
    HAL_Delay(5);

    /* Read reference photodiode */
    uint16_t ref = read_ref_adc();

    return ref;
}

void led_off(void)
{
    HAL_GPIO_WritePin(LED_DRV_EN_GPIO, LED_DRV_EN_PIN, GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 0);
}

uint16_t led_read_reference(void)
{
    return read_ref_adc();
}

ex_wavelength_t led_wheel_get_position(void)
{
    return current_pos;
}

uint16_t led_wavelength_nm(ex_wavelength_t wl)
{
    if (wl < NUM_EX_WAVELENGTHS) {
        return ex_wavelength_nm[wl];
    }
    return 0;
}