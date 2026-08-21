/* main.c — Plume Sniffer main entry point
 *
 * The firmware implements a state machine that drives a complete GC run:
 *   IDLE → PURGE → SAMPLE → DESORB → RAMP (with TCD sampling) → COOLDOWN → IDLE
 *
 * During RAMP, the TCD sampling task fills a ring buffer. The main task
 * drains the buffer into a large capture array. After the run, peaks are
 * detected, identified, logged to SD, and streamed over BLE.
 *
 * Core 0 (the only core on ESP32-C3) runs everything via FreeRTOS.
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_timer.h"

#include "sdkconfig.h"
#include "tcd.h"
#include "column.h"
#include "preconc.h"
#include "pump.h"
#include "peak.h"
#include "identify.h"
#include "library.h"
#include "display.h"
#include "sd_log.h"
#include "ble.h"
#include "bme280.h"
#include "battery.h"
#include "ui.h"

static const char *TAG = "plume";

/* ---- Capture buffer for a full run ---- */
static tcd_sample_t s_capture[PLUME_TCD_SAMPLES_PER_RUN];
static int s_capture_count = 0;

/* ---- Methods ---- */
static column_method_t methods[] = {
    /* M_ETHOS: standard 10°C/min, 35→180°C */
    { .start_temp_c = 35, .hold_start_s = 10, .ramp_c_per_min = 10,
      .final_temp_c = 180, .hold_final_s = 30 },
    /* M_FAST: 20°C/min, 35→120°C (4 min screening) */
    { .start_temp_c = 35, .hold_start_s = 5, .ramp_c_per_min = 20,
      .final_temp_c = 120, .hold_final_s = 15 },
    /* M_ISOTHERM: 80°C isothermal for volatiles */
    { .start_temp_c = 80, .hold_start_s = 300, .ramp_c_per_min = 0,
      .final_temp_c = 80, .hold_final_s = 0 },
    /* M_HIGH: 15°C/min to 180°C for semivolatiles */
    { .start_temp_c = 50, .hold_start_s = 10, .ramp_c_per_min = 15,
      .final_temp_c = 180, .hold_final_s = 60 },
};
static const char *method_names[] = { "M_ETHOS", "M_FAST", "M_ISOTH", "M_HIGH" };
static int s_method_sel = 0;

/* ---- Run estimate (seconds) for display ---- */
static int estimate_run_seconds(const column_method_t *m)
{
    int total = m->hold_start_s;
    if (m->ramp_c_per_min > 0)
        total += (int)((m->final_temp_c - m->start_temp_c) / m->ramp_c_per_min * 60);
    total += m->hold_final_s;
    total += 180;  /* cooldown estimate */
    return total;
}

