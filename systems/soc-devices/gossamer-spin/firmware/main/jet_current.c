/*
 * gossamer-spin / firmware / jet_current.c
 * Jet current monitoring via TIA + ADS122U04 24-bit ADC + state classifier.
 *
 * The collector electrode connects to the virtual ground input of an
 * ADA4530-1 electrometer op-amp with 100 MΩ feedback (TIA).
 * V_tia = I_jet × R_fb = 100 nA × 100 MΩ = 10 V
 * A 1/10 divider at the TIA output gives 0–1 V for 0–1000 nA.
 *
 * The ADS122U04 samples at 100 SPS with 24-bit resolution.
 * Current (nA) = adc_voltage (V) × 10 × 1e9 / R_fb
 *             = adc_voltage × 10 × 1e9 / 100e6
 *             = adc_voltage × 100  (nA per volt)
 *
 * The 5-second rolling-window classifier reports:
 *   STABLE      — steady 100–500 nA, σ < 50 nA
 *   INTERRUPTED — <20 nA for >2 s
 *   UNSTABLE    — σ > 100 nA or rapid oscillation
 *   DRIPPING    — periodic spikes >800 nA
 */
#include "main.h"

/* Rolling window buffer (500 samples at 100 SPS = 5 seconds) */
static float current_buf[JET_WINDOW_N];
static int   buf_idx = 0;
static int   buf_count = 0;

static struct {
    float latest_na;
    float avg_na;
    float sigma_na;
    jet_state_t state;
    int   low_count;      /* consecutive samples below 20 nA */
    int   spike_count;    /* spikes >800 nA in window */
} jet = { 0 };

static void *h_spi3 = (void *)1;

/* Read one sample from ADS122U04 (channel 0 = jet current) */
static float read_adc_current(void)
{
    /* In a real build:
       - Assert CS (PB9 low)
       - Send RDATA command (0x10)
       - Read 3 bytes (24-bit signed)
       - Convert: voltage = code / 2^23 × 2.048 (PGA=1, Vref=2.048)
       - current_na = voltage × 100.0

       Placeholder: generate a realistic synthetic jet current. */
    static uint32_t seed = 54321;
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF;

    /* Simulate a stable jet at ~200 nA with ±30 nA noise */
    float val = 200.0f + (float)(seed % 60 - 30);
    return val;
}

void jet_current_init(void)
{
    buf_idx = 0;
    buf_count = 0;
    jet.latest_na = 0;
    jet.avg_na = 0;
    jet.sigma_na = 0;
    jet.state = JET_IDLE;
    jet.low_count = 0;
    jet.spike_count = 0;
    (void)h_spi3;
}

float jet_current_read(void)
{
    jet.latest_na = read_adc_current();

    /* Add to rolling buffer */
    current_buf[buf_idx] = jet.latest_na;
    buf_idx = (buf_idx + 1) % JET_WINDOW_N;
    if (buf_count < JET_WINDOW_N) buf_count++;

    return jet.latest_na;
}

/*
 * Update the jet current state classifier.
 * Called at 10 Hz from the main loop (reads 10 new samples since last call,
 * or just uses the latest if single-step).
 */
void jet_current_update(float *out_na, float *out_sigma, jet_state_t *out_state)
{
    /* Read a new sample */
    jet_current_read();

    /* Compute rolling mean and std dev */
    if (buf_count < 2) {
        jet.avg_na = jet.latest_na;
        jet.sigma_na = 0;
    } else {
        double sum = 0, sum2 = 0;
        for (int i = 0; i < buf_count; i++) {
            float v = current_buf[i];
            sum  += v;
            sum2 += v * v;
        }
        jet.avg_na = (float)(sum / buf_count);
        double variance = (sum2 / buf_count) - (sum / buf_count) * (sum / buf_count);
        if (variance < 0) variance = 0;
        jet.sigma_na = (float)sqrt(variance);
    }

    /* Track low-current duration (INTERRUPTED detection) */
    if (jet.latest_na < 20.0f) {
        jet.low_count++;
    } else {
        jet.low_count = 0;
    }

    /* Count spikes (DRIPPING detection) */
    if (jet.latest_na > 800.0f) {
        jet.spike_count++;
    }
    /* Decay spike count slowly */
    if (buf_count > 0 && (buf_idx % 100) == 0) {
        jet.spike_count = jet.spike_count * 3 / 4;
    }

    /* Classify */
    if (jet.low_count > (2 * JET_SAMPLE_RATE)) {
        /* <20 nA for >2 seconds */
        jet.state = JET_INTERRUPTED;
    } else if (jet.spike_count > 10) {
        /* Multiple spikes in the window */
        jet.state = JET_DRIPPING;
    } else if (jet.sigma_na > 100.0f) {
        /* High variance → unstable */
        jet.state = JET_UNSTABLE;
    } else if (jet.avg_na > 50.0f && jet.sigma_na < 50.0f) {
        /* Steady current with low variance */
        jet.state = JET_STABLE;
    } else {
        jet.state = JET_IDLE;
    }

    *out_na = jet.avg_na;
    *out_sigma = jet.sigma_na;
    *out_state = jet.state;
}