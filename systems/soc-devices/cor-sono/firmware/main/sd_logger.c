/*
 * cor-sono / firmware / sd_logger.c
 * MicroSD WAV + CSV logging (FAT32 via SPI)
 * Writes stereo WAV (contact + ambient) + classification CSV
 */
#include "main.h"
#include "sd_logger.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/sdspi_host.h"
#include "driver/sdspi_device.h"
#include "esp_vfs_fat.h"
#include "sdkconfig.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

static const char *TAG = "sd";

#define SD_CS    16
#define SD_CLK   13
#define SD_MOSI  15
#define SD_MISO  14
#define MOUNT    "/sdcard"

static sdmmc_card_t *card;
static FILE *wav_fp = NULL;
static FILE *csv_fp = NULL;
static uint32_t wav_samples = 0;

/* ---- WAV header ---- */
typedef struct __attribute__((packed)) {
    char     riff[4];   uint32_t riff_sz;
    char     wave[4];
    char     fmt[4];    uint32_t fmt_sz;
    uint16_t audio_fmt; uint16_t n_ch;
    uint32_t sr;        uint32_t byte_rate;
    uint16_t block_align; uint16_t bits;
    char     data[4];   uint32_t data_sz;
} wav_hdr_t;

static void write_wav_header(FILE *f, int sr, int n_ch)
{
    wav_hdr_t h = {0};
    memcpy(h.riff, "RIFF", 4); memcpy(h.wave, "WAVE", 4);
    memcpy(h.fmt, "fmt ", 4);  memcpy(h.data, "data", 4);
    h.fmt_sz = 16; h.audio_fmt = 1; h.n_ch = n_ch;
    h.sr = sr; h.bits = 16; h.block_align = n_ch * 2; h.byte_rate = sr * n_ch * 2;
    h.data_sz = 0; h.riff_sz = 36;
    fwrite(&h, sizeof(h), 1, f);
}

static void finalize_wav_header(FILE *f, uint32_t data_bytes)
{
    wav_hdr_t h;
    fseek(f, 0, SEEK_SET);
    fread(&h, sizeof(h), 1, f);
    h.data_sz = data_bytes;
    h.riff_sz = 36 + data_bytes;
    fseek(f, 0, SEEK_SET);
    fwrite(&h, sizeof(h), 1, f);
}

void sd_logger_init(void)
{
    ESP_LOGI(TAG, "init MicroSD (SPI)");

    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    spi_bus_config_t buscfg = {
        .mosi_io_num = SD_MOSI, .miso_io_num = SD_MISO,
        .sclk_io_num = SD_CLK, .max_transfer_sz = 4096,
    };
    esp_err_t ret = spi_bus_initialize(host.slot, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "SPI bus init: %s", esp_err_to_name(ret));
        g_ctx.sd_present = false;
        return;
    }

    sdspi_device_config_t dev = SDSPI_DEVICE_CONFIG_DEFAULT();
    dev.host_cs = SD_CS; dev.gpio_cs = SD_CS; dev.gpio_int = -1;
    sdspi_dev_handle_t sdspi_handle;
    sdspi_host_init_device(&dev, &sdspi_handle);

    sdmmc_card_t *c;
    if (sdspi_host_get_card(sdspi_handle, &c) != ESP_OK) {
        ESP_LOGW(TAG, "SD card not detected");
        g_ctx.sd_present = false;
        return;
    }
    card = c;

    esp_vfs_fat_sdmmc_mount_config_t mcfg = {
        .format_if_mount_failed = false, .max_files = 5,
    };
    if (esp_vfs_fat_sdmmc_mount(MOUNT, &host, &dev, &mcfg, &card) != ESP_OK) {
        ESP_LOGW(TAG, "SD mount failed");
        g_ctx.sd_present = false;
        return;
    }
    g_ctx.sd_present = true;
    ESP_LOGI(TAG, "SD mounted: %s", card->cid.name);
}

static void make_filename(char *buf, size_t sz, const char *ext)
{
    time_t now = 0;  /* would use RTC */
    struct tm *t = gmtime(&now);
    snprintf(buf, sz, "%s/CS_%04d%02d%02d_%02d%02d%02d.%s",
             MOUNT, t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
             t->tm_hour, t->tm_min, t->tm_sec, ext);
}

void sd_logger_start_recording(void)
{
    if (!g_ctx.sd_present) return;

    char wname[64], cname[64];
    make_filename(wname, sizeof(wname), "wav");
    make_filename(cname, sizeof(cname), "csv");

    wav_fp = fopen(wname, "wb");
    csv_fp = fopen(cname, "w");
    if (!wav_fp || !csv_fp) {
        ESP_LOGE(TAG, "cannot open files");
        g_ctx.sd_present = false;
        return;
    }
    write_wav_header(wav_fp, SAMPLE_RATE, 2);
    wav_samples = 0;

    /* CSV header */
    fprintf(csv_fp, "# Cor Sono classification log\n");
    fprintf(csv_fp, "# Mode: %s\n",
            g_ctx.mode == MODE_HEART ? "heart" :
            g_ctx.mode == MODE_LUNG ? "lung" : "mixed");
    fprintf(csv_fp, "# Columns: t_s, class_id, class_name, confidence\n");
}

void sd_logger_write_block(const int16_t *contact, const int16_t *ambient, int n)
{
    if (!wav_fp) return;
    /* Interleave stereo */
    for (int i = 0; i < n; i++) {
        fwrite(&contact[i], 2, 1, wav_fp);
        fwrite(&ambient[i], 2, 1, wav_fp);
    }
    wav_samples += n;
}

void sd_logger_log_result(int class_id, int confidence, int hr)
{
    if (!csv_fp) return;
    float t = (float)wav_samples / SAMPLE_RATE;
    fprintf(csv_fp, "%.2f,%d,%s,%d\n", t, class_id, CLASS_NAMES[class_id], confidence);
}

void sd_logger_stop_recording(void)
{
    if (wav_fp) {
        finalize_wav_header(wav_fp, wav_samples * 2 * 2);
        fclose(wav_fp); wav_fp = NULL;
    }
    if (csv_fp) {
        fprintf(csv_fp, "# Summary: HR=%d, final_class=%s\n",
                g_ctx.heart_rate, CLASS_NAMES[g_ctx.class_id]);
        fprintf(csv_fp, "# END\n");
        fclose(csv_fp); csv_fp = NULL;
    }
    ESP_LOGI(TAG, "recording saved");
}