/*
 * main.c — Bolt Compass firmware entry (ESP32-S3-WROOM-1)
 *
 * Two-core layout:
 *   Core 1 (sferic core, priority 24):
 *     - adc_isr() feeds the PSRAM ring on every ADS131M04 DRDY (8 ksps).
 *     - sferic_task() runs the detect → classify → bearing → range →
 *       storm pipeline at ~100 Hz, pushes the resolved stroke to a
 *       FreeRTOS queue consumed by Core 0.
 *   Core 0 (connectivity / IO core, priority 5-12):
 *     - gps_task()         UART + PPS
 *     - log_task()         SD card writes (FatFS)
 *     - ble + wifi         GATT + HTTP/SSE
 *     - display_task()     OLED radar at 5 fps
 *     - power / supervisor light-sleep, alerts
 *
 * The sferic core is pinned and priority-locked so a Wi-Fi callback or
 * SD write can never drop a sample — the same hard-realtime / soft-IO
 * split used by Echo Mote (#8) and Ferro Weave (#21).
 */
#include "types.h"
#include "adc.h"
#include "detect.h"
#include "classify.h"
#include "bearing.h"
#include "range.h"
#include "storm.h"
#include "gps.h"
#include "display.h"
#include "sdlog.h"
#include "ble.h"
#include "wifi.h"
#include "power.h"

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

static const char *TAG = "bolt";

static QueueHandle_t s_stroke_q;     /* sferic core → IO core */
static range_model_t s_model;
static stroke_t      s_last;
static storm_t       s_storm_snap;

/* ── Sferic core (Core 1) ────────────────────────────────────────── */
static void sferic_task(void *arg)
{
    (void)arg;
    ring_t *r = adc_ring();
    sferic_t sf;
    detect_init();
    classify_init();

    for (;;) {
        if (detect_sferic(r, &sf)) {
            stroke_t st;
            st.ts_us = sf.ts_us;
            st.sf    = sf;
            classify_sferic(&sf, &st.cls);
            st.geo.azimuth_deg    = bearing_compute(&sf);
            st.geo.distance_km    = range_estimate(&sf, &s_model);
            st.geo.peak_field_uv  = sqrtf(sf.peak_ns*sf.peak_ns +
                                          sf.peak_ew*sf.peak_ew) / 4.096f;
            storm_add(&st);
            s_last = st;
            xQueueOverwrite(s_stroke_q, &st);   /* single-slot queue */
        }
        vTaskDelay(pdMS_TO_TICKS(10));          /* 100 Hz cadence */
    }
}

/* ── IO / connectivity core (Core 0) ─────────────────────────────── */
static void log_task(void *arg)
{
    (void)arg;
    stroke_t st;
    for (;;) {
        if (xQueueReceive(s_stroke_q, &st, pdMS_TO_TICKS(1000)) == pdTRUE) {
            sdlog_sferic(&st);
            ble_notify_sferic(&st);
            wifi_stream_sferic(&st);
        }
    }
}

static void display_task(void *arg)
{
    (void)arg;
    for (;;) {
        storm_snapshot(&s_storm_snap);
        display_radar(&s_storm_snap, &s_last);
        vTaskDelay(pdMS_TO_TICKS(200));          /* 5 fps */
    }
}

static void alert_task(void *arg)
{
    (void)arg;
    for (;;) {
        alert_t al[8];
        int n = storm_alerts(al, 8);
        for (int i = 0; i < n; i++) ble_notify_alert(al[i]);
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

int app_main(void)
{
    ESP_LOGI(TAG, "Bolt Compass booting…");

    power_init();
    gps_init();
    adc_init();
    display_init();
    sdlog_mount();
    ble_init();
    wifi_init();
    range_defaults(&s_model);

    s_stroke_q = xQueueCreate(1, sizeof(stroke_t));

    /* Sferic core on Core 1, high priority. */
    xTaskCreatePinnedToCore(sferic_task, "sferic", 8192, NULL, 24, NULL, 1);
    /* IO tasks on Core 0. */
    xTaskCreatePinnedToCore(log_task,     "log",     6144, NULL, 10, NULL, 0);
    xTaskCreatePinnedToCore(display_task, "disp",    3072, NULL, 6,  NULL, 0);
    xTaskCreatePinnedToCore(alert_task,   "alert",   2048, NULL, 5,  NULL, 0);

    display_status("Bolt Compass", "listening");
    ESP_LOGI(TAG, "all tasks started");
    return 0;
}