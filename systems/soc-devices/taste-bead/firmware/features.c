/* features.c — Feature extraction from EIS impedance spectra
 *
 * Extracts a 48-dimensional feature vector from the 5-electrode × 20-freq
 * impedance matrix. Features include:
 *   - 5 electrodes × 7 Randles params = 35 features
 *   - 13 cross-electrode ratios at key frequencies = 13 features
 *   Total: 48 features
 *
 * The Randles equivalent circuit parameters are extracted by analyzing
 * the Nyquist plot (Z_imag vs Z_real) shape:
 *   - High-frequency intercept → R_s (solution resistance)
 *   - Semicircle diameter → R_ct (charge-transfer resistance)
 *   - Semicircle peak frequency → C_dl = 1/(2π f_peak R_ct)
 *   - Low-frequency 45° slope → Warburg coefficient σ
 */

#include "features.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include <math.h>
#include <string.h>

static const char *TAG = "features";

/* Pre-computed PCA loadings (48×48 matrix, stored in flash)
 * In practice, these would be computed offline from training data
 * and stored as constants. Here we use identity (no PCA) for simplicity.
 * A real implementation would store the top-48 eigenvectors. */
static const float pca_loadings[NUM_FEATURES][NUM_FEATURES] = {0};
static const float pca_mean[NUM_FEATURES] = {0};
static const float pca_std[NUM_FEATURES] = {1};

void features_extract_electrode(const ad5941_z_point_t *spectrum,
                                  electrode_features_t *ef)
{
    memset(ef, 0, sizeof(*ef));

    if (spectrum == NULL || ef == NULL) return;

    /* Find highest frequency point (index 10 = 100 kHz) */
    int idx_hf = 0;
    for (int i = 0; i < NUM_FREQS; i++) {
        if (spectrum[i].freq_hz > spectrum[idx_hf].freq_hz)
            idx_hf = i;
    }

    /* R_s = |Z| at highest frequency (where capacitive impedance → 0) */
    ef->R_s = spectrum[idx_hf].z_mag;
    if (isnan(ef->R_s) || ef->R_s <= 0) ef->R_s = 1e6f; /* fallback */

    /* Find peak of semi-circle in Nyquist plot (max -Z_imag) */
    float max_neg_imag = 0;
    int idx_peak = 0;
    for (int i = 0; i < NUM_FREQS; i++) {
        float neg_imag = -spectrum[i].z_imag; /* Nyquist: -Z'' vs Z' */
        if (!isnan(neg_imag) && neg_imag > max_neg_imag) {
            max_neg_imag = neg_imag;
            idx_peak = i;
        }
    }

    /* R_ct = semi-circle diameter ≈ 2 × max(-Z_imag) */
    ef->R_ct = 2.0f * max_neg_imag;
    if (isnan(ef->R_ct) || ef->R_ct <= 0) ef->R_ct = 1e6f;

    /* Peak frequency */
    ef->peak_freq = spectrum[idx_peak].freq_hz;
    if (isnan(ef->peak_freq) || ef->peak_freq <= 0) ef->peak_freq = 100.0f;

    /* C_dl = 1 / (2π × f_peak × R_ct) */
    ef->C_dl = 1.0f / (2.0f * M_PI * ef->peak_freq * ef->R_ct);

    /* Warburg coefficient from low-frequency 45° slope
     * σ = d|Z|/d(ω^−0.5) at low frequencies
     * Simplified: use ratio of Z_imag increase at two low freqs */
    int idx_lf1 = 0, idx_lf2 = 1; /* two lowest freq points */
    for (int i = 0; i < NUM_FREQS; i++) {
        if (spectrum[i].freq_hz < spectrum[idx_lf1].freq_hz) {
            idx_lf2 = idx_lf1;
            idx_lf1 = i;
        } else if (spectrum[i].freq_hz < spectrum[idx_lf2].freq_hz) {
            idx_lf2 = i;
        }
    }
    if (spectrum[idx_lf1].freq_hz > 0 && spectrum[idx_lf2].freq_hz > 0) {
        float w1 = 2.0f * M_PI * spectrum[idx_lf1].freq_hz;
        float w2 = 2.0f * M_PI * spectrum[idx_lf2].freq_hz;
        float dw = fabs(1.0f / sqrtf(w2) - 1.0f / sqrtf(w1));
        float dz = fabs(spectrum[idx_lf2].z_imag - spectrum[idx_lf1].z_imag);
        if (dw > 0) ef->sigma_w = dz / dw;
    }
    if (isnan(ef->sigma_w) || ef->sigma_w <= 0) ef->sigma_w = 0;

    /* |Z| at 100 Hz */
    for (int i = 0; i < NUM_FREQS; i++) {
        if (fabs(spectrum[i].freq_hz - 100.0f) < 10.0f) {
            ef->z_at_100hz = spectrum[i].z_mag;
            break;
        }
    }
    if (isnan(ef->z_at_100hz)) ef->z_at_100hz = 0;

    /* Dispersion ratio: |Z(1Hz)| / |Z(100kHz)| */
    float z_lf = spectrum[0].z_mag;
    float z_hf = spectrum[idx_hf].z_mag;
    if (!isnan(z_lf) && !isnan(z_hf) && z_hf > 0) {
        ef->z_ratio = z_lf / z_hf;
    } else {
        ef->z_ratio = 1.0f;
    }
    if (isnan(ef->z_ratio)) ef->z_ratio = 1.0f;
}

