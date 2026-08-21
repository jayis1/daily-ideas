/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * matching.c — Spectral library matching via cosine similarity
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "matching.h"
#include "flash_store.h"
#include "deconv.h"
#include <math.h>
#include <string.h>

/* Built-in reference spectra (normalized absorbance at 128 points) */
/* Stored as wavelength, absorbance pairs for key compounds */
/* Full 128-point spectra stored in SPI flash; built-in are compressed */

typedef struct {
    CompoundID_t id;
    const char *name;
    uint8_t num_key_points;
    float molar_absorptivity;  /* L/(mol·cm) at peak */
    float key_wavelengths[8];  /* Up to 8 key absorbance wavelengths */
    float key_absorbances[8];  /* Normalized absorbance at those wavelengths */
} LibraryEntry_t;

/* Built-in library — 15 compounds */
static const LibraryEntry_t builtin_library[] = {
    {
        .id = COMPOUND_KMNO4,
        .name = "Potassium Permanganate",
        .num_key_points = 3,
        .molar_absorptivity = 2500.0f,
        .key_wavelengths = {525.0f, 545.0f, 310.0f},
        .key_absorbances = {1.0f, 0.85f, 0.35f},
    },
    {
        .id = COMPOUND_K2CR2O7,
        .name = "Potassium Dichromate",
        .num_key_points = 3,
        .molar_absorptivity = 3700.0f,
        .key_wavelengths = {350.0f, 440.0f, 370.0f},
        .key_absorbances = {1.0f, 0.28f, 0.65f},
    },
    {
        .id = COMPOUND_CUSO4,
        .name = "Copper Sulfate",
        .num_key_points = 2,
        .molar_absorptivity = 23.0f,
        .key_wavelengths = {800.0f, 610.0f},
        .key_absorbances = {1.0f, 0.55f},
    },
    {
        .id = COMPOUND_COCL2,
        .name = "Cobalt Chloride",
        .num_key_points = 2,
        .molar_absorptivity = 500.0f,
        .key_wavelengths = {510.0f, 630.0f},
        .key_absorbances = {0.4f, 1.0f},
    },
    {
        .id = COMPOUND_NISO4,
        .name = "Nickel Sulfate",
        .num_key_points = 3,
        .molar_absorptivity = 2.5f,
        .key_wavelengths = {395.0f, 720.0f, 650.0f},
        .key_absorbances = {1.0f, 0.6f, 0.3f},
    },
    {
        .id = COMPOUND_FESO4,
        .name = "Iron Sulfate",
        .num_key_points = 2,
        .molar_absorptivity = 2.8f,
        .key_wavelengths = {510.0f, 305.0f},
        .key_absorbances = {0.3f, 1.0f},
    },
    {
        .id = COMPOUND_NO3_ION,
        .name = "Nitrate (reagent)",
        .num_key_points = 2,
        .molar_absorptivity = 4800.0f,
        .key_wavelengths = {543.0f, 220.0f},
        .key_absorbances = {1.0f, 0.9f},
    },
    {
        .id = COMPOUND_PO4_ION,
        .name = "Phosphate (reagent)",
        .num_key_points = 2,
        .molar_absorptivity = 23500.0f,
        .key_wavelengths = {880.0f, 420.0f},
        .key_absorbances = {1.0f, 0.2f},
    },
    {
        .id = COMPOUND_CHLOROPHYLL,
        .name = "Chlorophyll",
        .num_key_points = 3,
        .molar_absorptivity = 90000.0f,
        .key_wavelengths = {430.0f, 662.0f, 450.0f},
        .key_absorbances = {1.0f, 0.8f, 0.55f},
    },
    {
        .id = COMPOUND_TARTRAZINE,
        .name = "Tartrazine (Yellow 5)",
        .num_key_points = 2,
        .molar_absorptivity = 23000.0f,
        .key_wavelengths = {425.0f, 257.0f},
        .key_absorbances = {1.0f, 0.7f},
    },
    {
        .id = COMPOUND_ALLURA_RED,
        .name = "Allura Red (Red 40)",
        .num_key_points = 2,
        .molar_absorptivity = 26000.0f,
        .key_wavelengths = {504.0f, 425.0f},
        .key_absorbances = {1.0f, 0.35f},
    },
    {
        .id = COMPOUND_BRILLIANT_BLUE,
        .name = "Brilliant Blue FCF",
        .num_key_points = 2,
        .molar_absorptivity = 83000.0f,
        .key_wavelengths = {629.0f, 310.0f},
        .key_absorbances = {1.0f, 0.4f},
    },
    {
        .id = COMPOUND_FLUORESCEIN,
        .name = "Fluorescein",
        .num_key_points = 2,
        .molar_absorptivity = 88000.0f,
        .key_wavelengths = {494.0f, 460.0f},
        .key_absorbances = {1.0f, 0.6f},
    },
    {
        .id = COMPOUND_RHODAMINE_B,
        .name = "Rhodamine B",
        .num_key_points = 2,
        .molar_absorptivity = 107000.0f,
        .key_wavelengths = {554.0f, 350.0f},
        .key_absorbances = {1.0f, 0.15f},
    },
    {
        .id = COMPOUND_QUININE,
        .name = "Quinine",
        .num_key_points = 2,
        .molar_absorptivity = 10000.0f,
        .key_wavelengths = {347.0f, 250.0f},
        .key_absorbances = {1.0f, 0.5f},
    },
};

