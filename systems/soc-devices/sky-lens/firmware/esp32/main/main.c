/*
 * main.c — Sky Lens application entry, acquisition FSM, task wiring
 *
 * Core 0 runs the time-critical coincidence / ADC path in an ISR +
 * high-priority task; core 1 runs the histogramming, display, IMU
 * fusion, BLE/Wi-Fi, and SD-logging tasks.
 *
 * This file is shared between the ESP32-S3 build (ESP-IDF) and the
 * native simulation build (SKY_LENS_SIM=1).
 */
#include "sky_lens.h"
#include "coincidence.h"
#include "adc.h"
#include "sipm_bias.h"
#include "imu.h"
#include "pressure.h"
#include "skymap.h"
#include "zenith.h"
#include "lifetime.h"
#include "display.h"
#include "sdlog.h"
#include "ble.h"
#include "wifi.h"
#include "proto.h"
#include "power.h"

#include <math.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "nvs_flash.h"
static const char *TAG = "skylens";
#endif

/* ── Globals ────────────────────────────────────────────────────────── */
static acquisition_status_t g_status = ACQ_IDLE;
static daily_t              g_daily;
static uint32_t             g_event_seq = 0;

/* ── Event queue (filled by coincidence path, drained by event task) ─── */
#ifndef SKY_LENS_SIM
static QueueHandle_t s_evt_queue = NULL;
#define EVT_QUEUE_LEN 64
#endif

/* ── Helper: now in microseconds ─────────────────────────────────────── */
static uint64_t now_us(void)
{
#ifdef SKY_LENS_SIM
    return port_sim_now_us();
#else
    return (uint64_t)esp_timer_get_time();
#endif
}

/* ── Process one coincidence event ──────────────────────────────────────
 * Called from the high-priority acquisition task (ESP32) or from the
 * simulation driver (sim). Fills in the derived fields, updates the
 * in-memory histograms, and pushes the event to the queue for the
 * (slower) log/BLE/wifi tasks.
 */
static void handle_event(event_t *ev)
{
    ev->seq = ++g_event_seq;
    ev->ts_us = now_us();

    /* Attitude from IMU */
    imu_read_quat(&ev->q_w, &ev->q_x, &ev->q_y, &ev->q_z);

    /* Pressure / temperature */
    ev->p_hpa = pressure_read_hpa();
    ev->t_c   = pressure_read_temp_c();

    /* Zenith angle from Δt:
     *   Δt = (d/c) * tan(θ)  →  θ = atan(Δt * c / d)
     *   dt_ps in picoseconds, d in mm
     *   Δt_s = dt_ps * 1e-12,  d_m = d_mm * 1e-3
     *   tan(θ) = Δt_s * c / d_m = dt_ps * 1e-12 * 3e8 / (d * 1e-3)
     *          = dt_ps * 3e-1 / d  =  dt_ps * 0.3 / d_mm
     */
    if (ev->dt_ps != 0) {
        float ratio = (float)ev->dt_ps * 0.3f / SKY_LENS_TILE_GAP_MM;
        ev->zenith_deg = (float)atanf(ratio) * (180.0f / 3.14159265f);
        if (ev->zenith_deg < 0.0f) ev->zenith_deg = -ev->zenith_deg;
    } else {
        ev->zenith_deg = 0.0f;
    }

    /* Azimuth from the attitude quaternion (project the up-vector into
     * the horizontal plane). This is a simplified derivation: we take
     * the heading from the quaternion's yaw component. */
    {
        /* yaw = atan2(2*(q_w*q_z + q_x*q_y), 1 - 2*(q_y² + q_z²)) */
        float yaw = atan2f(2.0f*(ev->q_w*ev->q_z + ev->q_x*ev->q_y),
                           1.0f - 2.0f*(ev->q_y*ev->q_y + ev->q_z*ev->q_z));
        ev->az_deg = yaw * (180.0f / 3.14159265f);
        if (ev->az_deg < 0.0f) ev->az_deg += 360.0f;
    }

    /* Update in-memory histograms (fast, lock-free for single producer) */
    skymap_add_event(ev->zenith_deg, ev->az_deg);
    zenith_add(ev->zenith_deg);
    g_daily.n_events++;

    /* Lifetime mode: feed the delay histogram if this is a delayed pulse */
    if (ev->flags & 0x02) {
        /* dt_ps here is the prompt-delayed gap; convert to µs */
        lifetime_add_delay((float)ev->dt_ps * 1e-6f);
    }

#ifndef SKY_LENS_SIM
    /* Push to the event queue for the slow tasks */
    if (s_evt_queue)
        xQueueSend(s_evt_queue, ev, 0);
#else
    /* Sim: log directly */
    sdlog_write_event(ev);
    ble_send_event(ev);
    wifi_send_event(ev);
#endif
}

