/*
 * Hive Mind — Bee Counter Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef BEE_COUNTER_H
#define BEE_COUNTER_H

#include <stdint.h>
#include <string.h>

typedef struct {
    uint16_t in_count;
    uint16_t out_count;
} bee_counts_t;

void bee_counter_init(void);
bee_counts_t bee_counter_count(uint32_t window_ms);
void bee_counter_leds_on(void);
void bee_counter_leds_off(void);

#endif /* BEE_COUNTER_H */