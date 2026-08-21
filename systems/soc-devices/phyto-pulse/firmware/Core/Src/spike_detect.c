/*
 * spike_detect.c — Adaptive threshold spike detection
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Implements:
 *   - IIR bandpass filter (0.5 Hz HP + 100 Hz LP) via FMAC
 *   - Exponentially-weighted moving average baseline (τ = 5 s)
 *   - Adaptive threshold μ + k·σ (k = 5, recomputed every 10 s)
 *   - Threshold crossing + 50 ms refractory period
 *   - Feature extraction: amplitude, duration, area, rise time, decay τ
 */

#include "spike_detect.h"
#include <math.h>
#include <string.h>

/* ---- Configuration ---- */
#define SAMPLE_RATE_HZ    1000
#define REFRACTORY_MS     50
#define REFRACTORY_SAMPLES (REFRACTORY_MS * SAMPLE_RATE_HZ / 1000)  /* 50 */
#define BASELINE_TAU_S    5.0f
#define BASELINE_ALPHA    (1.0f / (BASELINE_TAU_S * SAMPLE_RATE_HZ)) /* 1/5000 */
#define THRESHOLD_RECOMPUTE_MS  10000
#define K_THRESHOLD       5.0f
#define MAX_EVENT_DURATION_MS  12000   /* 12 s max for VP detection */
#define MIN_EVENT_DURATION_MS  2       /* 2 ms minimum */

/* ---- IIR bandpass filter coefficients ----
 * HP: 0.5 Hz, 1st order, fs=1000 Hz
 *   a = [1, -0.99686], b = [0.99843, -0.99843]
 * LP: 100 Hz, 1st order, fs=1000 Hz
 *   a = [1, -0.7546], b = [0.1227, 0.1227]
 * Combined as cascaded biquad (simplified 2nd order):
 */
static float hp_x1 = 0, hp_y1 = 0;
static float lp_x1 = 0, lp_y1 = 0;

static float iir_filter(float x)
{
    /* High-pass: 0.5 Hz */
    float hp_y = 0.9968614f * hp_y1 + 0.9984307f * (x - hp_x1);
    hp_x1 = x; hp_y1 = hp_y;

    /* Low-pass: 100 Hz */
    float lp_y = 0.7546703f * lp_y1 + 0.1226648f * (hp_y + lp_x1);
    lp_x1 = hp_y; lp_y1 = lp_y;

    return lp_y;
}

/* ---- Private state ---- */
static float    g_ring[SPIKE_BUF_SIZE];       /* filtered sample ring buffer */
static int      g_ring_head;                   /* write index */
static float    g_baseline;                    /* EWMA baseline */
static float    g_noise;                        /* running noise σ */
static float    g_threshold_pos;               /* positive threshold */
static float    g_threshold_neg;               /* negative threshold */
static float    g_k = K_THRESHOLD;
static uint32_t g_last_threshold_recompute;
static float    g_noise_accum;
static int      g_noise_count;

/* Spike detection state */
static bool     g_in_event;                    /* currently inside a detected spike */
static int      g_event_start_idx;             /* sample index where event started */
static uint32_t g_event_start_ms;              /* timestamp of event start */
static float    g_event_peak;                  /* peak amplitude during event */
static int      g_event_peak_idx;              /* sample index of peak */
static int      g_last_event_end_sample;       /* for refractory enforcement */
static int      g_sample_counter;              /* total samples processed */

/* Event queue */
static spike_event_t g_events[MAX_EVENTS];
static volatile int  g_event_head;
static volatile int  g_event_tail;

/* Display value (latest filtered sample) */
static float g_display_value;

/* ---- Helpers ---- */

static int ring_idx(int i)
{
    return ((i % SPIKE_BUF_SIZE) + SPIKE_BUF_SIZE) % SPIKE_BUF_SIZE;
}

static void push_event(spike_event_t *ev)
{
    int next = (g_event_head + 1) % MAX_EVENTS;
    if (next != g_event_tail) {
        g_events[g_event_head] = *ev;
        g_event_head = next;
    }
    /* If full, oldest event is dropped (tail stays) */
}

