/*
 * main.c — Bone Echo pocket QUS bone densitometer
 *
 * Top-level state machine + main loop. Wires together all modules:
 *   tx_pulser     — HRTIM-triggered 200 V 1 MHz 5-cycle burst
 *   rx_chain      — AD8331 VGA + TGC ramp + BPF control
 *   adc           — ADC1 3.6 Msps ToF capture + 28 ksps BUA oversample
 *   sos           — Speed-of-sound: threshold-cross ToF + d/t_f
 *   bua           — BUA: FFT, attenuation vs freq, linear fit 0.2–0.6 MHz
 *   stiffness     — SI = 0.67·BUA + 0.28·SOS − 420
 *   normative     — WHO/ISCD T-score / Z-score look-up
 *   phantom       — Acrylic phantom reference measurement
 *   heel_caliper  — Caliper pot → heel width d (mm)
 *   display       — SH1106 OLED: SOS/BUA/SI/T-score + waveform
 *   sd_log        — microSD CSV + raw waveform binary logging
 *   ble_bridge    — UART protocol to ESP32-C3 (BLE GATT server)
 *   aux_adc       — ADS1115 aux channel reads (temp, etc.)
 *   battery       — 18650 voltage monitor
 *   patient       — Patient ID + age + sex + ethnicity input
 *   ui            — Button + rotary encoder + numeric pad menu
 *
 * Main loop runs at ~10 kHz: poll UI, run scans, push to BLE at 10 Hz,
 * log to SD per scan, run safety checks at 1 Hz.
 */

#include "stm32g474_conf.h"
#include "tx_pulser.h"
#include "rx_chain.h"
#include "adc.h"
#include "sos.h"
#include "bua.h"
#include "stiffness.h"
#include "normative.h"
#include "phantom.h"
#include "heel_caliper.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "aux_adc.h"
#include "battery.h"
#include "patient.h"
#include "ui.h"
#include <string.h>
#include <stdio.h>

typedef enum {
    ST_IDLE,
    ST_MENU,
    ST_PATIENT_ENTRY,
    ST_PHANTOM_REF,
    ST_SCAN,
    ST_REPORT,
    ST_DONE,
} state_t;

static state_t  state = ST_IDLE;
static uint16_t scan_id = 1;
static uint32_t sys_ms = 0;
static uint32_t last_ble_ms = 0;
static uint32_t last_safety_ms = 0;
static uint32_t last_disp_ms = 0;

/* Latest measurement results */
static float    cur_sos = 0.0f;
static float    cur_bua = 0.0f;
static float    cur_si  = 0.0f;
static float    cur_t   = 0.0f;
static float    cur_z   = 0.0f;
static float    cur_d_mm = 25.0f;
static int      cur_class = 0;   /* 0=normal, 1=osteopenia, 2=osteoporosis, 3=severe */
static float    cur_bua_r2 = 0.0f;

/* Settings */
static bool     three_scan_avg = false;
static int      avg_count = 0;
static float    sos_sum = 0.0f, bua_sum = 0.0f;

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

void SysTick_Handler(void) { sys_ms++; }

