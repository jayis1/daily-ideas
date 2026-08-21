/*
 * visco-shear / firmware / main.c
 * Main application — Visco Shear pocket rotational rheometer
 *
 * State machine, UI, measurement orchestration.
 * Core 0: motor control + torque acquisition + Peltier PID
 * Core 1: rheology DSP + model fitting + OLED + SD + UART
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"
#include "hardware/i2c.h"
#include "hardware/pwm.h"
#include "hardware/uart.h"

#include "main.h"
#include "stepper.h"
#include "torque.h"
#include "rheology.h"
#include "temperature.h"
#include "spindle.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "ble_uart.h"
#include "database.h"
#include "buttons.h"

/* ── Global state ──────────────────────────────────────────────── */
volatile sys_state_t g_state = STATE_IDLE;
volatile bool g_measure_request = false;
volatile bool g_cancel_request = false;

static measure_mode_t current_mode = MODE_FLOW_CURVE;
static spindle_type_t current_spindle = SPINDLE_CC_13;
static float target_temp = 25.0f;       /* °C, -127 = no temp control */
static int menu_index = 0;

static measure_result_t last_result;

/* ── Menu items ────────────────────────────────────────────────── */
static const char *menu_items[] = {
    "Mode: ",
    "Spindle: ",
    "Temp: ",
    "Calibrate",
    "Info",
    "Exit",
};
#define MENU_COUNT 6

/* ── Buzzer ────────────────────────────────────────────────────── */
static uint8_t buzzer_slice;

void buzzer_beep(int ms, int freq_hz)
{
    if (freq_hz <= 0 || ms <= 0) {
        pwm_set_enabled(buzzer_slice, false);
        return;
    }
    uint32_t clk = 125000000;
    uint32_t div = 1;
    uint32_t top = clk / (div * freq_hz) - 1;
    if (top > 65534) { div = clk / (freq_hz * 65535) + 1; top = clk / (div * freq_hz) - 1; }
    pwm_set_clkdiv_int_frac(buzzer_slice, div, 0);
    pwm_set_wrap(buzzer_slice, top);
    pwm_set_chan_level(buzzer_slice, PWM_CHAN_A, top / 2);
    pwm_set_enabled(buzzer_slice, true);
    sleep_ms(ms);
    pwm_set_enabled(buzzer_slice, false);
}

static void buzzer_init(void)
{
    gpio_set_function(PIN_BUZZER, GPIO_FUNC_PWM);
    buzzer_slice = pwm_gpio_to_slice_num(PIN_BUZZER);
    pwm_set_enabled(buzzer_slice, false);
}

/* ── Status LED ────────────────────────────────────────────────── */
static void led_init(void)
{
    gpio_init(PIN_STATUS_LED);
    gpio_set_dir(PIN_STATUS_LED, GPIO_OUT);
    gpio_put(PIN_STATUS_LED, 0);
}

static void led_set(bool on)
{
    gpio_put(PIN_STATUS_LED, on);
}

/* ── Internal ADC (battery, spindle ID) ────────────────────────── */
static void adc_internal_init(void)
{
    adc_init();
    adc_gpio_init(PIN_ADC_VBAT);
    adc_gpio_init(PIN_SPINDLE_ID);
    adc_gpio_init(PIN_ADC_NTC);
    adc_set_temp_sensor_enabled(true);
}

static float read_battery_voltage(void)
{
    adc_select_input(2);  /* ADC2 = GPIO28 = VBAT */
    uint16_t raw = adc_read();
    /* Divider: 100k/100k → Vbat/2; ADC 3.3V/4095 */
    return (raw / 4095.0f) * 3.3f * 2.0f;
}

/* ── BLE/UART command callback ─────────────────────────────────── */
static void cmd_handler(uint8_t cmd, const uint8_t *payload, int len)
{
    switch (cmd) {
    case CMD_START:
        g_measure_request = true;
        printf("[CMD] Start measurement\n");
        break;
    case CMD_STOP:
        g_cancel_request = true;
        printf("[CMD] Stop\n");
        break;
    case CMD_SET_MODE:
        if (len >= 1 && payload[0] < MODE_COUNT) {
            current_mode = (measure_mode_t)payload[0];
            printf("[CMD] Mode set to %d\n", current_mode);
        }
        break;
    case CMD_SET_SPINDLE:
        if (len >= 1 && payload[0] < SPINDLE_COUNT) {
            current_spindle = (spindle_type_t)payload[0];
            printf("[CMD] Spindle set to %d\n", current_spindle);
        }
        break;
    case CMD_SET_TEMP:
        if (len >= 4) {
            memcpy(&target_temp, payload, 4);
            printf("[CMD] Target temp = %.1f °C\n", target_temp);
        }
        break;
    case CMD_CALIBRATE:
        printf("[CMD] Calibration requested\n");
        /* Run silicone oil calibration measurement */
        current_mode = MODE_SINGLE_SPEED;
        g_measure_request = true;
        break;
    case CMD_GET_INFO:
        ble_uart_send_info("Visco Shear v1.0", current_spindle, target_temp);
        break;
    default:
        printf("[CMD] Unknown 0x%02x\n", cmd);
    }
}

