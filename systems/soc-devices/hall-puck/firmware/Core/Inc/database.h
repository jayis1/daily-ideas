/*
 * hall-puck / firmware / Core / Inc / database.h
 * Semiconductor reference database
 *
 * 30 common semiconductors with typical transport properties
 * for QA pass/fail comparison and material identification.
 *
 * MIT License.
 */
#ifndef DATABASE_H
#define DATABASE_H

#include <stdbool.h>

typedef struct {
    const char *name;
    float typical_mobility;     /* cm²/V·s */
    float typical_conc;         /* cm⁻³ */
    float mobility_min;         /* cm²/V·s */
    float mobility_max;         /* cm²/V·s */
    float resistivity_min;      /* Ω·cm */
    float resistivity_max;      /* Ω·cm */
    const char *carrier_type;   /* "n" or "p" */
    const char *category;
} semiconductor_ref_t;

#define SEMI_REF_COUNT  30

const semiconductor_ref_t *database_get_all(int *count);
int database_find_match(float mobility, float conc, float resistivity,
                         carrier_type_t type);
const char *database_get_name(int idx);
bool database_qa_check(int target_idx, const meas_result_t *r, float tol_pct);

/* Forward decl to avoid circular include */
typedef uint8_t carrier_type_t_dummy;
#ifndef MEASUREMENT_H
typedef enum { CARRIER_UNKNOWN_DUMMY = 0, CARRIER_N_TYPE_DUMMY, CARRIER_P_TYPE_DUMMY } carrier_type_t;
#endif

#endif /* DATABASE_H */