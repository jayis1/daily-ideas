/*
 * Tremor Tile — Inter-Core FIFO Header
 * intercore_fifo.h
 */

#ifndef TREMOR_TILE_INTERCORE_FIFO_H
#define TREMOR_TILE_INTERCORE_FIFO_H

#include <stdbool.h>
#include "sensor_acq.h"

void intercore_fifo_init(void);
bool intercore_fifo_push(sample_batch_t *batch);
bool intercore_fifo_pop(sample_batch_t *batch);

#endif // TREMOR_TILE_INTERCORE_FIFO_H