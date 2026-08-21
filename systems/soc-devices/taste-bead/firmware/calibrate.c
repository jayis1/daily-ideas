/* calibrate.c — Open/Short/KCl calibration for Taste Bead
 *
 * Performs the three-point calibration needed for accurate EIS measurements.
 * Calibration data is stored in NVS and loaded at boot.
 */

#include "calibrate.h"
#include "sdkconfig.h"
#include "ad5941.h"
#include "eis.h"
#include "mux.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <math.h>

static const char *TAG = "calibrate";

static ad5941_cal_t g_cal;
static calibrate_status_t g_status = {0};

esp_err_t calibrate_init(void)
{
    memset(&g_cal, 0, sizeof(g_cal));
    calibrate_load();
    return ESP_OK;
}

esp_err_t calibrate_open(void)
{
    ESP_LOGI(TAG, "Starting OPEN calibration (probe in air)...");

    /* Measure all frequencies with probe in air (open circuit) */
    /* All electrodes disconnected → measure parasitic */
    mux_disable();
    vTaskDelay(pdMS_TO_TICKS(100));

    const float *freqs = eis_get_freq_table();
    ad5941_z_point_t results[NUM_FREQS];

    /* Sweep with electrode 0 selected (measures mux+probe parasitics) */
    mux_select(MUX_ELECTRODE_AU);
    vTaskDelay(pdMS_TO_TICKS(10));

    esp_err_t ret = ad5941_sweep(freqs, NUM_FREQS,
                                   EIS_EXCITION_AMPLITUDE, RTIA_100K, results);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Open calibration sweep failed");
        return ret;
    }

    /* Store results */
    for (int i = 0; i < NUM_FREQS; i++) {
        g_cal.open_mag[i] = results[i].z_mag;
        g_cal.open_phase[i] = results[i].z_phase;
    }

    g_status.open_done = true;
    g_cal.open_done = true;
    g_cal.cal_timestamp = esp_timer_get_time();

    ESP_LOGI(TAG, "OPEN calibration complete");
    return calibrate_save();
}

esp_err_t calibrate_short(void)
{
    ESP_LOGI(TAG, "Starting SHORT calibration (electrodes shorted)...");

    /* Measure with all electrodes shorted together.
     * In practice, user places probe in a metal cup that shorts all electrodes.
     * The mux selects one electrode; the counter electrode (Pt ring) and
     * reference (Ag/AgCl) provide the return path through the short. */

    const float *freqs = eis_get_freq_table();
    ad5941_z_point_t results[NUM_FREQS];

    mux_select(MUX_ELECTRODE_AU);
    vTaskDelay(pdMS_TO_TICKS(10));

    esp_err_t ret = ad5941_sweep(freqs, NUM_FREQS,
                                   EIS_EXCITION_AMPLITUDE, RTIA_200, results);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Short calibration sweep failed");
        return ret;
    }

    for (int i = 0; i < NUM_FREQS; i++) {
        g_cal.short_mag[i] = results[i].z_mag;
        g_cal.short_phase[i] = results[i].z_phase;
    }

    g_status.short_done = true;
    g_cal.short_done = true;
    g_cal.cal_timestamp = esp_timer_get_time();

    ESP_LOGI(TAG, "SHORT calibration complete");
    return calibrate_save();
}

esp_err_t calibrate_kcl(void)
{
    ESP_LOGI(TAG, "Starting KCl 0.01M calibration (probe in 0.01M KCl)...");

    /* 0.01 M KCl has a known conductivity of 1413 µS/cm at 25°C
     * (resistivity ≈ 708 Ω·cm). This serves as a load reference. */

    const float *freqs = eis_get_freq_table();
    ad5941_z_point_t results[NUM_FREQS];

    mux_select(MUX_ELECTRODE_AU);
    vTaskDelay(pdMS_TO_TICKS(10));

    esp_err_t ret = ad5941_sweep(freqs, NUM_FREQS,
                                   EIS_EXCITION_AMPLITUDE, RTIA_10K, results);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "KCl calibration sweep failed");
        return ret;
    }

    for (int i = 0; i < NUM_FREQS; i++) {
        g_cal.kcl_mag[i] = results[i].z_mag;
        g_cal.kcl_phase[i] = results[i].z_phase;
    }

    g_status.kcl_done = true;
    g_cal.kcl_done = true;
    g_cal.cal_timestamp = esp_timer_get_time();
    g_cal.rtia_actual = RTIA_10K;

    ESP_LOGI(TAG, "KCl calibration complete");
    return calibrate_save();
}

calibrate_status_t calibrate_get_status(void)
{
    return g_status;
}

esp_err_t calibrate_save(void)
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open(LIBRARY_NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) return ret;

    ret = nvs_set_blob(handle, "cal_data", &g_cal, sizeof(g_cal));
    if (ret == ESP_OK) {
        nvs_commit(handle);
        ESP_LOGI(TAG, "Calibration saved to NVS");
    }
    nvs_close(handle);
    return ret;
}

esp_err_t calibrate_load(void)
{
    nvs_handle_t handle;
    esp_err_t ret = nvs_open(LIBRARY_NVS_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "No calibration in NVS");
        return ret;
    }

    size_t required = sizeof(g_cal);
    ret = nvs_get_blob(handle, "cal_data", &g_cal, &required);
    nvs_close(handle);

    if (ret == ESP_OK) {
        g_status.open_done = g_cal.open_done;
        g_status.short_done = g_cal.short_done;
        g_status.kcl_done = g_cal.kcl_done;
        g_status.cal_timestamp = g_cal.cal_timestamp;
        ad5941_set_calibration(&g_cal);
        ESP_LOGI(TAG, "Calibration loaded (O=%d S=%d K=%d)",
                 g_status.open_done, g_status.short_done, g_status.kcl_done);
    }
    return ret;
}

esp_err_t calibrate_get_data(ad5941_cal_t *cal)
{
    memcpy(cal, &g_cal, sizeof(g_cal));
    return ESP_OK;
}