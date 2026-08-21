/*
 * kappa-pin / firmware / main / database.c
 * Material thermal property reference library
 *
 * 35 common materials for QA pass/fail and material identification.
 *
 * MIT License.
 */
#include "database.h"
#include <string.h>

static const material_ref_t ref_table[MAT_REF_COUNT] = {
    /* Gases & insulation */
    { "Air",              0.024,  0.028,  18.0,  26.0,    1200,  "gas" },
    { "Argon",            0.016,  0.020,  15.0,  22.0,    1000,  "gas" },
    { "Polyurethane foam", 0.020, 0.030,  10.0,  20.0,    40000, "insulation" },
    { "Polystyrene (EPS)", 0.030, 0.040,  10.0,  20.0,    45000, "insulation" },
    { "Mineral wool",     0.035,  0.045,  10.0,  20.0,    60000, "insulation" },
    { "Fiberglass",       0.035,  0.045,  10.0,  20.0,    65000, "insulation" },
    { "Aerogel blanket",  0.013,  0.022,   8.0,  15.0,    50000, "insulation" },

    /* Liquids */
    { "Water",            0.580,  0.610,  0.14,  0.16,   4200000, "liquid" },
    { "Glycerin",         0.280,  0.300,  0.09,  0.10,   2400000, "liquid" },
    { "Ethylene glycol",  0.240,  0.260,  0.09,  0.10,   2600000, "liquid" },
    { "Ethanol",          0.170,  0.180,  0.10,  0.11,   1900000, "liquid" },
    { "Olive oil",        0.170,  0.180,  0.09,  0.10,   1800000, "liquid" },
    { "Mineral oil",      0.130,  0.150,  0.08,  0.09,   1700000, "liquid" },
    { "Mercury",          8.300,  8.500,  4.50,  5.00,  18800000, "liquid" },

    /* Soils & granular */
    { "Dry sand",         0.150,  0.350,  0.15,  0.30,   800000,  "soil" },
    { "Wet sand",         1.500,  2.500,  0.50,  0.80,  2000000,  "soil" },
    { "Dry soil",         0.200,  0.400,  0.20,  0.35,   900000,  "soil" },
    { "Wet soil",         0.800,  2.000,  0.40,  0.70,  1800000,  "soil" },
    { "Saturated clay",   1.000,  1.600,  0.35,  0.55,  2200000,  "soil" },
    { "Snow (compact)",   0.300,  0.500,  0.30,  0.50,   400000,  "frozen" },
    { "Ice",              2.100,  2.300,  1.10,  1.20,  1900000,  "frozen" },

    /* Polymers */
    { "PTFE (Teflon)",    0.240,  0.260,  0.11,  0.12,  2200000,  "polymer" },
    { "PE (polyethylene)",0.420,  0.460,  0.20,  0.25,  2200000,  "polymer" },
    { "PP (polypropylene)",0.210, 0.240,  0.10,  0.12,  1900000,  "polymer" },
    { "PVC",              0.150,  0.180,  0.07,  0.09,  1600000,  "polymer" },
    { "PMMA (acrylic)",   0.180,  0.210,  0.11,  0.12,  1700000,  "polymer" },
    { "Nylon 6/6",        0.240,  0.270,  0.12,  0.14,  1900000,  "polymer" },

    /* Building materials */
    { "Concrete (dry)",   0.800,  1.400,  0.50,  0.80,  1800000,  "building" },
    { "Brick",            0.600,  0.900,  0.40,  0.60,  1700000,  "building" },
    { "Glass (window)",   0.900,  1.100,  0.50,  0.60,  2200000,  "building" },
    { "Wood (pine)",      0.100,  0.170,  0.10,  0.15,  1700000,  "building" },
    { "Gypsum board",     0.170,  0.250,  0.15,  0.25,  1100000,  "building" },

    /* Metals & high-λ */
    { "Aluminum",       200.0,  240.0,  90.0,  100.0,  2400000,  "metal" },
    { "Copper",         380.0,  420.0, 110.0,  120.0,  3400000,  "metal" },
    { "Stainless 304",   14.0,   18.0,   3.5,   4.5,  3800000,  "metal" },
    { "Iron/steel",      45.0,   55.0,  11.0,  13.0,  3700000,  "metal" },
};

const material_ref_t *database_get_all(int *count)
{
    *count = MAT_REF_COUNT;
    return ref_table;
}

int database_find_match(float lambda, float alpha)
{
    int best = -1;
    float best_score = 1e9;

    for (int i = 0; i < MAT_REF_COUNT; i++) {
        /* Normalized distance */
        float dl = (lambda < ref_table[i].lambda_min || lambda > ref_table[i].lambda_max)
                   ? fminf(fabsf(lambda - ref_table[i].lambda_min),
                           fabsf(lambda - ref_table[i].lambda_max))
                   : 0;
        float da = (alpha < ref_table[i].alpha_min || alpha > ref_table[i].alpha_max)
                   ? fminf(fabsf(alpha - ref_table[i].alpha_min),
                           fabsf(alpha - ref_table[i].alpha_max))
                   : 0;

        /* Normalize by typical range width */
        float rl = ref_table[i].lambda_max - ref_table[i].lambda_min + 0.01f;
        float ra = ref_table[i].alpha_max - ref_table[i].alpha_min + 0.01f;
        float score = (dl / rl) * (dl / rl) + (da / ra) * (da / ra);

        if (score < best_score) {
            best_score = score;
            best = i;
        }
    }

    return best;
}

const char *database_get_name(int idx)
{
    if (idx < 0 || idx >= MAT_REF_COUNT) return "Unknown";
    return ref_table[idx].name;
}

float database_get_typical_lambda(int idx)
{
    if (idx < 0 || idx >= MAT_REF_COUNT) return 0;
    return (ref_table[idx].lambda_min + ref_table[idx].lambda_max) / 2.0f;
}

bool database_qa_check(int target_idx, float measured_lambda, float tolerance_pct)
{
    if (target_idx < 0 || target_idx >= MAT_REF_COUNT) return false;
    float typical = (ref_table[target_idx].lambda_min +
                     ref_table[target_idx].lambda_max) / 2.0f;
    float tol = typical * (tolerance_pct / 100.0f);
    return (fabsf(measured_lambda - typical) <= tol);
}