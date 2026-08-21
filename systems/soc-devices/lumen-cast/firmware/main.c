/**
 * lumen_cast/firmware/main.c — Lumen Cast Pocket Goniophotometer
 *
 * STM32G491RET6 (Cortex-M4F @ 170 MHz, 512 KB flash, 112 KB SRAM)
 *
 * Main firmware — cooperative super-loop with timer-driven motor control.
 *
 * Hardware flow:
 *   Source mounted in center cradle
 *   → NEMA8 stepper (TMC2209) orbits sensor head in azimuth (TIM2 PWM step)
 *   → SG90 servo tilts sensor head in elevation (TIM3 PWM)
 *   → OPT3001 measures illuminance (lux) at each angle
 *   → TCS34725 measures RGBC color at each angle
 *   → I = lux × r² (candela), Φ = ∮ I dΩ (lumens)
 *   → beam angle, CCT, Duv, uniformity computed
 *   → results shown on OLED, logged to W25Q128, sent via UART
 *     to ESP32-C3 for BLE/WiFi relay (.IES/.LDT export to phone/PC)
 *
 * Scan state machine:
 *   IDLE → (SCAN button) → HOMING → SCANNING → RESULTS → IDLE
 *   Hold MODE 3s → CALIBRATION (reference lamp)
 *
 * Build: see firmware/Makefile
 */

#include "main.h"
#include "photometer.h"
#include "color.h"
#include "motor.h"
#include "servo.h"
#include "goniometry.h"
#include "sh1106.h"
#include "flashlog.h"
#include "ble_bridge.h"
#include "ds3231.h"
#include "ws2812.h"

#include <string.h>
#include <math.h>

static const char *TAG = "LUMEN";

/* ── Global state ──────────────────────────────────────────────────── */

volatile lumen_mode_t g_mode = MODE_IDLE;
volatile bool g_scan_trigger = false;
scan_buffer_t g_scan;
photo_result_t g_result;
float g_cal_factor = 1.0f;

/* Current scan configuration (defaults to Type C) */
static scan_config_t s_config = {
    .type = SCAN_TYPE_C,
    .az_steps = 24,
    .el_steps = 12,
    .az_start = 0.0f,
    .az_end = 360.0f,
    .el_start = 0.0f,
    .el_end = 180.0f,
    .step_deg = 15.0f,
};

/* ── Button debouncing ─────────────────────────────────────────────── */

static uint8_t btn_scan_debounce = 0;
static uint8_t btn_mode_debounce = 0;
static bool btn_scan_pressed = false;
static bool btn_mode_pressed = false;
static uint32_t btn_mode_press_time = 0;

static void buttons_poll(void)
{
    /* Active-low buttons with internal pull-ups */
    bool scan_raw = (GPIOA->IDR & (1 << PIN_BTN_SCAN)) == 0;
    bool mode_raw = (GPIOA->IDR & (1 << PIN_BTN_MODE)) == 0;

    /* Shift-register debounce (8 consecutive reads) */
    btn_scan_debounce = (btn_scan_debounce << 1) | (scan_raw ? 1 : 0);
    btn_mode_debounce = (btn_mode_debounce << 1) | (mode_raw ? 1 : 0);

    bool scan_now = (btn_scan_debounce & 0xFF) == 0xFF;
    bool mode_now = (btn_mode_debounce & 0xFF) == 0xFF;

    if (scan_now && !btn_scan_pressed) {
        btn_scan_pressed = true;
        g_scan_trigger = true;
        LOGI(TAG, "SCAN button pressed");
    } else if (!scan_now) {
        btn_scan_pressed = false;
    }

    if (mode_now && !btn_mode_pressed) {
        btn_mode_pressed = true;
        btn_mode_press_time = millis();
    } else if (!mode_now && btn_mode_pressed) {
        btn_mode_pressed = false;
        uint32_t hold = millis() - btn_mode_press_time;
        if (hold >= 3000) {
            /* Long press → calibration mode */
            g_mode = MODE_CALIBRATION;
            LOGI(TAG, "Entering calibration mode");
        } else if (hold > 50) {
            /* Short press → cycle scan type */
            s_config.type = (scan_type_t)((s_config.type + 1) % 4);
            update_scan_config(&s_config);
            LOGI(TAG, "Scan type: %d", s_config.type);
        }
    }
}

/* ── Update scan config from type ──────────────────────────────────── */

