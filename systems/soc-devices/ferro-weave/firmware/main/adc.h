/*
 * adc.h — dual-ADC 1 Msps simultaneous sampling
 */
#ifndef FERRO_WEAVE_ADC_H
#define FERRO_WEAVE_ADC_H

#include <stdint.h>
#include <stdbool.h>

#define ADC_BUF_LEN 4096   /* samples per channel (one full cycle) */

/* Raw DMA buffers — ADC1 (current, H) and ADC2 (integrator, B). */
extern uint16_t adc_raw_i[ADC_BUF_LEN];
extern uint16_t adc_raw_b[ADC_BUF_LEN];

/* Initialise ADC1+ADC2 in dual regular-simultaneous mode, 1 Msps each,
 * DMA into the buffers above, hardware oversample ×16 for the final
 * 62.5 ksps / 16-bit effective arrays. */
void adc_init(void);

/* Arm a capture — start DMA, triggered from the HRTIM update event so
 * sampling is synchronous to the sweep. */
void adc_arm_capture(void);

/* Block until the capture completes (DMA half/full + double-buffer). */
bool adc_wait_capture(uint32_t timeout_ms);

/* Convert raw ADC counts to engineering units:
 *   I (A)  = (raw - mid) * Vref / 4095 / Rsense / gain
 *   B (T)  = (raw - mid) * Vref / 4095 * k_int  (after air-flux corr) */
void adc_to_engineering(const uint16_t *raw_i, const uint16_t *raw_b,
                        int n, float *I, float *B);

/* OCP detection: called from the ADC watchdog ISR if any sample exceeds
 * the 2.5 A threshold. Sets the fault latch. */
void adc_ocp_handler(void);

#endif /* FERRO_WEAVE_ADC_H */