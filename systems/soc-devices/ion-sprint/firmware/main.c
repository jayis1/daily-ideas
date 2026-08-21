/*
 * main.c — Ion Sprint pocket capillary electrophoresis + C4D
 *
 * Top-level state machine + main loop. Wires together all modules:
 *   hv_supply    — Cockcroft-Walton 30 kV, PID, ramp, current/voltage monitor
 *   c4d          — C4D AC excitation, ADC capture, lock-in I/Q demodulation
 *   injection    — Electrokinetic / hydrodynamic injection
 *   eph          — Electropherogram: ALS baseline, peak detection, area
 *   library      — 40-ion migration-time library, k-NN identification
 *   quant        — Internal-standard calibration, mM/mg-L conversion
 *   temperature  — DS18B20 BGE temperature, mobility correction
 *   pump         — Peristaltic flush pump
 *   vial_lift    — NEMA8 stepper for hydrodynamic injection
 *   safety       — HW current limit, interlock, bleeder
 *   display      — SH1106 OLED: live electropherogram + peak table
 *   sd_log       — microSD CSV + raw binary electropherogram
 *   ble_bridge   — UART protocol to ESP32-C3 (BLE GATT server)
 *   battery      — 18650 voltage monitor
 *   ui           — Encoder + buttons + menu
 *
 * Main loop runs at ~10 kHz: poll UI, run state machine, push to
 * BLE at 10 Hz, log to SD per run, run safety checks at 1 Hz.
 */

#include "stm32g474_conf.h"
#include "hv_supply.h"
#include "c4d.h"
#include "injection.h"
#include "eph.h"
#include "library.h"
#include "quant.h"
#include "temperature.h"
#include "pump.h"
#include "vial_lift.h"
#include "safety.h"
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
    ST_PRIME,           /* Flush capillary with BGE */
    ST_INJECT,           /* Electrokinetic or hydrodynamic injection */
    ST_SEPARATE,         /* Apply HV, acquire electropherogram */
    ST_IDENTIFY,         /* k-NN library match + quantify */
    ST_REPORT,           /* OLED display, SD log, BLE stream */
    ST_FLUSH,            /* Clean capillary post-run */
    ST_ABORT,            /* HV abort / safety trip */
} state_t;

static state_t  state = ST_IDLE;
static uint16_t run_id = 1;
static uint32_t sys_ms = 0;
static uint32_t last_ble_ms = 0;
static uint32_t last_safety_ms = 0;
static uint32_t last_disp_ms = 0;
static uint32_t state_enter_ms = 0;

/* Settings */
static float    hv_setpoint_kv = 20.0f;     /* Default 20 kV */
static uint8_t  bge_recipe = 0;              /* BGE recipe index (0–7) */
static uint8_t  inj_mode = 0;                /* 0=electrokinetic, 1=hydrodynamic */
static float    inj_duration_s = 2.0f;       /* Injection duration */
static uint16_t run_timeout_s = 600;         /* Max run time (10 min) */

/* Latest run results */
static float    eph_data[EPH_SAMPLES_MAX];   /* Electropherogram buffer */
static uint32_t eph_count = 0;               /* Samples acquired */
static float    run_temp_c = 25.0f;          /* BGE temperature during run */
static float    hv_measured_kv = 0.0f;
static float    hv_current_ua = 0.0f;

/* Peak table (filled by eph module) */
static peak_t   peaks[MAX_PEAKS_PER_RUN];
static uint8_t  peak_count = 0;

/* Identification + quantification results (filled by library + quant) */
static ion_result_t results[MAX_PEAKS_PER_RUN];
static uint8_t  result_count = 0;