static void run_scan(void)
{
    /* Full scan sequence: TX → RX capture → SOS → BUA → SI → T-score */
    if (!battery_ok()) {
        display_show_message("Battery low", "charge first");
        return;
    }

    /* Read heel width from caliper (or phantom thickness if phantom detected) */
    if (phantom_present()) {
        cur_d_mm = PHANTOM_THICK_MM;
    } else {
        cur_d_mm = heel_caliper_read_mm();
        if (cur_d_mm < SOS_CALIPER_MIN_MM || cur_d_mm > SOS_CALIPER_MAX_MM) {
            display_show_message("Heel width out", "of range (20-80mm)");
            return;
        }
    }

    /* Arm HV, fire TX burst, capture RX */
    tx_pulser_arm();
    if (!tx_pulser_hv_ok()) {
        display_show_message("HV FAULT", "check pulser");
        tx_pulser_disarm();
        return;
    }
    rx_chain_set_tgc_ramp(TGC_RAMP_START_DB, TGC_RAMP_END_DB);

    /* ToF capture: full 3.6 Msps, 32 ms window */
    adc_start_tof_capture();
    tx_pulser_fire();   /* HRTIM edge → TX burst, ADC triggered simultaneously */
    adc_wait_tof_done();

    /* BUA capture: oversampled 16-bit @ 28 ksps, 50 ms window */
    adc_start_bua_capture();
    /* Fire another TX burst for BUA (separate burst avoids dead-time) */
    tx_pulser_fire();
    adc_wait_bua_done();

    tx_pulser_disarm();   /* Discharge HV immediately */

    /* Compute SOS */
    cur_sos = sos_compute(adc_tof_buffer(), TOF_SAMPLES,
                          tx_pulser_get_trigger_ts(), cur_d_mm,
                          phantom_get_probe_delay());
    if (cur_sos < SOS_MIN_MPS || cur_sos > SOS_MAX_MPS) {
        if (phantom_present()) {
            /* Phantom reference: validate and update probe delay */
            phantom_update_probe_delay(cur_d_mm, cur_sos);
            display_show_message("Phantom ref", "calibrated OK");
            /* Also capture BUA reference FFT */
            phantom_capture_ref_fft(adc_bua_buffer(), BUA_SAMPLES);
            state = ST_IDLE;
            return;
        }
        display_show_message("SOS out of range", "check gel/position");
        state = ST_IDLE;
        return;
    }

    /* Compute BUA */
    cur_bua = bua_compute(adc_bua_buffer(), BUA_SAMPLES,
                          phantom_get_ref_fft());
    cur_bua_r2 = bua_last_r2();
    if (cur_bua_r2 < BUA_FIT_R2_MIN) {
        display_show_message("Poor coupling", "reapply gel");
        state = ST_IDLE;
        return;
    }

    /* If phantom, store reference and return */
    if (phantom_present()) {
        phantom_update_probe_delay(cur_d_mm, cur_sos);
        phantom_capture_ref_fft(adc_bua_buffer(), BUA_SAMPLES);
        display_show_message("Phantom ref", "calibrated OK");
        state = ST_IDLE;
        return;
    }

    /* Three-scan average mode */
    if (three_scan_avg && avg_count < 2) {
        sos_sum += cur_sos;
        bua_sum += cur_bua;
        avg_count++;
        display_show_message("Scan", "repeat for avg");
        state = ST_SCAN;
        return;
    }
    if (three_scan_avg) {
        cur_sos = sos_sum / 3.0f;
        cur_bua = bua_sum / 3.0f;
        sos_sum = bua_sum = 0.0f;
        avg_count = 0;
    }

    /* Compute Stiffness Index */
    cur_si = stiffness_compute(cur_bua, cur_sos);

    /* Compute T-score and Z-score */
    const normative_t *n_young = normative_lookup(patient_get_sex(),
                                                   patient_get_ethnicity(),
                                                   NORM_YOUNG_ADULT);
    const normative_t *n_age    = normative_lookup(patient_get_sex(),
                                                   patient_get_ethnicity(),
                                                   normative_age_group(patient_get_age()));
    if (n_young && n_age) {
        cur_t = (cur_si - n_young->mean_si) / n_young->sd_si;
        cur_z = (cur_si - n_age->mean_si) / n_age->sd_si;
    } else {
        cur_t = cur_z = 0.0f;
    }

    /* WHO classification */
    cur_class = normative_classify(cur_t, patient_has_prior_fracture());

    /* Log to SD */
    sd_log_open_scan(scan_id, patient_get_id(), patient_get_age(),
                     patient_get_sex(), patient_get_ethnicity());
    sd_log_results(scan_id, cur_sos, cur_bua, cur_si, cur_t, cur_z, cur_class);
    sd_log_waveform(scan_id, adc_tof_buffer(), TOF_SAMPLES);
    sd_log_close();
    scan_id++;

    /* Push results + waveform to BLE */
    ble_bridge_push_results(cur_sos, cur_bua, cur_si, cur_t, cur_z, cur_class);
    ble_bridge_push_waveform(adc_tof_buffer(), TOF_SAMPLES);

    state = ST_REPORT;
    display_show_results(cur_sos, cur_bua, cur_si, cur_t, cur_z, cur_class);
}

static void stop_all(void)
{
    tx_pulser_disarm();
    adc_stop();
    state = ST_IDLE;
    display_show_message("STOPPED", "idle");
}

