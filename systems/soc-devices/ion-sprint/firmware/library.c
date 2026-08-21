/*
 * library.c — 40-ion migration-time library with k-NN identification
 *
 * The library stores reference migration times for 40 common ions
 * under standard BGE conditions (20 mM MES/His, pH 6.1, 25 °C, 20 kV,
 * 50 µm capillary, 20 cm to detector). A k-NN (k=3) classifier over
 * a 2D feature space (normalized migration time, peak skewness)
 * identifies the most likely ion for each detected peak.
 *
 * Migration times are approximate and depend on BGE, pH, voltage,
 * capillary length, and temperature. The firmware applies:
 *   - Temperature correction: μ(T) = μ(25°C) × [1 + 0.02·(T-25)]
 *   - Voltage normalization: t_m ∝ 1/V (higher V = faster)
 *   - Capillary length normalization: t_m ∝ L_d/L_total²
 *
 * The user can re-calibrate by running a known standard and updating
 * the stored migration times via the BLE interface.
 */

#include "library.h"
#include "stm32g474_conf.h"
#include <math.h>
#include <string.h>

/* Ion entry: name, migration time (s) under reference conditions,
 * typical skewness, charge */
typedef struct {
    const char name[12];
    float mt_ref;       /* Reference migration time (s) */
    float skew_ref;     /* Typical peak skewness */
    int8_t charge;     /* Ion charge (+1, +2, -1, -2, -3) */
} ion_entry_t;

/* 40-ion library under BGE recipe 0 (20 mM MES/His, pH 6.1, 25°C)
 * Migration times are approximate for 20 kV, 50µm capillary, 20 cm to detector.
 * Cations arrive first (EOF + ep mobility), anions arrive later (EOF - ep).
 */
static const ion_entry_t lib[ION_LIBRARY_SIZE] = {
    /* Cations (migrate toward cathode, arrive first) */
    {"NH4+",      65.0f,  0.10f, +1},
    {"K+",        68.0f,  0.08f, +1},
    {"Na+",       72.0f,  0.12f, +1},
    {"Li+",       80.0f,  0.15f, +1},
    {"Ba2+",      95.0f,  0.20f, +2},
    {"Sr2+",     102.0f,  0.20f, +2},
    {"Ca2+",     108.0f,  0.22f, +2},
    {"Mg2+",     118.0f,  0.25f, +2},
    {"Mn2+",     122.0f,  0.22f, +2},
    {"Fe2+",     125.0f,  0.23f, +2},
    {"Co2+",     128.0f,  0.22f, +2},
    {"Ni2+",     130.0f,  0.22f, +2},
    {"Cu2+",     135.0f,  0.25f, +2},
    {"Zn2+",     138.0f,  0.23f, +2},
    {"Cr3+",     155.0f,  0.30f, +3},
    {"Fe3+",     160.0f,  0.28f, +3},
    {"Al3+",     165.0f,  0.30f, +3},
    {"Pyrrolid.", 175.0f,  0.35f, +1},
    {"Morpholin.",180.0f, 0.35f, +1},
    {"Histidine", 185.0f,  0.40f, +1},

    /* Neutral marker (EOF marker) */
    {"EOF mark",  190.0f,  0.00f,  0},

    /* Anions (migrate against EOF, arrive after neutral marker) */
    {"Cl-",       205.0f, -0.10f, -1},
    {"F-",        215.0f, -0.12f, -1},
    {"NO2-",      210.0f, -0.10f, -1},
    {"NO3-",      208.0f, -0.08f, -1},
    {"Br-",       200.0f, -0.10f, -1},
    {"I-",        198.0f, -0.08f, -1},
    {"Formate",   225.0f, -0.15f, -1},
    {"Acetate",   235.0f, -0.18f, -1},
    {"Propionate",245.0f, -0.20f, -1},
    {"Lactate",   250.0f, -0.20f, -1},
    {"Butyrate",  255.0f, -0.22f, -1},
    {"Oxalate",   270.0f, -0.25f, -2},
    {"Malonate",  280.0f, -0.25f, -2},
    {"Succinate", 290.0f, -0.28f, -2},
    {"Malate",    285.0f, -0.25f, -2},
    {"Tartrate",  275.0f, -0.22f, -2},
    {"Citrate",   310.0f, -0.30f, -3},
    {"SO4--",     300.0f, -0.25f, -2},
    {"PO4 3-",    330.0f, -0.35f, -3},
    {"Benzoate",  260.0f, -0.20f, -1},
};

