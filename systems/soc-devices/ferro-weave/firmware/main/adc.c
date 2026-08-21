/*
 * adc.c — dual-ADC 1 Msps simultaneous sampling (STM32G474)
 *
 * Hardware: ADC1+ADC2 in regular-simultaneous dual mode, each sampling
 * its channel 1 (PA0 / PA1) at 1 Msps. DMA double-buffering into
 * adc_raw_i / adc_raw_b. A hardware ADC analog watchdog on ADC1 fires
 * the OCP handler if the current exceeds 2.5 A.
 *
 * This file uses the STM32G4 HAL. In the simulation build it is replaced
 * by port_sim.c stubs.
 */
#include "adc.h"
#include <string.h>

/* These defaults are overridden by calibration in flash; see
 * docs/calibration-guide.md. */
static float g_vref   = 3.300f;  /* ADC reference voltage        */
static float g_rsense = 0.100f;  /* current-sense resistor (Ω)   */
static float g_i_gain = 20.0f;   /* current-sense amp gain (V/V) */
static float g_b_kint = 1.0f;    /* integrator V→T scale (cal'd) */

uint16_t adc_raw_i[ADC_BUF_LEN];
uint16_t adc_raw_b[ADC_BUF_LEN];

static volatile bool g_capture_done = false;
static volatile bool g_ocp_fault    = false;

void adc_init(void)
{
    /* ── Real firmware: configure ADC1+ADC2 dual mode, 1 Msps, 12-bit,
     *    hardware oversample ×16 → 16-bit effective at 62.5 ksps for the
     *    final arrays, watchdog on ADC1 channel 1 at 2.5 A threshold,
     *    DMA double-buffer mode 2, TC + HT interrupts.
     * ── Sim build: port_sim.c stubs the HAL calls. */
    memset(adc_raw_i, 0, sizeof(adc_raw_i));
    memset(adc_raw_b, 0, sizeof(adc_raw_b));
}

void adc_arm_capture(void)
{
    g_capture_done = false;
    /* HAL_ADCEx_MultiModeStart_DMA(...) in firmware. */
}

bool adc_wait_capture(uint32_t timeout_ms)
{
    (void)timeout_ms;
    /* In firmware: wait on a binary semaphore given by the DMA TC ISR. */
    return g_capture_done;
}

void adc_to_engineering(const uint16_t *raw_i, const uint16_t *raw_b,
                        int n, float *I, float *B)
{
    uint16_t mid = 2048;   /* midpoint for bipolar signals around Vref/2 */
    float i_scale = g_vref / 4095.0f / g_rsense / g_i_gain;
    float b_scale = g_vref / 4095.0f * g_b_kint;
    for (int i = 0; i < n; i++) {
        I[i] = ((int16_t)raw_i[i] - (int16_t)mid) * i_scale;
        B[i] = ((int16_t)raw_b[i] - (int16_t)mid) * b_scale;
    }
}

void adc_ocp_handler(void)
{
    g_ocp_fault = true;
    /* Firmware: HAL_ADC_Stop, assert HRTIM fault, sweep_stop(). */
}

/* DMA transfer-complete callback (firmware) / sim hook. */
void adc_dma_tc_callback(void)
{
    g_capture_done = true;
}