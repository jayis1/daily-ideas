/*
 * normative.h — WHO/ISCD T-score / Z-score look-up
 */

#ifndef NORMATIVE_H
#define NORMATIVE_H

#include <stdint.h>

typedef enum {
    SEX_MALE = 0,
    SEX_FEMALE = 1,
} sex_t;

typedef enum {
    ETH_CAUCAASIAN = 0,
    ETH_ASIAN = 1,
    ETH_AFRICAN = 2,
    ETH_HISPANIC = 3,
    ETH_OTHER = 0,   /* Falls back to Caucasian */
} ethnicity_t;

typedef enum {
    NORM_YOUNG_ADULT = 0,   /* 20-29 reference for T-score */
    NORM_30_39 = 1,
    NORM_40_49 = 2,
    NORM_50_59 = 3,
    NORM_60_69 = 4,
    NORM_70_79 = 5,
    NORM_80_PLUS = 6,
} age_group_t;

typedef struct {
    float mean_si;   /* Mean Stiffness Index for this demographic */
    float sd_si;     /* Standard deviation of SI */
} normative_t;

void             normative_init(void);
const normative_t* normative_lookup(sex_t sex, ethnicity_t eth, age_group_t ag);
age_group_t      normative_age_group(uint8_t age_years);
int              normative_classify(float t_score, bool has_fracture);

#endif