/*
 * pulse.h — pulse detection, peak extraction, and size binning
 *
 * The photodiode signal is a baseline DC (~0.5 V) with brief positive
 * pulses (~0.1–3 V, 2–10 µs) when a particle crosses the laser focus.
 * The detector:
 *   1. Tracks baseline (IIR low-pass, τ ~10 ms)
 *   2. Detects threshold crossings (baseline + N·σ noise)
 *   3. Finds the peak within a 20 µs window
 *   4. Maps peak height → particle size bin via the calibration table
 *   5. Invokes the callback with (bin_index, peak_voltage)
 */

#ifndef PULSE_H
#define PULSE_H

#include <stdint.h>

#define NUM_CHANNELS          16    /* size bins */
#define PULSE_WINDOW_SAMPLES  10    /* 20 µs at 500 ksps */
#define PULSE_MIN_HEIGHT_MV   30    /* minimum pulse height above baseline */

typedef void (*pulse_cb_t)(uint8_t bin, float peak_v);

void   pulse_init(void);
void   pulse_set_callback(pulse_cb_t cb);
void   pulse_process(const uint16_t *buf, uint32_t len);

/* Peak-height → size-bin boundary (mV). Index 0 = smallest. */
void   pulse_set_boundaries(const float *boundaries_mv, uint8_t count);
void   pulse_get_boundaries(float *out, uint8_t max);

/* Current baseline (mV) and noise sigma (mV) — for diagnostics */
float  pulse_baseline_mv(void);
float  pulse_noise_sigma_mv(void);

#endif /* PULSE_H */