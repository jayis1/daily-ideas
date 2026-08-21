/*
 * main.c — Helio Tilt tracking pyrheliometer + AOD meter
 *
 * Top-level state machine + main loop. Wires together all modules:
 *   solar_pos    — NOAA/SPA truncated solar position (az/el/air_mass)
 *   gps          — NEO-M9N GPS NMEA parsing (lat/lon/time)
 *   imu          — LSM6DSO + MMC5603NJ fusion (tilt/heading)
 *   stepper      — NEMA8 AZ/EL drive (sun tracking)
 *   filter_wheel — SG90 servo 6-position filter rotation
 *   detector     — ADS122U04 24-bit ADC + thermopile (DNI)
 *   radiometry   — AOD, PWV, Angstrom exponent (Beer-Lambert-Bouguer)
 *   langley      — Langley regression calibration (V0 extraction)
 *   display      — SH1106 OLED: DNI/AOD + sun position
 *   sd_log       — microSD CSV (AERONET-compatible format)
 *   ble_bridge   — UART protocol to ESP32-C3 (BLE GATT server)
 *   battery      — 18650 voltage monitor
 *   ui           — Encoder + buttons + menu
 *
 * Main loop runs at ~1 kHz: poll UI, update tracking at 1 Hz,
 * sweep filter wheel at 0.1 Hz, push to BLE at 10 Hz,
 * log to SD per measurement, run safety checks.
 */

#include "stm32g474_conf.h"
#include "solar_pos.h"
#include "gps.h"
#include "imu.h"
#include "stepper.h"
#include "filter_wheel.h"
#include "detector.h"
#include "radiometry.h"
#include "langley.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "battery.h"
#include "ui.h"
#include <string.h>
#include <stdio.h>

typedef enum {
    ST_IDLE,
    ST_MENU,
    ST_GPS_FIX,         /* Acquire GPS position + time */
    ST_LEVEL,           /* Read IMU, compute tilt + heading */
    ST_HOME,            /* Home AZ + EL steppers */
    ST_TRACK,           /* Point at sun, measure DNI at current filter */
    ST_SWEEP,           /* Rotate filter wheel through 6 wavelengths */
    ST_COMPUTE,         /* Compute AOD, PWV, Angstrom */
    ST_LOG,             /* SD log + BLE stream */
    ST_LANGLEY,         /* Langley calibration run (2-3 hours) */
    ST_ABORT,           /* Error / abort */
} state_t;

static state_t  state = ST_IDLE;
static uint32_t sys_ms = 0;
static uint32_t last_track_ms = 0;
static uint32_t last_ble_ms = 0;
static uint32_t last_log_ms = 0;
static uint32_t last_disp_ms = 0;
static uint32_t state_enter_ms = 0;

/* GPS data */
static gps_data_t gps;

/* IMU tilt */
static imu_tilt_t tilt;

/* Solar position */
static solar_pos_t sun_pos;

/* Latest measurement */
static radiometry_result_t rad_result;
static float voltages_uv[WL_COUNT];
static float v0_cal[WL_COUNT] = {
    1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f
};

/* Langley state */
static uint32_t langley_last_sample_ms = 0;
static langley_result_t langley_result;

/* Settings */
static float pressure_hpa = 1013.25f;   /* Default, from BME280 (future) */
static float ozone_du = OZONE_DEFAULT_DU;
static bool   tracking_active = false;

/* ---- System initialization ---- */
void SystemInit(void)
{
    /* HSI 16 MHz → PLL → 170 MHz SYSCLK */
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) ;
    FLASH->ACR = FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_PRFTEN
               | FLASH_ACR_LATENCY_2WS;
    RCC->PLLCFGR = (RCC->PLLCFGR & ~(RCC_PLLCFGR_PLLM | RCC_PLLCFGR_PLLN
                                     | RCC_PLLCFGR_PLLP | RCC_PLLCFGR_PLLR))
                 | (PLLM_VALUE << RCC_PLLCFGR_PLLM_Pos)
                 | (PLLN_VALUE << RCC_PLLCFGR_PLLN_Pos)
                 | ((PLLP_VALUE - 1) << RCC_PLLCFGR_PLLP_Pos)
                 | RCC_PLLCFGR_PLLREN;
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) ;
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) ;

    /* SysTick 1 kHz */
    SysTick->LOAD = (SYSCLK_FREQ / SYSTICK_HZ) - 1;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk
                  | SysTick_CTRL_TICKINT_Msk;
}

/* ---- SysTick ISR ---- */
volatile uint32_t tick_1k = 0;
void SysTick_Handler(void) { tick_1k++; }

static uint32_t millis(void) { return tick_1k; }

static void delay_ms(uint32_t ms)
{
    uint32_t start = tick_1k;
    while ((tick_1k - start) < ms) ;
}

/* ---- Init all peripherals ---- */
static void init_all(void)
{
    battery_init();
    display_init();
    sd_log_init();
    ble_bridge_init();
    ui_init();
    gps_init();
    imu_init();
    stepper_init();
    filter_wheel_init();
    detector_init();
    langley_reset();

    display_show_splash("Booting...");
}

