/*
 * Tremor Tile — Tamper Detect Header
 * tamper_detect.h
 */

#ifndef TREMOR_TILE_TAMPER_DETECT_H
#define TREMOR_TILE_TAMPER_DETECT_H

#include <stdbool.h>

void tamper_detect_init(void);
bool tamper_detect_triggered(void);

#endif // TREMOR_TILE_TAMPER_DETECT_H