void update_scan_config(scan_config_t *c)
{
    switch (c->type) {
    case SCAN_TYPE_A:
        c->az_steps = 360; c->el_steps = 1;
        c->az_start = 0; c->az_end = 360;
        c->el_start = 90; c->el_end = 90;  /* equator only */
        c->step_deg = 1.0f;
        break;
    case SCAN_TYPE_C:
        c->az_steps = 24; c->el_steps = 12;
        c->az_start = 0; c->az_end = 360;
        c->el_start = 0; c->el_end = 180;
        c->step_deg = 15.0f;
        break;
    case SCAN_MERIDIAN:
        c->az_steps = 1; c->el_steps = 180;
        c->az_start = 0; c->az_end = 0;
        c->el_start = 0; c->el_end = 180;
        c->step_deg = 1.0f;
        break;
    case SCAN_NEARFIELD:
        c->az_steps = 25; c->el_steps = 25;
        c->az_start = -60; c->az_end = 60;
        c->el_start = 30; c->el_end = 150;
        c->step_deg = 5.0f;
        break;
    }
}

/* ── Ambient reading (before scan) ─────────────────────────────────── */

static float read_ambient(void)
{
    float lux;
    if (opt3001_read_lux(&lux) == 0)
        return lux;
    return 0.0f;
}

/* ── Run a complete scan ───────────────────────────────────────────── */

static void run_scan(scan_config_t *cfg, scan_buffer_t *buf)
{
    memset(buf, 0, sizeof(*buf));
    buf->config = *cfg;
    buf->n_samples = 0;
    buf->cal_factor = g_cal_factor;

    /* Timestamp from RTC */
    ds3231_get_time(&buf->timestamp);

    /* Read ambient light (will be subtracted) */
    buf->ambient_lux = read_ambient();
    LOGI(TAG, "Ambient: %.2f lux", buf->ambient_lux);

    /* Home the stepper to 0° */
    motor_home();
    while (g_mode == MODE_HOMING && !motor_at_target()) {
        delay_ms(10);
    }

    motor_enable(true);
    g_mode = MODE_SCANNING;

    float az_step = (cfg->az_end - cfg->az_start) / (float)cfg->az_steps;
    float el_step = (cfg->el_end - cfg->el_start) / (float)(cfg->el_steps > 1 ? cfg->el_steps - 1 : 1);

    LOGI(TAG, "Scan: %d az × %d el, az_step=%.1f° el_step=%.1f°",
         cfg->az_steps, cfg->el_steps, az_step, el_step);

    for (int el_idx = 0; el_idx < cfg->el_steps; el_idx++) {
        float elevation = cfg->el_start + el_idx * el_step;

        /* Set servo elevation (convert 0-180° to -90/+90°) */
        float servo_elev = elevation - 90.0f;
        servo_set_elevation(servo_elev);
        delay_ms(400);  /* servo settle */

        for (int az_idx = 0; az_idx < cfg->az_steps; az_idx++) {
            float azimuth = cfg->az_start + az_idx * az_step;

            /* Move stepper to azimuth */
            motor_move_to_deg(azimuth, STEPPER_SCAN_RPM);
            while (!motor_at_target()) {
                delay_ms(1);
            }

            /* Settle time for vibration */
            delay_ms(50);

            /* Read OPT3001 lux */
            float lux = 0;
            opt3001_read_lux(&lux);
            lux -= buf->ambient_lux;
            if (lux < 0) lux = 0;

            /* Read TCS34725 color */
            uint16_t r, g, b, c;
            tcs34725_read_rgbc(&r, &g, &b, &c);

            /* Compute candela: I = E × r² × cal_factor */
            float cd = lux * SENSOR_RADIUS_SQ * g_cal_factor;

            /* Compute CCT/Duv */
            float cct_k = 0, duv = 0, x = 0, y = 0;
            color_compute_cct_duv(r, g, b, c, &cct_k, &duv, &x, &y);

            /* Store sample */
            if (buf->n_samples < MAX_SAMPLES_TOTAL) {
                photo_sample_t *s = &buf->samples[buf->n_samples++];
                s->azimuth_deg = azimuth;
                s->elevation_deg = elevation;
                s->lux = lux;
                s->candela = cd;
                s->r = r; s->g = g; s->b = b; s->c = c;
                s->cct_k = cct_k;
                s->duv = duv;
                s->x = x; s->y = y;
            }

            /* Update display during scan */
            sh1106_draw_scanning(buf, azimuth, elevation, battery_read_pct());

            /* Send live data via BLE */
            if (buf->n_samples % 10 == 0) {
                ble_bridge_send_scan_data(buf);
            }
        }
    }

    motor_enable(false);
    servo_set_elevation(0.0f);  /* return to equator */
    delay_ms(300);

    LOGI(TAG, "Scan complete: %d samples", buf->n_samples);

    /* Compute photometric results */
    goniometry_compute(buf, &g_result);
    g_result.timestamp = buf->timestamp;
    g_result.scan_id = flashlog_get_count();
    g_result.valid = true;

    /* Log to flash */
    flashlog_write_scan(&g_result, buf);

    /* Send results via BLE */
    ble_bridge_send_result(&g_result);
    ble_bridge_send_ies_file(buf);

    g_mode = MODE_RESULTS;
    LOGI(TAG, "Flux: %.1f lm, Peak: %.0f cd, Beam: %.1f°",
         g_result.luminous_flux_lm, g_result.peak_candela,
         g_result.beam_angle_fwhm);
}

