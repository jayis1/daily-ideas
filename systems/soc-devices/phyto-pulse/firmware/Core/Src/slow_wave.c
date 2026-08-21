/*
 * slow_wave.c — Slow-wave potential analysis
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#include "slow_wave.h"
#include <math.h>
#include <string.h>

/* 60 s window at 1 kHz = 60,000 samples. We accumulate sum and count. */
#define SWP_WINDOW_SAMPLES 60000

static float    g_sum;           /* running sum of samples in window */
static uint32_t g_count;         /* samples in current window */
static uint32_t g_last_update;   /* last SWP output timestamp */
static float    g_window_min;    /* min in current window */
static float    g_window_max;    /* max in current window */
static float    g_prev_mean;     /* previous window mean (for slope) */
static float    g_current_mean;

static swp_result_t g_last_result;
static volatile bool g_result_available;

void slow_wave_init(void)
{
    g_sum = 0;
    g_count = 0;
    g_last_update = 0;
    g_window_min = 1e30f;
    g_window_max = -1e30f;
    g_prev_mean = 0;
    g_current_mean = 0;
    g_result_available = false;
    memset(&g_last_result, 0, sizeof(g_last_result));
}

void slow_wave_feed(float voltage_mv, uint32_t timestamp_ms)
{
    g_sum += voltage_mv;
    g_count++;
    if (voltage_mv < g_window_min) g_window_min = voltage_mv;
    if (voltage_mv > g_window_max) g_window_max = voltage_mv;

    if (timestamp_ms - g_last_update >= SWP_INTERVAL_MS) {
        if (g_count > 0) {
            g_last_result.timestamp_ms = timestamp_ms;
            g_last_result.mean_mv = g_sum / (float)g_count;
            g_last_result.peak_to_peak = g_window_max - g_window_min;

            /* Slope: (current_mean - prev_mean) per minute */
            g_last_result.slope_mV_per_min =
                (g_last_result.mean_mv - g_prev_mean) * 1.0f;
            g_prev_mean = g_last_result.mean_mv;
            g_current_mean = g_last_result.mean_mv;

            g_result_available = true;
        }

        /* Reset window */
        g_sum = 0;
        g_count = 0;
        g_window_min = 1e30f;
        g_window_max = -1e30f;
        g_last_update = timestamp_ms;
    }
}

bool slow_wave_result_available(void)
{
    return g_result_available;
}

bool slow_wave_get_result(swp_result_t *result)
{
    if (!g_result_available) return false;
    *result = g_last_result;
    g_result_available = false;
    return true;
}

float slow_wave_get_current_mean(void)
{
    return g_current_mean;
}