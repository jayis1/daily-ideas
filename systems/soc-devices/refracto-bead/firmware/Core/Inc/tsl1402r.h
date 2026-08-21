/**
 * tsl1402r.h — TSL1402R 256-pixel linear CCD driver
 *
 * The TSL1402R is a 256-pixel linear CCD array with 63.5 µm pixel pitch.
 * It requires:
 *   - CLK: 1 MHz square wave (TIM2_CH1 PWM)
 *   - SI:  start-integration pulse (TIM2_CH2, one-shot)
 *   - AO:  analog output (read by ADC1_IN1)
 *
 * Readout sequence:
 *   1. Pulse SI high for 1 CLK cycle (starts integration + pixel readout)
 *   2. Clock out 256 pixels, sampling AO on each CLK falling edge
 *   3. After 256 clocks, the next SI pulse starts a new integration
 *
 * Integration time = time between consecutive SI pulses.
 * Auto-exposure: adjust integration delay to keep peak pixel in 30–90% FS.
 */

#ifndef TSL1402R_H
#define TSL1402R_H

#include "stm32g4xx_hal.h"

#define TSL1402R_NUM_PIXELS   256
#define TSL1402R_CLK_FREQ_HZ  1000000  /* 1 MHz */
#define TSL1402R_ADC_MAX      4095     /* 12-bit ADC */

/**
 * Initialize the CCD driver with TIM2 (for CLK/SI) and ADC1 (for AO).
 * @param htim  TIM2 handle (CLK on CH1, SI on CH2)
 * @param hadc  ADC1 handle (AO on channel 1 = PA0)
 */
void tsl1402r_init(TIM_HandleTypeDef *htim, ADC_HandleTypeDef *hadc);

/**
 * Read all 256 pixels from the CCD.
 * Performs auto-exposure: if peak pixel > 90% FS, reduces integration time;
 * if < 10%, increases it. Returns 16-bit ADC values (0-4095).
 *
 * @param buffer  Output buffer (256 entries)
 */
void tsl1402r_read(uint16_t *buffer);

/**
 * Set the integration time (time between SI pulses in microseconds).
 * Range: 500–10000 µs (0.5–10 ms).
 */
void tsl1402r_set_integration(uint32_t us);

/**
 * Get current integration time.
 */
uint32_t tsl1402r_get_integration(void);

#endif /* TSL1402R_H */