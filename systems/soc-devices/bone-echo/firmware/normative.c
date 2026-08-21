/*
 * normative.c — WHO/ISCD T-score / Z-score look-up
 *
 * The normative database holds mean and SD of the Stiffness Index (SI)
 * for each demographic group, derived from the WHO/ISCD reference
 * values for calcaneus QUS (Langton et al., 1996; ISCD 2019 official
 * positions). The database has 4 ethnicities × 2 sex × 7 age groups
 * = 56 entries.
 *
 * T-score = (SI_patient − SI_youngAdultMean) / SI_youngAdultSD
 * Z-score = (SI_patient − SI_ageMatchedMean) / SI_ageMatchedSD
 *
 * WHO classification:
 *   T ≥ −1.0             → Normal
 *   −2.5 < T < −1.0      → Osteopenia
 *   T ≤ −2.5             → Osteoporosis
 *   T ≤ −2.5 + fracture  → Severe osteoporosis
 */

#include "normative.h"
#include "stm32g474_conf.h"

/* Normative database: [ethnicity][sex][age_group]
 * Values are approximate, derived from published QUS calcaneus studies.
 * In a clinical device, these would be from a validated reference
 * population (e.g., NHANES III, GE Achilles InSight database).
 */
static const normative_t norm_db[ETHNICITY_COUNT][SEX_COUNT][AGE_GROUP_COUNT] = {
  /* ETH_CAUCAASIAN */
  {
    /* MALE: mean, sd */
    { {95, 14}, {93, 14}, {91, 15}, {88, 15}, {84, 16}, {80, 16}, {75, 17} },
    /* FEMALE */
    { {89, 12}, {87, 12}, {84, 13}, {78, 14}, {70, 15}, {62, 16}, {55, 17} },
  },
  /* ETH_ASIAN */
  {
    /* MALE */
    { {93, 13}, {91, 13}, {89, 14}, {86, 14}, {82, 15}, {78, 15}, {73, 16} },
    /* FEMALE */
    { {87, 11}, {85, 11}, {82, 12}, {76, 13}, {68, 14}, {60, 15}, {53, 16} },
  },
  /* ETH_AFRICAN */
  {
    /* MALE */
    { {99, 13}, {97, 13}, {95, 14}, {92, 14}, {88, 15}, {84, 15}, {79, 16} },
    /* FEMALE */
    { {93, 11}, {91, 11}, {88, 12}, {82, 13}, {74, 14}, {66, 15}, {59, 16} },
  },
  /* ETH_HISPANIC */
  {
    /* MALE */
    { {94, 14}, {92, 14}, {90, 15}, {87, 15}, {83, 16}, {79, 16}, {74, 17} },
    /* FEMALE */
    { {88, 12}, {86, 12}, {83, 13}, {77, 14}, {69, 15}, {61, 16}, {54, 17} },
  },
};

void normative_init(void) { }

const normative_t* normative_lookup(sex_t sex, ethnicity_t eth, age_group_t ag)
{
    uint8_t e = (uint8_t)eth;
    uint8_t s = (uint8_t)sex;
    uint8_t a = (uint8_t)ag;
    if (e >= ETHNICITY_COUNT) e = 0;   /* Default to Caucasian */
    if (s >= SEX_COUNT) s = 0;
    if (a >= AGE_GROUP_COUNT) a = NORM_80_PLUS;
    return &norm_db[e][s][a];
}

age_group_t normative_age_group(uint8_t age_years)
{
    if (age_years < 30) return NORM_YOUNG_ADULT;
    if (age_years < 40) return NORM_30_39;
    if (age_years < 50) return NORM_40_49;
    if (age_years < 60) return NORM_50_59;
    if (age_years < 70) return NORM_60_69;
    if (age_years < 80) return NORM_70_79;
    return NORM_80_PLUS;
}

int normative_classify(float t_score, bool has_fracture)
{
    if (t_score > -1.0f)  return 0;   /* Normal */
    if (t_score > -2.5f)  return 1;   /* Osteopenia */
    if (has_fracture)     return 3;   /* Severe osteoporosis */
    return 2;                          /* Osteoporosis */
}