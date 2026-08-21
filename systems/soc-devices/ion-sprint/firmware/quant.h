/*
 * quant.h — Internal-standard quantification
 */

#ifndef QUANT_H
#define QUANT_H

#include "stdint.h"

typedef struct {
    uint8_t ion_id;
    char    ion_name[16];
    float   migration_time;    /* seconds */
    float   area;               /* peak area */
    float   height;              /* peak height */
    float   concentration_mM;   /* quantified concentration (mM) */
} ion_result_t;

/* Initialize quantification module */
void quant_init(void);

/* Compute concentration from peak area using internal-standard method.
 * C_unknown = C_IS × (Area_unknown / Area_IS) × RF
 * where RF = response factor for this ion relative to internal standard. */
float quant_compute(uint8_t ion_id, float area, uint8_t bge_recipe);

/* Set internal standard concentration (mM) */
void quant_set_is_concentration(float conc_mM);

/* Set internal standard peak area (from detected peaks) */
void quant_set_is_area(float area);

#endif /* QUANT_H */