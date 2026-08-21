/*
 * Pulse Hound — RF Signal Hunter
 * spectrum.h — Waterfall buffer interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_SPECTRUM_H
#define PULSE_HOUND_SPECTRUM_H

#include <stdint.h>

void spectrum_push_rssi(float rssi_dbm);
void spectrum_get_row(int display_row, uint8_t *dest);
int  spectrum_get_full(void);

float spectrum_get_peak_rssi(void);
float spectrum_get_instantaneous_peak(void);
void spectrum_peak_hold_decay(uint32_t decay_ms);
void spectrum_peak_hold_reset(void);

int  spectrum_get_history(float *dest, int max_count);
float spectrum_avg_rssi(void);
float spectrum_max_rssi(void);

void spectrum_reset(void);

#endif /* PULSE_HOUND_SPECTRUM_H */