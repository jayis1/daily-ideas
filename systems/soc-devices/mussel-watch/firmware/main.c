/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * main.c — Application entry point, cooperative scheduler, state machine
 *
 * The firmware uses a cooperative super-loop scheduler (no RTOS) for
 * portability. The main loop runs at the sample rate (default 4 Hz gape
 * sampling, but the "sample interval" controls how often the full
 * sample+process cycle runs; between cycles the device sleeps).
 *
 * Task schedule (every sample_interval_s seconds):
 *   1. Wake from sleep
 *   2. Power on sensor head
 *   3. Sample gape angles (all mussels)
 *   4. Run anomaly detection on gape data
 *   5. Every uplink_interval_s: sample water quality, build + TX LoRa packet
 *   6. Every log_interval_s: append SD card log line
 *   7. Power manage (read battery/solar)
 *   8. Check BLE commands
 *   9. Sleep until next sample
 *
 * Alert uplinks are sent immediately (don't wait for uplink_interval_s).
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "gape_sensor.h"
#include "water_quality.h"
#include "anomaly.h"
#include "lora_uplink.h"
#include "ble_config.h"
#include "logger.h"
#include "power.h"

#include <string.h>
#include <stdio.h>

/* ---- Platform HAL stubs (implemented by nRF SDK port layer) ---- */
extern void hal_init(void);
extern void gpio_set(int pin, int val);
extern int  gpio_read(int pin);
extern void delay_ms(uint32_t ms);
extern void enter_light_sleep(uint32_t ms);
extern uint32_t rtc_get_time_s(void);
extern uint32_t rtc_get_time_ms(void);
extern void i2c_init(int port, int sda, int scl, int freq_hz);
extern int  i2c_write(uint8_t addr, const uint8_t *data, uint8_t len);
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len);
extern void spi_init(int mosi, int miso, int sck, int cs, int freq_hz);
extern int  spi_write_read(const uint8_t *tx, uint8_t *rx, int len);

/* ---- Global state ---- */
static mussel_watch_state_t state;

/* ---- Forward declarations ---- */
static void state_init(mussel_watch_state_t *st);
static void handle_mode_button(mussel_watch_state_t *st);
static void blink_led(int pin, int count, int delay);

/* ============================================================
 * Main entry
 * ============================================================ */

int main(void)
{
    /* Hardware abstraction layer init (clocks, GPIO, RTC, SAADC) */
    hal_init();

    /* Initialize global state with defaults */
    state_init(&state);

    /* Power on sensor head */
    gpio_set(PIN_SENSOR_PWR, 1);
    delay_ms(100);

    /* Initialize I²C bus (100 kHz for sensors) */
    i2c_init(0, PIN_I2C_SDA, PIN_I2C_SCL, 100000);

    /* Initialize SPI bus (for SX1262 + SD card, 8 MHz) */
    spi_init(PIN_SPI_MOSI, PIN_SPI_MISO, PIN_SPI_SCK, PIN_SX1262_CS, 8000000);

    /* Initialize subsystems */
    gape_sensor_init();
    water_quality_init();
    anomaly_init(&state);
    lora_init();
    power_init();
    logger_init();

    /* Try to load calibration from flash */
    if (gape_cal_load(&state) < 0) {
        /* No calibration stored — enter calibrate mode */
        state.mode = MODE_CALIBRATE;
        blink_led(PIN_LED_BLUE, 5, 200);  /* signal: needs calibration */
    }

    /* Initialize BLE (always available for configuration) */
    ble_config_init(&state);
    ble_config_start_advertising();

    /* Signal successful boot */
    blink_led(PIN_LED_BLUE, 2, 100);

    /* ---- Main scheduler loop ---- */
    while (1) {
        uint32_t now = rtc_get_time_ms();

        /* Check mode button (debounced) */
        handle_mode_button(&state);

        /* Check for BLE commands (calibration, config changes) */
        ble_config_poll(&state);

        /* If in calibrate mode, just stream live gape data over BLE
         * and skip the normal sampling cycle */
        if (state.mode == MODE_CALIBRATE) {
            gape_sample_all(&state);
            ble_config_update_notify(&state);
            delay_ms(500);  /* 2 Hz in calibrate mode */
            continue;
        }

        /* ---- Normal sampling cycle ---- */

        /* 1. Sample gape angles for all mussels */
        gape_sample_all(&state);

        /* 2. Run anomaly detection on gape data */
        alert_code_t gape_alert = anomaly_update(&state, now);

        /* 3. Check if it's time for a full water-quality sample + uplink */
        if ((now - state.last_uplink_ms) >= (uint32_t)state.uplink_interval_s * 1000) {
            /* Sample water quality (temperature, DO, depth) */
            water_quality_sample_all(&state);

            /* Check water-quality anomalies */
            alert_code_t wq_alert = anomaly_check_water_quality(&state);

            /* Update rhythm profile */
            anomaly_update_rhythm(&state, now);

            /* Determine if we need an immediate alert uplink */
            int immediate = (gape_alert != ALERT_NONE || wq_alert != ALERT_NONE) ? 1 : 0;

            /* Build + transmit LoRa packet */
            lora_uplink(&state, immediate);

            /* If alert, log it */
            if (immediate && state.current_alert != ALERT_NONE) {
                logger_log_alert(&state, state.current_alert, rtc_get_time_s());
            }

            state.last_uplink_ms = now;
        }

        /* 4. Check if it's time for an SD card log entry */
        if ((now - state.last_log_ms) >= (uint32_t)state.log_interval_s * 1000) {
            logger_log(&state, rtc_get_time_s());
            state.last_log_ms = now;
        }

        /* 5. Power management (battery + solar) */
        power_manage(&state);

        /* 6. Update BLE notifications (if connected) */
        ble_config_update_notify(&state);

        /* 7. Compute sleep duration until next sample */
        uint32_t sleep_ms = (uint32_t)state.sample_interval_s * 1000;

        /* If alert is active, shorten sleep to catch rapid changes */
        if (state.current_alert != ALERT_NONE) {
            sleep_ms = 5000;  /* 5 seconds during active alert */
        }

        /* 8. Enter low-power sleep */
        state.last_sample_ms = now;
        power_enter_sleep(sleep_ms);
    }

    return 0;  /* never reached */
}

