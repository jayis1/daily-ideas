/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * deconv.c — Spectral deconvolution and interpolation
 *
 * Interpolates from 9 AS7343 channels to 128 effective spectral points
 * using Gaussian kernel interpolation with known channel response functions.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "deconv.h"
#include <math.h>
#include <string.h>

/* AS7343 channel center wavelengths and FWHM are passed in by caller */

/* Gaussian kernel for channel response approximation */
static float gaussian_kernel(float wavelength, float center, float fwhm)
{
    float sigma = fwhm / 2.3548f; /* FWHM to sigma */
    float diff = wavelength - center;
    return expf(-(diff * diff) / (2.0f * sigma * sigma));
}

/*
 * Deconv_Interpolate — Interpolate from N channel readings to SPECTRUM_POINTS
 *
 * For each output wavelength, compute weighted sum of all channel responses.
 * Weights are the Gaussian response of each channel at that wavelength.
 * This performs a simple spectral reconstruction assuming each channel
 * measures the integrated signal under its Gaussian response curve.
 *
 * Parameters:
 *   input      — array of N channel values
 *   centers    — center wavelength (nm) for each channel
 *   fwhms      — FWHM (nm) for each channel
 *   n_channels — number of input channels
 *   output     — SPECTRUM_POINTS output array (can alias input if first N elements valid)
 */
void Deconv_Interpolate(float *input, const float *centers, const float *fwhms,
                          int n_channels, float *output)
{
    float temp[SPECTRUM_POINTS];
    float weight_sum[SPECTRUM_POINTS];

    memset(temp, 0, sizeof(temp));
    memset(weight_sum, 0, sizeof(weight_sum));

    /* Wavelength range: 340 nm to 700 nm */
    const float wl_start = 340.0f;
    const float wl_end = 700.0f;
    const float wl_step = (wl_end - wl_start) / (SPECTRUM_POINTS - 1);

    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        float wl = wl_start + i * wl_step;
        float sum = 0.0f;
        float wsum = 0.0f;

        for (int ch = 0; ch < n_channels; ch++) {
            float weight = gaussian_kernel(wl, centers[ch], fwhms[ch]);
            sum += weight * input[ch];
            wsum += weight;
        }

        if (wsum > 1e-6f) {
            temp[i] = sum / wsum;
        } else {
            temp[i] = 0.0f;
        }
        weight_sum[i] = wsum;
    }

    /* Edge taper — reduce artifacts at edges where channel coverage is sparse */
    for (int i = 0; i < 5; i++) {
        float taper = (float)(i + 1) / 5.0f;
        temp[i] *= taper;
        temp[SPECTRUM_POINTS - 1 - i] *= taper;
    }

    /* Copy to output */
    memcpy(output, temp, sizeof(temp));
}

/*
 * Deconv_GetWavelength — Convert array index to wavelength
 */
float Deconv_GetWavelength(int index)
{
    if (index < 0) index = 0;
    if (index >= SPECTRUM_POINTS) index = SPECTRUM_POINTS - 1;
    return 340.0f + (360.0f * index / (SPECTRUM_POINTS - 1));
}

/*
 * Deconv_GetIndex — Convert wavelength to nearest array index
 */
int Deconv_GetIndex(float wavelength)
{
    int idx = (int)((wavelength - 340.0f) * (SPECTRUM_POINTS - 1) / 360.0f + 0.5f);
    if (idx < 0) idx = 0;
    if (idx >= SPECTRUM_POINTS) idx = SPECTRUM_POINTS - 1;
    return idx;
}