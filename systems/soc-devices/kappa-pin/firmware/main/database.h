/*
 * kappa-pin / firmware / main / database.h
 * Material thermal property reference library
 *
 * Used for QA pass/fail comparison and material identification.
 *
 * MIT License.
 */
#ifndef DATABASE_H
#define DATABASE_H

#include <stdbool.h>

typedef struct {
    const char *name;
    float lambda_min;    /* W/(m·K) */
    float lambda_max;
    float alpha_min;     /* mm²/s */
    float alpha_max;
    float typical_rho_cp; /* J/(m³·K) */
    const char *category;
} material_ref_t;

/* Number of reference materials */
#define MAT_REF_COUNT  35

/* Get reference table */
const material_ref_t *database_get_all(int *count);

/* Find best matching material for a measured λ */
int database_find_match(float lambda, float alpha);

/* Get material name by index */
const char *database_get_name(int idx);

/* Get typical λ for a material */
float database_get_typical_lambda(int idx);

/* QA check: is measured λ within spec for target material? */
bool database_qa_check(int target_idx, float measured_lambda, float tolerance_pct);

#endif /* DATABASE_H */