/* ---- State machine helpers ---- */
static void enter_state(state_t s)
{
    state = s;
    state_enter_ms = millis();
}

/* ---- Track sun: compute position, point steppers ---- */
static int update_tracking(void)
{
    /* Get GPS data */
    gps_get_data(&gps);
    if (!gps.fix_valid || !gps.time_valid) {
        display_show_error("No GPS fix");
        return -1;
    }

    /* Compute solar position */
    int rc = solar_pos_compute(gps.latitude, gps.longitude, gps.elevation_m,
                                gps.year, gps.month, gps.day,
                                gps.hour, gps.min, gps.sec,
                                &sun_pos);
    if (rc < 0) {
        display_show_error("Sun below horizon");
        return -1;
    }

    /* Read IMU for tilt compensation */
    imu_read_fusion(&tilt);

    /* Compute target AZ/EL angles (account for device mounting offset)
     * In production: add tilt.heading offset for device orientation.
     * The azimuth stepper angle = sun_pos.azimuth - heading_offset.
     * The elevation stepper angle = sun_pos.elevation - pitch_offset.
     */
    float target_az = sun_pos.azimuth - tilt.heading;
    if (target_az < 0) target_az += 360.0f;
    float target_el = sun_pos.elevation - tilt.pitch;
    if (target_el < 0) target_el = 0.0f;
    if (target_el > 90.0f) target_el = 90.0f;

    /* Move steppers */
    stepper_move_to(AXIS_AZIMUTH, target_az);
    stepper_move_to(AXIS_ELEVATION, target_el);

    return 0;
}

/* ---- Sweep filter wheel: measure DNI at all 6 wavelengths ---- */
static void sweep_filters(void)
{
    for (uint8_t wl = 0; wl < WL_COUNT; wl++) {
        filter_wheel_set(wl);
        delay_ms(500);   /* Wait for servo to settle + filter change */

        /* Read detector (average 4 samples for noise reduction) */
        detector_reading_t reading;
        detector_read_avg(&reading, 4);
        voltages_uv[wl] = reading.voltage_uv;
    }
}

