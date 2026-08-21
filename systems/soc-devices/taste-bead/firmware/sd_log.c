/* sd_log.c — SD card CSV logging for Taste Bead
 *
 * Logs full impedance spectra and classification results to a microSD
 * card in CSV format. Each measurement is one line containing:
 * timestamp, identified label, confidence, 48 features, 100 Z-points (mag+phase)
 */

#include "sd_log.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include "driver/sdspi_host.h"
#include "driver/spi_common.h"
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

static const char *TAG = "sd_log";
static sdmmc_card_t *g_card = NULL;
static char g_log_path[64] = {0};
static FILE *g_log_file = NULL;
static bool g_initialized = false;

esp_err_t sd_init(void)
{
    /* Configure SD card on SPI bus (shared with SD_HOST) */
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    host.slot = SPI3_HOST;
    sdspi_device_config_t slot_config = {
        .gpio_cs = PIN_SD_CS,
        .host_id = SPI3_HOST,
    };

    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_SD_MOSI,
        .miso_io_num = PIN_SD_MISO,
        .sclk_io_num = PIN_SD_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };

    esp_err_t ret = spi_bus_initialize(SPI3_HOST, &buscfg, SDSPI_DEFAULT_DMA);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "SD SPI bus init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = sdspi_host_init_device(&slot_config, &g_card);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "SDSPI init failed: %s — continuing without SD", esp_err_to_name(ret));
        return ret;
    }

    /* Mount FAT filesystem */
    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = false,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024,
    };

    ret = esp_vfs_fat_sdspi_mount("/sdcard", &host, &slot_config,
                                    &mount_config, &g_card);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "SD mount failed: %s — continuing without SD", esp_err_to_name(ret));
        return ret;
    }

    g_initialized = true;
    ESP_LOGI(TAG, "SD card mounted at /sdcard");
    return ESP_OK;
}

bool sd_is_present(void)
{
    return g_initialized && g_card != NULL;
}

esp_err_t sd_open_log(void)
{
    if (!g_initialized) return ESP_ERR_INVALID_STATE;

    /* Generate timestamped filename (use uptime since no RTC by default) */
    int64_t uptime = esp_timer_get_time() / 1000000;
    snprintf(g_log_path, sizeof(g_log_path),
             "/sdcard/taste_bead_%lld.csv", uptime);

    g_log_file = fopen(g_log_path, "w");
    if (g_log_file == NULL) {
        ESP_LOGE(TAG, "Failed to open %s", g_log_path);
        return ESP_FAIL;
    }

    /* Write CSV header */
    fprintf(g_log_file, "timestamp_us,label,confidence,liquid_temp_c,");
    /* Feature columns */
    for (int i = 0; i < NUM_FEATURES; i++) {
        fprintf(g_log_file, "f%d,", i);
    }
    /* Impedance spectra columns: 5 electrodes × 20 freqs × (mag,phase) */
    for (int e = 0; e < NUM_ELECTRODES; e++) {
        for (int f = 0; f < NUM_FREQS; f++) {
            fprintf(g_log_file, "Z_mag_e%d_f%d,Z_phase_e%d_f%d,",
                    e, f, e, f);
        }
    }
    fprintf(g_log_file, "\n");
    fflush(g_log_file);

    ESP_LOGI(TAG, "Log opened: %s", g_log_path);
    return ESP_OK;
}

/* Forward declaration for result_t (defined in main.c) */
typedef struct {
    char label[LIBRARY_MAX_NAME_LEN];
    float confidence;
    float distance;
    int lib_index;
    int64_t timestamp_us;
} result_t;

esp_err_t sd_log_measurement(const eis_result_t *eis,
                               const float features[NUM_FEATURES],
                               const void *result_ptr,
                               const void *ambient_ptr)
{
    if (!g_initialized || g_log_file == NULL) {
        /* Try to open log on first write */
        if (g_log_file == NULL && sd_is_present()) {
            sd_open_log();
        }
        if (g_log_file == NULL) return ESP_ERR_INVALID_STATE;
    }

    const result_t *result = (const result_t *)result_ptr;
    const bme280_data_t *ambient = (const bme280_data_t *)ambient_ptr;

    /* Write data row */
    fprintf(g_log_file, "%lld,%s,%.2f,%.1f,",
            eis->timestamp_us,
            result ? result->label : "unknown",
            result ? result->confidence : 0,
            eis->liquid_temp_c);

    /* Features */
    for (int i = 0; i < NUM_FEATURES; i++) {
        if (isnan(features[i]))
            fprintf(g_log_file, "NaN,");
        else
            fprintf(g_log_file, "%.6f,", features[i]);
    }

    /* Impedance spectra */
    for (int e = 0; e < NUM_ELECTRODES; e++) {
        for (int f = 0; f < NUM_FREQS; f++) {
            float mag = eis->spectra[e][f].z_mag;
            float phase = eis->spectra[e][f].z_phase;
            if (isnan(mag)) fprintf(g_log_file, "NaN,");
            else fprintf(g_log_file, "%.2f,", mag);
            if (isnan(phase)) fprintf(g_log_file, "NaN,");
            else fprintf(g_log_file, "%.2f,", phase);
        }
    }
    fprintf(g_log_file, "\n");

    /* Flush periodically (every write is safe for low-rate measurements) */
    fflush(g_log_file);

    return ESP_OK;
}

esp_err_t sd_close_log(void)
{
    if (g_log_file) {
        fclose(g_log_file);
        g_log_file = NULL;
        ESP_LOGI(TAG, "Log closed: %s", g_log_path);
    }
    return ESP_OK;
}