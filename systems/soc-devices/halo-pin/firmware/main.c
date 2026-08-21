/*
 * main.c — Halo Pin pocket optical particle counter
 *
 * Top-level state machine + main loop. Wires together all modules:
 *   laser       — 650 nm laser-diode current control + power monitor
 *   airflow     — blower PWM + flow-rate monitor (SDP810)
 *   adc         — 500 ksps photodiode sampling via DMA + circular buffer
 *   pulse       — pulse detection, peak extraction, size binning
 *   calibration — PSL sphere calibration → pulse-height → size-bin mapping
 *   concentration — number conc. (#/L) + mass conc. (µg/m³) per channel
 *   ambient     — SHT45 temperature/humidity + BME280 pressure for mass correction
 *   display     — SH1106 OLED: histogram, PM2.5/PM10, flow, battery
 *   sd_log      — microSD CSV logging (per-sample + per-minute summary)
 *   ble_bridge  — UART protocol to ESP32-C3 (BLE GATT server)
 *   battery     — 18650 voltage monitor
 *   ui          — button + rotary encoder navigation
 *
 * Main loop runs at ~10 kHz: poll UI, ADC ISR pushes pulses via queue,
 * concentration updated every 1 s, display at 5 Hz, BLE at 1 Hz, SD every 60 s.
 */

#include "stm32g474_conf.h"
#include "laser.h"
#include "airflow.h"
#include "adc.h"
#include "pulse.h"
#include "calibration.h"
#include "concentration.h"
#include "ambient.h"
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
    ST_SAMPLING,
    ST_CALIBRATION,
    ST_REPORT,
    ST_STOP,
} state_t;

static state_t  state = ST_IDLE;
static uint32_t sys_ms = 0;
static uint32_t last_conc_ms = 0;
static uint32_t last_ble_ms = 0;
static uint32_t last_disp_ms = 0;
static uint32_t last_sd_ms = 0;
static uint32_t sample_start_ms = 0;

/* Running counts per channel (since last 1 s update) */
static uint32_t chan_counts[NUM_CHANNELS];
static uint32_t total_counts = 0;
static float    flow_lpm = 0.0f;
static float    pm25_ugm3 = 0.0f;
static float    pm10_ugm3 = 0.0f;
static float    pm1_ugm3 = 0.0f;
static float    temp_c = 0.0f;
static float    rh_pct = 0.0f;
static float    pres_hpa = 0.0f;

/* Cumulative for minute summary */
static uint32_t minute_counts[NUM_CHANNELS];
static uint32_t minute_total = 0;
static uint16_t sample_id = 1;

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

void SysTick_Handler(void) { sys_ms++; }

/* Called from ADC DMA half/full interrupt context via pulse_detect() */
static void on_pulse(uint8_t bin, float peak_v)
{
    if (bin < NUM_CHANNELS) {
        chan_counts[bin]++;
        total_counts++;
    }
}

static void reset_counts(void)
{
    memset(chan_counts, 0, sizeof(chan_counts));
    total_counts = 0;
}

static void start_sampling(void)
{
    if (!battery_ok()) {
        display_show_message("Battery low", "charge first");
        return;
    }
    laser_on();
    airflow_start();
    /* Let flow stabilize + purge cell */
    display_show_message("PURGING...", " ");
    for (volatile int i = 0; i < 3000000; ++i) ;   /* ~0.3 s */
    reset_counts();
    sample_start_ms = sys_ms;
    last_conc_ms = sys_ms;
    last_sd_ms = sys_ms;
    memset(minute_counts, 0, sizeof(minute_counts));
    minute_total = 0;
    adc_start_sampling(on_pulse);
    state = ST_SAMPLING;
    display_show_message("SAMPLING", " ");
}

static void stop_sampling(void)
{
    adc_stop_sampling();
    laser_off();
    airflow_stop();
    state = ST_IDLE;
    display_show_message("STOPPED", "idle");
}

static void update_concentration(void)
{
    float dt = (float)(sys_ms - last_conc_ms) / 1000.0f;
    if (dt < 0.5f) return;
    flow_lpm = airflow_read_lpm();
    if (flow_lpm < 0.05f) {
        /* Flow fault — readings invalid */
        pm1_ugm3 = pm25_ugm3 = pm10_ugm3 = -1.0f;
        last_conc_ms = sys_ms;
        reset_counts();
        return;
    }
    float flow_lps = flow_lpm / 60.0f;     /* L/s */
    float vol_l = flow_lps * dt;          /* volume sampled this interval */

    /* Read ambient for mass-concentration correction */
    ambient_read(&temp_c, &rh_pct, &pres_hpa);

    /* Compute number concentration (#/L) and mass (µg/m³) */
    concentration_compute(chan_counts, vol_l, temp_c, rh_pct,
                          &pm1_ugm3, &pm25_ugm3, &pm10_ugm3);

    /* Accumulate minute summary */
    for (int i = 0; i < NUM_CHANNELS; ++i)
        minute_counts[i] += chan_counts[i];
    minute_total += total_counts;

    reset_counts();
    last_conc_ms = sys_ms;

    /* Minute summary to SD */
    if (sys_ms - last_sd_ms >= 60000) {
        float dt_min = (float)(sys_ms - last_sd_ms) / 1000.0f;
        float vol_min = flow_lpm / 60.0f * dt_min;
        sd_log_minute(sample_id, dt_min, vol_min, flow_lpm,
                       temp_c, rh_pct, pres_hpa,
                       minute_counts, NUM_CHANNELS,
                       pm1_ugm3, pm25_ugm3, pm10_ugm3);
        sd_log_flush();
        sample_id++;
        memset(minute_counts, 0, sizeof(minute_counts));
        minute_total = 0;
        last_sd_ms = sys_ms;
    }
}