/* ---- Main loop ---- */
int main(void)
{
    init_all();
    enter_state(ST_IDLE);

    while (1) {
        uint32_t now = millis();
        ui_event_t event = ui_poll();

        /* ---- State machine ---- */
        switch (state) {

        case ST_IDLE:
            if (event == UI_EVENT_START) {
                enter_state(ST_GPS_FIX);
            } else if (event == UI_EVENT_CALIBRATE) {
                langley_reset();
                enter_state(ST_LANGLEY);
            } else if (event == UI_EVENT_MODE) {
                enter_state(ST_MENU);
            }
            if (now - last_disp_ms > 1000) {
                float bat = battery_read();
                display_show_status(0, 0, 0, 0, 0, 0, bat, "IDLE");
                last_disp_ms = now;
            }
            break;

        case ST_MENU:
            /* Simplified menu: encoder scrolls, mode selects */
            {
                const char *items[] = {
                    "Start Tracking",
                    "Langley Cal",
                    "Set Pressure",
                    "Set Ozone",
                    "Mag Calibrate",
                    "Exit"
                };
                static uint8_t sel = 0;
                if (event == UI_EVENT_ENCODER_CW) {
                    if (sel < 5) sel++;
                } else if (event == UI_EVENT_ENCODER_CCW) {
                    if (sel > 0) sel--;
                } else if (event == UI_EVENT_MODE) {
                    switch (sel) {
                    case 0: enter_state(ST_GPS_FIX); break;
                    case 1: langley_reset(); enter_state(ST_LANGLEY); break;
                    case 4: imu_calibrate_mag(); break;
                    default: enter_state(ST_IDLE); break;
                    }
                } else if (event == UI_EVENT_START) {
                    enter_state(ST_IDLE);
                }
                display_show_menu(items, 6, sel);
            }
            break;

        case ST_GPS_FIX:
            display_show_splash("GPS Fix...");
            if (gps_has_fix()) {
                gps_get_data(&gps);
                enter_state(ST_LEVEL);
            } else if (now - state_enter_ms > GPS_FIX_TIMEOUT_S * 1000) {
                display_show_error("GPS timeout");
                delay_ms(2000);
                enter_state(ST_IDLE);
            }
            break;

        case ST_LEVEL:
            display_show_splash("Leveling...");
            imu_read_fusion(&tilt);
            if (tilt.tilt_mag > 10.0f) {
                display_show_error("Tilt > 10deg");
                delay_ms(2000);
                /* Continue anyway — tilt is compensated */
            }
            enter_state(ST_HOME);
            break;

        case ST_HOME:
            display_show_splash("Homing steppers...");
            if (stepper_home(AXIS_AZIMUTH) < 0) {
                display_show_error("AZ home fail");
                delay_ms(2000);
            }
            if (stepper_home(AXIS_ELEVATION) < 0) {
                display_show_error("EL home fail");
                delay_ms(2000);
            }
            filter_wheel_home();
            tracking_active = true;
            enter_state(ST_TRACK);
            break;

        case ST_TRACK:
            /* Update sun tracking at 1 Hz */
            if (now - last_track_ms >= 1000) {
                if (update_tracking() < 0) {
                    /* Sun below horizon or no GPS — keep trying */
                }
                last_track_ms = now;
            }

            /* Sweep filters at 0.1 Hz (every 10 s) */
            if (now - last_log_ms >= 10000) {
                enter_state(ST_SWEEP);
            }

            /* Display + BLE at 10 Hz */
            if (now - last_disp_ms >= 100) {
                float bat = battery_read();
                display_show_tracking(&rad_result, &sun_pos, bat);
                ble_bridge_send_status("TRACK", (float)sun_pos.azimuth,
                                       (float)sun_pos.elevation, bat,
                                       gps_has_fix());
                last_disp_ms = now;
            }

            if (event == UI_EVENT_START) {
                tracking_active = false;
                stepper_stop(AXIS_AZIMUTH);
                stepper_stop(AXIS_ELEVATION);
                enter_state(ST_IDLE);
            }
            break;

        case ST_SWEEP:
            /* Measure DNI at all 6 wavelengths */
            sweep_filters();

            /* Compute AOD, PWV, Angstrom */
            radiometry_compute(&rad_result, voltages_uv, v0_cal,
                               sun_pos.air_mass, sun_pos.zenith,
                               pressure_hpa, ozone_du);
            enter_state(ST_LOG);
            break;

        case ST_LOG:
            /* Log to SD card */
            gps_get_data(&gps);
            sd_log_measurement(&rad_result, &sun_pos,
                               gps.latitude, gps.longitude, gps.elevation_m,
                               25.0f, pressure_hpa,
                               gps.year, gps.month, gps.day,
                               gps.hour, gps.min, gps.sec);

            /* Stream over BLE */
            float bat = battery_read();
            ble_bridge_send_measurement(&rad_result, &sun_pos, bat, "TRACK");

            last_log_ms = millis();
            enter_state(ST_TRACK);
            break;

        case ST_LANGLEY:
            /* Langley calibration: log V(λ) vs air mass every 2 minutes */
            if (update_tracking() >= 0) {
                if (now - langley_last_sample_ms >= LANGLEY_INTERVAL_S * 1000) {
                    /* Sweep filters and log voltages */
                    sweep_filters();
                    langley_add_point(voltages_uv, sun_pos.air_mass);
                    sd_log_langley(voltages_uv, sun_pos.air_mass,
                                   gps.year, gps.month, gps.day,
                                   gps.hour, gps.min, gps.sec);

                    /* Run regression to check quality */
                    langley_regress(&langley_result);
                    display_show_langley(langley_result.num_points,
                                         langley_result.r_squared[WL_870],
                                         langley_result.v0[WL_870]);
                    ble_bridge_send_langley(langley_result.num_points,
                                            langley_result.r_squared[WL_870],
                                            langley_result.v0[WL_870]);
                    langley_last_sample_ms = now;
                }
            }

            /* Check if Langley is complete (enough points + good R²) */
            if (langley_result.valid ||
                (now - state_enter_ms > LANGLEY_DURATION_S * 1000)) {
                if (langley_result.valid) {
                    /* Save V₀ calibration constants */
                    for (int i = 0; i < WL_COUNT; i++)
                        v0_cal[i] = langley_result.v0[i];
                    display_show_splash("Langley OK!");
                    ble_bridge_send_error("Langley calibration complete");
                } else {
                    display_show_error("Langley failed (R2 low)");
                    ble_bridge_send_error("Langley calibration failed");
                }
                delay_ms(3000);
                stepper_stop(AXIS_AZIMUTH);
                stepper_stop(AXIS_ELEVATION);
                enter_state(ST_IDLE);
            }

            if (event == UI_EVENT_START) {
                stepper_stop(AXIS_AZIMUTH);
                stepper_stop(AXIS_ELEVATION);
                enter_state(ST_IDLE);
            }
            break;

        case ST_ABORT:
            stepper_stop(AXIS_AZIMUTH);
            stepper_stop(AXIS_ELEVATION);
            tracking_active = false;
            if (event == UI_EVENT_MODE)
                enter_state(ST_IDLE);
            break;
        }

        /* ---- BLE streaming at 10 Hz ---- */
        if (now - last_ble_ms >= 100) {
            if (state == ST_TRACK && rad_result.valid) {
                float bat = battery_read();
                ble_bridge_send_measurement(&rad_result, &sun_pos,
                                             bat, "TRACK");
            }
            last_ble_ms = now;
        }

        /* ---- Low battery check ---- */
        if (battery_low()) {
            display_show_error("LOW BATTERY");
            if (state == ST_TRACK || state == ST_LANGLEY) {
                stepper_stop(AXIS_AZIMUTH);
                stepper_stop(AXIS_ELEVATION);
                enter_state(ST_IDLE);
            }
        }

        delay_ms(1);   /* ~1 kHz loop rate */
    }
}