/* ── Flow curve measurement ────────────────────────────────────── */
/* Shear rate ladder (log-spaced), rpm values for CC-13 geometry */
static const float flow_rpm[] = {0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0};
#define N_FLOW_STEPS 7

static void run_flow_curve(measure_result_t *res)
{
    const spindle_geo_t *geo = &spindle_table[current_spindle];
    memset(res, 0, sizeof(*res));
    res->spindle = current_spindle;
    res->mode = MODE_FLOW_CURVE;
    res->temperature = temperature_read();

    /* Auto-zero torque sensor */
    torque_auto_zero();

    printf("[FLOW] Starting flow curve, spindle=%s\n", geo->name ? spindle_name(current_spindle) : "?");
    oled_display_show_status("Flow curve...", "");

    res->n_points = 0;

    for (int i = 0; i < N_FLOW_STEPS; i++) {
        if (g_cancel_request) {
            printf("[FLOW] Cancelled at step %d\n", i);
            stepper_stop();
            return;
        }

        float rpm = flow_rpm[i];
        float omega = rpm * 2.0f * M_PI / 60.0f;  /* rad/s */

        /* Accelerate to target speed (ramped) */
        printf("[FLOW] Step %d: %.2f rpm\n", i, rpm);
        stepper_run_rpm(rpm);

        /* Wait for steady state: torque drift < 1% over 3 seconds */
        float tau_prev = torque_read_averaged(TORQUE_AVG);
        sleep_ms(2000);
        float tau_now;
        int stable = 0;
        for (int s = 0; s < 10; s++) {
            sleep_ms(300);
            tau_now = torque_read_averaged(TORQUE_AVG);
            float drift = fabsf(tau_now - tau_prev) / (fabsf(tau_prev) + 1e-6f);
            if (drift < 0.01f) { stable++; if (stable >= 3) break; }
            else stable = 0;
            tau_prev = tau_now;
        }

        /* Record averaged torque (µN·m) */
        float tau_uNm = torque_read_averaged(TORQUE_AVG * 2);
        float tau_Nm = tau_uNm * 1e-6f;   /* Convert to N·m */
        float tau_Pa = tau_Nm / spindle_torque_to_stress_factor(current_spindle);

        /* Compute shear rate */
        float gamma_dot = spindle_shear_rate(current_spindle, omega);

        /* Compute viscosity */
        float eta_Pa_s = (gamma_dot > 0) ? (tau_Pa / gamma_dot) : 0;
        float eta_mPa_s = eta_Pa_s * 1000.0f;

        printf("[FLOW]   γ̇=%.3f s⁻¹, τ=%.2f µN·m, η=%.2f mPa·s\n",
               gamma_dot, tau_uNm, eta_mPa_s);

        res->omega[res->n_points] = rpm;
        res->shear_rate[res->n_points] = gamma_dot;
        res->torque[res->n_points] = tau_uNm;
        res->viscosity[res->n_points] = eta_mPa_s;
        res->n_points++;

        /* Stream data via BLE */
        ble_uart_send_torque_sample(i, (int16_t)tau_uNm, (int16_t)(rpm * 100));

        /* Update OLED live */
        oled_display_show_flow_point(i + 1, N_FLOW_STEPS, eta_mPa_s, gamma_dot);
    }

    /* Stop motor */
    stepper_stop();

    /* Fit rheological models */
    printf("[FLOW] Fitting models...\n");
    rheology_fit_models(res);

    printf("[FLOW] Best model: %s (R²=%.4f)\n",
           model_names[res->best_fit.model], res->best_fit.r_squared);

    /* Identify reference fluid */
    int match = database_identify(res->viscosity[3], res->temperature);
    if (match >= 0) {
        printf("[FLOW] Closest reference: %s\n", database_name(match));
    }
}

