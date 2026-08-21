/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * matching.h — Spectral library matching API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef MATCHING_H
#define MATCHING_H

#include "spectrometer.h"

#define MATCH_THRESHOLD  0.70f  /* Minimum cosine similarity for a valid match */

void Matching_FindBest(const float absorbance[SPECTRUM_POINTS], CompoundMatch_t *match);
const char *Matching_GetCompoundName(CompoundID_t id);
uint16_t Matching_GetLibraryCount(void);

#endif /* MATCHING_H */