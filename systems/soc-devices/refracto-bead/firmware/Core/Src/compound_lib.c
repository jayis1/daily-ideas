/**
 * compound_lib.c — 60-entry compound library and k-NN matching
 *
 * On-device library of known refractive index + Abbe number fingerprints.
 * k-NN (k=3) in (n_D, V_D) feature space identifies the measured liquid.
 * Distance is weighted Euclidean with n_D weighted 3× more than V_D
 * (since n_D is more precisely measured).
 */

#include "compound_lib.h"
#include <string.h>
#include <math.h>

/* ---- The 60-entry library ---- */
static compound_entry_t s_lib[LIB_SIZE] = {
    /* 1-10: Reference & Solvents */
    {"Water",          1.3330f, 55.8f, -0.8f, CAT_REFERENCE},
    {"Ethanol",        1.3611f, 59.0f, -4.0f, CAT_SOLVENT},
    {"Methanol",       1.3284f, 57.6f, -4.0f, CAT_SOLVENT},
    {"Acetone",        1.3588f, 54.6f, -4.9f, CAT_SOLVENT},
    {"Isopropanol",    1.3776f, 54.6f, -3.7f, CAT_SOLVENT},
    {"Toluene",        1.4961f, 30.6f, -5.4f, CAT_SOLVENT},
    {"Hexane",         1.3750f, 56.8f, -5.4f, CAT_SOLVENT},
    {"DCM",            1.4244f, 40.1f, -5.8f, CAT_SOLVENT},
    {"Ethyl acetate",  1.3723f, 53.8f, -4.7f, CAT_SOLVENT},
    {"Glycerol",       1.4735f, 46.9f, -2.2f, CAT_POLYOL},

    /* 11-20: Polyols, Coolant, Oils */
    {"Propylene gly",  1.4324f, 47.9f, -3.6f, CAT_POLYOL},
    {"Ethylene gly",   1.4318f, 49.6f, -2.6f, CAT_COOLANT},
    {"Olive oil",      1.4677f, 47.2f, -3.8f, CAT_OIL},
    {"Sunflower oil",  1.4657f, 47.1f, -3.8f, CAT_OIL},
    {"Castor oil",     1.4778f, 45.4f, -4.0f, CAT_OIL},
    {"Coconut oil",    1.4483f, 48.3f, -3.8f, CAT_OIL},
    {"Mineral oil",    1.4667f, 46.0f, -3.5f, CAT_OIL},
    {"Silicone 100c",  1.4035f, 58.6f, -3.5f, CAT_OIL},
    {"Honey 18%MC",    1.4900f, 50.0f, -3.5f, CAT_FOOD},
    {"Maple syrup",    1.4580f, 49.0f, -3.2f, CAT_FOOD},

    /* 21-30: Solutions & Beverages */
    {"NaCl 10%",       1.3509f, 55.5f, -1.6f, CAT_SOLUTION},
    {"NaCl 20%",       1.3686f, 55.0f, -1.8f, CAT_SOLUTION},
    {"NaCl sat.",      1.3780f, 54.0f, -2.0f, CAT_SOLUTION},
    {"Glucose 5%",     1.3402f, 55.5f, -1.4f, CAT_SOLUTION},
    {"Glucose 20%",    1.3635f, 55.0f, -2.0f, CAT_SOLUTION},
    {"Glucose 40%",    1.3900f, 54.5f, -2.8f, CAT_SOLUTION},
    {"Sucrose 60%",    1.4490f, 49.0f, -3.3f, CAT_SOLUTION},
    {"Sucrose 40%",    1.3997f, 53.0f, -2.6f, CAT_SOLUTION},
    {"Cane juice",     1.3550f, 55.0f, -1.6f, CAT_BEVERAGE},
    {"Apple juice",    1.3505f, 55.2f, -1.5f, CAT_BEVERAGE},

    /* 31-40: Beverages, Dairy, Clinical */
    {"Orange juice",   1.3490f, 55.3f, -1.5f, CAT_BEVERAGE},
    {"Red wine",       1.3448f, 55.5f, -1.4f, CAT_BEVERAGE},
    {"Beer",           1.3380f, 55.6f, -1.2f, CAT_BEVERAGE},
    {"Coffee",         1.3345f, 55.7f, -0.9f, CAT_BEVERAGE},
    {"Milk whole",     1.3460f, 55.4f, -1.5f, CAT_DAIRY},
    {"Skim milk",      1.3443f, 55.5f, -1.3f, CAT_DAIRY},
    {"Cream 35%",      1.4080f, 52.0f, -2.5f, CAT_DAIRY},
    {"Urine normal",   1.3355f, 55.6f, -1.0f, CAT_CLINICAL},
    {"Urine dehyd.",   1.3380f, 55.5f, -1.2f, CAT_CLINICAL},
    {"Serum",          1.3450f, 55.2f, -1.3f, CAT_CLINICAL},

    /* 41-50: Clinical & Solvents */
    {"Saline 0.9%",    1.3345f, 55.7f, -0.9f, CAT_CLINICAL},
    {"DMSO",           1.4770f, 47.0f, -4.4f, CAT_SOLVENT},
    {"DMF",            1.4305f, 49.2f, -4.3f, CAT_SOLVENT},
    {"Acetonitrile",   1.3441f, 56.0f, -4.5f, CAT_SOLVENT},
    {"THF",            1.4070f, 51.8f, -5.1f, CAT_SOLVENT},
    {"Chloroform",     1.4459f, 41.0f, -5.9f, CAT_SOLVENT},
    {"CCl4",           1.4601f, 36.4f, -5.8f, CAT_SOLVENT},
    {"Benzene",        1.5011f, 30.2f, -5.5f, CAT_SOLVENT},
    {"Turpentine",     1.4690f, 44.0f, -4.0f, CAT_SOLVENT},
    {"Linseed oil",    1.4780f, 45.0f, -3.9f, CAT_OIL},

    /* 51-60: Oils, Automotive, Pharma */
    {"Sesame oil",     1.4650f, 47.3f, -3.8f, CAT_OIL},
    {"Peanut oil",     1.4660f, 47.1f, -3.8f, CAT_OIL},
    {"Brake DOT4 new", 1.4460f, 48.0f, -3.5f, CAT_AUTOMOTIVE},
    {"Brake DOT4 wet", 1.4360f, 49.0f, -3.0f, CAT_AUTOMOTIVE},
    {"Battery full",   1.4030f, 52.0f, -3.0f, CAT_AUTOMOTIVE},
    {"Battery 50%",    1.3750f, 54.0f, -2.5f, CAT_AUTOMOTIVE},
    {"Coolant 50%EG",  1.3820f, 53.0f, -2.8f, CAT_AUTOMOTIVE},
    {"Coolant 50%PG",  1.3840f, 52.5f, -3.0f, CAT_AUTOMOTIVE},
    {"EO lavender",    1.4580f, 49.5f, -3.8f, CAT_PHARMA},
    {"EO peppermint",  1.4600f, 49.0f, -3.8f, CAT_PHARMA},
};

