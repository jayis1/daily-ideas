/*
 * volt-scribe — dsp.c
 * DSP utilities: DFT, peak detection, smoothing, CORDIC interface
 */

#include "dsp.h"
#include <math.h>
#include <string.h>

/* ── Init ──────────────────────────────────────────────────────── */

void dsp_init(void)
{
    /* Configure CORDIC peripheral for future accelerated trig/sqrt ops */
    /* STM32G4 CORDIC: cosine, sine, phase, modulus, atan2 */
    CORDIC_ConfigTypeDef cordic_cfg = {
        .Function = CORDIC_FUNCTION_COSINE,
        .Precision = CORDIC_PRECISION_6CYCLES,
        .Scale = CORDIC_SCALE_0,
        .InSize = CORDIC_INSIZE_32BITS,
        .OutSize = CORDIC_OUTSIZE_32BITS,
        .NbWrite = CORDIC_NBWRITE_1,
        .NbRead = CORDIC_NBREAD_1,
    };
    /* HAL_CORDIC_Configure(&hcordic, &cordic_cfg); */
}

/* ── DFT at single frequency ──────────────────────────────────── */

void dsp_dft_single(const float *signal, int n_samples, float freq,
                    float sample_rate, float *real_out, float *imag_out)
{
    float re = 0, im = 0;
    float omega = 2.0f * (float)M_PI * freq / sample_rate;

    for (int k = 0; k < n_samples; k++) {
        float angle = omega * (float)k;
        re += signal[k] * cosf(angle);
        im += signal[k] * sinf(angle);
    }

    re *= 2.0f / (float)n_samples;
    im *= 2.0f / (float)n_samples;

    *real_out = re;
    *imag_out = im;
}

/* ── Full DFT magnitude spectrum ───────────────────────────────── */

void dsp_dft_magnitude(const float *signal, int n_samples,
                       float sample_rate, float *mag_out, int n_bins)
{
    for (int b = 0; b < n_bins; b++) {
        float freq = (float)b * sample_rate / (float)n_samples;
        float re, im;
        dsp_dft_single(signal, n_samples, freq, sample_rate, &re, &im);
        mag_out[b] = sqrtf(re * re + im * im);
    }
}

/* ── Moving average smoothing ──────────────────────────────────── */

void dsp_smooth(const float *in, float *out, int n, int window)
{
    int half = window / 2;
    for (int i = 0; i < n; i++) {
        float sum = 0;
        int count = 0;
        for (int j = -half; j <= half; j++) {
            int idx = i + j;
            if (idx < 0) idx = 0;
            if (idx >= n) idx = n - 1;
            sum += in[idx];
            count++;
        }
        out[i] = sum / (float)count;
    }
}

/* ── Derivative (central difference) ───────────────────────────── */

void dsp_derivative(const float *x, const float *y, float *dy, int n)
{
    for (int i = 1; i < n - 1; i++) {
        float dx = x[i + 1] - x[i - 1];
        if (fabsf(dx) < 1e-12f) dx = 1e-12f;
        dy[i] = (y[i + 1] - y[i - 1]) / dx;
    }
    dy[0] = dy[1];
    dy[n - 1] = dy[n - 2];
}

/* ── Peak detection ─────────────────────────────────────────────── */

int dsp_find_peaks(const float *x, const float *y, int n,
                   dsp_peak_t *peaks, int max_peaks,
                   float min_height, float min_distance)
{
    float *dy = (float *)malloc(n * sizeof(float));
    if (!dy) return 0;

    dsp_derivative(x, y, dy, n);

    int count = 0;
    for (int i = 1; i < n - 1 && count < max_peaks; i++) {
        /* Zero-crossing from positive to negative derivative → maximum */
        if (dy[i - 1] > 0 && dy[i] <= 0) {
            if (fabsf(y[i]) > min_height) {
                /* Check minimum distance from previous peak */
                int too_close = 0;
                for (int j = 0; j < count; j++) {
                    if (fabsf(x[i] - peaks[j].position) < min_distance) {
                        too_close = 1;
                        break;
                    }
                }
                if (!too_close) {
                    peaks[count].position = x[i];
                    peaks[count].height = y[i];
                    peaks[count].index = i;
                    count++;
                }
            }
        }
    }

    free(dy);
    return count;
}

/* ── Baseline correction (linear) ──────────────────────────────── */