void SystemInit(void)
{
    /* Set HSI 16 MHz → PLL → 170 MHz SYSCLK */
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

/* ---- Init all peripherals ---- */
static void init_all(void)
{
    battery_init();
    display_init();
    sd_log_init();
    ble_bridge_init();
    ui_init();
    hv_supply_init();
    c4d_init();
    injection_init();
    eph_init();
    library_init();
    quant_init();
    temperature_init();
    pump_init();
    vial_lift_init();
    safety_init();

    display_show_splash("Ion Sprint v1.0");
}

/* ---- State machine helpers ---- */
static void enter_state(state_t s)
{
    state = s;
    state_enter_ms = millis();
}

static uint32_t time_in_state_s(void)
{
    return (millis() - state_enter_ms) / 1000u;
}

/* ---- Run the separation ---- */
static void do_separate(void)
{
    /* Start C4D acquisition */
    c4d_start_acquisition(eph_data, EPH_SAMPLES_MAX);
    run_temp_c = temperature_read();

    /* Soft-start HV ramp */
    hv_supply_ramp(hv_setpoint_kv, HV_RAMP_TIME_S);

    /* Monitor HV current/voltage during run */
    uint32_t start_ms = millis();
    while (c4d_is_acquiring() && time_in_state_s() < run_timeout_s) {
        hv_measured_kv = hv_supply_read_voltage();
        hv_current_ua  = hv_supply_read_current();

        /* Safety checks */
        if (safety_check(hv_current_ua, hv_measured_kv)) {
            hv_supply_off();
            hv_supply_discharge();
            enter_state(ST_ABORT);
            return;
        }

        /* Update display (electropherogram live view) */
        if (millis() - last_disp_ms > 100) {  /* 10 Hz display */
            uint32_t idx = c4d_get_sample_count();
            display_show_eph_live(eph_data, idx, hv_measured_kv, hv_current_ua);
            last_disp_ms = millis();
        }

        /* Stream over BLE */
        if (millis() - last_ble_ms > 100) {  /* 10 Hz BLE */
            uint32_t idx = c4d_get_sample_count();
            ble_bridge_send_eph_chunk(eph_data, idx, hv_measured_kv, hv_current_ua);
            last_ble_ms = millis();
        }
    }

    /* Stop acquisition, turn off HV, discharge */
    c4d_stop_acquisition();
    eph_count = c4d_get_sample_count();
    hv_supply_off();
    hv_supply_discharge();
}

/* ---- Identify peaks + quantify ---- */
static void do_identify(void)
{
    /* Peak detection */
    peak_count = eph_detect_peaks(eph_data, eph_count, peaks, MAX_PEAKS_PER_RUN);

    /* Temperature correction for migration times */
    float temp_corr = 1.0f + MT_NORM_TEMP_COEF * (run_temp_c - BGE_TEMP_REF_C);

    /* Identify each peak via k-NN library match */
    result_count = 0;
    for (uint8_t i = 0; i < peak_count && i < MAX_PEAKS_PER_RUN; i++) {
        float norm_mt = peaks[i].migration_time * temp_corr;
        int8_t ion_idx = library_identify(norm_mt, peaks[i].skewness,
                                          bge_recipe);
        if (ion_idx >= 0) {
            results[result_count].ion_id = ion_idx;
            strncpy(results[result_count].ion_name,
                    library_get_name(ion_idx), 15);
            results[result_count].migration_time = peaks[i].migration_time;
            results[result_count].area = peaks[i].area;
            results[result_count].height = peaks[i].height;
            /* Quantify via internal-standard response factor */
            results[result_count].concentration_mM =
                quant_compute(ion_idx, peaks[i].area, bge_recipe);
            result_count++;
        }
    }
}

int main(void)
{
    SystemInit();
    init_all();

    for (;;) {
        ui_poll();
        uint32_t now = millis();

        switch (state) {
        case ST_IDLE:
            display_show_idle(hv_setpoint_kv, bge_recipe, inj_mode, battery_read());
            if (ui_button_pressed(BTN_START)) {
                enter_state(ST_PRIME);
            }
            if (ui_button_pressed(BTN_MODE)) {
                enter_state(ST_MENU);
            }
            break;

        case ST_MENU:
            ui_menu_update(&hv_setpoint_kv, &bge_recipe, &inj_mode,
                          &inj_duration_s, &run_timeout_s);
            if (ui_button_pressed(BTN_MODE)) {
                enter_state(ST_IDLE);
            }
            break;

        case ST_PRIME:
            display_show_status("Priming capillary...");
            pump_flush(PUMP_FLUSH_TIME_S);
            if (time_in_state_s() >= PUMP_FLUSH_TIME_S) {
                pump_off();
                enter_state(ST_INJECT);
            }
            break;

        case ST_INJECT:
            display_show_status("Injecting sample...");
            if (inj_mode == 0) {
                /* Electrokinetic: 5 kV for 2 s */
                injection_electrokinetic(INJ_EK_VOLTAGE_KV, inj_duration_s);
            } else {
                /* Hydrodynamic: lift vial 10 cm for 10 s */
                injection_hydrodynamic(INJ_HD_LIFT_MM, inj_duration_s);
            }
            if (time_in_state_s() >= (uint32_t)(inj_duration_s + 1)) {
                enter_state(ST_SEPARATE);
            }
            break;

        case ST_SEPARATE:
            display_show_status("Separating... HV ramping");
            do_separate();
            if (state == ST_SEPARATE) {
                enter_state(ST_IDENTIFY);
            }
            break;

        case ST_IDENTIFY:
            display_show_status("Identifying ions...");
            do_identify();
            enter_state(ST_REPORT);
            break;

        case ST_REPORT:
            display_show_results(results, result_count, run_temp_c,
                                hv_measured_kv, run_id);
            sd_log_write_run(run_id, bge_recipe, hv_setpoint_kv,
                            hv_measured_kv, run_temp_c, eph_data, eph_count,
                            results, result_count);
            ble_bridge_send_results(results, result_count, run_id);
            run_id++;
            enter_state(ST_FLUSH);
            break;

        case ST_FLUSH:
            display_show_status("Flushing capillary...");
            pump_flush(PUMP_FLUSH_TIME_S);
            if (time_in_state_s() >= PUMP_FLUSH_TIME_S) {
                pump_off();
                enter_state(ST_IDLE);
            }
            break;

        case ST_ABORT:
            display_show_error("ABORTED: HV safety trip!");
            ble_bridge_send_error("HV safety trip", hv_current_ua, hv_measured_kv);
            sd_log_write_error(run_id, "HV safety trip", hv_current_ua, hv_measured_kv);
            enter_state(ST_IDLE);
            break;
        }

        /* Periodic safety check (1 Hz) */
        if (now - last_safety_ms > 1000) {
            last_safety_ms = now;
            if (!battery_ok()) {
                hv_supply_off();
                display_show_error("LOW BATTERY!");
            }
            if (!safety_interlock_ok()) {
                hv_supply_off();
                display_show_error("LID OPEN!");
            }
        }
    }
}