/* Distance threshold for "confident" match */
#define CONFIDENCE_THRESHOLD  0.5f  /* Max normalized distance for 100% confidence */

void compound_lib_init(void) {
    /* TODO: Load custom entries from flash if present.
     * For now, use the hardcoded library above.
     */
}

/* Weighted Euclidean distance in (n_D, V_D) space.
 * n_D is weighted 3× because it's measured more precisely (±0.0003)
 * than V_D (±2.0).
 */
static float compound_distance(float n_D_meas, float vd_meas,
                                float n_D_lib, float vd_lib) {
    float dn = n_D_meas - n_D_lib;
    float dv = vd_meas - vd_lib;
    return sqrtf(3.0f * dn * dn + dv * dv * 0.01f);  /* V_D scaled down */
}

void compound_lib_match_detail(ri_result_t *result, knn_result_t *knn) {
    if (!result || !knn) return;

    /* Initialize k nearest with large distances */
    for (int i = 0; i < KNN_K; i++) {
        knn->indices[i] = -1;
        knn->distances[i] = 1e9f;
    }

    /* Find k nearest neighbors */
    for (int i = 0; i < LIB_SIZE; i++) {
        float d = compound_distance(result->n_D, result->abbe_vd,
                                     s_lib[i].n_D, s_lib[i].abbe_vd);

        /* Insert into k-nearest list */
        for (int j = 0; j < KNN_K; j++) {
            if (d < knn->distances[j]) {
                /* Shift remaining entries down */
                for (int k = KNN_K - 1; k > j; k--) {
                    knn->indices[k] = knn->indices[k - 1];
                    knn->distances[k] = knn->distances[k - 1];
                }
                knn->indices[j] = (int8_t)i;
                knn->distances[j] = d;
                break;
            }
        }
    }

    /* Confidence: inverse of nearest distance, normalized */
    if (knn->distances[0] < CONFIDENCE_THRESHOLD) {
        knn->confidence = 1.0f - (knn->distances[0] / CONFIDENCE_THRESHOLD);
    } else {
        knn->confidence = 0.0f;
    }
}

void compound_lib_match(ri_result_t *result) {
    if (!result) return;

    knn_result_t knn;
    compound_lib_match_detail(result, &knn);

    /* Set result fields from nearest match */
    if (knn.indices[0] >= 0) {
        result->compound_id = knn.indices[0];
        strncpy(result->compound_name, s_lib[knn.indices[0]].name,
                MAX_NAME_LEN - 1);
        result->compound_name[MAX_NAME_LEN - 1] = '\0';
        result->confidence = knn.confidence;

        /* If confidence is low, mark as unknown */
        if (knn.confidence < 0.15f) {
            result->compound_id = -1;
            /* Keep the name as the closest match for reference */
        }
    } else {
        result->compound_id = -1;
        strcpy(result->compound_name, "Unknown");
        result->confidence = 0;
    }
}

const compound_entry_t *compound_lib_get(uint8_t index) {
    if (index < LIB_SIZE) return &s_lib[index];
    return NULL;
}

void compound_lib_set(uint8_t index, const compound_entry_t *entry) {
    if (index < LIB_SIZE && entry) {
        s_lib[index] = *entry;
        /* TODO: Persist to flash */
    }
}

uint8_t compound_lib_size(void) {
    return LIB_SIZE;
}