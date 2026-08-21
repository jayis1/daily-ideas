/*
 * library.c — Specific rotation compound library
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Contains a built-in table of 40 common chiral compounds with their
 * specific rotation [α]_D (at 589 nm, 20°C), temperature coefficient,
 * and approximate Drude parameters. Supports up to 10 additional
 * user-defined entries stored on SD card.
 *
 * Matching uses k-NN (k=3) on a feature vector of:
 *   [α_589, α_405, α_520, K, λ₀]
 * normalized to comparable scales.
 *
 * Data sources: CRC Handbook of Chemistry & Physics, literature values.
 * Values are approximate; precision measurement requires calibration.
 */
#include <string.h>
#include <math.h>
#include "library.h"
#include "sd_log.h"

/* Built-in compound library (40 entries) */
static const library_entry_t builtin_library[] = {
    /* name                  [α]_D    temp_coeff  Drude K      λ₀ (nm) */
    {"Sucrose",              +66.5,   -0.01,      2.1e6,      190},
    {"D-Glucose",            +52.7,   -0.02,      1.7e6,      190},
    {"D-Fructose",           -92.4,   -0.02,      -2.9e6,     190},
    {"D-Galactose",          +80.2,   -0.02,      2.5e6,      190},
    {"D-Mannose",           +14.5,   -0.02,      4.5e5,      190},
    {"Lactose",             +52.6,   -0.01,      1.7e6,      190},
    {"Maltose",            +137.0,   -0.01,      4.3e6,      190},
    {"D-Xylose",            +18.8,   -0.02,      5.9e5,      190},
    {"L-Arabinose",         +104.5,  -0.02,      3.3e6,      190},
    {"Raffinose",          +101.0,  -0.01,      3.2e6,      190},
    {"D-Sorbitol",           -2.0,   -0.01,      -6.3e4,     190},
    {"D-Mannitol",          -23.0,   -0.01,      -7.2e5,     190},
    {"Tartaric acid (L+)",  +12.0,   -0.003,     3.8e5,      200},
    {"Tartaric acid (D-)",  -12.0,   -0.003,     -3.8e5,     200},
    {"Malic acid (L-)",      -2.3,   -0.003,     -7.2e4,     200},
    {"Citric acid",           0.0,    0.0,        0.0,        200}, /* achiral */
    {"Lactic acid (L+)",    +3.3,    -0.005,     1.0e5,      200},
    {"L-Aspartic acid",      +25.0,  -0.005,     7.9e5,      200},
    {"L-Glutamic acid",      +31.8,  -0.005,     1.0e6,      200},
    {"L-Alanine",            +2.7,   -0.005,     8.5e4,      200},
    {"L-Valine",            +28.3,  -0.005,     8.9e5,      200},
    {"L-Leucine",           +15.1,   -0.005,     4.7e5,      200},
    {"L-Phenylalanine",     -34.0,  -0.005,     -1.1e6,     260},
    {"L-Tyrosine",           -7.4,   -0.005,     -2.3e5,     280},
    {"L-Tryptophan",        -31.5,   -0.005,     -1.0e6,     280},
    {"L-Proline",           -85.0,   -0.005,     -2.7e6,     210},
    {"L-Histidine",         -39.0,  -0.005,     -1.2e6,     210},
    {"L-Serine",            +14.9,  -0.005,     4.7e5,      200},
    {"L-Threonine",         -28.5,  -0.005,     -9.0e5,     200},
    {"Glycine",              0.0,    0.0,        0.0,        200}, /* achiral */
    {"Camphor (D+)",        +44.0,   -0.005,     1.4e6,      290},
    {"Camphor (L-)",       -44.0,   -0.005,     -1.4e6,     290},
    {"Menthol (L-)",        -49.0,  -0.005,     -1.5e6,     250},
    {"Menthol (D+)",       +49.0,   -0.005,     1.5e6,      250},
    {"Limonene (D+)",      +125.0,  -0.005,     3.9e6,      260},
    {"Limonene (L-)",      -125.0,  -0.005,     -3.9e6,     260},
    {"Carvone (R-)",       -61.0,   -0.005,     -1.9e6,     320},
    {"Carvone (S+)",       +61.0,   -0.005,     1.9e6,      320},
    {"Thalidomide (R)",    +63.0,   -0.003,     2.0e6,      300},
    {"Ascorbic acid (L)",  +20.5,   -0.005,     6.5e5,      250},
};

#define BUILTIN_COUNT (sizeof(builtin_library) / sizeof(builtin_library[0]))

static library_entry_t custom_entries[LIBRARY_MAX_CUSTOM];
static int custom_count = 0;

void library_init(void)
{
    memset(custom_entries, 0, sizeof(custom_entries));
    custom_count = 0;
}

int library_size(void)
{
    return (int)(BUILTIN_COUNT + custom_count);
}

