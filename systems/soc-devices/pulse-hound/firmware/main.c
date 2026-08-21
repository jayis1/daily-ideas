/*
 * Pulse Hound — RF Signal Hunter
 * ESP32-S3-WROOM-1 Firmware
 *
 * main.c — Application entry point, FreeRTOS task creation,
 *          mode state machine, main scheduler loop
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "rf_detector.h"
#include "spectrum.h"
#include "direction.h"
#include "classifier.h"
#include "audio.h"
#include "display.h"
#include "ble_stream.h"
#include "sd_logger.h"
#include "power.h"

#include <math.h>
#include <string.h>
#include <stdio.h>

/* ---- Platform HAL stubs (implemented by ESP-IDF port layer) ---- */
extern void hal_init(void);
extern void gpio_set(int pin, int val);
extern int  gpio_read(int pin);
extern void delay_ms(uint32_t ms);
extern uint32_t rtc_get_time_s(void);
extern uint32_t rtc_get_time_ms(void);
extern void i2c_init(int port, int sda, int scl, int freq_hz);
extern int  i2c_write(uint8_t addr, const uint8_t *data, uint8_t len);
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len);
extern void spi_init(int mosi, int miso, int sck, int cs, int freq_hz);
extern int  spi_write_read(const uint8_t *tx, uint8_t *rx, int len);
extern void pwm_set_duty(int gpio, int channel, uint32_t duty);
extern void pwm_set_freq(int channel, uint32_t freq_hz);
extern void enter_light_sleep(uint32_t ms);

/* ---- FreeRTOS task handles (if using ESP-IDF) ---- */
/* In a real ESP-IDF build, these would be TaskHandle_t. */
/* For portability of this source, we use a cooperative scheduler loop. */

/* ---- Global state ---- */
static pulse_hound_mode_t current_mode = MODE_SWEEP;
static pulse_hound_mode_t prev_mode = MODE_SWEEP;
static volatile int mode_changed = 0;

static float current_rssi = RSSI_NOISE_FLOOR_DBM;
static float current_bearing = 0.0f;
static float df_peak_rssi = RSSI_NOISE_FLOOR_DBM;
static int   battery_pct = 100;
static int   audio_enabled = 1;
static int    sensitivity_boost = 0; /* SCAN button long-press → boost */

static uint32_t last_sample_ms = 0;
static uint32_t last_display_ms = 0;
static uint32_t last_power_ms = 0;
static uint32_t last_ble_ms = 0;
static uint32_t last_classify_ms = 0;

/* ---- Mode change callback (from BLE write or button) ---- */
void on_mode_changed(uint8_t new_mode)
{
    if (new_mode <= MODE_POWER_SAVE) {
        prev_mode = current_mode;
        current_mode = (pulse_hound_mode_t)new_mode;
        mode_changed = 1;
    }
}

/* ---- Button handling ---- */
static void handle_buttons(void)
{
    static uint32_t last_btn_check = 0;
    uint32_t now = rtc_get_time_ms();
    if (now - last_btn_check < BTN_DEBOUNCE_MS) return;
    last_btn_check = now;

    /* MODE button: cycle through modes */
    if (gpio_read(BTN_MODE_GPIO) == 0) {
        static int mode_held = 0;
        if (!mode_held) {
            mode_held = 1;
            uint8_t next = (uint8_t)((current_mode + 1) % 4);
            on_mode_changed(next);
        }
    } else {
        /* reset held state handled outside; simplified */
    }

    /* SCAN/SENS button: toggle audio */
    if (gpio_read(BTN_SCAN_GPIO) == 0) {
        audio_enabled = !audio_enabled;
        if (audio_enabled) audio_enable();
        else audio_disable();
        delay_ms(200); /* crude debounce */
    }

    /* DF button: trigger direction finding */
    if (gpio_read(BTN_DF_GPIO) == 0) {
        /* Switch to DF mode temporarily */
        prev_mode = current_mode;
        current_mode = MODE_DF;
        mode_changed = 1;
        delay_ms(200);
    }
}

/* ---- RF sweep task: sample AD8318, push to waterfall ---- */
static void run_rf_sweep(void)
{
    uint32_t now = rtc_get_time_ms();

    uint32_t sample_interval;
    switch (current_mode) {
        case MODE_SWEEP:     sample_interval = 1000U / SWEEP_SAMPLE_RATE_HZ; break; /* 2 ms */
        case MODE_MONITOR:   sample_interval = 20U; break; /* 50 Hz for monitor mode */
        case MODE_POWER_SAVE: sample_interval = 1000U; break; /* 1 Hz */
        default:             sample_interval = 1000U / SWEEP_SAMPLE_RATE_HZ; break;
    }

    if (now - last_sample_ms < sample_interval) return;
    last_sample_ms = now;

    if (!rf_detector_is_powered())
        rf_detector_power_on();

    if (rf_detector_read_rssi_dbm(&current_rssi) == 0) {
        spectrum_push_rssi(current_rssi);
        audio_update(current_rssi);
    }
}

/* ---- Direction finding task ---- */
static void run_direction_finding(void)
{
    if (!power_can_sustain_df()) {
        /* Battery too low for stepper — return to sweep mode */
        current_mode = MODE_SWEEP;
        mode_changed = 1;
        return;
    }

    /* Ensure detector is on */
    if (!rf_detector_is_powered())
        rf_detector_power_on();

    /* Run full 360° sweep (blocking ~30 s) */
    float bearing = 0.0f;
    float peak_rssi = RSSI_NOISE_FLOOR_DBM;

    if (direction_find_bearing(&bearing, &peak_rssi) == 0) {
        current_bearing = bearing;
        df_peak_rssi = peak_rssi;

        /* Log this DF result */
        sd_logger_write(peak_rssi, peak_rssi, (int)classifier_get_current(),
                        bearing, battery_pct, (int)MODE_DF);

        /* Stream over BLE */
        ble_stream_bearing(bearing, peak_rssi);

        /* Audio feedback based on peak RSSI */
        audio_update(peak_rssi);
    }

    /* Return to previous mode after one DF sweep */
    if (current_mode == MODE_DF && prev_mode != MODE_DF) {
        current_mode = prev_mode;
        mode_changed = 1;
    }
}

