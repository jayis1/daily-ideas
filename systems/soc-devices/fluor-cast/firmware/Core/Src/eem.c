/*
 * eem.c — Excitation-Emission Matrix acquisition and processing
 *
 * Sweeps 8 excitation wavelengths, captures emission spectrum at each,
 * builds EEM matrix, applies scatter masking, extracts features.
 */

#include "eem.h"
#include "main.h"
#include <math.h>
#include <string.h>

/* ── Private helpers ──────────────────────────────────── */

static float wavenumber_to_wavelength(float wl_ex, float shift_cm)
{
    /* λ_raman = 1 / (1/λ_ex - shift)  [shift in cm⁻¹, λ in nm] */
    float inv_ex = 1.0f / wl_ex;  /* nm⁻¹ */
    float inv_raman = inv_ex - shift_cm * 1e-7f;  /* convert cm⁻¹ to nm⁻¹ */
    if (inv_raman <= 0) return 9999.0f;
    return 1.0f / inv_raman;
}

static int is_in_range(float wl, float center, float half_width)
{
    return (wl >= center - half_width) && (wl <= center + half_width);
}

/* ── Public Functions ─────────────────────────────────── */

void eem_init(void)
{
    /* Nothing special needed */
}

int eem_acquire(const acq_params_t *params, eem_t *eem)
{
    if (!params || !eem) return -1;

    memset(eem, 0, sizeof(eem_t));
    uint32_t start = HAL_GetTick();

    /* Read sample temperature */
    ds18b20_read_temp(&eem->temp_c);

    /* Check which wavelengths to scan */
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        if (!(params->scan_mask & (1 << w))) continue;

        ex_wavelength_t ex = (ex_wavelength_t)w;

        /* HDR or normal measurement */
        if (params->hdr_mode) {
            fluorometer_measure_hdr(ex, params, &eem->spectra[w]);
        } else {
            fluorometer_measure(ex, params, &eem->spectra[w]);
        }

        /* Copy emission data to EEM matrix */
        for (int p = 0; p < CCD_PIXELS; p++) {
            eem->matrix[w][p] = eem->spectra[w].emission.pixels[p];
            eem->matrix_mask[w][p] = 1;  /* all valid initially */
        }
    }

    eem->timestamp = HAL_GetTick();
    eem->valid = 1;

    return 0;
}

void eem_process(eem_t *eem)
{
    if (!eem || !eem->valid) return;

    /* 1. Mask Rayleigh and Raman scatter */
    eem_mask_scatter(eem);
    eem_mask_raman(eem);

    /* 2. Extract features */
    eem_extract_features(eem);
}

void eem_mask_scatter(eem_t *eem)
{
    /* For each excitation wavelength, mask ±15 nm around λ_ex (1st order)
     * and ±15 nm around 2×λ_ex (2nd order Rayleigh) */
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        float ex_nm = (float)ex_wavelength_nm[w];
        float rayleigh1 = ex_nm;
        float rayleigh2 = ex_nm * 2.0f;  /* 2nd order */

        for (int p = 0; p < CCD_PIXELS; p++) {
            float em_nm = ccd_pixel_to_wavelength(p);

            /* 1st order Rayleigh */
            if (is_in_range(em_nm, rayleigh1, 15.0f)) {
                eem->matrix_mask[w][p] = 0;
            }
            /* 2nd order Rayleigh */
            if (is_in_range(em_nm, rayleigh2, 15.0f)) {
                eem->matrix_mask[w][p] = 0;
            }
        }
    }
}

void eem_mask_raman(eem_t *eem)
{
    /* Water Raman: ~3400 cm⁻¹ shift
     * For 365 nm ex: Raman peak ≈ 416 nm
     * For 280 nm ex: Raman peak ≈ 311 nm */
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        float ex_nm = (float)ex_wavelength_nm[w];
        float raman_wl = wavenumber_to_wavelength(ex_nm, 3400.0f);

        for (int p = 0; p < CCD_PIXELS; p++) {
            float em_nm = ccd_pixel_to_wavelength(p);
            if (is_in_range(em_nm, raman_wl, 15.0f)) {
                eem->matrix_mask[w][p] = 0;
            }
        }
    }
}