const library_entry_t *library_get(int index)
{
    if (index < 0)
        return NULL;
    if (index < (int)BUILTIN_COUNT)
        return &builtin_library[index];
    int ci = index - (int)BUILTIN_COUNT;
    if (ci < custom_count)
        return &custom_entries[ci];
    return NULL;
}

int library_find_by_name(const char *name)
{
    for (int i = 0; i < library_size(); i++) {
        const library_entry_t *e = library_get(i);
        if (e && strncmp(e->name, name, LIBRARY_NAME_MAX_LEN) == 0)
            return i;
    }
    return -1;
}

int library_add(const char *name, double alpha_d, double temp_coeff,
               double K, double lambda0)
{
    if (custom_count >= LIBRARY_MAX_CUSTOM)
        return -1;
    library_entry_t *e = &custom_entries[custom_count];
    strncpy(e->name, name, LIBRARY_NAME_MAX_LEN - 1);
    e->name[LIBRARY_NAME_MAX_LEN - 1] = '\0';
    e->specific_rotation  = alpha_d;
    e->temp_coefficient   = temp_coeff;
    e->drude_K            = K;
    e->drude_lambda0      = lambda0;
    e->is_custom          = 1;
    custom_count++;
    return library_size() - 1;
}

int library_remove(int index)
{
    int ci = index - (int)BUILTIN_COUNT;
    if (ci < 0 || ci >= custom_count)
        return -1;
    /* Shift remaining entries */
    for (int i = ci; i < custom_count - 1; i++) {
        custom_entries[i] = custom_entries[i + 1];
    }
    custom_count--;
    return 0;
}

library_match_t library_match(double alpha_589, double alpha_405,
                               double alpha_520, const drude_result_t *drude)
{
    library_match_t match = { -1, 0.0, 1e18 };

    /* Feature vector for comparison:
     * [α_589, α_405, α_520, K, λ₀]
     * We normalize each dimension to ~[-1,1] scale for distance computation.
     * α values typically ±130°, K ~ ±5e6, λ₀ ~ 150-350 nm
     */
    double target[5] = {
        alpha_589 / 130.0,
        alpha_405 / 400.0,    /* rotation increases at shorter λ (Drude) */
        alpha_520 / 200.0,
        (drude ? drude->K : 0.0) / 5e6,
        (drude ? drude->lambda0_nm : 0.0) / 300.0
    };

    /* k-NN with k=3 */
    double distances[LIBRARY_MAX_COMPOUNDS];
    int    indices[LIBRARY_MAX_COMPOUNDS];
    int    total = library_size();

    for (int i = 0; i < total; i++) {
        const library_entry_t *e = library_get(i);
        if (!e) continue;

        /* Predict rotation at each wavelength from Drude params */
        double a589 = e->specific_rotation;
        double a405 = (e->drude_K != 0 && e->drude_lambda0 > 0) ?
            drude_predict(e->drude_K, e->drude_lambda0, 405.0) : a589 * 2.5;
        double a520 = (e->drude_K != 0 && e->drude_lambda0 > 0) ?
            drude_predict(e->drude_K, e->drude_lambda0, 520.0) : a589 * 1.5;

        double vec[5] = {
            a589 / 130.0,
            a405 / 400.0,
            a520 / 200.0,
            e->drude_K / 5e6,
            e->drude_lambda0 / 300.0
        };

        double d2 = 0;
        for (int j = 0; j < 5; j++) {
            double diff = target[j] - vec[j];
            d2 += diff * diff;
        }
        distances[i] = sqrt(d2);
        indices[i] = i;
    }

    /* Simple selection sort for top-3 (small array) */
    for (int i = 0; i < total && i < 3; i++) {
        int min_idx = i;
        for (int j = i + 1; j < total; j++) {
            if (distances[j] < distances[min_idx])
                min_idx = j;
        }
        double td = distances[i]; distances[i] = distances[min_idx]; distances[min_idx] = td;
        int ti = indices[i];      indices[i] = indices[min_idx];     indices[min_idx] = ti;
    }

    if (total > 0) {
        match.best_index = indices[0];
        match.distance   = distances[0];
        /* Confidence: based on distance ratio between best and 3rd-nearest */
        if (total >= 3 && distances[2] > 1e-9) {
            double ratio = distances[0] / distances[2];
            match.confidence = 100.0 * (1.0 - ratio);
            if (match.confidence < 0) match.confidence = 0;
            if (match.confidence > 100) match.confidence = 100;
        } else if (total >= 1) {
            /* Only one entry — high confidence if very close */
            match.confidence = (distances[0] < 0.1) ? 90.0 : 50.0;
        }
    }

    return match;
}

void library_load_from_sd(void)
{
    /* Implementation reads custom entries from SD card binary file.
     * Format: uint8 count, followed by count × library_entry_t. */
    sd_log_load_library(custom_entries, LIBRARY_MAX_CUSTOM, &custom_count);
}

void library_save_to_sd(void)
{
    sd_log_save_library(custom_entries, custom_count);
}