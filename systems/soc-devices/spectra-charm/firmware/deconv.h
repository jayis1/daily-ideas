/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * deconv.h — Spectral deconvolution API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef DECONV_H
#define DECONV_H

#include <stdint.h>

#define SPECTRUM_WL_START  340.0f
#define SPECTRUM_WL_END    700.0f
#define SPECTRUM_WL_RANGE  360.0f

void Deconv_Interpolate(float *input, const float *centers, const float *fwhms,
                          int n_channels, float *output);
float Deconv_GetWavelength(int index);
int Deconv_GetIndex(float wavelength);

#endif /* DECONV_H */