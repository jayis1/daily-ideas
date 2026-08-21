/*
 * qcm_driver.h — QCM crystal drive, frequency counting, ring-down
 */

#ifndef QCM_DRIVER_H
#define QCM_DRIVER_H

#include "config.h"

/* ── Si5351A control ─────────────────────────────────────── */
int  si5351_init(void);
int  si5351_set_freq(uint8_t channel, uint32_t freq_hz, uint8_t clk_out);
void si5351_disable_all(void);
void si5351_enable_clk(uint8_t clk_out);

/* ── TX/RX switch control ────────────────────────────────── */
void qcm_tx_enable(uint8_t channel);
void qcm_rx_enable(uint8_t channel);
void qcm_disable_all(void);

/* ── Frequency measurement (reciprocal counting) ─────────── */
/*  Uses TIM2 in input capture mode, gated by a 1s timebase.
 *  f = input_freq_count / gate_time_seconds
 *  Resolution: 0.01 Hz at 5 MHz with 1s gate + interpolation.
 */
float qcm_measure_frequency(uint8_t channel, uint32_t gate_ms);

/* ── Ring-down capture ────────────────────────────────────── */
/*  Disables TX drive, triggers ADC DMA to capture N samples
 *  of the crystal's decaying oscillation envelope.
 *  Returns the raw sample buffer for dissipation fitting.
 */
void qcm_capture_ringdown(uint8_t channel, uint16_t *buf, uint16_t n);

/* ── Baseline management ──────────────────────────────────── */
void qcm_set_baseline(uint8_t channel, uint8_t overtone_idx, float f, float d);
void qcm_get_baseline(uint8_t channel, uint8_t overtone_idx, float *f, float *d);

/* ── Full QCM-D measurement cycle ─────────────────────────── */
qcm_result_t qcm_measure(uint8_t channel, uint8_t overtone_idx,
                         float temperature, int do_ringdown, int do_voigt);

/* ── Multi-overtone sweep ─────────────────────────────────── */
uint8_t qcm_measure_all_overtones(uint8_t channel, float temperature,
                                  qcm_result_t *results, uint8_t max_n);

#endif /* QCM_DRIVER_H */