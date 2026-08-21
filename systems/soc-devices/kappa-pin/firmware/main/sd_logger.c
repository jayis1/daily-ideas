/*
 * kappa-pin / firmware / main / sd_logger.c
 * MicroSD FAT32 CSV + binary logging
 *
 * MIT License.
 */
#include "sd_logger.h"
#include "esp_log.h"
#include "driver/sdspi.h"
#include "driver/sdmmc_host.h"
#include "fatfs/ff.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

static const char *TAG = "sdlog";

static bool mounted = false;
static char current_filename[64];
static FIL current_file;
static bool file_open = false;

sd_err_t sd_logger_init(void)
{
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    sdspi_device_config_t slot_cfg = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot_cfg.gpio_cs = SD_CS_PIN;
    slot_cfg.host_id = SPI_HOST;

    esp_vfs_fat_sdmmc_mount_config_t mount_cfg = {
        .format_if_mount_failed = false,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024,
    };

    sdmmc_card_t *card;
    esp_err_t ret = esp_vfs_fat_sdspi_mount("/sdcard", &host, &slot_cfg, &mount_cfg, &card);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SD mount failed: %s", esp_err_to_name(ret));
        return SD_ERR_MOUNT;
    }

    mounted = true;
    ESP_LOGI(TAG, "SD card mounted at /sdcard");
    return SD_OK;
}

sd_err_t sd_logger_start(const meas_result_t *header, material_t mat)
{
    if (!mounted) return SD_ERR_NOTMOUNTED;

    /* Generate filename with timestamp */
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    snprintf(current_filename, sizeof(current_filename),
             "/sdcard/KP_%04d%02d%02d_%02d%02d%02d.csv",
             t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
             t->tm_hour, t->tm_min, t->tm_sec);

    FRESULT fr = f_open(&current_file, current_filename, FA_WRITE | FA_CREATE_NEW);
    if (fr != FR_OK) {
        ESP_LOGE(TAG, "File open failed: %d", fr);
        return SD_ERR_OPEN;
    }
    file_open = true;

    /* Write header */
    char buf[256];
    int len = snprintf(buf, sizeof(buf),
        "# Kappa Pin measurement log\n"
        "# Date: %04d-%02d-%02dT%02d:%02d:%02d\n"
        "# Probe: %d\n"
        "# Material: %d\n"
        "# Power: %.3f W\n"
        "# Pulse: %.1f s\n"
        "# T0: %.4f C\n"
        "# Columns: t_s,T_C,dT_mK,V_heater_V,I_heater_A,Q_W\n",
        t->tm_year+1900, t->tm_mon+1, t->tm_mday,
        t->tm_hour, t->tm_min, t->tm_sec,
        header->probe_type, (int)mat,
        header->avg_power_w, header->pulse_duration_s,
        header->t0_c);

    UINT written;
    f_write(&current_file, buf, len, &written);

    ESP_LOGI(TAG, "Started log: %s", current_filename);
    return SD_OK;
}

sd_err_t sd_logger_write_sample(const meas_sample_t *s)
{
    if (!file_open) return SD_ERR_NOTMOUNTED;

    char buf[128];
    int len = snprintf(buf, sizeof(buf),
        "%.4f,%.4f,%.2f,%.4f,%.4f,%.4f\n",
        s->t_s, s->temp_c, s->dt_mk, s->v_heater, s->i_heater, s->q_w);

    UINT written;
    FRESULT fr = f_write(&current_file, buf, len, &written);
    if (fr != FR_OK) return SD_ERR_WRITE;

    return SD_OK;
}

sd_err_t sd_logger_write_result(const meas_result_t *r)
{
    if (!file_open) return SD_ERR_NOTMOUNTED;

    char buf[256];
    int len = snprintf(buf, sizeof(buf),
        "# Result:\n"
        "# lambda=%.4f W/m.K\n"
        "# alpha=%.4f mm2/s\n"
        "# rhoCp=%.4e J/m3.K\n"
        "# effusivity=%.1f J/m2.K.s0.5\n"
        "# R2=%.5f\n"
        "# n_points=%d\n"
        "# END\n",
        r->lambda, r->alpha, r->rho_cp, r->effusivity,
        r->r_squared, r->n_points);

    UINT written;
    f_write(&current_file, buf, len, &written);
    f_sync(&current_file);

    return SD_OK;
}

sd_err_t sd_logger_close(void)
{
    if (!file_open) return SD_OK;
    f_close(&current_file);
    file_open = false;
    ESP_LOGI(TAG, "Closed log: %s", current_filename);
    return SD_OK;
}

bool sd_logger_is_mounted(void)
{
    return mounted;
}

const char *sd_logger_last_filename(void)
{
    return current_filename;
}