/* ── Oscillatory measurement ───────────────────────────────────── */
static const float osc_freqs[] = {0.1, 0.316, 1.0, 3.162, 10.0};
#define N_OSC_FREQS 5
#define OSC_AMP_RAD 0.05f    /* 0.05 rad (~2.9°) small strain */
#define OSC_PERIODS 5        /* measure over 5 cycles */
#define OSC_SAMPLE_HZ 2000

static void run_oscillatory(measure_result_t *res)
{
    const spindle_geo_t *geo = &spindle_table[current_spindle];
    res->n_freq = 0;

    printf("[OSC] Starting oscillatory sweep, amp=%.3f rad\n", OSC_AMP_RAD);
    oled_display_show_status("Oscillatory...", "");

    torque_auto_zero();

    for (int f = 0; f < N_OSC_FREQS; f++) {
        if (g_cancel_request) { stepper_stop(); return; }

        float freq = osc_freqs[f];
        float omega = 2.0f * M_PI * freq;
        int n_samples = (int)(OSC_PERIODS / freq * OSC_SAMPLE_HZ);
        if (n_samples > 8000) n_samples = 8000;
        float dt = 1.0f / OSC_SAMPLE_HZ;

        printf("[OSC] Freq %d: %.3f Hz, %d samples\n", f, freq, n_samples);

        /* Start sinusoidal oscillation */
        stepper_oscillate(freq, OSC_AMP_RAD);
        sleep_ms(500);  /* Settling */

        /* Collect torque samples and I/Q demodulate */
        float I_acc = 0, Q_acc = 0;
        for (int s = 0; s < n_samples; s++) {
            float t = s * dt;
            float tau = torque_read_single() * 1e-6f;  /* N·m */
            float sin_wt = sinf(omega * t);
            float cos_wt = cosf(omega * t);
            I_acc += tau * sin_wt;
            Q_acc += tau * cos_wt;
            sleep_us((int)(dt * 1e6f) - 50);  /* Approximate sample interval */
        }
        float T_total = n_samples * dt;
        float G_prime  = (2.0f / T_total) * I_acc / OSC_AMP_RAD;  /* Pa */
        float G_double = (2.0f / T_total) * Q_acc / OSC_AMP_RAD;  /* Pa */
        float tan_d = (G_prime > 1e-6f) ? (G_double / G_prime) : 999.0f;
        float eta_star = sqrtf(G_prime * G_prime + G_double * G_double) / omega;

        printf("[OSC]   G'=%.2f Pa, G''=%.2f Pa, tanδ=%.3f, |η*|=%.2f Pa·s\n",
               G_prime, G_double, tan_d, eta_star);

        res->freq[res->n_freq] = freq;
        res->G_prime[res->n_freq] = G_prime;
        res->G_double[res->n_freq] = G_double;
        res->tan_delta[res->n_freq] = tan_d;
        res->eta_complex[res->n_freq] = eta_star;
        res->n_freq++;

        oled_display_show_osc_point(f + 1, N_OSC_FREQS, G_prime, G_double);

        stepper_stop();
        sleep_ms(200);
    }
}