esp_err_t features_extract(const eis_result_t *eis,
                            float features[NUM_FEATURES],
                            const bme280_data_t *ambient)
{
    if (eis == NULL || features == NULL) return ESP_ERR_INVALID_ARG;

    int idx = 0;

    /* 5 electrodes × 7 Randles parameters = 35 features */
    electrode_features_t ef[NUM_ELECTRODES];
    for (int e = 0; e < NUM_ELECTRODES; e++) {
        features_extract_electrode(eis->spectra[e], &ef[e]);

        /* Log-transform large-value features for better k-NN performance */
        features[idx++] = log10f(ef[e].R_s + 1.0f);
        features[idx++] = log10f(ef[e].R_ct + 1.0f);
        features[idx++] = log10f(ef[e].C_dl * 1e6f + 1.0f); /* µF scale */
        features[idx++] = log10f(ef[e].sigma_w + 1.0f);
        features[idx++] = log10f(ef[e].peak_freq + 1.0f);
        features[idx++] = log10f(ef[e].z_at_100hz + 1.0f);
        features[idx++] = ef[e].z_ratio; /* already a ratio, no log */
    }

    /* 13 cross-electrode ratios at key frequencies = 13 features */
    /* These capture how different metals respond differently to the same liquid */
    const int key_freq_indices[] = {0, 5, 10}; /* ~1 Hz, ~400 Hz, ~100 kHz */
    for (int fi = 0; fi < 3; fi++) {
        int f = key_freq_indices[fi];
        /* Au/Cu ratio — detects sugar/alcohol content */
        float z_au = eis->spectra[0][f].z_mag;
        float z_cu = eis->spectra[4][f].z_mag;
        if (!isnan(z_au) && !isnan(z_cu) && z_cu > 0)
            features[idx++] = z_au / z_cu;
        else
            features[idx++] = 1.0f;

        /* Pt/GC ratio — detects aromatic compounds */
        float z_pt = eis->spectra[1][f].z_mag;
        float z_gc = eis->spectra[3][f].z_mag;
        if (!isnan(z_pt) && !isnan(z_gc) && z_gc > 0)
            features[idx++] = z_pt / z_gc;
        else
            features[idx++] = 1.0f;

        /* Ag/Au ratio — detects chloride/halide content */
        float z_ag = eis->spectra[2][f].z_mag;
        if (!isnan(z_ag) && !isnan(z_au) && z_au > 0)
            features[idx++] = z_ag / z_au;
        else
            features[idx++] = 1.0f;
    }
    /* 3 frequencies × 3 ratios = 9 cross-electrode features */

    /* 4 more: phase angle differences at 100 Hz */
    int f100 = 10; /* ~100 Hz index */
    for (int pair = 0; pair < 4; pair++) {
        float p1 = eis->spectra[pair][f100].z_phase;
        float p2 = eis->spectra[pair + 1][f100].z_phase;
        if (!isnan(p1) && !isnan(p2))
            features[idx++] = p1 - p2;
        else
            features[idx++] = 0.0f;
    }
    /* 4 phase-difference features */

    /* Total: 35 + 9 + 4 = 48 features */
    while (idx < NUM_FEATURES) {
        features[idx++] = 0.0f; /* pad if needed */
    }

    /* Apply PCA projection (optional — uses stored loadings) */
    /* features_pca_project(features, features); */

    ESP_LOGD(TAG, "Extracted %d features", idx);
    return ESP_OK;
}

void features_pca_project(const float raw[NUM_FEATURES],
                           float projected[NUM_FEATURES])
{
    /* Simple PCA: subtract mean, divide by std, multiply by loadings
     * In practice, the pca_loadings matrix would be pre-computed.
     * Here we just normalize. */
    for (int i = 0; i < NUM_FEATURES; i++) {
        projected[i] = (raw[i] - pca_mean[i]) / pca_std[i];
    }

    /* If PCA loadings are non-zero, apply rotation:
     * projected[j] = sum_i(loadings[j][i] × normalized[i]) */
    for (int j = 0; j < NUM_FEATURES; j++) {
        float sum = 0;
        for (int i = 0; i < NUM_FEATURES; i++) {
            sum += pca_loadings[j][i] * projected[i];
        }
        if (pca_loadings[j][0] != 0) { /* only if loadings are populated */
            projected[j] = sum;
        }
    }
}