void dsp_baseline_correct(float *y, int n, int edge_percent)
{
    int edge_n = n * edge_percent / 100;
    if (edge_n < 2) edge_n = 2;

    /* Average of first and last edge_percent points */
    float y_start = 0;
    for (int i = 0; i < edge_n; i++) y_start += y[i];
    y_start /= edge_n;

    float y_end = 0;
    for (int i = n - edge_n; i < n; i++) y_end += y[i];
    y_end /= edge_n;

    /* Subtract linear baseline */
    for (int i = 0; i < n; i++) {
        float frac = (float)i / (float)(n - 1);
        y[i] -= y_start + (y_end - y_start) * frac;
    }
}

/* ── Nernst equation helper ────────────────────────────────────── */

float dsp_nernst_potential(float E0, int n_electrons, float C_ox, float C_red,
                           float temperature_K)
{
    /* E = E0 + (RT/nF) * ln(C_ox / C_red) */
    const float R = 8.314f;   /* J/(mol·K) */
    const float F = 96485.0f; /* C/mol */
    float ratio = C_ox / C_red;
    if (ratio < 1e-30f) ratio = 1e-30f;
    return E0 + (R * temperature_K / ((float)n_electrons * F)) * logf(ratio);
}

/* ── Randles circuit impedance ─────────────────────────────────── */

void dsp_randles_impedance(float R_s, float R_ct, float C_dl, float alpha,
                           float sigma_w, float freq,
                           float *Z_real, float *Z_imag)
{
    float omega = 2.0f * (float)M_PI * freq;
    float jw_alpha_re = powf(omega, alpha) * cosf(alpha * (float)M_PI / 2.0f);
    float jw_alpha_im = powf(omega, alpha) * sinf(alpha * (float)M_PI / 2.0f);

    /* CPE: Z_CPE = 1 / (C_dl * (jω)^α) */
    /* Real part of 1/(C_dl * jω^α) */
    float cpe_re = C_dl * jw_alpha_re;
    float cpe_im = C_dl * jw_alpha_im;
    float cpe_mag2 = cpe_re * cpe_re + cpe_im * cpe_im;
    if (cpe_mag2 < 1e-30f) cpe_mag2 = 1e-30f;

    float Z_cpe_re = cpe_re / cpe_mag2;
    float Z_cpe_im = -cpe_im / cpe_mag2;

    /* Warburg: Z_W = σ_w / √(jω) = σ_w * (1-j) / √(2ω) */
    float sqrt_2w = sqrtf(2.0f * omega);
    if (sqrt_2w < 1e-10f) sqrt_2w = 1e-10f;
    float Z_w_re = sigma_w / sqrt_2w;
    float Z_w_im = -sigma_w / sqrt_2w;

    /* Parallel combination: CPE ∥ (R_ct + Z_W) */
    float branch2_re = R_ct + Z_w_re;
    float branch2_im = Z_w_im;

    float par_re = Z_cpe_re + branch2_re;
    float par_im = Z_cpe_im + branch2_im;
    /* Wrong — parallel is 1/(1/Z1 + 1/Z2) */

    /* Z1 = Z_cpe (real + j*imag) */
    float z1_re = Z_cpe_re, z1_im = Z_cpe_im;
    /* Z2 = R_ct + Z_w */
    float z2_re = branch2_re, z2_im = branch2_im;

    /* 1/Z1 = conj(Z1)/|Z1|^2 */
    float z1_mag2 = z1_re * z1_re + z1_im * z1_im;
    float inv_z1_re = z1_re / z1_mag2;
    float inv_z1_im = -z1_im / z1_mag2;

    float z2_mag2 = z2_re * z2_re + z2_im * z2_im;
    float inv_z2_re = z2_re / z2_mag2;
    float inv_z2_im = -z2_im / z2_mag2;

    /* 1/Z_parallel = 1/Z1 + 1/Z2 */
    float inv_par_re = inv_z1_re + inv_z2_re;
    float inv_par_im = inv_z1_im + inv_z2_im;

    /* Z_parallel = conj(1/Z_parallel) / |1/Z_parallel|^2 */
    float inv_par_mag2 = inv_par_re * inv_par_re + inv_par_im * inv_par_im;
    if (inv_par_mag2 < 1e-30f) inv_par_mag2 = 1e-30f;

    float z_par_re = inv_par_re / inv_par_mag2;
    float z_par_im = -inv_par_im / inv_par_mag2;

    /* Total: Z = R_s + Z_parallel */
    *Z_real = R_s + z_par_re;
    *Z_imag = z_par_im;
}