/* ── Thixotropy measurement ────────────────────────────────────── */
static void run_thixotropy(measure_result_t *res)
{
    printf("[THIXO] Hysteresis loop + recovery test\n");
    oled_display_show_status("Thixotropy...", "");

    torque_auto_zero();

    /* Up-ramp: 1 → 100 rpm in 30 s (log ramp) */
    float t_start = time_us_32() / 1e6f;
    float tau_up[60], gamma_up[60];
    int n_up = 0;
    for (int i = 0; i <= 30; i++) {
        float frac = (float)i / 30.0f;
        float rpm = powf(100.0f, frac);  /* 1 → 100 rpm log */
        stepper_run_rpm(rpm);
        sleep_ms(500);
        float tau = torque_read_averaged(TORQUE_AVG) * 1e-6f;
        float omega = rpm * 2.0f * M_PI / 60.0f;
        float gamma = spindle_shear_rate(current_spindle, omega);
        tau_up[n_up] = tau; gamma_up[n_up] = gamma;
        n_up++;
    }

    /* Down-ramp: 100 → 1 rpm in 30 s */
    float tau_dn[60], gamma_dn[60];
    int n_dn = 0;
    for (int i = 0; i <= 30; i++) {
        float frac = (float)i / 30.0f;
        float rpm = powf(100.0f, 1.0f - frac);  /* 100 → 1 rpm */
        stepper_run_rpm(rpm);
        sleep_ms(500);
        float tau = torque_read_averaged(TORQUE_AVG) * 1e-6f;
        float omega = rpm * 2.0f * M_PI / 60.0f;
        float gamma = spindle_shear_rate(current_spindle, omega);
        tau_dn[n_dn] = tau; gamma_dn[n_dn] = gamma;
        n_dn++;
    }
    stepper_stop();

    /* Hysteresis loop area (trapezoidal) */
    float area = 0;
    for (int i = 1; i < n_up && i < n_dn; i++) {
        float d_gamma = gamma_up[i] - gamma_up[i-1];
        float d_tau = tau_up[i] - tau_dn[i];
        area += d_tau * d_gamma;
    }
    res->hysteresis_area = fabsf(area);
    printf("[THIXO] Hysteresis area = %.2f Pa·s⁻¹\n", res->hysteresis_area);

    /* Recovery test: high shear then step to low, monitor */
    stepper_run_rpm(100.0f);
    sleep_ms(30);  /* Break structure */
    stepper_run_rpm(1.0f);

    float eta_t[30];
    for (int i = 0; i < 30; i++) {
        sleep_ms(1000);
        float tau = torque_read_averaged(TORQUE_AVG) * 1e-6f;
        float omega = 1.0f * 2.0f * M_PI / 60.0f;
        float gamma = spindle_shear_rate(current_spindle, omega);
        eta_t[i] = (gamma > 0) ? (tau / gamma) * 1000.0f : 0;  /* mPa·s */
    }
    stepper_stop();

    /* Fit recovery: η(t) = η_∞ + (η_0 − η_∞)(1 − exp(−t/τ_r)) */
    float eta_inf = eta_t[29];
    float eta_0 = eta_t[0];
    /* Simple log-linear fit for τ_r */
    float sum_xy = 0, sum_xx = 0;
    for (int i = 1; i < 20; i++) {
        float frac = (eta_inf - eta_t[i]) / (eta_inf - eta_0 + 1e-6f);
        if (frac > 0 && frac < 1) {
            float x = (float)i;  /* time in seconds */
            float y = -logf(frac);
            sum_xy += x * y;
            sum_xx += x * x;
        }
    }
    res->recovery_time = (sum_xx > 0) ? (sum_xy / sum_xx) : 0;
    printf("[THIXO] Recovery time τ_r = %.2f s\n", res->recovery_time);
}

/* ── Full measurement sequence ─────────────────────────────────── */
static void do_measurement(void)
{
    g_state = STATE_EQUIL;
    g_measure_request = false;
    led_set(true);
    buzzer_beep(100, 2000);

    printf("\n=== Visco Shear Measurement ===\n");
    printf("Mode: %d, Spindle: %s, Temp target: %.1f °C\n",
           current_mode, spindle_name(current_spindle), target_temp);

    /* Temperature equilibration */
    if (target_temp > -100.0f) {
        printf("[EQUIL] Ramping to %.1f °C...\n", target_temp);
        oled_display_show_status("Equilibrating...", NULL);
        temperature_set_target(target_temp);
        int timeout = 0;
        while (!temperature_is_stable() && timeout < 120 && !g_cancel_request) {
            sleep_ms(1000);
            timeout++;
            if (timeout % 10 == 0)
                printf("[EQUIL] T=%.2f °C, %d s\n", temperature_read(), timeout);
        }
        if (g_cancel_request) { g_state = STATE_IDLE; led_set(false); return; }
        printf("[EQUIL] Stable at %.2f °C\n", temperature_read());
    }

    memset(&last_result, 0, sizeof(last_result));
    last_result.temperature = temperature_read();

    /* Run selected mode */
    switch (current_mode) {
    case MODE_FLOW_CURVE:
        g_state = STATE_FLOW;
        run_flow_curve(&last_result);
        break;
    case MODE_OSCILLATORY:
        g_state = STATE_OSCILL;
        run_oscillatory(&last_result);
        break;
    case MODE_THIXOTROPY:
        g_state = STATE_THIXO;
        run_thixotropy(&last_result);
        break;
    case MODE_SINGLE_SPEED:
        g_state = STATE_FLOW;
        run_flow_curve(&last_result);
        break;
    case MODE_YIELD_STRESS:
        /* Controlled-stress ramp: increase torque until rotation detected */
        g_state = STATE_FLOW;
        run_flow_curve(&last_result);  /* Simplified for firmware skeleton */
        break;
    default:
        break;
    }

    /* Log to SD */
    g_state = STATE_RESULT;
    sd_logger_write_result(&last_result);

    /* Send result via BLE */
    ble_uart_send_result(&last_result);

    /* Display result on OLED */
    oled_display_show_result(&last_result);

    printf("=== Measurement complete ===\n");
    printf("Best model: %s, R²=%.4f\n",
           model_names[last_result.best_fit.model],
           last_result.best_fit.r_squared);

    buzzer_beep(200, 3000);
    led_set(false);
    g_state = STATE_IDLE;
}