void eem_apply_ife(eem_t *eem, const float *a_ex, const float *a_em)
{
    /* Inner Filter Effect correction:
     * F_corrected = F_observed × 10^(A_ex/2 + A_em/2) */
    if (!a_ex || !a_em) return;

    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        float correction = powf(10.0f, a_ex[w] / 2.0f);
        for (int p = 0; p < CCD_PIXELS; p++) {
            /* Approximate emission absorbance by interpolating */
            float em_nm = ccd_pixel_to_wavelength(p);
            int em_idx = (int)((em_nm - 350) / 400.0f * EEM_ROWS);
            if (em_idx < 0) em_idx = 0;
            if (em_idx >= EEM_ROWS) em_idx = EEM_ROWS - 1;

            float corr_total = correction * powf(10.0f, a_em[em_idx] / 2.0f);
            eem->matrix[w][p] = (uint16_t)(eem->matrix[w][p] * corr_total);
        }
    }
}

void eem_extract_features(eem_t *eem)
{
    if (!eem || !eem->valid) return;

    memset(eem->features, 0, sizeof(eem->features));
    int fidx = 0;

    /* Feature 0-23: 8 excitation × 3 emission band integrals */
    float band_ranges[3][2] = {
        {280, 350},  /* UV emission */
        {350, 450},  /* blue emission */
        {450, 750}   /* visible emission */
    };

    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        for (int b = 0; b < 3; b++) {
            uint32_t integral = 0;
            for (int p = 0; p < CCD_PIXELS; p++) {
                float wl = ccd_pixel_to_wavelength(p);
                if (wl >= band_ranges[b][0] && wl <= band_ranges[b][1]) {
                    if (eem->matrix_mask[w][p]) {
                        integral += eem->matrix[w][p];
                    }
                }
            }
            eem->features[fidx++] = (float)integral;
        }
    }

    /* Feature 24-26: Peak location and intensity */
    float global_peak_wl = 0;
    uint16_t global_peak_val = 0;
    int peak_w = 0, peak_p = 0;

    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        for (int p = 0; p < CCD_PIXELS; p++) {
            if (eem->matrix_mask[w][p] && eem->matrix[w][p] > global_peak_val) {
                global_peak_val = eem->matrix[w][p];
                peak_w = w;
                peak_p = p;
            }
        }
    }
    global_peak_wl = ccd_pixel_to_wavelength(peak_p);
    eem->features[fidx++] = global_peak_wl;
    eem->features[fidx++] = (float)ex_wavelength_nm[peak_w];
    eem->features[fidx++] = (float)global_peak_val;

    /* Feature 27: Peak area / total integral ratio */
    float total = eem_volume(eem);
    eem->features[fidx++] = (total > 0) ? (float)global_peak_val / total : 0;

    /* Feature 28: EEM volume (total fluorescence) */
    eem->features[fidx++] = total;

    /* Feature 29-30: EEM centroid (weighted mean ex/em) */
    float ex_mean = 0, em_mean = 0, weight_sum = 0;
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        for (int p = 0; p < CCD_PIXELS; p++) {
            float v = eem->matrix_mask[w][p] ? (float)eem->matrix[w][p] : 0;
            ex_mean += (float)ex_wavelength_nm[w] * v;
            em_mean += ccd_pixel_to_wavelength(p) * v;
            weight_sum += v;
        }
    }
    if (weight_sum > 0) {
        ex_mean /= weight_sum;
        em_mean /= weight_sum;
    }
    eem->features[fidx++] = ex_mean;
    eem->features[fidx++] = em_mean;

    /* Feature 31-34: Fluorescence indices */
    float fi, bix, hix, beta_alpha;
    eem_compute_indices(eem, &fi, &bix, &hix, &beta_alpha);
    eem->features[fidx++] = fi;
    eem->features[fidx++] = bix;
    eem->features[fidx++] = hix;
    eem->features[fidx++] = beta_alpha;

    /* Feature 35-39: 5 PCA scores (pre-computed from training set)
     * In production: load PCA matrix from flash and project features
     * For now, use first 5 band integrals normalized as proxy PCA */
    for (int i = 0; i < 5; i++) {
        if (total > 0) {
            eem->features[fidx] = eem->features[i * 3 + 2] / total * 1000.0f;
        }
        fidx++;
    }

    /* Feature 40-47: Emission spectrum shape descriptors at 365nm ex */
    if (eem->spectra[EX_365NM].emission.valid) {
        const ccd_frame_t *frame = &eem->spectra[EX_365NM].emission;

        /* Variance, skewness, kurtosis of emission spectrum */
        float mean = 0;
        int n_valid = 0;
        for (int p = 10; p < CCD_PIXELS - 10; p++) {
            mean += frame->pixels[p];
            n_valid++;
        }
        mean /= n_valid;

        float var = 0, skew = 0, kurt = 0;
        for (int p = 10; p < CCD_PIXELS - 10; p++) {
            float d = frame->pixels[p] - mean;
            var += d * d;
            skew += d * d * d;
            kurt += d * d * d * d;
        }
        var /= n_valid;
        if (var > 0) {
            skew = skew / (n_valid * powf(var, 1.5f));
            kurt = kurt / (n_valid * var * var) - 3.0f;  /* excess kurtosis */
        }

        eem->features[fidx++] = var;
        eem->features[fidx++] = skew;
        eem->features[fidx++] = kurt;
        eem->features[fidx++] = mean;
        eem->features[fidx++] = (float)global_peak_val / (mean + 1);  /* peak/mean ratio */
        eem->features[fidx++] = ccd_pixel_to_wavelength(peak_p);
        eem->features[fidx++] = (float)global_peak_val;
        eem->features[fidx++] = sqrtf(var);  /* std deviation */
    } else {
        for (int i = 0; i < 8; i++) {
            eem->features[fidx++] = 0;
        }
    }
}

