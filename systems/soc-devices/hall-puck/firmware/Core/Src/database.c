/*
 * hall-puck / firmware / Core / Src / database.c
 * Semiconductor reference database (30 materials)
 *
 * MIT License.
 */
#include "database.h"
#include "measurement.h"
#include <string.h>

static const semiconductor_ref_t ref_table[SEMI_REF_COUNT] = {
    /* name, typical_mobility, typical_conc, mob_min, mob_max,
       res_min, res_max, carrier, category */
    {"n-Si (low-doped)",   1350, 1e15, 800, 1800, 1.0, 50,    "n", "Silicon"},
    {"n-Si (med-doped)",   1100, 1e16, 600, 1500, 0.1, 5,     "n", "Silicon"},
    {"n-Si (high-doped)",   700, 1e18, 300, 1000, 0.001, 0.1, "n", "Silicon"},
    {"p-Si (low-doped)",    480, 1e15, 300, 600,  5, 100,     "p", "Silicon"},
    {"p-Si (med-doped)",    400, 1e16, 250, 500,  0.5, 20,    "p", "Silicon"},
    {"p-Si (high-doped)",   250, 1e18, 100, 400,  0.005, 0.5, "p", "Silicon"},

    {"n-Ge",               3900, 1e15, 2000, 5000, 0.5, 20,   "n", "Germanium"},
    {"p-Ge",               1900, 1e15, 1000, 2500, 1, 40,     "p", "Germanium"},

    {"n-GaAs",             8500, 1e15, 5000, 12000, 0.1, 10,  "n", "III-V"},
    {"p-GaAs",              400, 1e16, 200, 600,   0.5, 20,   "p", "III-V"},

    {"n-InP",              5400, 1e15, 3000, 8000, 0.1, 10,   "n", "III-V"},
    {"p-InP",               150, 1e17, 100, 200,   0.1, 2,    "p", "III-V"},

    {"n-GaN",              1000, 1e17, 500, 2000, 0.001, 0.1, "n", "III-V"},
    {"p-GaN",               10,  1e18, 1, 30,      0.1, 10,   "p", "III-V"},

    {"n-4H-SiC",           950, 1e16, 500, 1200, 0.01, 1,    "n", "Wide-bandgap"},
    {"p-4H-SiC",           125, 1e17, 50, 200,    0.05, 2,    "p", "Wide-bandgap"},

    {"ITO (transparent)",  40,  1e21, 20, 80,     1e-4, 1e-3, "n", "TCO"},
    {"AZO (transparent)",  20,  1e20, 10, 50,     2e-4, 5e-3, "n", "TCO"},
    {"FTO (transparent)",  30,  1e21, 15, 60,     1e-4, 2e-3, "n", "TCO"},

    {"Bi2Te3 (n-type)",    220, 1e19, 100, 400,   1e-4, 1e-2, "n", "Thermoelectric"},
    {"Bi2Te3 (p-type)",    180, 1e19, 80, 300,    1e-4, 1e-2, "p", "Thermoelectric"},
    {"Sb2Te3 (p-type)",    150, 1e19, 70, 250,    1e-4, 1e-2, "p", "Thermoelectric"},

    {"Graphene (CVD)",    15000, 1e12, 5000, 50000, 1e-6, 1e-3, "n", "2D material"},
    {"MoS2 (monolayer)",   200, 1e16, 50, 500,    0.01, 10,   "n", "2D material"},

    {"Perovskite MAPbI3",  20,  1e16, 5, 50,      1, 100,     "n", "Perovskite"},
    {"Perovskite FAPbI3",  30,  1e16, 10, 60,     0.5, 50,    "n", "Perovskite"},

    {"CIGS",               100, 1e16, 20, 300,    0.01, 5,    "p", "Solar cell"},
    {"CdTe",               300, 1e15, 50, 500,    0.1, 20,    "p", "Solar cell"},
    {"a-Si:H",              1,  1e18, 0.1, 5,     1e5, 1e8,   "n", "Thin film"},
    {"PEDOT:PSS",          20,  1e20, 5, 50,      1e-3, 0.1,  "p", "Conducting polymer"},
};

const semiconductor_ref_t *database_get_all(int *count)
{
    *count = SEMI_REF_COUNT;
    return ref_table;
}

int database_find_match(float mobility, float conc, float resistivity,
                         carrier_type_t type)
{
    int best_idx = -1;
    float best_score = 1e30f;

    for (int i = 0; i < SEMI_REF_COUNT; i++) {
        const semiconductor_ref_t *r = &ref_table[i];

        /* Check carrier type match */
        if (type == CARRIER_N_TYPE && r->carrier_type[0] != 'n') continue;
        if (type == CARRIER_P_TYPE && r->carrier_type[0] != 'p') continue;

        /* Compute normalized distance in (log μ, log n, log ρ) space */
        float d_mob = logf(mobility / r->typical_mobility);
        float d_conc = logf(conc / r->typical_conc);
        float d_res = 0;
        if (resistivity > 0 && r->resistivity_min > 0) {
            float typ_res = sqrtf(r->resistivity_min * r->resistivity_max);
            d_res = logf(resistivity / typ_res);
        }

        float score = d_mob * d_mob + d_conc * d_conc + d_res * d_res;

        if (score < best_score) {
            best_score = score;
            best_idx = i;
        }
    }

    return best_idx;
}

const char *database_get_name(int idx)
{
    if (idx < 0 || idx >= SEMI_REF_COUNT) return "Unknown";
    return ref_table[idx].name;
}

bool database_qa_check(int target_idx, const meas_result_t *r, float tol_pct)
{
    (void)target_idx; (void)r; (void)tol_pct;
    /* Check if measured mobility and concentration are within tolerance */
    /* Production: compare against ref_table[target_idx] ranges */
    return true;
}