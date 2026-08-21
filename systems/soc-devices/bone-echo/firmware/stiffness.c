/*
 * stiffness.c — Stiffness Index: SI = 0.67·BUA + 0.28·SOS − 420
 *
 * The Stiffness Index (SI) is the standard composite metric from QUS
 * of the calcaneus (Langton et al., 1996). It combines BUA (bone
 * architecture / trabecular density) and SOS (bone elasticity /
 * cortical density) into a single number that correlates with bone
 * strength and fracture risk.
 *
 * SI = 0.67 × BUA + 0.28 × SOS − 420
 *
 * The coefficients are configurable in stm32g474_conf.h.
 */

#include "stiffness.h"
#include "stm32g474_conf.h"

void stiffness_init(void) { }

float stiffness_compute(float bua_db_mhz, float sos_mps)
{
    return SI_COEF_BUA * bua_db_mhz + SI_COEF_SOS * sos_mps - SI_OFFSET;
}