static void recompute_threshold(void)
{
    /* σ = sqrt(E[x²] - (E[x])²) over last 10 s */
    /* Simplified: use accumulated noise estimate */
    if (g_noise_count > 0) {
        float mean_sq = g_noise_accum / g_noise_count;
        g_noise = sqrtf(mean_sq);
        g_threshold_pos = g_baseline + g_k * g_noise;
        g_threshold_neg = g_baseline - g_k * g_noise;
    }
    g_noise_accum = 0;
    g_noise_count = 0;
}

static float compute_decay_tau(float *window, int start, int peak, int end)
{
    /* Fit exponential decay from peak to end: y(t) = A * exp(-t/τ) + offset
     * Simplified: log(y - offset) vs t linear fit */
    if (end - peak < 5) return 0.0f;

    /* Use 80% of decay span for fitting */
    int fit_start = peak;
    int fit_end = peak + (int)((end - peak) * 0.8);
    if (fit_end - fit_start < 3) return 0.0f;

    float y0 = window[ring_idx(fit_start)] - g_baseline;
    if (fabsf(y0) < 1e-6f) return 0.0f;

    /* Single-point τ estimate at 37% decay */
    for (int i = fit_start + 1; i <= fit_end; i++) {
        float y = window[ring_idx(i)] - g_baseline;
        if (fabsf(y) <= fabsf(y0) * 0.368f) {
            return (float)(i - fit_start) * 1000.0f / SAMPLE_RATE_HZ;
        }
    }
    return (float)(fit_end - fit_start) * 1000.0f / SAMPLE_RATE_HZ;
}

static void extract_event(int start_idx, int peak_idx, int end_idx,
                          uint32_t start_ms, uint32_t end_ms)
{
    spike_event_t ev;
    ev.timestamp_ms = start_ms;
    ev.sample_index = start_idx;

    /* Amplitude = peak relative to baseline */
    float peak_val = g_ring[ring_idx(peak_idx)];
    ev.amplitude_mv = peak_val - g_baseline;

    /* Duration */
    ev.duration_ms = (float)(end_ms - start_ms);

    /* Area = trapezoidal integration over event window */
    float area = 0;
    for (int i = start_idx; i < end_idx; i++) {
        float v1 = g_ring[ring_idx(i)] - g_baseline;
        float v2 = g_ring[ring_idx(i + 1)] - g_baseline;
        area += 0.5f * (v1 + v2) * (1000.0f / SAMPLE_RATE_HZ);
    }
    ev.area_mvms = area;

    /* Rise time (10% → 90%) */
    int rise10 = start_idx, rise90 = peak_idx;
    float peak_amp = fabsf(ev.amplitude_mv);
    if (peak_amp > 1e-6f) {
        for (int i = start_idx; i <= peak_idx; i++) {
            float frac = fabsf(g_ring[ring_idx(i)] - g_baseline) / peak_amp;
            if (frac >= 0.10f && rise10 == start_idx) rise10 = i;
            if (frac >= 0.90f) { rise90 = i; break; }
        }
    }
    ev.rise_time_ms = (float)(rise90 - rise10) * 1000.0f / SAMPLE_RATE_HZ;

    /* Decay tau */
    ev.decay_tau_ms = compute_decay_tau(g_ring, peak_idx, peak_idx, end_idx);

    /* Asymmetry = rise / (rise + decay) */
    float rise_ms = ev.rise_time_ms;
    float decay_ms = (float)(end_idx - peak_idx) * 1000.0f / SAMPLE_RATE_HZ;
    if (rise_ms + decay_ms > 1e-6f)
        ev.asymmetry = rise_ms / (rise_ms + decay_ms);
    else
        ev.asymmetry = 0.5f;

    /* Classification is set by spike_classify() later; default to AP */
    ev.classification = EVENT_AP;
    ev.confidence = 0.0f;

    push_event(&ev);
}

/* ---- Public API ---- */