/* ── Acquisition control ──────────────────────────────────────────────── */
void acquisition_start(void)
{
    if (g_status == ACQ_RUN || g_status == ACQ_LIFETIME)
        return;
    if (!sipm_bias_enable()) {
        g_status = ACQ_FAULT;
        return;
    }
    adc_init();
    coincidence_init();
    g_status = (g_daily.n_events == 0) ? ACQ_RUN : ACQ_RUN; /* simplified */
#ifdef SKY_LENS_SIM
    port_sim_log("acquisition started");
#else
    ESP_LOGI(TAG, "acquisition started");
#endif
}

void acquisition_stop(void)
{
    sipm_bias_disable();
    adc_deinit();
    g_status = ACQ_IDLE;
#ifdef SKY_LENS_SIM
    port_sim_log("acquisition stopped");
#else
    ESP_LOGI(TAG, "acquisition stopped");
#endif
}

acquisition_status_t acquisition_get_status(void)
{
    return g_status;
}

/* ── Event task (ESP32 only) ─────────────────────────────────────────── */
#ifndef SKY_LENS_SIM
static void event_task(void *arg)
{
    event_t ev;
    while (1) {
        if (xQueueReceive(s_evt_queue, &ev, portMAX_DELAY) == pdTRUE) {
            sdlog_write_event(&ev);
            ble_send_event(&ev);
            wifi_send_event(&ev);
        }
    }
}
#endif

/* ── Display / rollup task ───────────────────────────────────────────── */
static void dashboard_tick(void)
{
    skymap_t m;
    zenith_fit_t z;
    lifetime_result_t lf;
    skymap_get(&m);
    z  = zenith_fit();
    lf = lifetime_fit();

    /* Compute rolling rate from the daily accumulator */
    uint64_t elapsed_s = (now_us() - g_daily.start_us) / 1000000ULL;
    if (elapsed_s > 0) {
        g_daily.rate_raw_cpm = (float)g_daily.n_events / ((float)elapsed_s / 60.0f);
        g_daily.rate_corr_cpm = pressure_correct_rate(
            g_daily.rate_raw_cpm, g_daily.mean_p_hpa, g_daily.mean_t_c);
    }
    display_update(&g_daily, &m, &z, &lf);
}

/* ── App entry ───────────────────────────────────────────────────────── */
void app_main(void)
{
#ifdef SKY_LENS_SIM
    port_sim_init();
    port_sim_log("=== Sky Lens simulation ===");
#else
    /* NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
        nvs_flash_erase() + nvs_flash_init();   /* recover */
    /* Peripherals */
    power_init();
    sipm_bias_init();
    imu_init();
    pressure_init();
    display_init();
    sdlog_init();
    ble_init();
    wifi_init();
    /* Event queue + tasks */
    s_evt_queue = xQueueCreate(EVT_QUEUE_LEN, sizeof(event_t));
    xTaskCreatePinnedToCore(event_task, "evt", 8192, NULL, 5, NULL, 1);
    ESP_LOGI(TAG, "Sky Lens boot complete");
#endif

    g_daily.start_us = now_us();
    g_daily.mean_p_hpa = pressure_read_hpa();
    g_daily.mean_t_c   = pressure_read_temp_c();

    acquisition_start();

    /* Main loop: dashboard tick + simulation event generation */
    while (1) {
#ifdef SKY_LENS_SIM
        /* The sim feeds synthetic events through the coincidence path */
        event_t ev;
        while (coincidence_pop(&ev)) {
            handle_event(&ev);
        }
        port_sim_step();
        if (port_sim_done()) {
            dashboard_tick();
            /* Print final summary */
            skymap_t m; skymap_get(&m);
            zenith_fit_t z = zenith_fit();
            lifetime_result_t lf = lifetime_fit();
            port_sim_log("=== FINAL SUMMARY ===");
            port_sim_log("total events: %lu", (unsigned long)m.total);
            port_sim_log("skymap total: %lu", (unsigned long)m.total);
            port_sim_log("zenith I(0) = %.2f cpm, chi2 = %.3f", z.i0, z.chi2);
            port_sim_log("lifetime tau = %.3f us, err = +/-%.3f us, pairs=%lu, chi2=%.2f",
                         lf.tau_us, lf.tau_err_us, (unsigned long)lf.n_pairs, lf.chi2);
            port_sim_log("raw rate = %.2f cpm, corrected = %.2f cpm",
                         g_daily.rate_raw_cpm, g_daily.rate_corr_cpm);
            acquisition_stop();
            break;
        }
#else
        event_t ev;
        if (coincidence_pop(&ev)) {
            handle_event(&ev);
        }
        vTaskDelay(pdMS_TO_TICKS(250));
        dashboard_tick();
#endif
    }

#ifdef SKY_LENS_SIM
    port_sim_log("=== Sky Lens simulation done ===");
#endif
}

#ifdef SKY_LENS_SIM
/* Host simulation entry point — calls app_main */
int main(void)
{
    app_main();
    return 0;
}
#endif