/* ── Calibration mode ──────────────────────────────────────────────── */

static void run_calibration(void)
{
    scan_config_t cal_cfg = {
        .type = SCAN_TYPE_A,
        .az_steps = 360, .el_steps = 1,
        .az_start = 0, .az_end = 360,
        .el_start = 90, .el_end = 90,
        .step_deg = 1.0f,
    };

    sh1106_draw_idle();  /* TODO: calibration prompt */

    LOGI(TAG, "Starting calibration scan with reference lamp");
    LOGI(TAG, "Expected flux: 1000.0 lm (reference)");

    scan_buffer_t cal_buf;
    run_scan(&cal_cfg, &cal_buf);

    /* Compute measured flux (without current cal factor) */
    float old_factor = g_cal_factor;
    g_cal_factor = 1.0f;
    photo_result_t cal_result;
    goniometry_compute(&cal_buf, &cal_result);
    g_cal_factor = old_factor;

    if (cal_result.luminous_flux_lm > 0) {
        float new_factor = 1000.0f / cal_result.luminous_flux_lm;
        g_cal_factor = new_factor;
        LOGI(TAG, "Calibration factor: %.4f (was %.4f)", new_factor, old_factor);
        LOGI(TAG, "Measured: %.1f lm → calibrated to 1000.0 lm",
             cal_result.luminous_flux_lm);
    } else {
        LOGE(TAG, "Calibration failed: no valid flux reading");
    }

    g_mode = MODE_IDLE;
}

/* ── Main loop ─────────────────────────────────────────────────────── */

int main(void)
{
    /* HAL init: clock, GPIO, timers, I2C, SPI, USART, ADC */
    hal_init();

    LOGI(TAG, "=== Lumen Cast — Pocket Goniophotometer ===");
    LOGI(TAG, "STM32G491RET6 @ 170 MHz, %s", __DATE__);

    /* Initialize peripherals */
    ws2812_init();
    sh1106_init();
    motor_init();
    servo_init();
    opt3001_init();
    tcs34725_init();
    ds3231_init();
    flashlog_init();
    ble_bridge_init();

    /* Load calibration factor from flash */
    /* (stored in last flash sector by flashlog module) */
    g_cal_factor = flashlog_load_cal_factor();
    LOGI(TAG, "Cal factor: %.4f", g_cal_factor);

    ws2812_set(0, 8, 0);  /* dim green = ready */
    sh1106_draw_idle();

    g_mode = MODE_IDLE;

    /* ── Super-loop ── */
    while (1) {
        buttons_poll();
        ble_bridge_poll();

        switch (g_mode) {
        case MODE_IDLE:
            sh1106_draw_idle();
            if (g_scan_trigger) {
                g_scan_trigger = false;
                g_mode = MODE_HOMING;
                run_scan(&s_config, &g_scan);
            }
            break;

        case MODE_RESULTS:
            sh1106_draw_results(&g_result, battery_read_pct());
            if (g_scan_trigger) {
                g_scan_trigger = false;
                g_mode = MODE_IDLE;
            }
            break;

        case MODE_CALIBRATION:
            run_calibration();
            break;

        case MODE_HOMING:
        case MODE_SCANNING:
        case MODE_REVIEW:
        case MODE_SETTINGS:
            /* handled by scan state machine or sub-loops */
            break;
        }

        delay_ms(50);  /* 20 Hz main loop */
    }
}