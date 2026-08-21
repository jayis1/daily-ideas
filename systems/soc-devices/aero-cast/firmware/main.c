/* main.c — Aero Cast main entry point
 *
 * Core 0: ultrasonic measurement loop (20 Hz), wind computation, turbulence
 * Core 1: UI (buttons, OLED), SD logging, BLE bridge communication
 *
 * The two cores communicate via a shared volatile sample buffer protected
 * by a spinlock.
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/watchdog.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"

#include "sdkconfig.h"
#include "sonic.h"
#include "wind.h"
#include "bme280.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "ui.h"
#include "calibration.h"

/* Shared state between cores (protected by spinlock) */
static spin_lock_t *sample_lock;

typedef struct {
    sonic_sample_t  sonic;
    wind_vector_t    wind;
    bme280_data_t    atm;
    turbulence_stats_t turb;
    float max_gust;
    float max_gust_dir;
    uint32_t avg_count;
    float avg_speed_sum;
    float avg_dir_x_sum;  /* for circular averaging */
    float avg_dir_y_sum;
    uint32_t sample_count;
    uint32_t window_start_us;
} shared_state_t;

static shared_state_t shared;

static void shared_lock(void)   { spin_lock_blocking(sample_lock); }
static void shared_unlock(void) { spin_unlock(sample_lock); }

/* ---- Core 1: UI + SD + BLE ---- */

static void core1_main(void)
{
    /* Initialize peripherals on core 1 */
    display_init();
    sd_init();
    ble_bridge_init();

    /* Try to open SD log */
    bool sd_ok = sd_open_log();
    if (!sd_ok) {
        printf("[core1] SD logging unavailable, continuing without\n");
    }

    uint32_t last_display_us = 0;
    uint32_t last_atm_us = 0;
    bme280_data_t atm_local;

    while (1) {
        /* Poll buttons */
        ui_poll();

        /* Read BME280 every 1 second */
        uint32_t now = time_us_32();
        if (now - last_atm_us > 1000000) {
            bme280_read(&atm_local);
            shared_lock();
            memcpy(&shared.atm, &atm_local, sizeof(atm_local));
            shared_unlock();
            last_atm_us = now;
        }

        /* Update display at 5 Hz */
        if (now - last_display_us > 200000) {
            last_display_us = now;

            shared_lock();
            wind_vector_t wind_cpy = shared.wind;
            bme280_data_t atm_cpy = shared.atm;
            turbulence_stats_t turb_cpy = shared.turb;
            float gust_cpy = shared.max_gust;
            float gust_dir_cpy = shared.max_gust_dir;
            uint32_t avg_n = shared.avg_count;
            float spd_sum = shared.avg_speed_sum;
            float dx_sum = shared.avg_dir_x_sum;
            float dy_sum = shared.avg_dir_y_sum;
            uint32_t elapsed = (now - shared.window_start_us) / 1000000;
            shared_unlock();

            ui_mode_t mode = ui_get_mode();

            switch (mode) {
            case UI_MODE_WIND:
                display_show_wind(&wind_cpy, &atm_cpy, gust_cpy);
                break;
            case UI_MODE_GUST:
                display_show_gust(gust_cpy, gust_dir_cpy, &wind_cpy);
                break;
            case UI_MODE_FLUX:
                display_show_flux(&turb_cpy, elapsed);
                break;
            case UI_MODE_PROFILE: {
                float avg_spd = (avg_n > 0) ? spd_sum / avg_n : 0.0f;
                float avg_dir = (avg_n > 0) ? atan2f(dx_sum, dy_sum) * 180.0f / M_PI : 0.0f;
                if (avg_dir < 0) avg_dir += 360.0f;
                display_show_profile(avg_spd, avg_dir, avg_n);
                break;
            }
            case UI_MODE_CALIB:
                display_show_status("CAL MODE");
                break;
            case UI_MODE_STREAM:
                display_show_status("STREAMING");
                break;
            default:
                display_show_wind(&wind_cpy, &atm_cpy, gust_cpy);
                break;
            }
        }

        /* Log to SD if in wind/flux/profile mode */
        if (sd_ok) {
            static uint32_t last_log_us = 0;
            if (now - last_log_us > (1000000 / SAMPLE_RATE_HZ)) {
                last_log_us = now;
                shared_lock();
                sonic_sample_t sonic_cpy = shared.sonic;
                wind_vector_t wind_cpy2 = shared.wind;
                bme280_data_t atm_cpy2 = shared.atm;
                shared_unlock();
                sd_log_wind(&sonic_cpy, &wind_cpy2, &atm_cpy2);
            }
        }

        /* Stream over BLE if connected */
        static uint32_t last_ble_us = 0;
        if (now - last_ble_us > (1000000 / SAMPLE_RATE_HZ)) {
            last_ble_us = now;
            shared_lock();
            wind_vector_t wind_ble = shared.wind;
            bme280_data_t atm_ble = shared.atm;
            uint32_t ts = shared.sonic.timestamp_us;
            shared_unlock();
            ble_send_wind(&wind_ble, &atm_ble, ts);
        }

        /* Poll for BLE commands */
        uint8_t cmd, arg[64], arg_len;
        if (ble_poll_command(&cmd, arg, &arg_len)) {
            switch (cmd) {
            case 0x01:  /* set mode */
                if (arg_len >= 1) {
                    int m = arg[0];
                    if (m >= 0 && m < UI_MODE_NUM) {
                        /* Directly set mode — needs a way to force mode */
                        printf("[ble] set mode %d\n", m);
                    }
                }
                break;
            case 0x02:  /* start calibration */
                printf("[ble] start calibration\n");
                ble_send_status("CAL START");
                break;
            case 0x03:  /* set sample rate */
                if (arg_len >= 1) {
                    printf("[ble] sample rate %d\n", arg[0]);
                    ble_send_status("RATE SET");
                }
                break;
            default:
                break;
            }
        }

        /* Check power button hold for shutdown */
        if (ui_power_held()) {
            display_show_status("POWER OFF");
            sleep_ms(500);
            /* In a real device, cut power via a load switch.
             * For now, enter deep sleep. */
            ble_send_status("SHUTDOWN");
            sd_close_log();
            /* Pull a GPIO to disable the load switch */
            /* For this reference, just halt. */
            while (1) sleep_ms(1000);
        }

        sleep_ms(5);  /* yield */
    }
}