static void run_calibration(void)
{
    /* PSL calibration: user inserts a known-size PSL aerosol;
       device records peak-height distribution and maps bins. */
    if (!battery_ok()) {
        display_show_message("Battery low", "charge first");
        return;
    }
    laser_on();
    airflow_start();
    calibration_start();
    adc_start_sampling(on_pulse);
    state = ST_CALIBRATION;
    display_show_message("CALIB", "PSL flow");
}

static void finish_calibration(void)
{
    adc_stop_sampling();
    laser_off();
    airflow_stop();
    calibration_finish();
    state = ST_IDLE;
    display_show_message("CALIB", "done");
}

int main(void)
{
    SystemInit();

    display_init();
    laser_init();
    airflow_init();
    adc_init();
    pulse_init();
    calibration_init();
    concentration_init();
    ambient_init();
    sd_log_init();
    ble_bridge_init();
    battery_init();
    ui_init();

    display_show_message("HALO PIN", "v1.0 ready");
    for (volatile int i = 0; i < 5000000; ++i) ;   /* splash ~0.5 s */

    state = ST_MENU;

    while (1) {
        ui_poll();

        /* Check for BLE command */
        char cmd[32];
        if (ble_bridge_poll_cmd(cmd, sizeof(cmd))) {
            if (strncmp(cmd, "START", 5) == 0)      start_sampling();
            else if (strncmp(cmd, "STOP", 4) == 0)  stop_sampling();
            else if (strncmp(cmd, "CALIB", 5) == 0) run_calibration();
            else if (strncmp(cmd, "ZERO", 4) == 0)  { /* zero-air filter test */
                airflow_start(); laser_on(); adc_start_sampling(on_pulse);
                state = ST_SAMPLING; display_show_message("ZERO AIR", " ");
            }
        }

        if (ui_scan_pressed()) {
            if (state == ST_IDLE || state == ST_MENU || state == ST_REPORT) {
                start_sampling();
            }
        }
        if (ui_mode_pressed()) {
            if (state == ST_SAMPLING) stop_sampling();
        }
        if (ui_select_pressed()) {
            if (state == ST_MENU) {
                switch (ui_current()) {
                    case UI_SAMPLE:  start_sampling(); break;
                    case UI_CALIB:   run_calibration(); break;
                    case UI_ZERO:    /* HEPA zero test */
                        airflow_start(); laser_on(); adc_start_sampling(on_pulse);
                        state = ST_SAMPLING;
                        display_show_message("ZERO AIR TEST", " ");
                        break;
                    default: break;
                }
            } else if (state == ST_CALIBRATION) {
                finish_calibration();
            }
        }

        /* Concentration update @ ~1 Hz */
        if (state == ST_SAMPLING || state == ST_CALIBRATION) {
            update_concentration();
        }

        /* BLE status push @ 1 Hz */
        if (sys_ms - last_ble_ms >= 1000) {
            last_ble_ms = sys_ms;
            ble_bridge_push_status(battery_read(), state, flow_lpm,
                                   pm1_ugm3, pm25_ugm3, pm10_ugm3,
                                   chan_counts, NUM_CHANNELS);
        }

        /* Display update @ 5 Hz */
        if (sys_ms - last_disp_ms >= 200) {
            last_disp_ms = sys_ms;
            switch (state) {
                case ST_MENU:
                    display_show_menu(ui_current());
                    break;
                case ST_SAMPLING:
                    display_show_sampling(chan_counts, NUM_CHANNELS,
                                           flow_lpm, pm25_ugm3, pm10_ugm3,
                                           battery_read());
                    break;
                case ST_CALIBRATION:
                    display_show_calibration(calibration_counts(),
                                              calibration_current_size());
                    break;
                default: break;
            }
        }

        /* Safety: flow fault / battery low / laser interlock */
        if (state == ST_SAMPLING) {
            if (!laser_ok()) {
                stop_sampling();
                display_show_message("LASER FAULT", "stopped");
            }
            if (flow_lpm > 0.001f && flow_lpm < 0.05f) {
                stop_sampling();
                display_show_message("FLOW FAULT", "check filter");
            }
            if (battery_low()) {
                stop_sampling();
                display_show_message("Battery low", "stopped");
            }
        }
    }
}