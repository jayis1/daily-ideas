/* eis.c — Multi-electrode EIS measurement orchestration
 *
 * Runs a full impedance spectroscopy sweep across all 5 working electrodes
 * at 20 logarithmically-spaced frequencies (1 Hz to 100 kHz).
 * Total measurement time: ~12 seconds.
 */

#include "eis.h"
#include "sdkconfig.h"
#include "ad5941.h"
#include "mux.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "eis";

/* Frequency table: 20 log-spaced points from ~1 Hz to 100 kHz */
static const float freq_table[NUM_FREQS] = {
    1.0f, 1.47f, 2.15f, 3.16f, 4.64f,
    6.81f, 10.0f, 14.68f, 21.54f, 31.62f,
    46.42f, 68.13f, 100.0f, 146.78f, 215.44f,
    316.23f, 464.16f, 681.29f, 1000.0f, 2154.43f,
    /* Extended: */
    /* 3162.28f, 4641.59f, 6812.92f, 10000.0f, 21544.35f,
     * 46415.89f, 100000.0f */
};

/* Actually use full 20-point table up to 100 kHz */
static const float freq_table_full[NUM_FREQS] = {
    1.0f, 4.0f, 10.0f, 40.0f, 100.0f,
    400.0f, 1000.0f, 4000.0f, 10000.0f, 40000.0f,
    100000.0f, 2.15f, 21.5f, 215.0f, 2150.0f,
    21500.0f, 3.16f, 31.6f, 316.0f, 3160.0f
};

esp_err_t eis_init(void)
{
    ESP_LOGI(TAG, "EIS engine: %d electrodes × %d freqs (%.0f Hz - %.0f Hz)",
             NUM_ELECTRODES, NUM_FREQS, FREQ_MIN_HZ, FREQ_MAX_HZ);
    return ESP_OK;
}

esp_err_t eis_sweep(eis_result_t *result)
{
    if (result == NULL) return ESP_ERR_INVALID_ARG;

    memset(result, 0, sizeof(eis_result_t));
    result->timestamp_us = esp_timer_get_time();
    result->exc_amplitude = EIS_EXCITION_AMPLITUDE;

    /* Copy frequency table */
    memcpy(result->freqs, freq_table_full, sizeof(freq_table_full));

    /* Sweep each electrode */
    for (int e = 0; e < NUM_ELECTRODES; e++) {
        ESP_LOGI(TAG, "Sweeping electrode %d/%d...", e + 1, NUM_ELECTRODES);

        /* Connect this electrode to AD5941 */
        mux_select(e);

        /* Small settling delay after switching */
        vTaskDelay(pdMS_TO_TICKS(10));

        /* Run frequency sweep for this electrode */
        uint32_t rtia = 0; /* 0 = auto-select */
        result->rtia[e] = 0;

        esp_err_t ret = ad5941_sweep(result->freqs, NUM_FREQS,
                                       result->exc_amplitude, rtia,
                                       result->spectra[e]);
        if (ret != ESP_OK) {
            ESP_LOGW(TAG, "Electrode %d sweep had errors", e);
            /* Continue with other electrodes */
        }
    }

    /* Disconnect all electrodes for safety */
    mux_disable();

    ESP_LOGI(TAG, "Full EIS sweep complete (%lld ms)",
             (esp_timer_get_time() - result->timestamp_us) / 1000);
    return ESP_OK;
}

esp_err_t eis_sweep_electrode(int electrode, ad5941_z_point_t *results)
{
    if (electrode < 0 || electrode >= NUM_ELECTRODES) {
        return ESP_ERR_INVALID_ARG;
    }

    mux_select(electrode);
    vTaskDelay(pdMS_TO_TICKS(10));

    esp_err_t ret = ad5941_sweep(freq_table_full, NUM_FREQS,
                                   EIS_EXCITION_AMPLITUDE, 0, results);
    mux_disable();
    return ret;
}

const float *eis_get_freq_table(void)
{
    return freq_table_full;
}

float eis_estimate_temperature(const eis_result_t *result,
                                 float ambient_temp_c)
{
    /* Estimate liquid temperature from the shift in low-frequency impedance.
     *
     * Ionic conductivity increases ~2% per °C. We use the 1 Hz impedance
     * of the Ag/AgCl electrode (most ionic-sensitive) as a temperature proxy:
     *   T_liquid ≈ T_ambient + (Z_ref - Z_measured) / (Z_ref × 0.02)
     *
     * This is a rough estimate; for precision, use an external temp probe.
     */
    if (result == NULL) return ambient_temp_c;

    /* Use Ag/AgCl electrode (index 2) at lowest frequency (index 0) */
    float z_low = result->spectra[2][0].z_mag;
    if (isnan(z_low) || z_low <= 0) return ambient_temp_c;

    /* Reference: nominal 1 kΩ at 25°C for 0.01 M KCl */
    const float z_ref_25c = 1000.0f;
    const float temp_coeff = 0.02f; /* 2%/°C */

    float temp_est = 25.0f + (z_ref_25c - z_low) / (z_ref_25c * temp_coeff);

    /* Sanity-clamp to reasonable range */
    if (temp_est < 0.0f) temp_est = 0.0f;
    if (temp_est > 80.0f) temp_est = 80.0f;

    /* Blend with ambient (liquid is close to ambient for small samples) */
    return 0.7f * temp_est + 0.3f * ambient_temp_c;
}