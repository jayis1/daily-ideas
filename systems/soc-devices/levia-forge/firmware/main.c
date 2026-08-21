/*
 * Levia Forge — Main Control Loop (Core 0)
 *
 * Reads user input (joystick, encoder, buttons), computes phase
 * patterns, updates the DMA phase buffer, manages safety, display,
 * SD logging, and BLE communication.
 *
 * SPDX-License-Identifier: MIT
 */
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "pico/util/queue.h"
#include "hardware/adc.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/watchdog.h"
#include "hardware/clocks.h"
#include <stdio.h>
#include <string.h>

#include "sdkconfig.h"
#include "phase_engine.h"
#include "phase_compute.h"
#include "transducer_layout.h"
#include "display.h"
#include "tof.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "safety.h"
#include "input.h"

/* ---- Global State ---- */
typedef struct {
    float target_x, target_y, target_z;     /* desired trap position (mm) */
    float actual_x, actual_y, actual_z;     /* smoothed actual position */
    phase_pattern_t pattern;
    int vortex_charge;
    float twin_delta;
    float bend_gradient;
    float transport_progress;
    float transport_speed;                  /* progress per second */
    bool active;                            /* transducers energized */
    bool particle_detected;
    float particle_height_mm;
    int battery_mv;
    float temp_c;
    safety_state_t safety;
    uint32_t uptime_ms;
    bool auto_track_z;
} levia_state_t;

static levia_state_t state;

/* ---- Core 1 entry: phase engine ---- */
void core1_main(void)
{
    /* Core 1 handles the PIO/DMA engine. The phase engine is
     * initialized from Core 0 and the DMA runs autonomously.
     * Core 1 monitors for underrun and manages PIO health. */
    while (true) {
        if (phase_engine_is_underrun()) {
            /* Restart the engine if underrun detected */
            phase_engine_stop();
            busy_wait_ms(1);
            phase_engine_start();
        }
        sleep_ms(10);
    }
}

