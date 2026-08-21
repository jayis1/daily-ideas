/* sd_log.c — microSD chromatogram CSV logging
 *
 * Uses ESP-IDF FATFS on SPI2 (separate bus from the ADS122U04's SPI1).
 * Each run produces:
 *   /sdcard/RUN_NNNN.csv       — chromatogram (time_s, raw_uv, baseline_uv, corrected_uv)
 *   /sdcard/RUN_NNNN_meta.txt  — peak table + run metadata
 */
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include "esp_log.h"
#include "esp_vfs_fat.h"
#include "driver/sdspi_host.h"
#include "sdmmc_cmd.h"

#include "sdkconfig.h"
#include "sd_log.h"
#include "library.h"

static const char *TAG = "sd_log";
static sdmmc_card_t *s_card = NULL;
static int s_run_counter = 0;

#define SD_PIN_CS    20
#define SD_PIN_SCLK  21
#define SD_PIN_MOSI  11
#define SD_PIN_MISO  12
#define SD_MOUNT     "/sdcard"

void sd_init(void)
{
    ESP_LOGI(TAG, "Initializing microSD (SPI2)");

    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    host.slot = SPI3_HOST;
    sdspi_device_config_t dev = {
        .host_id = SPI3_HOST,
        .gpio_cs = SD_PIN_CS,
        .gpio_cd = SDSPI_SLOT_NO_CD,
        .gpio_wp = SDSPI_SLOT_NO_WP,
    };
    spi_bus_config_t bus = {
        .miso_io_num = SD_PIN_MISO,
        .mosi_io_num = SD_PIN_MOSI,
        .sclk_io_num = SD_PIN_SCLK,
        .max_transfer_sz = 4096,
    };
    esp_err_t ret = spi_bus_initialize(SPI3_HOST, &bus, SDSPI_DEFAULT_DMA);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        return;
    }
    ret = sdspi_host_init();
    if (ret != ESP_OK) { ESP_LOGE(TAG, "sdspi init: %s", esp_err_to_name(ret)); return; }

    sdspi_dev_handle_t handle;
    ret = sdspi_host_add_device(&host, &dev, &handle, &s_card);
    if (ret != ESP_OK) { ESP_LOGE(TAG, "sdspi dev: %s", esp_err_to_name(ret)); return; }

    esp_vfs_fat_sdmmc_mount_config_t mcfg = {
        .format_if_mount_failed = false,
        .max_files = 5,
    };
    ret = esp_vfs_fat_sdspi_mount(SD_MOUNT, &host, &handle, &mcfg, &s_card);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "mount failed: %s", esp_err_to_name(ret));
        return;
    }
    ESP_LOGI(TAG, "SD mounted: %s", SD_MOUNT);

    /* Find highest existing run number */
    for (int i = 9999; i >= 1; i--) {
        char path[40];
        snprintf(path, sizeof(path), SD_MOUNT "/RUN_%04d.csv", i);
        struct stat st;
        if (stat(path, &st) == 0) { s_run_counter = i; break; }
    }
    ESP_LOGI(TAG, "Next run: %d", s_run_counter + 1);
}

int sd_save_run(const tcd_sample_t *samples, int n_samples,
                const peak_t *peaks, int n_peaks,
                const identification_t *ids, int n_ids,
                float sample_vol_ml, const char *method_name,
                float battery_mv, float ambient_temp_c)
{
    if (!s_card) { ESP_LOGE(TAG, "SD not mounted"); return -1; }

    int run = ++s_run_counter;
    char path[48];

    /* Chromatogram CSV */
    snprintf(path, sizeof(path), SD_MOUNT "/RUN_%04d.csv", run);
    FILE *f = fopen(path, "w");
    if (!f) { ESP_LOGE(TAG, "Cannot write %s", path); return -1; }

    fprintf(f, "# Plume Sniffer Run %04d\n", run);
    fprintf(f, "# Method: %s\n", method_name);
    fprintf(f, "# Sample volume: %.1f mL\n", sample_vol_ml);
    fprintf(f, "# Battery: %.0f mV\n", battery_mv);
    fprintf(f, "# Ambient: %.1f C\n", ambient_temp_c);
    fprintf(f, "# Samples: %d @ %d Hz\n", n_samples, PLUME_TCD_SAMPLE_HZ);
    fprintf(f, "time_s,raw_uv,baseline_uv,corrected_uv\n");
    for (int i = 0; i < n_samples; i++) {
        float t = (float)(samples[i].timestamp_us - samples[0].timestamp_us) / 1e6f;
        fprintf(f, "%.3f,%d,%.1f,%.1f\n", t,
                samples[i].microvolts, samples[i].baseline_uv,
                samples[i].corrected_uv);
    }
    fclose(f);

    /* Metadata / peak table */
    snprintf(path, sizeof(path), SD_MOUNT "/RUN_%04d_meta.txt", run);
    f = fopen(path, "w");
    if (f) {
        fprintf(f, "Plume Sniffer Run %04d\n", run);
        fprintf(f, "Method: %s\n", method_name);
        fprintf(f, "Sample volume: %.1f mL\n", sample_vol_ml);
        fprintf(f, "Battery: %.0f mV\n", battery_mv);
        fprintf(f, "Ambient temp: %.1f C\n", ambient_temp_c);
        fprintf(f, "Peaks detected: %d\n\n", n_peaks);
        fprintf(f, "tR_s\tRI\tCompound\t\tConc_ppm\tArea_uVs\tHeight_uV\n");
        for (int i = 0; i < n_ids; i++) {
            const char *name = ids[i].n_matches > 0
                ? library_get(ids[i].matches[0].index)->name : "unknown";
            fprintf(f, "%.1f\t%.0f\t%-16s\t%.0f\t%.0f\t%.0f\n",
                    ids[i].retention_s, ids[i].retention_index,
                    name, ids[i].est_conc_ppm,
                    ids[i].area_uv_s, ids[i].height_uv);
        }
        fclose(f);
    }

    ESP_LOGI(TAG, "Run %04d saved: %d samples, %d peaks", run, n_samples, n_peaks);
    return run;
}

int sd_list_runs(char *out, int max_len)
{
    if (!s_card) { return 0; }
    int n = 0, off = 0;
    for (int i = 1; i <= s_run_counter; i++) {
        char path[48];
        snprintf(path, sizeof(path), SD_MOUNT "/RUN_%04d.csv", i);
        struct stat st;
        if (stat(path, &st) == 0) {
            int w = snprintf(out + off, max_len - off, "RUN_%04d (%ld bytes)\n", i, (long)st.st_size);
            if (w < 0 || off + w >= max_len) break;
            off += w; n++;
        }
    }
    return n;
}