/* ── Core 1 entry: DSP + display + comms ───────────────────────── */
static void core1_entry(void)
{
    /* Core 1 handles OLED updates, SD writes, BLE streaming in background */
    while (1) {
        /* Process BLE/UART commands */
        ble_uart_poll();

        /* Update OLED if idle */
        if (g_state == STATE_IDLE) {
            oled_display_show_idle(current_mode, current_spindle,
                                   temperature_read(),
                                   read_battery_voltage());
        }

        sleep_ms(100);
    }
}

/* ── Main ──────────────────────────────────────────────────────── */
int main(void)
{
    /* Init stdio (USB CDC) */
    stdio_init_all();

    printf("\n");
    printf("╔══════════════════════════════════════╗\n");
    printf("║   Visco Shear v1.0                   ║\n");
    printf("║   Pocket Rotational Rheometer        ║\n");
    printf("║   RP2040 + ESP32-C3                  ║\n");
    printf("╚══════════════════════════════════════╝\n\n");

    /* Hardware init */
    led_init();
    buzzer_init();
    adc_internal_init();

    /* I2C bus (ADS1115 + OLED) */
    i2c_init(i2c0, I2C_FREQ_HZ);
    gpio_set_function(PIN_I2C_SCL, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C_SDA, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C_SCL);
    gpio_pull_up(PIN_I2C_SDA);

    /* UART to ESP32-C3 */
    uart_init(uart0, UART_BAUD);
    gpio_set_function(PIN_UART_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_UART_RX, GPIO_FUNC_UART);

    /* Subsystem init */
    buttons_init();
    spindle_init();
    torque_init();
    stepper_init();
    temperature_init();
    oled_display_init();
    sd_logger_init();
    database_init();
    ble_uart_init(cmd_handler);

    printf("[INIT] All subsystems initialized\n");

    /* Spindle detection */
    current_spindle = spindle_detect();
    printf("[INIT] Detected spindle: %s\n", spindle_name(current_spindle));

    /* Start Core 1 */
    multicore_launch_core1(core1_entry);

    buzzer_beep(150, 4000);
    sleep_ms(100);
    buzzer_beep(100, 3000);

    /* Main loop (Core 0) */
    uint32_t last_btn_time = 0;
    while (1) {
        /* Button handling */
        if (time_us_32() - last_btn_time > 200000) {  /* Debounce 200ms */
            if (gpio_get(PIN_BTN_START) == 0) {
                last_btn_time = time_us_32();
                if (g_state == STATE_IDLE) {
                    printf("[BTN] START pressed — begin measurement\n");
                    g_measure_request = true;
                } else {
                    printf("[BTN] START pressed — cancel\n");
                    g_cancel_request = true;
                }
                buzzer_beep(50, 2500);
            }
            if (gpio_get(PIN_BTN_MODE) == 0) {
                last_btn_time = time_us_32();
                current_mode = (measure_mode_t)((current_mode + 1) % MODE_COUNT);
                printf("[BTN] MODE → %d (%s)\n", current_mode,
                       current_mode == MODE_FLOW_CURVE ? "Flow curve" :
                       current_mode == MODE_OSCILLATORY ? "Oscillatory" :
                       current_mode == MODE_THIXOTROPY ? "Thixotropy" : "Other");
                buzzer_beep(50, 2000);
            }
            if (gpio_get(PIN_BTN_MENU) == 0) {
                last_btn_time = time_us_32();
                menu_index = (menu_index + 1) % MENU_COUNT;
                printf("[BTN] MENU → %s\n", menu_items[menu_index]);
                buzzer_beep(50, 1500);
            }
        }

        /* Measurement request */
        if (g_measure_request && g_state == STATE_IDLE) {
            do_measurement();
        }

        /* Temperature control loop (1 Hz) */
        temperature_task();

        sleep_ms(10);
    }

    return 0;
}