void spike_detect_init(void)
{
    memset(g_ring, 0, sizeof(g_ring));
    g_ring_head = 0;
    g_baseline = 0;
    g_noise = 1.0f;  /* initial guess */
    g_threshold_pos = 5.0f;
    g_threshold_neg = -5.0f;
    g_k = K_THRESHOLD;
    g_in_event = false;
    g_event_start_idx = 0;
    g_event_start_ms = 0;
    g_event_peak = 0;
    g_event_peak_idx = 0;
    g_last_event_end_sample = -10000;
    g_sample_counter = 0;
    g_event_head = 0;
    g_event_tail = 0;
    g_last_threshold_recompute = 0;
    g_noise_accum = 0;
    g_noise_count = 0;
    hp_x1 = hp_y1 = lp_x1 = lp_y1 = 0;
    g_display_value = 0;
}

void spike_detect_feed(float voltage_mv, uint32_t timestamp_ms, int32_t sample_idx)
{
    /* 1. Bandpass filter */
    float filtered = iir_filter(voltage_mv);

    /* Store in ring buffer */
    g_ring[g_ring_head] = filtered;
    g_display_value = filtered;
    g_ring_head = ring_idx(g_ring_head + 1);

    /* 2. Update baseline (EWMA) */
    g_baseline += BASELINE_ALPHA * (filtered - g_baseline);

    /* 3. Update noise estimate (for threshold recompute) */
    float dev = filtered - g_baseline;
    g_noise_accum += dev * dev;
    g_noise_count++;

    /* 4. Recompute threshold periodically */
    if (timestamp_ms - g_last_threshold_recompute >= THRESHOLD_RECOMPUTE_MS) {
        recompute_threshold();
        g_last_threshold_recompute = timestamp_ms;
    }

    /* 5. Spike detection */
    if (!g_in_event) {
        /* Check for threshold crossing (positive or negative) */
        if ((filtered > g_threshold_pos || filtered < g_threshold_neg) &&
            (sample_idx - g_last_event_end_sample) > REFRACTORY_SAMPLES) {
            g_in_event = true;
            g_event_start_idx = sample_idx;
            g_event_start_ms = timestamp_ms;
            g_event_peak = filtered;
            g_event_peak_idx = sample_idx;
        }
    } else {
        /* Track peak */
        if (fabsf(filtered - g_baseline) > fabsf(g_event_peak - g_baseline)) {
            g_event_peak = filtered;
            g_event_peak_idx = sample_idx;
        }

        /* Check for return to baseline (within 1σ) */
        bool back_to_baseline = (fabsf(filtered - g_baseline) < g_noise);
        float duration_ms = (float)(timestamp_ms - g_event_start_ms);

        if (back_to_baseline || duration_ms > MAX_EVENT_DURATION_MS) {
            g_in_event = false;
            int end_idx = sample_idx;

            /* Validate minimum duration */
            if (duration_ms >= MIN_EVENT_DURATION_MS) {
                extract_event(g_event_start_idx, g_event_peak_idx,
                              end_idx, g_event_start_ms, timestamp_ms);
            }
            g_last_event_end_sample = sample_idx;
        }
    }

    g_sample_counter++;
}

bool spike_detect_event_available(void)
{
    return g_event_head != g_event_tail;
}

bool spike_detect_get_event(spike_event_t *event)
{
    if (g_event_head == g_event_tail) return false;
    *event = g_events[g_event_tail];
    g_event_tail = (g_event_tail + 1) % MAX_EVENTS;
    return true;
}

float spike_detect_get_baseline(void)    { return g_baseline; }
float spike_detect_get_threshold(void)   { return g_threshold_pos; }
float spike_detect_get_noise(void)       { return g_noise; }
float spike_detect_get_display_value(void) { return g_display_value; }

void spike_detect_set_sensitivity(float k)
{
    g_k = k;
}

int spike_detect_get_window(float *buffer, int max_samples)
{
    int n = (max_samples < SPIKE_BUF_SIZE) ? max_samples : SPIKE_BUF_SIZE;
    int start = ring_idx(g_ring_head - n);
    for (int i = 0; i < n; i++) {
        buffer[i] = g_ring[ring_idx(start + i)];
    }
    return n;
}