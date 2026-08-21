/*
 * pulse.c — pulse detection, peak extraction, and size binning
 *
 * Works on 512-sample (1 ms) chunks fed from the ADC DMA half/full IRQ.
 * Baseline tracking via IIR; threshold = baseline + 4·σ.
 * Peak detected via local maximum within PULSE_WINDOW_SAMPLES.
 * Peak height (mV above baseline) → size bin via boundaries table.
 */

#include "pulse.h"
#include "calibration.h"
#include <string.h>

static pulse_cb_t cb = NULL;
static float  baseline = 500.0f;    /* mV, init 0.5 V */
static float  noise_sigma = 5.0f;   /* mV */
static float  boundaries[NUM_CHANNELS + 1];  /* bin boundaries in mV */

static float raw_to_mv(uint16_t raw)
{
    return (float)raw / 4095.0f * 3300.0f;
}

void pulse_init(void)
{
    baseline = 500.0f;
    noise_sigma = 5.0f;
    cb = NULL;
    /* Default boundaries (mV) — will be overwritten by calibration */
    /* Index 0 = 0.3 µm ... up to 30 µm at bin 15 */
    boundaries[0] = 30;   boundaries[1] = 50;   boundaries[2] = 80;
    boundaries[3] = 120;  boundaries[4] = 170;  boundaries[5] = 230;
    boundaries[6] = 300;  boundaries[7] = 400;  boundaries[8] = 520;
    boundaries[9] = 680;  boundaries[10] = 880; boundaries[11] = 1100;
    boundaries[12] = 1400; boundaries[13] = 1800; boundaries[14] = 2300;
    boundaries[15] = 2900; boundaries[16] = 3300;
}

void pulse_set_callback(pulse_cb_t callback) { cb = callback; }

void pulse_set_boundaries(const float *b, uint8_t count)
{
    if (count > NUM_CHANNELS + 1) count = NUM_CHANNELS + 1;
    memcpy(boundaries, b, count * sizeof(float));
}

void pulse_get_boundaries(float *out, uint8_t max)
{
    uint8_t n = (max < NUM_CHANNELS + 1) ? max : NUM_CHANNELS + 1;
    memcpy(out, boundaries, n * sizeof(float));
}

float pulse_baseline_mv(void) { return baseline; }
float pulse_noise_sigma_mv(void) { return noise_sigma; }

static uint8_t map_to_bin(float peak_mv)
{
    for (uint8_t i = 0; i < NUM_CHANNELS; ++i) {
        if (peak_mv < boundaries[i + 1]) return i;
    }
    return NUM_CHANNELS - 1;
}

void pulse_process(const uint16_t *buf, uint32_t len)
{
    /* Update baseline (slow IIR on minimum of each chunk) */
    float chunk_min = 3300.0f;
    for (uint32_t i = 0; i < len; ++i) {
        float mv = raw_to_mv(buf[i]);
        if (mv < chunk_min) chunk_min = mv;
    }
    baseline = baseline * 0.95f + chunk_min * 0.05f;

    /* Compute noise sigma from the first 64 samples (assuming no pulse) */
    float sum = 0, sumsq = 0;
    uint32_t n = (len > 64) ? 64 : len;
    for (uint32_t i = 0; i < n; ++i) {
        float mv = raw_to_mv(buf[i]);
        float d = mv - baseline;
        sum += d;
        sumsq += d * d;
    }
    if (n > 1) {
        float mean = sum / (float)n;
        float var = (sumsq / (float)n) - (mean * mean);
        if (var < 0) var = 0;
        noise_sigma = noise_sigma * 0.9f + sqrtf(var) * 0.1f;
    }

    float threshold = baseline + 4.0f * noise_sigma;
    if (threshold < baseline + PULSE_MIN_HEIGHT_MV)
        threshold = baseline + PULSE_MIN_HEIGHT_MV;

    /* Detect pulses */
    uint32_t i = 0;
    while (i < len) {
        float mv = raw_to_mv(buf[i]);
        if (mv > threshold) {
            /* Find peak within window */
            float peak = mv;
            uint32_t peak_i = i;
            uint32_t end = i + PULSE_WINDOW_SAMPLES;
            if (end > len) end = len;
            for (uint32_t j = i + 1; j < end; ++j) {
                float v = raw_to_mv(buf[j]);
                if (v > peak) { peak = v; peak_i = j; }
            }
            float height = peak - baseline;
            if (height > PULSE_MIN_HEIGHT_MV && cb) {
                uint8_t bin = map_to_bin(height);
                cb(bin, height / 1000.0f);   /* pass volts */
            }
            i = peak_i + 2;   /* skip past this pulse */
        } else {
            i++;
        }
    }
}