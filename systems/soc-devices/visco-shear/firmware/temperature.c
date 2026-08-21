/*
 * visco-shear / firmware / temperature.c
 * Peltier TEC1-12706 PID temperature control + NTC readout
 *
 * DRV8833 H-bridge drives Peltier bidirectionally.
 * NTC 10kΩ thermistor + 10kΩ divider → RP2040 ADC.
 * PID loop at 1 Hz, ±0.1 °C stability.
 *
 * MIT License.
 */
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "hardware/adc.h"
#include "main.h"
#include "temperature.h"

#define NTC_BETA        3950.0f
#define NTC_R0          10000.0f   /* 10kΩ at 25°C */
#define NTC_T0          298.15f    /* 25°C in K */
#define PID_KP          8.0f
#define PID_KI          0.5f
#define PID_KD          2.0f
#define PID_MAX         4095.0f    /* PWM max (12-bit) */

static float target_temp = -127.0f;   /* -127 = disabled */
static float pid_integral = 0;
static float pid_prev_err = 0;
static absolute_time_t last_pid_time;
static bool stable = false;
static float last_temp = 25.0f;
static uint8_t peltier_slice;

static float ntc_read_temperature(void)
{
    /* NTC divider: 3.3V → 10kΩ → NTC → GND
     * V_adc = 3.3 * R_ntc / (R_ntc + 10k)
     * R_ntc = 10k * V / (3.3 - V) */
    adc_select_input(1);  /* ADC1 = GPIO27 = NTC */
    uint16_t raw = adc_read();
    float v = raw * 3.3f / 4095.0f;
    if (v > 3.29f) v = 3.29f;
    float r_ntc = NTC_R0 * v / (3.3f - v + 1e-6f);

    /* Steinhart-Hart: 1/T = 1/T0 + (1/B)·ln(R/R0) */
    float inv_t = 1.0f / NTC_T0 + (1.0f / NTC_BETA) * logf(r_ntc / NTC_R0);
    float temp_k = 1.0f / inv_t;
    return temp_k - 273.15f;
}

void temperature_init(void)
{
    gpio_init(PIN_PELTIER_EN);
    gpio_set_dir(PIN_PELTIER_EN, GPIO_OUT);
    gpio_put(PIN_PELTIER_EN, 0);

    gpio_init(PIN_PELTIER_DIR);
    gpio_set_dir(PIN_PELTIER_DIR, GPIO_OUT);
    gpio_put(PIN_PELTIER_DIR, 0);  /* Heating by default */

    gpio_set_function(PIN_PELTIER_PWM, GPIO_FUNC_PWM);
    peltier_slice = pwm_gpio_to_slice_num(PIN_PELTIER_PWM);
    pwm_set_wrap(peltier_slice, 4095);
    pwm_set_chan_level(peltier_slice, pwm_gpio_to_channel(PIN_PELTIER_PWM), 0);
    pwm_set_enabled(peltier_slice, false);

    adc_gpio_init(PIN_ADC_NTC);
    last_pid_time = get_absolute_time();
    last_temp = ntc_read_temperature();
    printf("[TEMP] Initialized, T=%.2f °C\n", last_temp);
}

void temperature_set_target(float temp_c)
{
    target_temp = temp_c;
    pid_integral = 0;
    pid_prev_err = 0;
    stable = false;
    printf("[TEMP] Target set to %.1f °C\n", target_temp);
}

float temperature_read(void)
{
    last_temp = ntc_read_temperature();
    return last_temp;
}

bool temperature_is_stable(void)
{
    return stable;
}

void temperature_disable(void)
{
    target_temp = -127.0f;
    gpio_put(PIN_PELTIER_EN, 0);
    pwm_set_enabled(peltier_slice, false);
}

void temperature_task(void)
{
    if (target_temp < -100.0f) return;

    /* 1 Hz PID loop */
    uint32_t now_us = to_us_since_boot(get_absolute_time());
    uint32_t elapsed = now_us - to_us_since_boot(last_pid_time);
    if (elapsed < 1000000) return;  /* 1 second */
    last_pid_time = get_absolute_time();

    float temp = ntc_read_temperature();
    last_temp = temp;
    float err = target_temp - temp;

    /* PID */
    float dt = elapsed / 1e6f;
    pid_integral += err * dt;
    if (pid_integral > 200) pid_integral = 200;
    if (pid_integral < -200) pid_integral = -200;
    float derivative = (err - pid_prev_err) / dt;
    pid_prev_err = err;

    float output = PID_KP * err + PID_KI * pid_integral + PID_KD * derivative;

    /* Determine heating or cooling */
    bool heating = (output > 0);
    float abs_output = fabsf(output);
    if (abs_output > PID_MAX) abs_output = PID_MAX;

    gpio_put(PIN_PELTIER_DIR, heating ? 0 : 1);  /* Polarity */
    pwm_set_chan_level(peltier_slice, pwm_gpio_to_channel(PIN_PELTIER_PWM),
                       (uint16_t)abs_output);
    pwm_set_enabled(peltier_slice, abs_output > 50);
    gpio_put(PIN_PELTIER_EN, abs_output > 50);

    /* Check stability: |err| < 0.1°C for 5 consecutive seconds */
    static int stable_count = 0;
    if (fabsf(err) < 0.1f) {
        stable_count++;
        if (stable_count >= 5) stable = true;
    } else {
        stable_count = 0;
        stable = false;
    }
}