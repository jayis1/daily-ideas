/*
 * Levia Forge — Input Handler
 * Joystick (ADC), rotary encoder (GPIO), buttons, battery, temperature.
 *
 * SPDX-License-Identifier: MIT
 */
#include "input.h"
#include "sdkconfig.h"
#include "pico/stdlib.h"
#include "hardware/adc.h"
#include <math.h>

#define ADC_MAX         4095.0f
#define JOYSTICK_CENTER 2048.0f
#define JOYSTICK_DEADZONE 100.0f

/* Rotary encoder state */
static int32_t enc_count = 0;
static uint8_t enc_state = 0;

/* Button debounce state */
static uint32_t btn_last_read[32] = {0};
static bool btn_last_state[32] = {false};

void input_init(void)
{
    /* Initialize ADC for joystick + battery */
    adc_init();
    gpio_init(PIN_ADC_JOY_X);
    gpio_init(PIN_ADC_JOY_Y);
    gpio_init(PIN_ADC_VBAT);
    adc_gpio_init(PIN_ADC_JOY_X);
    adc_gpio_init(PIN_ADC_JOY_Y);
    adc_gpio_init(PIN_ADC_VBAT);

    /* Configure ADC for internal temperature sensor (channel 4) */
    /* adc_select_input(4); for temp */

    /* Rotary encoder pins */
    gpio_init(PIN_ENC_A);
    gpio_init(PIN_ENC_B);
    gpio_set_dir(PIN_ENC_A, GPIO_IN);
    gpio_set_dir(PIN_ENC_B, GPIO_IN);
    gpio_pull_up(PIN_ENC_A);
    gpio_pull_up(PIN_ENC_B);

    /* Encoder button */
    gpio_init(PIN_ENC_BTN);
    gpio_set_dir(PIN_ENC_BTN, GPIO_IN);
    gpio_pull_up(PIN_ENC_BTN);

    /* Mode + release buttons */
    gpio_init(PIN_BTN_MODE_DEF);
    gpio_init(PIN_BTN_RELEASE_DEF);
    gpio_set_dir(PIN_BTN_MODE_DEF, GPIO_IN);
    gpio_set_dir(PIN_BTN_RELEASE_DEF, GPIO_IN);
    gpio_pull_up(PIN_BTN_MODE_DEF);
    gpio_pull_up(PIN_BTN_RELEASE_DEF);

    /* Status LED */
    gpio_init(PIN_LED_ONBOARD);
    gpio_set_dir(PIN_LED_ONBOARD, GPIO_OUT);

    /* Initialize encoder state */
    enc_state = (gpio_get(PIN_ENC_A) ? 1 : 0) | ((gpio_get(PIN_ENC_B) ? 1 : 0) << 1);
}

input_joystick_t input_read_joystick(void)
{
    input_joystick_t joy = { 0.0f, 0.0f };

    /* Read X axis */
    adc_select_input(0);  /* ADC0 = GP26 */
    uint16_t raw_x = adc_read();

    /* Read Y axis */
    adc_select_input(1);  /* ADC1 = GP27 */
    uint16_t raw_y = adc_read();

    /* Normalize to -1.0 .. +1.0 with deadzone */
    float fx = ((float)raw_x - JOYSTICK_CENTER) / (ADC_MAX / 2.0f);
    float fy = ((float)raw_y - JOYSTICK_CENTER) / (ADC_MAX / 2.0f);

    if (fabsf(fx) < (JOYSTICK_DEADZONE / (ADC_MAX / 2.0f)))
        fx = 0.0f;
    if (fabsf(fy) < (JOYSTICK_DEADZONE / (ADC_MAX / 2.0f)))
        fy = 0.0f;

    /* Clamp */
    if (fx > 1.0f) fx = 1.0f;
    if (fx < -1.0f) fx = -1.0f;
    if (fy > 1.0f) fy = 1.0f;
    if (fy < -1.0f) fy = -1.0f;

    joy.x = fx;
    joy.y = fy;
    return joy;
}

float input_read_encoder_delta(void)
{
    /* Quadrature decoder using state transition table */
    static const int8_t enc_table[] = {
         0, -1,  1,  0,
         1,  0,  0, -1,
        -1,  0,  0,  1,
         0,  1, -1,  0
    };

    uint8_t new_state = (gpio_get(PIN_ENC_A) ? 1 : 0) |
                        ((gpio_get(PIN_ENC_B) ? 1 : 0) << 1);
    int8_t delta = enc_table[(enc_state << 2) | new_state];
    enc_state = new_state;
    enc_count += delta;

    /* Return the number of detents (typically 4 transitions per detent) */
    static int32_t last_count = 0;
    float result = (float)(enc_count - last_count) / 4.0f;
    last_count = enc_count;
    return result;
}

bool input_read_button(uint8_t pin)
{
    /* Active-low with debounce */
    uint32_t now = time_us_32();
    bool current = (gpio_get(pin) == 0);

    if (pin < 32) {
        if (current != btn_last_state[pin]) {
            if ((now - btn_last_read[pin]) > 5000) {  /* 5 ms debounce */
                btn_last_state[pin] = current;
                btn_last_read[pin] = now;
            }
        }
        return btn_last_state[pin];
    }
    return false;
}

int input_read_battery_mv(void)
{
    /* Battery voltage via divider (÷4) on ADC2 (GP28) */
    adc_select_input(2);
    uint16_t raw = adc_read();
    /* raw/4095 * 3.3V * 4 = battery voltage in V → mV */
    float voltage = (float)raw / ADC_MAX * 3.3f * 4.0f * 1000.0f;
    return (int)voltage;
}

float input_read_temp_c(void)
{
    /* RP2040 internal temperature sensor (ADC channel 4) */
    adc_select_input(4);
    uint16_t raw = adc_read();
    /* T = 27 - (V - 0.706) / 0.001721
     * V = raw/4095 * 3.3V */
    float voltage = (float)raw / ADC_MAX * 3.3f;
    float temp = 27.0f - (voltage - 0.706f) / 0.001721f;
    return temp;
}

void input_set_led(bool on)
{
    gpio_put(PIN_LED_ONBOARD, on);
}