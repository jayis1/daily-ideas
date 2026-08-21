/*
 * kappa-pin / firmware / main / flash_store.c
 * NVS-backed persistent storage for calibration and settings
 *
 * MIT License.
 */
#include "flash_store.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include <string.h>

static const char *TAG = "flash";
static flash_config_t config;
static nvs_handle_t nvs;

static const char *NVS_NAMESPACE = "kappa";
static const char *KEY_CONFIG = "cfg";

void flash_store_init(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES) {
        nvs_flash_erase();
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ret = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        /* Set defaults */
        config.calibration_factor = 1.0f;
        config.cal_offset = 0.0f;
        config.heater_resistance = 1.0f;
        config.rtd_r0 = 1000.0f;
        config.last_material = 0;
        config.cal_timestamp = 0;
        strcpy(config.cal_ref_material, "");
        config.total_measurements = 0;
        return;
    }

    /* Load config */
    size_t len = sizeof(config);
    ret = nvs_get_blob(nvs, KEY_CONFIG, &config, &len);
    if (ret != ESP_OK || len != sizeof(config)) {
        ESP_LOGI(TAG, "No saved config, using defaults");
        config.calibration_factor = 1.0f;
        config.cal_offset = 0.0f;
        config.heater_resistance = 1.0f;
        config.rtd_r0 = 1000.0f;
        config.last_material = 0;
        config.cal_timestamp = 0;
        strcpy(config.cal_ref_material, "");
        config.total_measurements = 0;
        flash_store_save(&config);
    }

    ESP_LOGI(TAG, "Config loaded: CF=%.4f, R_heat=%.3f, total_meas=%lu",
             config.calibration_factor, config.heater_resistance,
             (unsigned long)config.total_measurements);
}

const flash_config_t *flash_store_get(void)
{
    return &config;
}

void flash_store_save(const flash_config_t *cfg)
{
    memcpy(&config, cfg, sizeof(config));
    esp_err_t ret = nvs_set_blob(nvs, KEY_CONFIG, &config, sizeof(config));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS save failed: %s", esp_err_to_name(ret));
        return;
    }
    nvs_commit(nvs);
    ESP_LOGI(TAG, "Config saved");
}

void flash_store_set_calibration(float cf, float offset, const char *ref)
{
    config.calibration_factor = cf;
    config.cal_offset = offset;
    if (ref) {
        strncpy(config.cal_ref_material, ref, sizeof(config.cal_ref_material) - 1);
        config.cal_ref_material[sizeof(config.cal_ref_material) - 1] = '\0';
    }
    config.cal_timestamp = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS / 1000);
    flash_store_save(&config);
    ESP_LOGI(TAG, "Calibration updated: CF=%.4f, offset=%.4f, ref=%s",
             cf, offset, ref ? ref : "");
}

void flash_store_set_probe(float heater_r, float rtd_r0)
{
    config.heater_resistance = heater_r;
    config.rtd_r0 = rtd_r0;
    flash_store_save(&config);
}

void flash_store_increment_measurements(void)
{
    config.total_measurements++;
    flash_store_save(&config);
}

void flash_store_reset(void)
{
    config.calibration_factor = 1.0f;
    config.cal_offset = 0.0f;
    config.heater_resistance = 1.0f;
    config.rtd_r0 = 1000.0f;
    config.last_material = 0;
    config.cal_timestamp = 0;
    strcpy(config.cal_ref_material, "");
    config.total_measurements = 0;
    flash_store_save(&config);
    ESP_LOGI(TAG, "Config reset to defaults");
}