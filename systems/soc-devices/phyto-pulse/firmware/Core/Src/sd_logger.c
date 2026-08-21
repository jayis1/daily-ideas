/*
 * sd_logger.c — SD card logging
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Uses FatFs via SPI2 (microSD).
 * Raw data: binary file with header + 16-bit samples + 32-bit timestamps
 * Events: CSV with timestamp, type, amplitude, duration, area, class, confidence
 */

#include "sd_logger.h"
#include "main.h"
#include "fatfs.h"
#include <string.h>
#include <stdio.h>

extern FATFS   fatfs;
extern FIL     sd_file;

static FIL g_raw_file;
static FIL g_event_file;
static bool g_session_active = false;
static char g_session_name[32];
static char g_raw_filename[48];
static char g_event_filename[48];
static uint16_t g_session_counter;

/* Raw data header (16 bytes) */
typedef struct {
    char     magic[4];       /* "PHYTO" truncated to 4: "PHYT" */
    uint16_t version;        /* 1 */
    uint16_t sample_rate;    /* 1000 Hz */
    uint16_t ina_gain;       /* INA gain × 100 */
    uint8_t  pga;            /* ADS1256 PGA setting */
    uint8_t  reserved;
    uint32_t start_timestamp; /* HAL tick at start */
} raw_header_t;

int sd_logger_init(void)
{
    g_session_active = false;
    g_session_counter = 0;
    return 0;
}

bool sd_logger_card_present(void)
{
    return (HAL_GPIO_ReadPin(SD_DETECT_GPIO_Port, SD_DETECT_Pin) == GPIO_PIN_RESET);
}

int sd_logger_start_session(void)
{
    if (!sd_logger_card_present()) return -1;

    /* Generate session name based on counter */
    g_session_counter++;
    snprintf(g_session_name, sizeof(g_session_name), "SESS_%04d",
             g_session_counter);
    snprintf(g_raw_filename, sizeof(g_raw_filename), "0:/RAW_%04d.BIN",
             g_session_counter);
    snprintf(g_event_filename, sizeof(g_event_filename), "0:/EVENTS_%04d.CSV",
             g_session_counter);

    /* Open raw binary file */
    if (f_open(&g_raw_file, g_raw_filename, FA_WRITE | FA_CREATE_ALWAYS) != FR_OK)
        return -1;

    /* Write raw header */
    raw_header_t hdr = {
        .magic = "PHYT",
        .version = 1,
        .sample_rate = 1000,
        .ina_gain = 10100,
        .pga = 6,
        .reserved = 0,
        .start_timestamp = HAL_GetTick(),
    };
    UINT bw;
    f_write(&g_raw_file, &hdr, sizeof(hdr), &bw);

    /* Open events CSV */
    if (f_open(&g_event_file, g_event_filename, FA_WRITE | FA_CREATE_ALWAYS) != FR_OK) {
        f_close(&g_raw_file);
        return -1;
    }
    /* CSV header */
    const char *csv_hdr = "timestamp_ms,sample_idx,amp_mV,duration_ms,area_mVms,"
                           "rise_ms,decay_tau_ms,asymmetry,class,confidence\n";
    f_write(&g_event_file, csv_hdr, strlen(csv_hdr), &bw);
    f_sync(&g_event_file);

    g_session_active = true;
    return 0;
}

int sd_logger_log_sample(int32_t sample_idx, float voltage_mv, uint32_t timestamp_ms)
{
    if (!g_session_active) return -1;

    /* Store as: int16_t mV (scaled ×100 for 0.01 mV resolution) + uint32_t timestamp */
    int16_t mv_scaled = (int16_t)(voltage_mv * 100.0f);
    uint32_t ts = timestamp_ms;

    UINT bw;
    f_write(&g_raw_file, &mv_scaled, 2, &bw);
    f_write(&g_raw_file, &ts, 4, &bw);

    /* Sync every 1000 samples (1 s) to limit write frequency */
    if ((sample_idx % 1000) == 0) {
        f_sync(&g_raw_file);
    }
    return 0;
}

int sd_logger_log_event(const spike_event_t *event)
{
    if (!g_session_active) return -1;

    char line[192];
    const char *cls = (event->classification == EVENT_AP) ? "AP" :
                      (event->classification == EVENT_VP) ? "VP" : "ART";
    snprintf(line, sizeof(line), "%lu,%ld,%.3f,%.1f,%.2f,%.1f,%.1f,%.3f,%s,%.3f\n",
             (unsigned long)event->timestamp_ms,
             (long)event->sample_index,
             event->amplitude_mv,
             event->duration_ms,
             event->area_mvms,
             event->rise_time_ms,
             event->decay_tau_ms,
             event->asymmetry,
             cls,
             event->confidence);

    UINT bw;
    f_write(&g_event_file, line, strlen(line), &bw);
    f_sync(&g_event_file);
    return 0;
}

int sd_logger_log_swp(const swp_result_t *result)
{
    if (!g_session_active) return -1;

    /* Append SWP to a separate line in event file */
    char line[128];
    snprintf(line, sizeof(line), "# SWP,%lu,%.3f,%.3f,%.3f\n",
             (unsigned long)result->timestamp_ms,
             result->mean_mv,
             result->peak_to_peak,
             result->slope_mV_per_min);

    UINT bw;
    f_write(&g_event_file, line, strlen(line), &bw);
    f_sync(&g_event_file);
    return 0;
}

int sd_logger_stop_session(void)
{
    if (!g_session_active) return -1;
    f_sync(&g_raw_file);
    f_close(&g_raw_file);
    f_sync(&g_event_file);
    f_close(&g_event_file);
    g_session_active = false;
    return 0;
}

uint32_t sd_logger_free_mb(void)
{
    FATFS *fs;
    DWORD free_clust;
    if (f_getfree("0:", &free_clust, &fs) != FR_OK) return 0;
    return (uint32_t)((free_clust * fs->csize) / 2048);  /* MB */
}

const char *sd_logger_session_filename(void)
{
    return g_session_name;
}