/* ---- Core 0: measurement loop ---- */

static void core0_main(void)
{
    /* Initialize measurement subsystems on core 0 */
    sonic_init();
    bme280_init();
    cal_init();
    wind_init();

    /* Initialize turbulence accumulator */
    turb_init(&shared.turb);
    shared.window_start_us = time_us_32();
    shared.max_gust = 0.0f;
    shared.max_gust_dir = 0.0f;
    shared.avg_count = 0;
    shared.avg_speed_sum = 0.0f;
    shared.avg_dir_x_sum = 0.0f;
    shared.avg_dir_y_sum = 0.0f;
    shared.sample_count = 0;

    uint32_t period_us = 1000000 / SAMPLE_RATE_HZ;
    uint32_t next_wakeup = time_us_32();

    printf("[core0] measurement loop started at %d Hz\n", SAMPLE_RATE_HZ);

    while (1) {
        /* Measure */
        sonic_sample_t sample;
        bool ok = sonic_measure(&sample);

        if (ok) {
            /* Compute wind vector */
            wind_vector_t wind;
            wind_compute(&sample, &wind);

            /* Update shared state */
            shared_lock();
            shared.sonic = sample;
            shared.wind = wind;
            shared_unlock();

            /* Track gust */
            if (wind.speed > shared.max_gust) {
                shared.max_gust = wind.speed;
                shared.max_gust_dir = wind.direction;
            }

            /* Turbulence accumulation */
            turb_add(&shared.turb, &wind);

            /* Profile averaging */
            shared.avg_count++;
            shared.avg_speed_sum += wind.speed;
            float dir_rad = wind.direction * M_PI / 180.0f;
            shared.avg_dir_x_sum += sinf(dir_rad);
            shared.avg_dir_y_sum += cosf(dir_rad);
            shared.sample_count++;

            /* Check if averaging window elapsed */
            uint32_t now = time_us_32();
            uint32_t elapsed = now - shared.window_start_us;
            if (elapsed >= ui_avg_seconds() * 1000000) {
                /* Finalize turbulence stats */
                turb_finalize(&shared.turb);

                /* Send turbulence stats over BLE */
                ble_send_turbulence(&shared.turb, elapsed / 1000000);

                /* Log turbulence stats to SD */
                sd_log_turbulence(&shared.turb, elapsed / 1000000);

                /* Reset accumulators */
                turb_init(&shared.turb);
                shared.avg_count = 0;
                shared.avg_speed_sum = 0.0f;
                shared.avg_dir_x_sum = 0.0f;
                shared.avg_dir_y_sum = 0.0f;
                shared.window_start_us = now;
            }

        } else {
            /* Measurement failed — log error */
            static uint32_t err_count = 0;
            err_count++;
            if (err_count % 100 == 0) {
                printf("[core0] measurement failed (%lu times)\n", err_count);
            }
        }

        /* Sleep until next sample period */
        next_wakeup += period_us;
        uint32_t now = time_us_32();
        int32_t sleep_us = (int32_t)(next_wakeup - now);
        if (sleep_us > 0 && sleep_us < period_us) {
            sleep_us(sleep_us);
        } else {
            /* We fell behind — reset schedule */
            next_wakeup = now + period_us;
        }
    }
}

int main(void)
{
    /* Set system clock to 125 MHz (default for RP2040) */
    set_sys_clock_khz(125000, true);

    stdio_init_all();

    /* Wait for USB serial to be ready (if connected) */
    sleep_ms(500);

    printf("\n[Aero Cast] Booting...\n");
    printf("[Aero Cast] RP2040 3-axis ultrasonic anemometer\n");

    /* Initialize ADC for battery monitoring */
    adc_init();
    adc_gpio_init(PIN_ADC_BATT);

    /* Initialize UI buttons */
    ui_init();

    /* Initialize status LEDs */
    gpio_init(PIN_LED_STATUS);
    gpio_set_dir(PIN_LED_STATUS, GPIO_OUT);
    gpio_init(PIN_LED_DATA);
    gpio_set_dir(PIN_LED_DATA, GPIO_OUT);

    /* Allocate spinlock for shared state */
    sample_lock = spin_lock_init(31);  /* use last spinlock ID */

    /* Launch core 1 */
    multicore_launch_core1(core1_main);

    /* Run core 0 main loop */
    core0_main();

    return 0;
}