int main(void)
{
    /* ---- System initialization ---- */
    set_sys_clock_khz(133000, true);

    stdio_init_all();
    adc_init();

    /* Initialize transducer layout */
    transducer_layout_init();
    phase_compute_init();

    /* Initialize peripherals */
    display_init();
    tof_init();
    sd_log_init();
    ble_bridge_init();
    safety_init();
    input_init();

    /* Initialize phase engine */
    phase_engine_init();

    /* Launch Core 1 */
    multicore_launch_core1(core1_main);

    /* Enable hardware watchdog (100 ms timeout) */
    watchdog_enable(WATCHDOG_TIMEOUT_MS, 1);

    /* ---- State initialization ---- */
    memset(&state, 0, sizeof(state));
    state.target_x = 0.0f;
    state.target_y = 0.0f;
    state.target_z = 10.0f;
    state.actual_x = 0.0f;
    state.actual_y = 0.0f;
    state.actual_z = 10.0f;
    state.pattern = PATTERN_POINT;
    state.vortex_charge = 1;
    state.twin_delta = 8.0f;
    state.bend_gradient = 0.02f;
    state.transport_progress = 0.0f;
    state.transport_speed = 0.1f;   /* 10 seconds full sweep */
    state.active = false;
    state.auto_track_z = true;
    state.safety = SAFETY_DISABLED;

    /* ---- Display boot message ---- */
    display_show_boot();
    sleep_ms(1000);

    absolute_time_t last_control = get_absolute_time();
    absolute_time_t last_display = get_absolute_time();
    absolute_time_t last_sd = get_absolute_time();
    absolute_time_t last_ble = get_absolute_time();

    uint32_t frame_count = 0;

    /* ---- Main control loop (50 Hz) ---- */
    while (true) {
        absolute_time_t now = get_absolute_time();
        state.uptime_ms = to_ms_since_boot(now);

        /* ---- 50 Hz control loop ---- */
        if (absolute_time_diff_us(last_control, now) >= (CONTROL_LOOP_PERIOD_MS * 1000)) {
            last_control = now;

            /* 1. Read inputs */
            input_joystick_t joy = input_read_joystick();
            float enc_delta = input_read_encoder_delta();
            bool btn_mode = input_read_button(PIN_BTN_MODE_DEF);
            bool btn_release = input_read_button(PIN_BTN_RELEASE_DEF);

            /* 2. Handle mode button (debounced) */
            static bool mode_was_pressed = false;
            if (btn_mode && !mode_was_pressed) {
                mode_was_pressed = true;
                state.pattern = (phase_pattern_t)((state.pattern + 1) % PATTERN_COUNT);
                if (state.pattern == PATTERN_TRANSPORT)
                    state.transport_progress = 0.0f;
            } else if (!btn_mode) {
                mode_was_pressed = false;
            }

            /* 3. Handle release button */
            if (btn_release) {
                state.active = false;
                phase_engine_set_blank(true);
            }

            /* 4. Update target position from joystick */
            state.target_x += joy.x * 0.5f;   /* 0.5 mm per frame at full deflection */
            state.target_y += joy.y * 0.5f;
            state.target_z += enc_delta * 0.2f;  /* 0.2 mm per encoder detent */

            /* Clamp to working volume */
            if (state.target_x > WORK_VOL_X_MM)  state.target_x = WORK_VOL_X_MM;
            if (state.target_x < -WORK_VOL_X_MM) state.target_x = -WORK_VOL_X_MM;
            if (state.target_y > WORK_VOL_Y_MM)  state.target_y = WORK_VOL_Y_MM;
            if (state.target_y < -WORK_VOL_Y_MM) state.target_y = -WORK_VOL_Y_MM;
            if (state.target_z > WORK_VOL_Z_MAX_MM) state.target_z = WORK_VOL_Z_MAX_MM;
            if (state.target_z < WORK_VOL_Z_MIN_MM) state.target_z = WORK_VOL_Z_MIN_MM;

            /* 5. Smooth actual position (low-pass filter) */
            float alpha = 0.3f;
            state.actual_x += (state.target_x - state.actual_x) * alpha;
            state.actual_y += (state.target_y - state.actual_y) * alpha;
            state.actual_z += (state.target_z - state.actual_z) * alpha;

            /* 6. Read ToF sensor (particle height) */
            float tof_mm = tof_read_distance_mm();
            if (tof_mm > 0 && tof_mm < 70.0f) {
                state.particle_detected = true;
                state.particle_height_mm = tof_mm;
                /* Auto-track Z: adjust target Z to maintain particle height */
                if (state.auto_track_z && state.active) {
                    /* PID-like correction: if particle is too low, raise trap */
                    float height_error = state.actual_z - (70.0f - tof_mm);
                    state.target_z += height_error * 0.05f;
                }
            } else {
                state.particle_detected = false;
                state.particle_height_mm = 0.0f;
            }

            /* 7. Read battery voltage */
            state.battery_mv = input_read_battery_mv();

            /* 8. Read temperature (RP2040 internal) */
            state.temp_c = input_read_temp_c();

            /* 9. Safety checks */
            state.safety = safety_check(&state);
            if (state.safety != SAFETY_OK) {
                state.active = false;
                phase_engine_set_blank(true);
            } else if (!state.active && !btn_release) {
                /* Auto-activate if safety is OK and release not held */
                /* (user must press MODE to activate first time) */
            }

            /* 10. Compute phase pattern */
            if (state.active && state.safety == SAFETY_OK) {
                switch (state.pattern) {
                case PATTERN_POINT:
                    phase_compute_point(state.actual_x, state.actual_y, state.actual_z);
                    break;
                case PATTERN_TWIN:
                    phase_compute_twin(state.actual_x, state.actual_y,
                                       state.actual_z, state.twin_delta);
                    break;
                case PATTERN_VORTEX:
                    phase_compute_vortex(state.actual_x, state.actual_y,
                                         state.actual_z, state.vortex_charge);
                    break;
                case PATTERN_BOTTLE:
                    /* Bottle = twin with negative delta + point overlay.
                     * Simplified: use vortex with ℓ=0 (hollow via twin). */
                    phase_compute_twin(state.actual_x, state.actual_y,
                                       state.actual_z, -state.twin_delta);
                    break;
                case PATTERN_BENDING:
                    phase_compute_bending(state.actual_x, state.actual_y,
                                          state.actual_z, state.bend_gradient);
                    break;
                case PATTERN_TRANSPORT:
                    state.transport_progress += state.transport_speed / CONTROL_LOOP_HZ;
                    if (state.transport_progress > 1.0f)
                        state.transport_progress = 0.0f;
                    phase_compute_transport(state.actual_y, state.actual_z,
                                           state.transport_progress, 12.0f);
                    break;
                default:
                    phase_compute_point(0, 0, 10);
                    break;
                }
                phase_engine_set_blank(false);
            } else {
                phase_engine_set_blank(true);
            }

            frame_count++;
        }

        /* ---- 10 Hz display update ---- */
        if (absolute_time_diff_us(last_display, now) >= 100000) {
            last_display = now;
            display_update(&state);
        }

        /* ---- 10 Hz SD logging ---- */
        if (absolute_time_diff_us(last_sd, now) >= 100000) {
            last_sd = now;
            sd_log_write(&state);
        }

        /* ---- 10 Hz BLE poll ---- */
        if (absolute_time_diff_us(last_ble, now) >= 100000) {
            last_ble = now;
            ble_bridge_poll(&state);
        }

        /* Kick the watchdog */
        watchdog_update();

        /* Small yield to prevent tight-loop issues */
        sleep_ms(1);
    }

    return 0;
}