/*
 * species.h — Species class definitions, names, target/beneficial flags
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_SPECIES_H
#define ECHO_TRAP_SPECIES_H

#include "config.h"

void species_init(void);
const char *species_name(uint8_t id);
int species_is_target(uint8_t id);
int species_is_beneficial(uint8_t id);
float species_wingbeat_typical(uint8_t id);

#endif /* ECHO_TRAP_SPECIES_H */