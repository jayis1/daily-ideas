/*
 * volt-scribe — dsp.h
 * DSP utilities for electrochemical analysis
 */

#ifndef DSP_H
#define DSP_H

#include <stdlib.h>

typedef struct {
    float position;  /* x-value (potential, frequency, etc.) */
    float height;    /* y-value at peak */
    int   index;     /* array index */
} dsp_peak_t;

void dsp_init(void);

/* DFT */
void dsp_dft_single(const float *signal, int n_samples, float freq,
                    float sample_rate, float *real_out, float *imag_out);
void dsp_dft_magnitude(const float *signal, int n_samples,
                       float sample_rate, float *mag_out, int n_bins);

/* Smoothing */
void dsp_smooth(const float *in, float *out, int n, int window);

/* Derivative */
void dsp_derivative(const float *x, const float *y, float *dy, int n);

/* Peak detection */
int dsp_find_peaks(const float *x, const float *y, int n,
                   dsp_peak_t *peaks, int max_peaks,
                   float min_height, float min_distance);

/* Baseline correction */
void dsp_baseline_correct(float *y, int n, int edge_percent);

/* Nernst equation */
float dsp_nernst_potential(float E0, int n_electrons,
                           float C_ox, float C_red, float temperature_K);

/* Randles circuit model */
void dsp_randles_impedance(float R_s, float R_ct, float C_dl, float alpha,
                           float sigma_w, float freq,
                           float *Z_real, float *Z_imag);

#endif /* DSP_H */