/* Per-BGE recipe migration time scaling factors */
static const float bge_scale[BGE_RECIPE_COUNT] = {
    1.00f,  /* 0: MES/His pH 6.1 (reference) */
    0.95f,  /* 1: MES/His + CTAB (reversed EOF, anions first) */
    1.05f,  /* 2: His/MES pH 4.5 (cations) */
    0.98f,  /* 3: MES/His pH 5.7 (organic acids) */
    1.10f,  /* 4: Phosphate pH 2.5 (amino acids) */
    1.20f,  /* 5: NaOH pH 12.1 (sugars) */
    1.02f,  /* 6: MES/His + EDTA (transition metals) */
    0.92f,  /* 7: Borate pH 9.3 (organic acids anionic) */
};

void library_init(void)
{
    /* In a real implementation, would load from W25Q128 flash.
     * For now, use the static table above. */
}

const char *library_get_name(uint8_t index)
{
    if (index >= ION_LIBRARY_SIZE) return "???";
    return lib[index].name;
}

float library_get_mt(uint8_t index, uint8_t bge_recipe)
{
    if (index >= ION_LIBRARY_SIZE) return 0.0f;
    float scale = (bge_recipe < BGE_RECIPE_COUNT) ?
                  bge_scale[bge_recipe] : 1.0f;
    return lib[index].mt_ref * scale;
}

uint8_t library_size(void) { return ION_LIBRARY_SIZE; }

/* k-NN (k=3) classification over 2D feature space:
 * Feature 1: normalized migration time (scaled to reference BGE)
 * Feature 2: peak skewness
 * Distance: Euclidean (with weighting: mt contributes 80%, skewness 20%)
 */
int8_t library_identify(float norm_mt, float skewness, uint8_t bge_recipe)
{
    float scale = (bge_recipe < BGE_RECIPE_COUNT) ?
                  bge_scale[bge_recipe] : 1.0f;

    /* Compute distances to all library ions */
    float dist[ION_LIBRARY_SIZE];
    for (uint8_t i = 0; i < ION_LIBRARY_SIZE; i++) {
        float mt_ref = lib[i].mt_ref * scale;
        float d_mt = (norm_mt - mt_ref) / mt_ref;  /* Relative MT error */
        float d_skew = skewness - lib[i].skew_ref;
        /* Weighted distance: 80% MT, 20% skewness */
        dist[i] = 0.8f * d_mt * d_mt + 0.2f * d_skew * d_skew;
    }

    /* Find k=3 nearest neighbors */
    uint8_t nn[KNN_K] = {0, 0, 0};
    float nn_dist[KNN_K] = {1e30f, 1e30f, 1e30f};
    for (uint8_t i = 0; i < ION_LIBRARY_SIZE; i++) {
        for (uint8_t j = 0; j < KNN_K; j++) {
            if (dist[i] < nn_dist[j]) {
                /* Shift down */
                for (uint8_t k = KNN_K - 1; k > j; k--) {
                    nn[k] = nn[k-1];
                    nn_dist[k] = nn_dist[k-1];
                }
                nn[j] = i;
                nn_dist[j] = dist[i];
                break;
            }
        }
    }

    /* Check if nearest is within tolerance */
    float mt_ref_best = lib[nn[0]].mt_ref * scale;
    float mt_err_pct = fabsf(norm_mt - mt_ref_best) / mt_ref_best * 100.0f;
    if (mt_err_pct > MT_TOLERANCE_PCT) return -1;

    /* Vote: pick the most common ion among k=3 nearest */
    /* For k=3, majority vote. If all different, pick nearest. */
    if (nn[0] == nn[1] || nn[0] == nn[2]) return (int8_t)nn[0];
    if (nn[1] == nn[2]) return (int8_t)nn[1];
    return (int8_t)nn[0];  /* Nearest wins ties */
}