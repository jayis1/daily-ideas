/*
 * library.c — 45-compound reduced-mobility (K0) library + k-NN classifier
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * K0 values are representative literature values for positive-ion mode IMS
 * in air. Real instruments vary by ±0.02-0.05 with instrument geometry and
 * drift-gas humidity; the classifier tolerates this via k-NN distance.
 */
#include "library.h"
#include <string.h>
#include <math.h>

const lib_entry_t g_library[LIB_SIZE] = {
    /* Reference */
    { "Reactant_Ion_Peak", 2.70f, CLASS_REFERENCE },
    { "Ammonium_adduct",   2.45f, CLASS_REFERENCE },

    /* Explosives */
    { "TNT",   1.54f, CLASS_EXPLOSIVE },
    { "RDX",   1.42f, CLASS_EXPLOSIVE },
    { "PETN",  1.34f, CLASS_EXPLOSIVE },
    { "NG",    1.62f, CLASS_EXPLOSIVE },
    { "EGDN",  1.73f, CLASS_EXPLOSIVE },
    { "DNT",   1.86f, CLASS_EXPLOSIVE },
    { "TATP",  1.49f, CLASS_EXPLOSIVE },
    { "HMTD",  1.35f, CLASS_EXPLOSIVE },
    { "AN",    2.18f, CLASS_EXPLOSIVE },   /* ammonium nitrate */
    { "Smokeless_powder", 1.58f, CLASS_EXPLOSIVE },

    /* Drugs */
    { "Cocaine",       1.98f, CLASS_DRUG },
    { "Heroin",        1.92f, CLASS_DRUG },
    { "MDMA",          1.74f, CLASS_DRUG },
    { "Methamphetamine",1.56f, CLASS_DRUG },
    { "Amphetamine",   1.62f, CLASS_DRUG },
    { "Fentanyl",      1.80f, CLASS_DRUG },
    { "THC",           1.65f, CLASS_DRUG },
    { "Morphine",      1.88f, CLASS_DRUG },
    { "Ketamine",      1.70f, CLASS_DRUG },

    /* Chemical warfare agents / simulants */
    { "DMMP_Sarin_sim", 1.78f, CLASS_CWA },
    { "GB_Sarin",       1.85f, CLASS_CWA },
    { "GD_Soman",       1.82f, CLASS_CWA },
    { "GA_Tabun",       1.51f, CLASS_CWA },
    { "HD_Mustard",    1.78f, CLASS_CWA },
    { "VX",            1.32f, CLASS_CWA },
    { "L_Lewisite",    1.69f, CLASS_CWA },
    { "DM_Adamsite",   1.60f, CLASS_CWA },
    { "CR",            1.77f, CLASS_CWA },
    { "Malathion_sim", 1.71f, CLASS_CWA },

    /* Toxic industrial chemicals */
    { "Ammonia",       2.18f, CLASS_TIC },
    { "Chlorine_adduct",1.95f, CLASS_TIC },
    { "HCl_adduct",    2.05f, CLASS_TIC },
    { "HCN",           2.30f, CLASS_TIC },
    { "Acetonitrile",  2.10f, CLASS_TIC },
    { "Phosgene",      1.68f, CLASS_TIC },
    { "Formaldehyde",  2.25f, CLASS_TIC },

    /* VOCs */
    { "Toluene",       1.79f, CLASS_VOC },
    { "Benzene",       1.65f, CLASS_VOC },
    { "Acetone",       1.95f, CLASS_VOC },
    { "Ethanol",       2.15f, CLASS_VOC },
    { "Methanol",      2.30f, CLASS_VOC },
    { "Isopropanol",   2.00f, CLASS_VOC },
    { "Hexane",        1.70f, CLASS_VOC },
    { "Xylene",        1.72f, CLASS_VOC },
    { "MEK",           1.88f, CLASS_VOC },
};
const uint8_t g_library_size = LIB_SIZE;

void library_classify(const ims_peak_t *peaks, uint8_t n, classify_result_t *out)
{
    if (!out) return;
    memset(out, 0, sizeof(*out));
    out->name = "None";
    out->cls = CLASS_NONE;
    out->confidence = 0.0f;
    if (n == 0) return;

    /* For each peak find K nearest library entries, accumulate votes.
     * The best (highest-confidence) match across all peaks wins. */
    float best_conf = 0.0f;
    const lib_entry_t *best_entry = NULL;
    float best_k0 = 0.0f;

    for (int p = 0; p < n; p++) {
        float k0 = peaks[p].k0;
        if (k0 < 0.3f || k0 > 3.0f) continue;     /* out of library range */
        /* find K nearest by absolute K0 distance */
        float dists[LIB_SIZE];
        for (int i = 0; i < LIB_SIZE; i++)
            dists[i] = fabsf(k0 - g_library[i].k0);
        /* partial selection of K smallest (simple: copy + bubble sort K times) */
        int idx[LIB_SIZE]; for (int i = 0; i < LIB_SIZE; i++) idx[i] = i;
        for (int kk = 0; kk < LIB_KNN_K; kk++) {
            int min_j = kk;
            for (int j = kk+1; j < LIB_SIZE; j++)
                if (dists[idx[j]] < dists[idx[min_j]]) min_j = j;
            int tmp = idx[kk]; idx[kk] = idx[min_j]; idx[min_j] = tmp;
        }
        /* confidence: 1 - (mean of K distances / max_acceptable(0.10)) */
        float sum = 0.0f;
        for (int kk = 0; kk < LIB_KNN_K; kk++) sum += dists[idx[kk]];
        float mean_dist = sum / LIB_KNN_K;
        float conf = 1.0f - (mean_dist / 0.10f);
        if (conf < 0.0f) conf = 0.0f;
        /* weight by peak amplitude (bigger peaks = more reliable) */
        float amp_w = (float)peaks[p].amplitude / 30000.0f;
        if (amp_w > 1.0f) amp_w = 1.0f;
        conf = conf * (0.5f + 0.5f * amp_w);
        if (conf > best_conf) {
            best_conf = conf;
            best_entry = &g_library[idx[0]];
            best_k0 = k0;
        }
    }
    if (best_entry) {
        out->name = best_entry->name;
        out->cls = best_entry->cls;
        out->k0 = best_k0;
        out->confidence = best_conf;
        out->distance = fabsf(best_k0 - best_entry->k0);
    }
}