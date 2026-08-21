/*
 * ref_osc.h — reference oscillator: CORDIC sine + DAC1 drive
 * Generates a phase-coherent sine at f0 (1 Hz–100 kHz) for both the
 * external Ref Out BNC and the internal digital demodulator.
 */
#ifndef REF_OSC_H
#define REF_OSC_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float    freq_hz;        /* current reference frequency           */
    float    amplitude_v;    /* Ref Out amplitude (0–2 V)             */
    float    phase_deg;      /* user phase shift (0–360°)             */
    uint32_t phase_accum;    /* 32-bit phase accumulator (q32)        */
    uint32_t phase_inc;      /* phase increment per DAC sample         */
    bool     running;       /* reference enabled?                     */
    bool     dual_mode;     /* also demodulate at 2×f0 (2f)           */
} ref_osc_t;

void ref_osc_init(void);
void ref_osc_set_freq(float f_hz);
void ref_osc_set_amplitude(float v);
void ref_osc_set_phase(float deg);
void ref_osc_start(void);
void ref_osc_stop(void);

/* Get the current I/Q reference samples (q1.31) for the demodulator.
 * Called once per ADC sample (f_s = 28 ksps); the reference is
 * upsampled from the 1 MHz DDS by linear interpolation.
 */
void ref_osc_get_iq(int32_t *i_ref, int32_t *q_ref);

extern ref_osc_t g_ref;

#endif /* REF_OSC_H */