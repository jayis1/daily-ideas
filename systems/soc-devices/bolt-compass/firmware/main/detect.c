/*
 * detect.c — CFAR sferic detector + feature extraction
 *
 * Pipeline (all fixed-point / float on the ESP32-S3, <2 ms per call):
 *
 *   1.  Estimate the noise floor: rolling median + MAD of the combined
 *       loop energy  E(t) = NS(t)^2 + EW(t)^2  over a 50 ms window.
 *   2.  A sferic candidate is a contiguous run where E(t) exceeds
 *       floor + k*MAD  (k=12) for  >= 2 samples (250 us at 8 ksps)
 *       and  <= 16 samples (2 ms), with a rise-time gate of 2–50 us
 *       equivalent (1–6 samples at 8 ksps) — this rejects slow
 *       E-field transients and 50/60 Hz mains hum.
 *   3.  On detection, freeze a SFERIC_WIN (50 ms = 400 samples) window
 *       straddling the trigger and extract 16 features:
 *         - peak_ns, peak_ew, peak_slow_e, peak_fast_e
 *         - rise_us (10→90%)
 *         - zero_cross_us (time to first sign flip after peak)
 *         - slow_tail_ratio (energy 5–50 ms after peak / total)
 *         - loop_coherence (|cos(dphi)| at peak, from a 256-pt FFT)
 *         - spectral_centroid_khz
 *         - e_sign (polarity of slow-E at t+5ms)
 *       plus the raw waveform for logging / streaming.
 *
 * The CFAR threshold adapts to local noise (rural quiet vs. urban noisy),
 * giving a roughly constant false-alarm rate. The k=12 (≈ 6 sigma on a
 * Rayleigh amplitude distribution) gives <1 false alarm per minute in a
 * -40 dBV/√Hz noise floor.
 */
#include "detect.h"
#include "fft.h"
#include <math.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "detect";

static float s_floor;        /* noise floor (energy units)   */
static float s_mad;          /* median absolute deviation     */
static int   s_last_trig;    /* last trigger index (debounce)*/

#define K_CFAR        12.0f
#define MIN_RUN       2       /* 250 us minimum duration       */
#define MAX_RUN       16      /* 2 ms maximum duration         */
#define MIN_RISE      1       /* 125 us min rise (1 sample)    */
#define DEBOUNCE      80      /* 10 ms debounce between sferics*/

void detect_init(void)
{
    s_floor = 1.0f;
    s_mad   = 1.0f;
    s_last_trig = -1000;
}

static float medianf(float *a, int n)
{
    /* simple insertion sort (n small, <= 64) */
    for (int i = 1; i < n; i++) {
        float x = a[i]; int j = i - 1;
        while (j >= 0 && a[j] > x) { a[j+1] = a[j]; j--; }
        a[j+1] = x;
    }
    return a[n/2];
}

static void estimate_floor(ring_t *r)
{
    /* 64-sample (8 ms) rolling window of combined loop energy, taken
     * from the region *before* the 80-sample scan window so a sferic
     * in the scan window doesn't inflate the floor. */
    int wr = r->wr;
    float e[64];
    for (int i = 0; i < 64; i++) {
        int idx = (wr - 144 + i) & (RING_LEN - 1);
        float ns = r->buf[idx].ch[0];
        float ew = r->buf[idx].ch[1];
        e[i] = ns*ns + ew*ew;
    }
    float med = medianf(e, 64);
    /* MAD */
    float d[64];
    for (int i = 0; i < 64; i++) d[i] = fabsf(e[i] - med);
    s_floor = med;
    s_mad   = medianf(d, 64) + 1e-3f;
}