void eem_compute_indices(const eem_t *eem, float *fi, float *bix, float *hix, float *beta_alpha)
{
    /* Fluorescence Index (FI): I(450nm) / I(500nm) at 370 nm excitation
     * McKnight 2001: FI ~1.9 for microbial fulvic, ~1.4 for terrestrial */
    *fi = 0;
    *bix = 0;
    *hix = 0;
    *beta_alpha = 0;

    /* Use 365 nm as closest to 370 nm */
    int ex_idx = EX_365NM;

    /* Find pixel indices for specific wavelengths */
    int p450 = -1, p500 = -1, p380 = -1, p430 = -1;
    int p435_480_lo = -1, p435_480_hi = -1, p300_345_lo = -1, p300_345_hi = -1;
    int p460_480_lo = -1, p460_480_hi = -1;

    for (int p = 0; p < CCD_PIXELS; p++) {
        float wl = ccd_pixel_to_wavelength(p);
        if (fabsf(wl - 450) < 1.0f) p450 = p;
        if (fabsf(wl - 500) < 1.0f) p500 = p;
        if (fabsf(wl - 380) < 1.0f) p380 = p;
        if (fabsf(wl - 430) < 1.0f) p430 = p;
        if (fabsf(wl - 435) < 1.0f) p435_480_lo = p;
        if (fabsf(wl - 480) < 1.0f) p435_480_hi = p;
        if (fabsf(wl - 300) < 1.0f) p300_345_lo = p;
        if (fabsf(wl - 345) < 1.0f) p300_345_hi = p;
        if (fabsf(wl - 460) < 1.0f) p460_480_lo = p;
    }

    if (ex_idx < NUM_EX_WAVELENGTHS) {
        /* FI: 450/500 */
        if (p450 >= 0 && p500 >= 0 && eem->matrix[ex_idx][p500] > 0) {
            *fi = (float)eem->matrix[ex_idx][p450] / (float)eem->matrix[ex_idx][p500];
        }

        /* BIX: 380/430 at ~310 nm ex (use 340 nm as closest) */
        ex_idx = EX_340NM;
        if (p380 >= 0 && p430 >= 0 && eem->matrix[ex_idx][p430] > 0) {
            *bix = (float)eem->matrix[ex_idx][p380] / (float)eem->matrix[ex_idx][p430];
        }

        /* HIX: sum(435-480) / sum(300-345) at 254 nm ex */
        ex_idx = EX_255NM;
        if (p435_480_lo >= 0 && p435_480_hi >= 0 &&
            p300_345_lo >= 0 && p300_345_hi >= 0) {
            float num = 0, den = 0;
            for (int p = p435_480_lo; p <= p435_480_hi; p++) {
                if (eem->matrix_mask[ex_idx][p]) num += eem->matrix[ex_idx][p];
            }
            for (int p = p300_345_lo; p <= p300_345_hi; p++) {
                if (eem->matrix_mask[ex_idx][p]) den += eem->matrix[ex_idx][p];
            }
            if (den > 0) *hix = num / den;
        }

        /* β/α: I(380) / I(460-480 max) at 310 nm ex (use 340 nm) */
        ex_idx = EX_340NM;
        if (p380 >= 0 && p460_480_lo >= 0 && p500 >= 0) {
            float max_460_480 = 0;
            for (int p = p460_480_lo; p <= p500; p++) {
                if (eem->matrix_mask[ex_idx][p] && eem->matrix[ex_idx][p] > max_460_480) {
                    max_460_480 = eem->matrix[ex_idx][p];
                }
            }
            if (max_460_480 > 0) {
                *beta_alpha = (float)eem->matrix[ex_idx][p380] / max_460_480;
            }
        }
    }
}

