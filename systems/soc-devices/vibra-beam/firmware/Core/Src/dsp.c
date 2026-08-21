/*
 * dsp.c — FFT, windowing, spectrum analysis, modal fit
 *
 * Uses CMSIS-DSP arm_rfft_fast_f32 for the 4096-point real FFT,
 * Hann windowing, peak picking, THD, SNR, and modal parameter
 * extraction (resonance frequency, -3dB bandwidth, Q, damping ζ).
 */

#include "dsp.h"
#include "stm32g4xx_hal.h"
#include <math.h>
#include <string.h>

/* CMSIS-DSP (provided in firmware/Drivers/CMSIS/DSP) */
#include "arm_math.h"
#include "arm_const_structs.h"

static float s_window[CONFIG_FFT_SIZE];

/* ── Init ────────────────────────────────────────────────── */
void dsp_init(void)
{
    dsp_window_hann(s_window, CONFIG_FFT_SIZE);
}

/* ── Window functions ────────────────────────────────────── */
void dsp_window_hann(float *w, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++) {
        w[i] = 0.5f * (1.0f - cosf(2.0f * (float)M_PI * i / (n - 1)));
    }
}

void dsp_window_hamming(float *w, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++) {
        w[i] = 0.54f - 0.46f * cosf(2.0f * (float)M_PI * i / (n - 1));
    }
}

/* ── FFT ────────────────────────────────────────────────── */
void dsp_fft(const float *vel, uint32_t n, fft_result_t *res)
{
    static float fft_in[CONFIG_FFT_SIZE];
    static float fft_out[CONFIG_FFT_SIZE * 2];

    uint32_t N = CONFIG_FFT_SIZE;
    if (n < N) N = n;
    /* Apply window */
    for (uint32_t i = 0; i < N; i++) {
        fft_in[i] = vel[i] * s_window[i];
    }

    /* CMSIS-DSP real FFT */
    arm_rfft_fast_instance_f32 S;
    arm_rfft_fast_init_f32(&S, N);
    arm_rfft_fast_f32(&S, fft_in, fft_out, 0);

    /* Compute single-sided magnitude spectrum */
    float fs = (float)CONFIG_ADC_SAMPLE_RATE_HZ;
    res->bin_hz = fs / N;
    for (uint32_t i = 0; i < N / 2; i++) {
        float re = fft_out[2 * i];
        float im = fft_out[2 * i + 1];
        res->mag[i] = sqrtf(re * re + im * im) * 2.0f / N;
    }

    /* Peak picking */
    float peak = 0.0f;
    uint32_t peak_bin = 0;
    for (uint32_t i = 1; i < N / 2; i++) {
        if (res->mag[i] > peak) {
            peak = res->mag[i];
            peak_bin = i;
        }
    }
    res->freq_peak_hz = (float)peak_bin * res->bin_hz;
    res->mag_peak = peak;

    /* THD: ratio of harmonic energy to fundamental */
    float fund = res->mag[peak_bin];
    float harm = 0.0f;
    for (uint32_t h = 2; h <= 5; h++) {
        uint32_t bin = peak_bin * h;
        if (bin < N / 2) harm += res->mag[bin] * res->mag[bin];
    }
    res->thd_pct = (fund > 0.0f) ? 100.0f * sqrtf(harm) / fund : 0.0f;

    /* SNR: peak / median noise floor */
    float noise = 0.0f;
    uint32_t cnt = 0;
    for (uint32_t i = 1; i < N / 2; i++) {
        if (abs((int)i - (int)peak_bin) > 5) {  /* exclude peak lobe */
            noise += res->mag[i];
            cnt++;
        }
    }
    noise = (cnt > 0) ? noise / cnt : 1e-9f;
    res->snr_db = 20.0f * log10f((peak + 1e-12f) / (noise + 1e-12f));
}

/* ── Modal fit ──────────────────────────────────────────── */
void dsp_modal_fit(const fft_result_t *fft, float fmin, float fmax, modal_result_t *m)
{
    /* Find peak in [fmin, fmax] */
    uint32_t bin_min = (uint32_t)(fmin / fft->bin_hz);
    uint32_t bin_max = (uint32_t)(fmax / fft->bin_hz);
    if (bin_max > CONFIG_FFT_SIZE / 2) bin_max = CONFIG_FFT_SIZE / 2;

    float peak = 0.0f;
    uint32_t peak_bin = bin_min;
    for (uint32_t i = bin_min; i < bin_max; i++) {
        if (fft->mag[i] > peak) {
            peak = fft->mag[i];
            peak_bin = i;
        }
    }
    m->fn_hz = (float)peak_bin * fft->bin_hz;
    m->peak_mms = peak;

    /* Find -3dB points around peak */
    float thresh = peak / 1.41421356f;   /* -3dB ≈ 0.707× */
    uint32_t bl = peak_bin, br = peak_bin;
    while (bl > bin_min && fft->mag[bl] > thresh) bl--;
    while (br < bin_max && fft->mag[br] > thresh) br++;
    m->bw_3db_hz = (float)(br - bl) * fft->bin_hz;
    m->Q = (m->bw_3db_hz > 0.0f) ? m->fn_hz / m->bw_3db_hz : 0.0f;
    m->zeta = (m->Q > 0.0f) ? 1.0f / (2.0f * m->Q) : 0.0f;
}