/**
 * terra_pin/sdlog.c — SD card FAT32 CSV logging
 *
 * Uses ESP-IDF FATFS with SPI mode on HSPI bus.
 * One CSV file per session, named TERRA_XXXX.CSV
 */

#include "main.h"
#include "esp_log.h"
#include "esp_vfs_fat.h"
#include "driver/sdspi_host.h"
#include "driver/sdmmc_host.h"
#include "sdmmc_cmd.h"
#include <stdio.h>
#include <string.h>

static const char *TAG = "SDLOG";
static sdmmc_card_t *g_card = NULL;
static char g_current_file[32] = "";
static uint32_t g_session_id = 0;

esp_err_t sdlog_init(void)
{
    ESP_LOGI(TAG, "Initializing SD card (SPI mode)");

    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    host.slot = SPI3_HOST;  /* ESP32-S3 HSPI */

    sdspi_device_config_t slot_config = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot_config.gpio_cs = PIN_SD_CS;
    slot_config.host_id = host.slot;

    spi_bus_config_t bus_cfg = {
        .mosi_io_num = PIN_SPI_MOSI,
        .miso_io_num = PIN_SPI_MISO,
        .sclk_io_num = PIN_SPI_SCK,
        .max_transfer_sz = 4000,
    };

    esp_err_t ret = spi_bus_initialize(host.slot, &bus_cfg, SDSPI_DEFAULT_DMA);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = sdspi_host_init();
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "SDSPI init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = sdspi_host_init_device(&slot_config, &g_card);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SD device init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    esp_vfs_fat_sdmmc_mount_config_t mount_cfg = {
        .format_if_mount_failed = true,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024,
    };

    ret = esp_vfs_fat_sdspi_mount("/sd", &host, &slot_config, &mount_cfg, &g_card);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SD mount failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "SD card mounted: %s, %llu MB",
             g_card->cid.name, ((uint64_t)g_card->csd.capacity) / (1024 * 1024));

    /* Find next session ID */
    for (uint32_t i = 1; i < 9999; i++) {
        snprintf(g_current_file, sizeof(g_current_file),
                 "/sd/TERRA_%04lU.CSV", (unsigned long)i);
        FILE *f = fopen(g_current_file, "r");
        if (!f) {
            g_session_id = i;
            break;
        }
        fclose(f);
    }

    /* Write header */
    FILE *f = fopen(g_current_file, "w");
    if (f) {
        fprintf(f, "# Terra Pin soil health log\n");
        fprintf(f, "# session,timestamp,co2_chamber,co2_ambient,flux_ppm_min,"
                "flux_mgC,orp_mv,ec_us,moisture_vwc,temp_c,shi,"
                "shi_resp,shi_redox,shi_ec,shi_moist,shi_temp\n");
        fclose(f);
        ESP_LOGI(TAG, "Log file: %s (session %lu)", g_current_file,
                 (unsigned long)g_session_id);
    }

    return ESP_OK;
}

esp_err_t sdlog_write(const terra_reading_t *r, uint32_t session_id)
{
    if (!g_current_file[0]) return ESP_ERR_INVALID_STATE;

    FILE *f = fopen(g_current_file, "a");
    if (!f) {
        ESP_LOGE(TAG, "Cannot open %s", g_current_file);
        return ESP_FAIL;
    }

    fprintf(f, "%lu,%lu,%u,%u,%.2f,%.1f,%d,%u,%.1f,%.1f,%d,"
               "%.2f,%.2f,%.2f,%.2f,%.2f\n",
            (unsigned long)session_id,
            (unsigned long)r->timestamp,
            r->co2_chamber, r->co2_ambient,
            r->flux_ppm_min, r->flux_mgC,
            r->orp_mv, r->ec_us,
            r->moisture_vwc, r->temp_c, r->shi,
            r->shi_resp, r->shi_redox, r->shi_ec,
            r->shi_moist, r->shi_temp);
    fclose(f);

    return ESP_OK;
}