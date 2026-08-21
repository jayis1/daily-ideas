/*
 * Pulse Hound — RF Signal Hunter
 * spectrum.c — Waterfall ring buffer, decimation, peak-hold
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "spectrum.h"
#include "config.h"
#include <string.h>
#include <math.h>

/* ---- Waterfall ring buffer ---- */
/* 64 rows × 96 columns, each cell is 8-bit intensity (0–255) */
static uint8_t waterfall[WATERFALL_ROWS][WATERFALL_COLS];
static int    waterfall_write_row = 0;
static int    waterfall_full = 0;

/* Peak-hold: tracks the maximum RSSI seen per column over the peak-hold window */
static float  peak_hold_rssi = RSSI_NOISE_FLOOR_DBM;
static uint32_t peak_hold_age_ms = 0;
static float  instantaneous_peak = RSSI_NOISE_FLOOR_DBM;

/* Recent RSSI history (for audio rate + classifier) */
#define HISTORY_LEN 512
static float  rssi_history[HISTORY_LEN];
static int    history_write_idx = 0;
static int    history_count = 0;

/* ---- Map dBm to 8-bit waterfall intensity ---- */
static uint8_t rssi_to_intensity(float rssi_dbm)
{
    /* Map -80 dBm..+5 dBm to 0..255 */
    float range = RSSI_MAX_DBM - RSSI_MIN_DBM;  /* 85 dB */
    float norm = (rssi_dbm - RSSI_MIN_DBM) / range;
    if (norm < 0.0f) norm = 0.0f;
    if (norm > 1.0f) norm = 1.0f;
    /* Gamma correction for better visual contrast */
    float gamma = powf(norm, 0.7f);
    return (uint8_t)(gamma * 255.0f);
}

/* ---- Push a new RSSI sample into the waterfall + history ---- */
void spectrum_push_rssi(float rssi_dbm)
{
    /* Fill the current row across all columns (each row = one sample batch) */
    uint8_t intensity = rssi_to_intensity(rssi_dbm);
    memset(waterfall[waterfall_write_row], intensity, WATERFALL_COLS);

    /* Advance write row */
    waterfall_write_row = (waterfall_write_row + 1) % WATERFALL_ROWS;
    if (waterfall_write_row == 0)
        waterfall_full = 1;

    /* Peak hold */
    if (rssi_dbm > instantaneous_peak)
        instantaneous_peak = rssi_dbm;
    if (rssi_dbm > peak_hold_rssi)
        peak_hold_rssi = rssi_dbm;
    peak_hold_age_ms += WATERFALL_ROW_MS;

    /* History */
    rssi_history[history_write_idx] = rssi_dbm;
    history_write_idx = (history_write_idx + 1) % HISTORY_LEN;
    if (history_count < HISTORY_LEN)
        history_count++;
}

/* ---- Get a row for display (row 0 = newest) ---- */
void spectrum_get_row(int display_row, uint8_t *dest)
{
    /* display_row 0 = newest, WATERFALL_ROWS-1 = oldest */
    int src_row = (waterfall_write_row - 1 - display_row + WATERFALL_ROWS) % WATERFALL_ROWS;
    memcpy(dest, waterfall[src_row], WATERFALL_COLS);
}

int spectrum_get_full(void)
{
    return waterfall_full;
}

/* ---- Peak hold ---- */
float spectrum_get_peak_rssi(void)
{
    return peak_hold_rssi;
}

float spectrum_get_instantaneous_peak(void)
{
    return instantaneous_peak;
}

void spectrum_peak_hold_decay(uint32_t decay_ms)
{
    /* Slowly decay peak hold */
    (void)decay_ms;
    peak_hold_rssi -= 0.5f; /* 0.5 dB per frame decay */
    if (peak_hold_rssi < RSSI_NOISE_FLOOR_DBM)
        peak_hold_rssi = RSSI_NOISE_FLOOR_DBM;
    instantaneous_peak = RSSI_NOISE_FLOOR_DBM;
}

void spectrum_peak_hold_reset(void)
{
    peak_hold_rssi = RSSI_NOISE_FLOOR_DBM;
    instantaneous_peak = RSSI_NOISE_FLOOR_DBM;
}

/* ---- RSSI history access (for classifier + audio) ---- */
int spectrum_get_history(float *dest, int max_count)
{
    int n = history_count < max_count ? history_count : max_count;
    /* Copy in chronological order (oldest first) */
    int start = (history_write_idx - n + HISTORY_LEN) % HISTORY_LEN;
    for (int i = 0; i < n; i++) {
        dest[i] = rssi_history[(start + i) % HISTORY_LEN];
    }
    return n;
}

/* ---- Statistics ---- */
float spectrum_avg_rssi(void)
{
    if (history_count == 0) return RSSI_NOISE_FLOOR_DBM;
    float sum = 0.0f;
    int start = (history_write_idx - history_count + HISTORY_LEN) % HISTORY_LEN;
    for (int i = 0; i < history_count; i++)
        sum += rssi_history[(start + i) % HISTORY_LEN];
    return sum / history_count;
}

float spectrum_max_rssi(void)
{
    if (history_count == 0) return RSSI_NOISE_FLOOR_DBM;
    float mx = RSSI_NOISE_FLOOR_DBM;
    int start = (history_write_idx - history_count + HISTORY_LEN) % HISTORY_LEN;
    for (int i = 0; i < history_count; i++) {
        float v = rssi_history[(start + i) % HISTORY_LEN];
        if (v > mx) mx = v;
    }
    return mx;
}

/* ---- Reset ---- */
void spectrum_reset(void)
{
    memset(waterfall, 0, sizeof(waterfall));
    waterfall_write_row = 0;
    waterfall_full = 0;
    peak_hold_rssi = RSSI_NOISE_FLOOR_DBM;
    instantaneous_peak = RSSI_NOISE_FLOOR_DBM;
    history_write_idx = 0;
    history_count = 0;
}