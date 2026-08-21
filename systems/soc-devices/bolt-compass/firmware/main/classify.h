/*
 * classify.h — int8 CG/IC/CC stroke classifier
 */
#ifndef BOLT_COMPASS_CLASSIFY_H
#define BOLT_COMPASS_CLASSIFY_H

#include "types.h"

void classify_init(void);

/* Run the int8 logistic-regression classifier on the sferic features.
 * Fills out->label, out->conf, out->prob[]. */
void classify_sferic(const sferic_t *s, classify_t *out);

#endif /* BOLT_COMPASS_CLASSIFY_H */