/*
 * Levia Forge — Phase Engine Header
 * SPDX-License-Identifier: MIT
 */
#ifndef PHASE_ENGINE_H
#define PHASE_ENGINE_H

#include <stdint.h>
#include <stdbool.h>

void phase_engine_init(void);
void phase_engine_start(void);
void phase_engine_stop(void);
void phase_engine_set_blank(bool blanked);
bool phase_engine_is_underrun(void);
uint32_t phase_engine_get_cycles(void);

/* DMA IRQ handler (called by DMA_IRQ_0) */
void phase_engine_dma_irq(void);

#endif /* PHASE_ENGINE_H */