#define BUILTIN_LIBRARY_SIZE (sizeof(builtin_library) / sizeof(builtin_library[0]))

/* ========================================================================
 * Reconstruct a full 128-point spectrum from key points using
 * Gaussian interpolation
 * ======================================================================== */
static void ReconstructSpectrum(const LibraryEntry_t *entry, float spectrum[SPECTRUM_POINTS])
{
    memset(spectrum, 0, SPECTRUM_POINTS * sizeof(float));

    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        float wl = Deconv_GetWavelength(i);
        float sum = 0.0f;
        float wsum = 0.0f;

        for (int k = 0; k < entry->num_key_points; k++) {
            /* Each key point contributes a Gaussian with ~30 nm FWHM */
            float sigma = 13.0f; /* ~30 nm FWHM */
            float diff = wl - entry->key_wavelengths[k];
            float weight = expf(-(diff * diff) / (2.0f * sigma * sigma));
            sum += weight * entry->key_absorbances[k];
            wsum += weight;
        }

        if (wsum > 1e-6f) {
            spectrum[i] = sum / wsum;
        }
    }
}

/* ========================================================================
 * Cosine Similarity — core matching metric
 * ======================================================================== */
static float CosineSimilarity(const float *a, const float *b, int n)
{
    float dot = 0.0f, norm_a = 0.0f, norm_b = 0.0f;

    for (int i = 0; i < n; i++) {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    if (norm_a < 1e-10f || norm_b < 1e-10f) return 0.0f;

    return dot / (sqrtf(norm_a) * sqrtf(norm_b));
}

/* ========================================================================
 * Find best matching compound in library
 * ======================================================================== */
void Matching_FindBest(const float absorbance[SPECTRUM_POINTS], CompoundMatch_t *match)
{
    float best_similarity = 0.0f;
    int best_idx = -1;
    float ref_spectrum[SPECTRUM_POINTS];

    /* Search built-in library */
    for (int i = 0; i < (int)BUILTIN_LIBRARY_SIZE; i++) {
        ReconstructSpectrum(&builtin_library[i], ref_spectrum);
        float sim = CosineSimilarity(absorbance, ref_spectrum, SPECTRUM_POINTS);

        if (sim > best_similarity) {
            best_similarity = sim;
            best_idx = i;
        }
    }

    /* TODO: Search SPI flash library (compound IDs 16-200) */

    /* Report result */
    if (best_idx >= 0 && best_similarity > MATCH_THRESHOLD) {
        match->compound_id = builtin_library[best_idx].id;
        match->confidence = best_similarity;
        match->molar_absorptivity = builtin_library[best_idx].molar_absorptivity;
        strncpy(match->name, builtin_library[best_idx].name, sizeof(match->name) - 1);
        match->name[sizeof(match->name) - 1] = '\0';
        match->name_len = strlen(match->name);
    } else {
        match->compound_id = COMPOUND_NONE;
        match->confidence = best_similarity;
        match->molar_absorptivity = 0.0f;
        strncpy(match->name, "Unknown", sizeof(match->name) - 1);
        match->name_len = 7;
    }
}

/* ========================================================================
 * Get library entry by compound ID
 * ======================================================================== */
const char *Matching_GetCompoundName(CompoundID_t id)
{
    for (int i = 0; i < (int)BUILTIN_LIBRARY_SIZE; i++) {
        if (builtin_library[i].id == id) {
            return builtin_library[i].name;
        }
    }
    return "Unknown";
}

uint16_t Matching_GetLibraryCount(void)
{
    return (uint16_t)BUILTIN_LIBRARY_SIZE;
}