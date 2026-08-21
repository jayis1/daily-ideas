/*
 * Levia Forge — Safety Header
 * SPDX-License-Identifier: MIT
 */
#ifndef SAFETY_H
#define SAFETY_H

#include "sdkconfig.h"

void safety_init(void);
int safety_check(void *state);

#endif /* SAFETY_H */