/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * beerlambert.c — Beer-Lambert law concentration calculation
 *
 * A = ε · c · l
 * where A = absorbance, ε = molar absorptivity, c = concentration, l = path length
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "beerlambert.h"
#include "spectrometer.h"
#include "matching.h"
#include <math.h>

#define PATH_LENGTH_CM  1.0f  /* Standard 10 mm cuvette = 1 cm */

float BeerLambert_Calculate(const float absorbance[SPECTRUM_POINTS],
                              const CompoundMatch_t *match)
{
    if (match->compound_id == COMPOUND_NONE) return 0.0f;
    if (match->molar_absorptivity < 1e-6f) return 0.0f;

    /* Find the peak absorbance value in the spectrum */
    float peak_abs = 0.0f;
    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        if (absorbance[i] > peak_abs) {
            peak_abs = absorbance[i];
        }
    }

    /* Beer-Lambert: c = A / (ε · l) */
    float concentration = peak_abs / (match->molar_absorptivity * PATH_LENGTH_CM);

    return concentration;
}

/*
 * BeerLambert_VerifyLinearRange — Check if sample is within linear range
 *
 * Returns true if absorbance at peak is < 1.5 AU (linear region)
 */
bool BeerLambert_IsInLinearRange(const float absorbance[SPECTRUM_POINTS])
{
    float peak_abs = 0.0f;
    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        if (absorbance[i] > peak_abs) {
            peak_abs = absorbance[i];
        }
    }
    return (peak_abs < 1.5f);
}

/*
 * BeerLambert_FormatConcentration — Human-readable concentration string
 */
void BeerLambert_FormatConcentration(float concentration_mol_L, char *buf, int buf_len)
{
    if (concentration_mol_L >= 1.0f) {
        snprintf(buf, buf_len, "%.2f M", concentration_mol_L);
    } else if (concentration_mol_L >= 1e-3f) {
        snprintf(buf, buf_len, "%.2f mM", concentration_mol_L * 1e3f);
    } else if (concentration_mol_L >= 1e-6f) {
        snprintf(buf, buf_len, "%.2f µM", concentration_mol_L * 1e6f);
    } else if (concentration_mol_L >= 1e-9f) {
        snprintf(buf, buf_len, "%.2f nM", concentration_mol_L * 1e9f);
    } else {
        snprintf(buf, buf_len, "< 1 pM");
    }
}