/* tcd.h — Thermal Conductivity Detector driver (ADS122U04 + MEMS TCD bridge)
 *
 * The TCD is a 4-wire Wheatstone bridge with two hot filaments: one exposed
 * to the column effluent (measure) and one sealed in reference carrier gas.
 * The ADS122U04 measures the differential bridge voltage at 24-bit / 50 Hz.
 */
#ifndef TCD_H
#define TCD_H

#include <stdint.h>
#include <stdbool.h>

/* Raw sample from ADS122U04 — differential bridge voltage in µV */
typedef struct {
    int32_t  microvolts;   /* differential bridge reading, µV (signed) */
    float    baseline_uv;  /* running baseline estimate, µV */
    float    corrected_uv; /* microvolts - baseline_uv */
    int64_t  timestamp_us; /* esp_timer_get_us() at sample */
} tcd_sample_t;

/* Initialize ADS122U04 over SPI: configure registers for differential
 * input, gain=1, 50 SPS, internal 1.8 V reference, continuous mode. */
void tcd_init(void);

/* Start continuous sampling; sets up DRDY interrupt + ring buffer. */
void tcd_start(void);

/* Stop sampling. */
void tcd_stop(void);

/* Fetch the latest sample (non-blocking). Returns false if no new data. */
bool tcd_read(tcd_sample_t *out);

/* Fetch a block of samples into a caller-provided buffer.
 * Returns number actually copied (0..max). */
int tcd_read_batch(tcd_sample_t *buf, int max);

/* Current noise sigma estimate (µV) — updated every 256 samples. */
float tcd_noise_sigma(void);

/* Reset the baseline tracker (call at the start of each run). */
void tcd_reset_baseline(void);

#endif /* TCD_H */