uint16_t eem_get(const eem_t *eem, uint8_t ex_idx, uint16_t pixel)
{
    if (ex_idx >= EEM_ROWS || pixel >= EEM_COLS) return 0;
    if (!eem->matrix_mask[ex_idx][pixel]) return 0;
    return eem->matrix[ex_idx][pixel];
}

uint16_t eem_get_nm(const eem_t *eem, float ex_nm, float em_nm)
{
    /* Find closest excitation wavelength */
    int best_ex = -1;
    float best_diff = 1e9;
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        float diff = fabsf((float)ex_wavelength_nm[w] - ex_nm);
        if (diff < best_diff) {
            best_diff = diff;
            best_ex = w;
        }
    }
    if (best_ex < 0 || best_diff > 30) return 0;

    /* Find pixel for emission wavelength */
    for (int p = 0; p < CCD_PIXELS; p++) {
        if (fabsf(ccd_pixel_to_wavelength(p) - em_nm) < 1.5f) {
            return eem_get(eem, best_ex, p);
        }
    }
    return 0;
}

float eem_volume(const eem_t *eem)
{
    float vol = 0;
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        for (int p = 0; p < CCD_PIXELS; p++) {
            if (eem->matrix_mask[w][p]) {
                vol += (float)eem->matrix[w][p];
            }
        }
    }
    return vol;
}

void eem_centroid(const eem_t *eem, float *ex_mean_nm, float *em_mean_nm)
{
    float ex_sum = 0, em_sum = 0, w_sum = 0;
    for (int w = 0; w < NUM_EX_WAVELENGTHS; w++) {
        for (int p = 0; p < CCD_PIXELS; p++) {
            if (eem->matrix_mask[w][p]) {
                float v = (float)eem->matrix[w][p];
                ex_sum += (float)ex_wavelength_nm[w] * v;
                em_sum += ccd_pixel_to_wavelength(p) * v;
                w_sum += v;
            }
        }
    }
    if (w_sum > 0) {
        *ex_mean_nm = ex_sum / w_sum;
        *em_mean_nm = em_sum / w_sum;
    } else {
        *ex_mean_nm = 0;
        *em_mean_nm = 0;
    }
}