/* ---- Classification task (every 5 s) ---- */
static void run_classification(void)
{
    uint32_t now = rtc_get_time_ms();
    if (now - last_classify_ms < (CLASS_WINDOW_S * 1000U)) return;
    last_classify_ms = now;

    signal_class_t cls = classifier_run();
    ble_stream_classification(cls);
}

/* ---- Display task (30 FPS) ---- */
static void run_display(void)
{
    uint32_t now = rtc_get_time_ms();
    uint32_t interval = (current_mode == MODE_POWER_SAVE) ? 5000U : (1000U / DISPLAY_FPS);
    if (now - last_display_ms < interval) return;
    last_display_ms = now;

    float peak_rssi = spectrum_get_peak_rssi();
    signal_class_t cls = classifier_get_current();

    display_render(current_rssi, peak_rssi, cls, current_bearing,
                   battery_pct, current_mode, audio_enabled);

    /* Update status LEDs */
    gpio_set(LED_GREEN_GPIO, 1); /* power on */
    if (current_rssi > RSSI_ALARM_DBM)
        gpio_set(LED_RED_GPIO, 1);
    else
        gpio_set(LED_RED_GPIO, 0);

    display_flush();

    /* Peak-hold decay */
    spectrum_peak_hold_decay(1000U / DISPLAY_FPS);
}

/* ---- BLE streaming task (100 ms) ---- */
static void run_ble_stream(void)
{
    uint32_t now = rtc_get_time_ms();
    if (now - last_ble_ms < BLE_NOTIFY_INTERVAL_MS) return;
    last_ble_ms = now;

    if (!ble_stream_is_connected()) return;

    ble_stream_rssi(current_rssi);
    ble_stream_battery(battery_pct);

    /* Stream one waterfall row per interval */
    uint8_t row_data[WATERFALL_COLS];
    spectrum_get_row(0, row_data); /* newest row */
    ble_stream_spectrum_row(row_data, WATERFALL_COLS);
}

/* ---- Power management task (every 60 s) ---- */
static void run_power_mgmt(void)
{
    uint32_t now = rtc_get_time_s();
    if (now - last_power_ms < 60U) return;
    last_power_ms = now;

    power_update();
    battery_pct = power_get_battery_pct();

    /* Enter power-save mode on low battery */
    if (power_is_low_power() && current_mode != MODE_POWER_SAVE) {
        prev_mode = current_mode;
        current_mode = MODE_POWER_SAVE;
        mode_changed = 1;
    }
}

/* ---- Mode transition handling ---- */
static void handle_mode_change(void)
{
    if (!mode_changed) return;
    mode_changed = 0;

    switch (current_mode) {
        case MODE_SWEEP:
            rf_detector_power_on();
            audio_enable();
            display_on();
            break;

        case MODE_DF:
            rf_detector_power_on();
            audio_enable();
            display_on();
            direction_init();
            break;

        case MODE_MONITOR:
            rf_detector_power_on();
            audio_enable();
            display_on();
            spectrum_peak_hold_reset();
            break;

        case MODE_POWER_SAVE:
            /* Reduce sampling, dim display, disable audio */
            audio_disable();
            /* Keep detector on but at 1 Hz (handled by sweep interval) */
            break;
    }
}

/* ---- Main loop ---- */
int main(void)
{
    /* ---- Hardware initialization ---- */
    hal_init();
    i2c_init(I2C_PORT, I2C_SDA_GPIO, I2C_SCL_GPIO, I2C_FREQ_HZ);

    /* ---- Module initialization ---- */
    power_init();
    battery_pct = power_get_battery_pct();

    rf_detector_power_on();
    direction_init();
    audio_init();
    audio_enable();
    display_init();
    spectrum_reset();

    sd_logger_init();
    if (sd_logger_is_present())
        sd_logger_start("/sd/pulse_hound.log");

    ble_stream_init(NULL, on_mode_changed);

    /* Load calibration from NVS (stub — real impl reads NVS) */
    rf_detector_set_calibration(AD8318_SLOPE_MV_PER_DB, AD8318_INTERCEPT_V,
                                AD8318_TEMP_COEFF_MV_PER_C);

    /* Initial state */
    current_mode = MODE_SWEEP;
    audio_enabled = 1;

    /* ---- Main scheduler loop ---- */
    /* In a real ESP-IDF build, these would be separate FreeRTOS tasks.
     * For portability, we run a cooperative scheduler in a single loop. */
    while (1) {
        handle_buttons();
        handle_mode_change();

        switch (current_mode) {
            case MODE_SWEEP:
                run_rf_sweep();
                run_classification();
                break;

            case MODE_DF:
                run_direction_finding();
                /* Still sample during DF for waterfall */
                run_rf_sweep();
                break;

            case MODE_MONITOR:
                run_rf_sweep();
                run_classification();
                break;

            case MODE_POWER_SAVE:
                run_rf_sweep(); /* 1 Hz, handled by interval */
                break;
        }

        run_display();
        run_ble_stream();
        run_power_mgmt();

        /* Yield to let lower-priority tasks run (FreeRTOS task yield) */
        /* In real ESP-IDF: vTaskDelay(pdMS_TO_TICKS(1)) */
        delay_ms(1);
    }

    return 0;
}