/*
 * Hive Mind — Temperature Chain Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef TEMP_CHAIN_H
#define TEMP_CHAIN_H

#include <stdint.h>
#include <string.h>

typedef enum {
    PROBE_FLOOR = 0,
    PROBE_MID,
    PROBE_CROWN,
} probe_location_t;

void temp_chain_init(void);
void temp_chain_read_all(float temps[3]);
uint8_t temp_chain_get_num_probes(void);
void temp_chain_get_rom_id(uint8_t index, uint8_t rom[8]);
void temp_chain_assign(uint8_t index, probe_location_t location);

#endif /* TEMP_CHAIN_H */