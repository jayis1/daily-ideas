/*
 * Spectra Charm — beerlambert.h
 */
#ifndef BEERLAMBERT_H
#define BEERLAMBERT_H

#include "spectrometer.h"
#include <stdbool.h>

float BeerLambert_Calculate(const float absorbance[SPECTRUM_POINTS],
                              const CompoundMatch_t *match);
bool BeerLambert_IsInLinearRange(const float absorbance[SPECTRUM_POINTS]);
void BeerLambert_FormatConcentration(float concentration_mol_L, char *buf, int buf_len);

#endif