/* ============================================================
 * State initialization
 * ============================================================ */

static void state_init(mussel_watch_state_t *st)
{
    memset(st, 0, sizeof(*st));

    st->mode = MODE_NORMAL;
    st->n_mussels = 1;  /* default: single mussel */
    st->sample_interval_s = DEFAULT_SAMPLE_INTERVAL_S;
    st->uplink_interval_s = DEFAULT_UPLINK_INTERVAL_S;
    st->log_interval_s = DEFAULT_LOG_INTERVAL_S;
    st->gape_threshold_deg = GAPE_CLOSED_THRESHOLD;
    st->closure_duration_s = SUSTAINED_CLOSURE_ALERT_S;
    st->deployment_id = 0x01;
    st->battery_pct = 100;
    st->battery_v = 4.0f;
    st->boot_time_ms = rtc_get_time_ms();
    st->current_alert = ALERT_NONE;
    st->prev_temp_c = -999.0f;

    for (int i = 0; i < MAX_MUSSELS; i++) {
        st->gape_angle[i] = -1.0f;
        st->cal_valid[i] = 0;
    }
}

/* ============================================================
 * Mode button handler
 * ============================================================ */

static void handle_mode_button(mussel_watch_state_t *st)
{
    static uint32_t last_press_ms = 0;
    static int btn_held = 0;
    uint32_t now = rtc_get_time_ms();

    int btn = gpio_read(PIN_MODE_BTN);

    if (btn == 0 && !btn_held) {
        /* Button pressed (active low) */
        btn_held = 1;
        last_press_ms = now;
    } else if (btn == 1 && btn_held) {
        /* Button released */
        btn_held = 0;
        uint32_t dur = now - last_press_ms;

        if (dur > 2000) {
            /* Long press (>2s): toggle calibrate mode */
            if (st->mode == MODE_CALIBRATE) {
                st->mode = MODE_NORMAL;
                blink_led(PIN_LED_BLUE, 3, 100);  /* exit calibrate */
            } else {
                st->mode = MODE_CALIBRATE;
                blink_led(PIN_LED_BLUE, 5, 100);  /* enter calibrate */
            }
        } else if (dur > 50) {
            /* Short press: cycle number of active mussel heads (1→2→3→4→1) */
            st->n_mussels++;
            if (st->n_mussels > MAX_MUSSELS) st->n_mussels = 1;
            blink_led(PIN_LED_BLUE, st->n_mussels, 150);
        }
    }
}

/* ============================================================
 * LED blink helper
 * ============================================================ */

static void blink_led(int pin, int count, int delay)
{
    for (int i = 0; i < count; i++) {
        gpio_set(pin, 1);
        delay_ms(delay);
        gpio_set(pin, 0);
        delay_ms(delay / 2);
    }
}