/*
 * lode-sweep / firmware / pi_driver.c
 * HRTIM TX pulse generation + ADC DMA sampling for 16-gate extraction.
 *
 * The HRTIM drives the IRFH7440 MOSFET that connects the search coil to the
 * 12 V boosted rail. After TX off, the HRTIM generates 16 ADC trigger
 * pulses at log-spaced delays. The ADC captures 16 samples per gate,
 * DMA'd into a buffer.
 */
#include "main.h"

/* Placeholder HAL handles */
static void *h_hrtim1 = (void *)1;
static void *h_adc1   = (void *)2;

/* HRTIM configuration for the TX pulse:
   - Timer A, center-aligned, period = TX_PERIOD_US (1 ms at 170 MHz)
   - CHA1: high for TX_PULSE_US (100 µs) → MOSFET ON
   - CHA2: complementary, for discharge path (deadtime 200 ns)
   - After CHA1 goes low (TX off), 16 compare events trigger ADC injections
     at the log-spaced gate delays. */
static void hrtim_config_tx_pulse(void)
{
    /* In a real implementation:
       - HRTIM Timer A period = 170MHz * 1000us = 170000 counts (1 ms)
       - CHA1 compare = 170MHz * 100us = 17000 counts (100 µs on)
       - CHA2 = complementary with 200 ns deadtime
       - ADC trigger from HRTIM compare events at gate delays
       - Burst mode: continuous at 1 kHz
    */
    (void)h_hrtim1;
}

/* ADC configuration for 16-gate sampling:
   - ADC1, 12-bit, 1 Msps, DMA circular
   - 16 injected channels triggered by HRTIM compare events
   - 16 oversample samples per gate, hardware averaged */
static void adc_config_gates(void)
{
    /* In a real implementation:
       - ADC1 in injected sequence mode
       - 16 triggers from HRTIM (one per gate delay)
       - Each trigger captures GATE_OVERSAMPLE (16) samples
       - DMA into adc_samples buffer (256 samples total)
       - Hardware oversampling: 16× → 16-bit effective
    */
    (void)h_adc1;
}

void pi_driver_init(void)
{
    hrtim_config_tx_pulse();
    adc_config_gates();
}

/*
 * Fire one TX pulse and capture the ADC samples.
 *
 * Sequence:
 *   1. Enable 12 V boost (PC15 high)
 *   2. Trigger HRTIM: MOSFET ON for 100 µs
 *   3. MOSFET OFF, flyback clamped by TVS
 *   4. Wait 10 µs for coil ring-down to settle
 *   5. HRTIM generates 16 ADC trigger pulses at gate delays
 *   6. ADC DMA captures 16 samples per gate (256 total)
 *   7. Return when DMA complete (blocking, ~300 µs total)
 */
void pi_fire_and_sample(int16_t *samples_out)
{
    /* 1. Ensure boost is enabled */
    /* gpio_set(PC15, 1) */

    /* 2. Trigger HRTIM single-shot pulse sequence */
    /* HAL_HRTIM_SimpleOnePulseStart(HRTIM1, HRTIM_TIMERINDEX_TIMER_A) */

    /* 3. Wait for ADC DMA complete (all 16 gates sampled) */
    /* The last gate ends at 284.2 + 16 = 300.2 µs after TX off */
    /* Total: 100 µs TX + 300 µs sampling = 400 µs; remaining 600 µs is idle */
    /* HAL_ADCEx_InjectedPollForConversion(h_adc1, 1) — or DMA IRQ semaphore */

    /* 4. Copy DMA buffer to output */
    /* In real build: memcpy(samples_out, dma_buf, 256 * sizeof(int16_t)) */
    /* Placeholder: fill with a synthetic decay curve for testing */
    static uint32_t seed = 12345;
    for (int g = 0; g < NUM_GATES; g++) {
        float t = GATE_DELAY_US[g] * 1e-6f;
        /* Simulated target decay: A * exp(-t/tau) + noise */
        float tau = 30e-6f;   /* copper-like decay */
        float val = 2000.0f * expf(-t / tau) + 100.0f;
        /* Add some noise */
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF;
        float noise = (float)(seed % 100) - 50.0f;
        val += noise;
        /* Fill 16 oversample samples with the same value (simulated) */
        for (int s = 0; s < GATE_OVERSAMPLE; s++) {
            samples_out[g * GATE_OVERSAMPLE + s] = (int16_t)val;
        }
    }
}