/* ---- Execute a full GC run ---- */
static void execute_run(void)
{
    column_method_t *m = &methods[s_method_sel];
    column_set_method(m);
    int total_s = estimate_run_seconds(m);

    /* Pre-run checks */
    if (!battery_ok_for_run()) {
        display_status("BAT LOW!");
        vTaskDelay(pdMS_TO_TICKS(2000));
        return;
    }

    float bat_mv = battery_read_mv();
    bme280_data_t ambient;
    bme280_read(&ambient);
    ESP_LOGI(TAG, "=== RUN START: %s  bat=%.0fmV  amb=%.1fC  %dml ===",
             method_names[s_method_sel], bat_mv, ambient.temp_c,
             PLUME_SAMPLE_VOLUME_DEFAULT_ML);

    /* PHASE 1: PURGE (10 s with carrier) */
    display_running(0, m->start_temp_c, 0, 0, total_s, "PURGE");
    valve_set(VALVE_CARRIER);
    pump_set(100.0f);
    vTaskDelay(pdMS_TO_TICKS(10000));

    /* PHASE 2: SAMPLE (pull through preconcentrator) */
    display_running(0, m->start_temp_c, 0, 10, total_s, "SAMPLE");
    valve_set(VALVE_SAMPLE);
    pump_start_sampling();
    /* Sample for the time needed for the target volume */
    int sample_s = (PLUME_SAMPLE_VOLUME_DEFAULT_ML * 60) / PLUME_PUMP_FLOW_ML_MIN;
    for (int s = 0; s < sample_s; s++) {
        display_running(column_read_temp_c(), m->start_temp_c,
                        preconc_read_temp_c(), 10 + s, total_s, "SAMPLE");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    float vol_ml = pump_stop_sampling();
    pump_off();
    valve_set(VALVE_CARRIER);

    /* PHASE 3: DESORB (flash heat preconcentrator) */
    display_running(0, m->start_temp_c, 0, 10 + sample_s, total_s, "DESORB");
    /* Start column at initial temp and carrier flowing */
    pump_set(40.0f);  /* low carrier flow: ~12 mL/min */
    column_start_ramp();
    preconc_flash_desorb();

    /* PHASE 4: RAMP — TCD sampling throughout */
    s_capture_count = 0;
    tcd_reset_baseline();
    tcd_start();

    int64_t t0 = esp_timer_get_time();
    int ramp_s = (m->ramp_c_per_min > 0)
        ? (int)((m->final_temp_c - m->start_temp_c) / m->ramp_c_per_min * 60)
        : m->hold_start_s;
    int ramp_elapsed = 0;

    while (!false) {
        /* Drain ring buffer into capture array */
        tcd_sample_t tmp[32];
        int got = tcd_read_batch(tmp, 32);
        for (int i = 0; i < got && s_capture_count < PLUME_TCD_SAMPLES_PER_RUN; i++)
            s_capture[s_capture_count++] = tmp[i];

        /* Update display every 500 ms */
        static int64_t last_disp = 0;
        int64_t now = esp_timer_get_time();
        if (now - last_disp > 500000) {
            last_disp = now;
            display_running(column_read_temp_c(), column_read_target_c(),
                            preconc_read_temp_c(),
                            10 + sample_s + ramp_elapsed, total_s, "RAMP");

            /* Send a small chromatogram preview over BLE */
            if (ble_is_connected() && s_capture_count > 20) {
                float preview[20];
                int stride = s_capture_count / 20;
                for (int i = 0; i < 20; i++)
                    preview[i] = s_capture[i * stride].corrected_uv;
                ble_send_chromatogram(preview, 20);
            }
        }

        ramp_elapsed = (int)((esp_timer_get_time() - t0) / 1000000);

        /* Check if column program is done */
        extern bool s_ramp_done;  /* from column.c — set by program task */
        /* Instead, poll column temp: if we've reached final + hold, we're done.
         * For simplicity, check elapsed time vs ramp_s + hold. */
        if (ramp_elapsed > ramp_s + m->hold_final_s) break;
        vTaskDelay(pdMS_TO_TICKS(50));
    }

    /* Drain remaining samples */
    vTaskDelay(pdMS_TO_TICKS(500));
    tcd_sample_t tmp[32];
    int got;
    while ((got = tcd_read_batch(tmp, 32)) > 0) {
        for (int i = 0; i < got && s_capture_count < PLUME_TCD_SAMPLES_PER_RUN; i++)
            s_capture[s_capture_count++] = tmp[i];
    }
    tcd_stop();
    pump_off();

    ESP_LOGI(TAG, "Captured %d samples", s_capture_count);

    /* PHASE 5: COOLDOWN */
    display_running(column_read_temp_c(), 25, 0,
                    10 + sample_s + ramp_elapsed, total_s, "COOL");
    column_cooldown();
    column_wait_cooldown();

    /* PHASE 6: ANALYSIS — peak detection + identification */
    display_status("ANALYZING...");
    float noise = tcd_noise_sigma();
    peak_t peaks[PEAK_MAX_PER_RUN];
    int n_peaks = peak_detect(s_capture, s_capture_count, noise,
                              peaks, PEAK_MAX_PER_RUN);

    identification_t ids[PEAK_MAX_PER_RUN];
    int n_ids = identify_peaks(peaks, n_peaks, vol_ml, ids);

    ESP_LOGI(TAG, "Identified %d peaks", n_ids);
    for (int i = 0; i < n_ids; i++) {
        const char *name = ids[i].n_matches > 0
            ? library_get(ids[i].matches[0].index)->name : "unknown";
        ESP_LOGI(TAG, "  [%d] tR=%.1fs RI=%.0f %s %.0fppm",
                 i, ids[i].retention_s, ids[i].retention_index,
                 name, ids[i].est_conc_ppm);
    }

    /* PHASE 7: LOG + STREAM */
    bat_mv = battery_read_mv();
    int run_num = sd_save_run(s_capture, s_capture_count,
                              peaks, n_peaks, ids, n_ids,
                              vol_ml, method_names[s_method_sel],
                              bat_mv, ambient.temp_c);
    if (run_num > 0)
        ESP_LOGI(TAG, "Saved as RUN_%04d", run_num);

    ble_send_results(ids, n_ids);

    /* Display peak table (scrollable via MODE button) */
    int scroll = 0;
    display_peak_table(ids, n_ids, scroll);
    ui_cmd_t cmd;
    while ((cmd = ui_wait_cmd(0)) != UI_CMD_RUN) {
        if (cmd == UI_CMD_MENU_NEXT) {
            scroll = (scroll + 5) % (n_ids > 0 ? n_ids : 1);
            display_peak_table(ids, n_ids, scroll);
        }
    }

    ESP_LOGI(TAG, "=== RUN COMPLETE ===");
    display_status("READY");
}

/* ---- Main task ---- */
static void plume_main_task(void *arg)
{
    ESP_LOGI(TAG, "Plume Sniffer main task started");

    /* Load alkane anchors from NVS */
    float anchors[12];
    library_get_anchors(anchors, 12);

    display_boot(battery_read_mv());
    vTaskDelay(pdMS_TO_TICKS(2000));

    int menu_sel = 0;
    display_menu(menu_sel);

    while (1) {
        ui_cmd_t cmd = ui_wait_cmd(portMAX_DELAY);

        if (cmd == UI_CMD_RUN) {
            execute_run();
            display_menu(menu_sel);
        } else if (cmd == UI_CMD_MENU_NEXT) {
            menu_sel = (menu_sel + 1) % 4;
            s_method_sel = menu_sel % 4;  /* simplified: menu cycles methods */
            display_menu(menu_sel);
        }
    }
}

/* ---- app_main ---- */
void app_main(void)
{
    ESP_LOGI(TAG, "Plume Sniffer booting...");
    ESP_LOGI(TAG, "ESP32-C3 · %d Hz TCD · %d-sample buffer",
             PLUME_TCD_SAMPLE_HZ, PLUME_TCD_SAMPLES_PER_RUN);

    /* NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize subsystems */
    battery_read_mv();  /* triggers ADC init */
    display_init();
    bme280_init();
    column_init();
    preconc_init();
    pump_init();
    tcd_init();
    sd_init();
    ble_init();
    ui_init();

    /* Start main task */
    xTaskCreate(plume_main_task, "plume_main", 8192, NULL, 5, NULL);
}