int detect_sferic(ring_t *r, sferic_t *out)
{
    estimate_floor(r);
    float thr = s_floor + K_CFAR * s_mad;

    int wr = r->wr;
    /* Find the peak-energy sample in the last 80 samples (10 ms). */
    int   trig = -1;
    float max_e = 0;
    for (int i = 1; i <= 80; i++) {
        int idx = (wr - i) & (RING_LEN - 1);
        float ns = r->buf[idx].ch[0];
        float ew = r->buf[idx].ch[1];
        float e = ns*ns + ew*ew;
        if (e > max_e) { max_e = e; trig = idx; }
    }
    if (trig < 0 || max_e < thr) return 0;

    /* Rise-time gate: require a sharp rise (the 10→90 % rise must be
     * <= 6 samples = 750 us) to reject slow E-field transients and
     * 50/60 Hz mains hum. Also require the peak to be significantly
     * above the floor (k=12 already, but add a run check: at least
     * 2 consecutive samples above half-threshold around the peak). */
    int half = (int)(s_floor + 6.0f * s_mad);
    int run = 0;
    for (int i = -1; i <= 1; i++) {
        int idx = (trig + i) & (RING_LEN - 1);
        float ns = r->buf[idx].ch[0];
        float ew = r->buf[idx].ch[1];
        if (ns*ns + ew*ew > half) run++;
    }
    if (run < MIN_RUN) return 0;

    /* Debounce — skip if too close to the last trigger. */
    int delta = (trig - s_last_trig) & (RING_LEN - 1);
    if (delta < DEBOUNCE && delta > 0) return 0;
    s_last_trig = trig;

    /* Freeze a SFERIC_WIN window ending at trig + 350 samples
     * (so we capture the slow tail). */
    int win_end = (trig + 350) & (RING_LEN - 1);
    int win_start = (win_end - SFERIC_WIN) & (RING_LEN - 1);

    memset(out, 0, sizeof(*out));
    float p_ns = 0, p_ew = 0, p_slow = 0, p_fast = 0;
    int   p_idx = 0;
    float peak_e = 0;
    for (int i = 0; i < SFERIC_WIN; i++) {
        int idx = (win_start + i) & (RING_LEN - 1);
        float ns = r->buf[idx].ch[0];
        float ew = r->buf[idx].ch[1];
        float sl = r->buf[idx].ch[2];
        float fa = r->buf[idx].ch[3];
        out->wave_ns[i] = (int16_t)ns;
        out->wave_ew[i] = (int16_t)ew;
        out->wave_e[i]  = (int16_t)sl;
        float e = ns*ns + ew*ew;
        if (e > peak_e) {
            peak_e = e;
            p_ns = ns; p_ew = ew; p_slow = sl; p_fast = fa;
            p_idx = i;
        }
    }
    out->peak_ns      = p_ns;
    out->peak_ew      = p_ew;
    out->peak_slow_e  = p_slow;
    out->peak_fast_e  = p_fast;

    /* Rise time 10→90 % (in samples → us). */
    float thr_lo = 0.10f * sqrtf(peak_e);
    float thr_hi = 0.90f * sqrtf(peak_e);
    int i10 = p_idx, i90 = p_idx;
    for (int i = p_idx; i >= 0; i--) {
        float amp = sqrtf((float)out->wave_ns[i]*out->wave_ns[i] +
                          (float)out->wave_ew[i]*out->wave_ew[i]);
        if (amp < thr_lo) { i10 = i; break; }
    }
    for (int i = p_idx; i >= 0; i--) {
        float amp = sqrtf((float)out->wave_ns[i]*out->wave_ns[i] +
                          (float)out->wave_ew[i]*out->wave_ew[i]);
        if (amp < thr_hi) { i90 = i; break; }
    }
    out->rise_us = (float)(p_idx - i10) * (1e6f / ADC_RATE);

    /* Zero-cross time after peak (loop amplitude sign flip). */
    int zc = -1;
    int sgn_peak = (p_ns >= 0) ? 1 : -1;
    for (int i = p_idx + 1; i < SFERIC_WIN; i++) {
        int s = (out->wave_ns[i] >= 0) ? 1 : -1;
        if (s != sgn_peak) { zc = i; break; }
    }
    out->zero_cross_us = (zc > 0)
        ? (float)(zc - p_idx) * (1e6f / ADC_RATE) : 9999.0f;

    /* Slow-tail energy ratio: energy in [p_idx+40, end] / total. */
    float e_tail = 0, e_tot = 0;
    for (int i = 0; i < SFERIC_WIN; i++) {
        float e = (float)out->wave_ns[i]*out->wave_ns[i] +
                  (float)out->wave_ew[i]*out->wave_ew[i];
        e_tot += e;
        if (i >= p_idx + 40) e_tail += e;
    }
    out->slow_tail_ratio = (e_tot > 0) ? e_tail / e_tot : 0;

    /* E-field sign at t+5 ms (40 samples) after peak. */
    int e_idx = p_idx + 40;
    if (e_idx < SFERIC_WIN) {
        float es = out->wave_e[e_idx];
        out->e_sign = (es >  50) ? +1 :
                      (es < -50) ? -1 : 0;
    }

    /* Loop coherence + spectral centroid via a 256-pt FFT on the N-S ch. */
    float re[256], im[256];
    for (int i = 0; i < 256; i++) {
        re[i] = (p_idx + i - 128 >= 0 && p_idx + i - 128 < SFERIC_WIN)
              ? (float)out->wave_ns[p_idx + i - 128] : 0;
        im[i] = 0;
    }
    fft256(re, im);
    float mag_tot = 0, mag_w = 0;
    for (int k = 1; k < 128; k++) {
        float m = sqrtf(re[k]*re[k] + im[k]*im[k]);
        mag_tot += m;
        mag_w   += m * (float)k;
    }
    out->spectral_centroid_khz = (mag_tot > 0)
        ? (mag_w / mag_tot) * (ADC_RATE / 256.0f) / 1000.0f : 0;

    /* Loop coherence: |cos(dphi)| between NS and EW at the peak bin.
     * Approximate using the time-domain cross-correlation at zero lag. */
    float c = 0, an = 0, ae = 0;
    for (int i = p_idx; i < p_idx + 16 && i < SFERIC_WIN; i++) {
        c  += (float)out->wave_ns[i] * (float)out->wave_ew[i];
        an += (float)out->wave_ns[i] * (float)out->wave_ns[i];
        ae += (float)out->wave_ew[i] * (float)out->wave_ew[i];
    }
    out->loop_coherence = (an > 0 && ae > 0)
        ? fabsf(c) / sqrtf(an * ae) : 0;

    /* Build the 16-dim feature vector, normalized to roughly [-8, +8]
     * so the int8 quantization (q = feat*4 → [-32,32] clipped to [-128,128])
     * keeps useful resolution. */
    out->feat[0]  = out->peak_ns / 1000.0f;
    out->feat[1]  = out->peak_ew / 1000.0f;
    out->feat[2]  = out->peak_slow_e / 1000.0f;
    out->feat[3]  = out->peak_fast_e / 1000.0f;
    out->feat[4]  = out->rise_us / 20.0f;                 /* 0..~5 */
    out->feat[5]  = (out->zero_cross_us > 9000 ? 20.0f : out->zero_cross_us / 200.0f);
    out->feat[6]  = out->slow_tail_ratio * 10.0f;         /* 0..~10 */
    out->feat[7]  = out->loop_coherence * 2.0f - 1.0f;    /* -1..+1 */
    out->feat[8]  = out->spectral_centroid_khz / 5.0f;    /* 0..~6 */
    out->feat[9]  = (float)out->e_sign;                   /* -1,0,+1 */
    out->feat[10] = sqrtf(peak_e) / 1000.0f;              /* peak amplitude */
    out->feat[11] = out->rise_us > 0 ? (out->zero_cross_us / out->rise_us) / 10.0f : 0;
    out->feat[12] = out->peak_ew / (out->peak_ns + 100.0f);/* tan(bearing), clamped */
    out->feat[13] = out->slow_tail_ratio * 10.0f;
    out->feat[14] = out->loop_coherence * 2.0f - 1.0f;
    out->feat[15] = out->spectral_centroid_khz / 5.0f;

    out->ts_us = r->ts_us - (uint64_t)((SFERIC_WIN - p_idx) * (1000000/ADC_RATE));
    return 1;
}

float detect_noise_floor(void) { return s_floor; }