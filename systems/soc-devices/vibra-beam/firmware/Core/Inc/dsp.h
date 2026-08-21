/*
 * dsp.h — FFT, windowing, spectrum analysis, modal fit
 */

#ifndef DSP_H
#define DSP_H

#include <stdint.h>
#include <math.h>
#include "config.h"

/* FFT result */
typedef struct {
    float    freq_peak_hz;
    float    mag_peak;
    float    thd_pct;
    float    snr_db;
    float    bin_hz;
    float    mag[CONFIG_FFT_SIZE / 2];   /* single-sided magnitude */
} fft_result_t;

void dsp_init(void);
void dsp_fft(const float *vel, uint32_t n, fft_result_t *res);
void dsp_window_hann(float *w, uint32_t n);
void dsp_window_hamming(float *w, uint32_t n);

/* Modal fit: find resonance peak & -3dB bandwidth → damping ζ */
typedef struct {
    float    fn_hz;       /* natural frequency */
    float    bw_3db_hz;   /* -3dB bandwidth */
    float    Q;           /* quality factor */
    float    zeta;       /* damping ratio */
    float    peak_mms;   /* peak velocity */
} modal_result_t;

void dsp_modal_fit(const fft_result_t *fft, float fmin, float fmax, modal_result_t *m);

#endif /* DSP_H */