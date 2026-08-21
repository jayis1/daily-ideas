/*
 * dent-scope / Core/Src/database.c
 * Dent Scope — 30-material hardness/modulus library + k-NN matching
 *
 * Library stores {HV, E_GPa, eta} for 30 common materials.
 * k-NN (k=3) matching in normalized {H, E, η} space.
 *
 * MIT License.
 */
#include "database.h"

typedef struct {
    const char *name;
    float HV;      /* Vickers hardness (kgf/mm²) */
    float E_GPa;  /* Young's modulus (GPa) */
    float eta;    /* elastic work ratio (typical) */
} material_entry_t;

static const material_entry_t library[30] = {
    /* Metals */
    {"Al 6061-T6",    107,  69,   0.05 },
    {"Al 2024-T3",    137,  73,   0.04 },
    {"Al pure(anneal)", 25,   69,   0.10 },
    {"Cu (annealed)",  47,  110,   0.08 },
    {"Cu (cold-work)", 110, 120,   0.03 },
    {"Brass 360",      160,  97,   0.04 },
    {"Bronze",         180, 110,   0.03 },
    {"Steel 1018",     126, 200,   0.03 },
    {"Steel 1045",     170, 200,   0.02 },
    {"Steel 4140",     250, 200,   0.02 },
    {"Steel 304 SS",   210, 193,   0.04 },
    {"Steel 316 SS",   160, 193,   0.05 },
    {"Cast iron gray", 200, 100,   0.02 },
    {"Cast iron duct", 180, 170,   0.03 },
    {"Ti Gr2",         145, 103,   0.05 },
    {"Ti Gr5 (6Al4V)", 349, 114,   0.02 },
    {"Mg AZ31",        60,   45,   0.08 },
    {"Zn (die cast)",  82,  108,   0.04 },
    /* Ceramics */
    {"Alumina 96%",  1500, 330,   0.40 },
    {"Zirconia Y-TZP", 1300, 210, 0.35 },
    {"Glass soda-lime", 540,  70,  0.45 },
    {"SiC",          2800, 410,  0.50 },
    {"Si3N4",        2200, 310,  0.45 },
    /* Polymers */
    {"PMMA",            20,  3.3, 0.70 },
    {"PE HDPE",         6,   1.1, 0.85 },
    {"PC",              14,  2.6, 0.65 },
    {"Nylon 66",        30,  3.0, 0.70 },
    {"PTFE",             5,  0.5, 0.90 },
    /* Composites */
    {"CFRP",           60, 150,  0.50 },
    {"GFRP",           35,  35,  0.60 },
    /* Coatings */
    {"TiN coating",   2500, 600,  0.55 },
};

void database_init(void)
{
    /* nothing to do — library is static const */
}

static float normalize_H(float hv)
{
    /* log-scale: 5–3000 HV → 0–1 */
    return logf(hv / 5.0f + 1.0f) / logf(3000.0f / 5.0f + 1.0f);
}

static float normalize_E(float e)
{
    /* 0.5–600 GPa → 0–1 */
    return logf(e / 0.5f + 1.0f) / logf(600.0f / 0.5f + 1.0f);
}

void database_match(ds_status_t *st)
{
    if (st->hardness_HV <= 0 || st->modulus_E_GPa <= 0) {
        st->matched_material = -1;
        return;
    }

    float q_h = normalize_H(st->hardness_HV);
    float q_e = normalize_E(st->modulus_E_GPa);
    float q_eta = st->elastic_ratio;
    if (q_eta > 1.0f) q_eta = 1.0f;

    /* k-NN (k=3): find 3 nearest, vote on best */
    float dists[30];
    int indices[30];
    for (int i = 0; i < 30; i++) {
        float dh = q_h - normalize_H(library[i].HV);
        float de = q_e - normalize_E(library[i].E_GPa);
        float det = q_eta - library[i].eta;
        dists[i] = dh*dh + de*de + det*det;
        indices[i] = i;
    }
    /* simple selection sort for top-3 */
    for (int i = 0; i < 3; i++) {
        int min = i;
        for (int j = i + 1; j < 30; j++)
            if (dists[j] < dists[min]) min = j;
        if (min != i) {
            float td = dists[i]; dists[i] = dists[min]; dists[min] = td;
            int ti = indices[i]; indices[i] = indices[min]; indices[min] = ti;
        }
    }

    /* vote: if top match is clearly closest (<0.5× second), use it */
    if (dists[0] < dists[1] * 0.5f) {
        st->matched_material = indices[0];
    } else {
        st->matched_material = indices[0]; /* else just nearest */
    }
}

const char *database_name(int idx)
{
    if (idx < 0 || idx >= 30) return "Unknown";
    return library[idx].name;
}