/*
 * classify.h — Crystal type decision-tree classifier
 *
 * Uses extracted motional parameters and turnover curve
 * to classify the crystal type: AT-cut, BT-cut, XY-fork,
 * SC-cut, ceramic resonator, SAW resonator, or unknown.
 */

#ifndef QUARTZ_TUNER_CLASSIFY_H
#define QUARTZ_TUNER_CLASSIFY_H

#include "types.h"

/* Classify crystal type from motional parameters and turnover curve.
 * Populates the classification result with label, confidence,
 * and per-class probabilities. */
void classify_crystal(const motional_t *params, classify_t *result);

/* Get human-readable name for a classification label */
const char *classify_name(int label);

#endif /* QUARTZ_TUNER_CLASSIFY_H */