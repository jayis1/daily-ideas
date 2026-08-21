/*
 * si5351.h — Si5351A I2C clock generator driver
 *
 * Controls the Si5351A to generate programmable frequency sweeps
 * for crystal stimulus. The Si5351A provides CLK0 as the sweep
 * stimulus and CLK1 as the AD5933 MCLK.
 */

#ifndef QUARTZ_TUNER_SI5351_H
#define QUARTZ_TUNER_SI5351_H

#include <stdint.h>
#include <stdbool.h>

/* Si5351A I2C address */
#define SI5351_ADDR     0x60    /* A0=A1=GND */

/* Crystal load capacitance (on-board 25 MHz XTAL) */
#define SI5351_XTAL_FREQ    25000000UL  /* 25 MHz */
#define SI5351_XTAL_CL      10          /* 10 pF load caps */

/* Initialize Si5351A: configure PLL, set MCLK output, enable CLK0 */
int si5351_init(void);

/* Set CLK0 to a specific frequency (Hz) for sweep stimulus.
 * Uses fractional-N synthesis for fine resolution (~0.1 Hz).
 * Returns 0 on success, -1 on error. */
int si5351_set_frequency(uint32_t freq_hz);

/* Start a frequency sweep from f_start to f_stop in n_steps.
 * Each step is approximately (f_stop - f_start) / n_steps Hz.
 * Call si5351_sweep_next() to advance to the next frequency. */
int si5351_sweep_start(uint32_t f_start_hz, uint32_t f_stop_hz, uint16_t n_steps);

/* Advance to the next sweep frequency. Returns the current frequency in Hz,
 * or 0 if the sweep is complete. */
uint32_t si5351_sweep_next(void);

/* Reset the Si5351A */
void si5351_reset(void);

/* Enable/disable CLK0 output */
void si5351_output_enable(bool enable);

/* Set CLK1 to a fixed MCLK frequency for the AD5933.
 * Typically 16.776 MHz (AD5933 internal oscillator = MCLK/4). */
int si5351_set_mclk(uint32_t mclk_hz);

/* Get the actual frequency set (may differ from requested due to
 * fractional-N rounding). Returns the closest achievable frequency. */
uint32_t si5351_get_actual_frequency(void);

#endif /* QUARTZ_TUNER_SI5351_H */