int main(void)
{
    SystemInit();

    /* Init all peripherals */
    display_init();
    tx_pulser_init();
    rx_chain_init();
    adc_init();
    sos_init();
    bua_init();
    stiffness_init();
    normative_init();
    phantom_init();
    heel_caliper_init();
    sd_log_init();
    ble_bridge_init();
    aux_adc_init();
    battery_init();
    patient_init();
    ui_init();

    display_show_message("BONE ECHO", "v1.0 ready");
    for (volatile int i = 0; i < 5000000; ++i) ;   /* splash ~0.5 s */

    state = ST_MENU;

    while (1) {
        ui_poll();

        /* Check for BLE command */
        char cmd[32];
        if (ble_bridge_poll_cmd(cmd, sizeof(cmd))) {
            if (strncmp(cmd, "SCAN", 4) == 0)        run_scan();
            else if (strncmp(cmd, "STOP", 4) == 0)  stop_all();
            else if (strncmp(cmd, "PHANTOM", 7) == 0) { state = ST_PHANTOM_REF; run_scan(); }
            else if (strncmp(cmd, "ID:", 3) == 0)   { int id; sscanf(cmd + 3, "%d", &id); patient_set_id(id); }
            else if (strncmp(cmd, "AGE:", 4) == 0)  { int a; sscanf(cmd + 4, "%d", &a); patient_set_age(a); }
            else if (strncmp(cmd, "SEX:", 4) == 0)  { int s; sscanf(cmd + 4, "%d", &s); patient_set_sex(s); }
            else if (strncmp(cmd, "ETH:", 4) == 0)  { int e; sscanf(cmd + 4, "%d", &e); patient_set_ethnicity(e); }
        }

        if (ui_scan_pressed()) {
            if (state == ST_IDLE || state == ST_MENU || state == ST_REPORT) {
                state = ST_SCAN;
                run_scan();
            }
        }

        if (ui_mode_pressed()) {
            if (state == ST_REPORT || state == ST_SCAN) stop_all();
        }

        /* Patient entry via numeric pad */
        if (state == ST_MENU) {
            patient_poll_input();
            if (patient_entry_complete()) {
                state = ST_IDLE;
                display_show_message("Patient ready", "press SCAN");
            }
        }

        /* BLE status push @ 10 Hz */
        if (sys_ms - last_ble_ms >= 100) {
            last_ble_ms = sys_ms;
            ble_bridge_push_status(battery_read(), state, cur_sos, cur_bua);
        }

        /* Safety check @ 1 Hz */
        if (sys_ms - last_safety_ms >= 1000) {
            last_safety_ms = sys_ms;
            if (state == ST_SCAN) {
                if (!tx_pulser_hv_ok()) {
                    stop_all();
                    display_show_message("HV FAULT", "disarmed");
                }
                if (battery_low()) {
                    display_show_message("Battery low", "");
                    if (state != ST_IDLE) stop_all();
                }
            }
            /* Auto-disarm HV if idle > 2 s */
            if (state != ST_SCAN && tx_pulser_armed()) {
                tx_pulser_disarm();
            }
        }

        /* Display update @ ~20 Hz */
        if (sys_ms - last_disp_ms >= 50) {
            last_disp_ms = sys_ms;
            switch (state) {
                case ST_MENU:
                    display_show_menu(ui_current());
                    break;
                case ST_REPORT:
                    display_show_results(cur_sos, cur_bua, cur_si, cur_t, cur_z, cur_class);
                    break;
                case ST_SCAN:
                    display_show_message("SCANNING...", "");
                    break;
                default: break;
            }
        }

        /* Menu navigation */
        if (state == ST_MENU) {
            int d = ui_encoder_delta();
            if (d != 0) {
                switch (ui_current()) {
                    case UI_PATIENT:  if (ui_select_pressed()) patient_start_entry(); break;
                    case UI_3SCAN:     three_scan_avg = !three_scan_avg; break;
                    case UI_PHANTOM:   if (ui_select_pressed()) { state = ST_PHANTOM_REF; run_scan(); } break;
                    case UI_SCAN:      if (ui_select_pressed()) { state = ST_SCAN; run_scan(); } break;
                    case UI_LOG:       /* logging is automatic */ break;
                    default: break;
                }
            }
        }
    }
}