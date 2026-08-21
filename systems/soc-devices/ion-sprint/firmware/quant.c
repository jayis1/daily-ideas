/*
 * quant.c — Internal-standard quantification
 *
 * The internal standard (IS) method corrects for injection variability:
 * a known concentration of a non-sample ion (e.g., Ba²⁺ 1 mM) is added
 * to the sample. The ratio of unknown peak area to IS peak area is
 * proportional to the unknown concentration, independent of injection
 * volume:
 *
 *   C_unknown = C_IS × (Area_unknown / Area_IS) × RF
 *
 * where RF is the relative response factor (per-ion, per-BGE), stored
 * in flash. Default RF = 1.0 for all ions (C4D response is roughly
 * proportional to ionic mobility × concentration).
 */

#include "quant.h"
#include "stm32g474_conf.h"

static float is_concentration_mM = 1.0f;  /* Default 1 mM IS */
static float is_area = 1.0f;               /* Set from detected IS peak */

/* Per-ion response factors (relative to Ba²⁺ internal standard)
 * RF = μ_ion / μ_IS (electrophoretic mobility ratio)
 * These are approximate; user can calibrate with standards.
 */
static const float response_factors[ION_LIBRARY_SIZE] = {
    /* Cations */
    0.75f, 0.78f, 0.65f, 0.50f,  /* NH4, K, Na, Li */
    0.90f, 0.85f, 0.80f, 0.75f,  /* Ba, Sr, Ca, Mg */
    0.72f, 0.68f, 0.70f, 0.71f,  /* Mn, Fe, Co, Ni */
    0.69f, 0.73f, 0.60f, 0.55f,  /* Cu, Zn, Cr, Fe3 */
    0.50f, 0.45f, 0.48f, 0.40f,  /* Al, pyrrolid, morph, histidine */
    /* Neutral */
    0.00f,  /* EOF marker (no response) */
    /* Anions */
    0.82f, 0.60f, 0.70f, 0.75f,  /* Cl, F, NO2, NO3 */
    0.80f, 0.85f, 0.55f, 0.50f,  /* Br, I, formate, acetate */
    0.48f, 0.52f, 0.45f, 0.88f,  /* propionate, lactate, butyrate, oxalate */
    0.78f, 0.65f, 0.60f, 0.82f,  /* malonate, succinate, malate, tartrate */
    0.70f, 0.90f, 0.95f, 0.50f,  /* citrate, SO4, PO4, benzoate */
};

void quant_init(void)
{
    is_concentration_mM = 1.0f;
    is_area = 1.0f;
}

void quant_set_is_concentration(float conc_mM)
{
    is_concentration_mM = conc_mM;
}

void quant_set_is_area(float area)
{
    if (area > 1e-12f) is_area = area;
}

float quant_compute(uint8_t ion_id, float area, uint8_t bge_recipe)
{
    if (ion_id >= ION_LIBRARY_SIZE) return 0.0f;
    if (is_area < 1e-12f) return 0.0f;  /* No IS detected */

    float rf = response_factors[ion_id];
    if (rf < 1e-6f) return 0.0f;  /* Neutral or invalid */

    /* C_unknown = C_IS × (Area / Area_IS) × (1 / RF)
     * Note: RF = μ_ion/μ_IS, so higher-mobility ions give larger
     * C4D signal per unit concentration → divide by RF.
     */
    return is_concentration_mM * (area / is_area) / rf;
}