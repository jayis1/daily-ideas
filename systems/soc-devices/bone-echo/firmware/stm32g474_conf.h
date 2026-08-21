/*
 * stm32g474_conf.h — HAL / clock / peripheral configuration
 * for the STM32G474RET6 in the Bone Echo QUS densitometer.
 */

#ifndef STM32G474_CONF_H
#define STM32G474_CONF_H

#include "stm32g474xx.h"

/* ---- Clocking ----
 * HSI 16 MHz → PLL (PLLM=4, PLLN=85, PLLP=2, PLLR=2) → 170 MHz SYSCLK
 */
#define HSI_FREQ_HZ        16000000u
#define SYSCLK_FREQ        170000000u
#define SYSTICK_HZ         1000u
#define PLLM_VALUE         4u
#define PLLN_VALUE         85u
#define PLLP_VALUE         2u
#define PLLR_VALUE         2u

/* ---- ADC1 (RX signal) ----
 * 12-bit, up to 3.6 Msps. For ToF: full 3.6 Msps, 32 ms window = 115k samples.
 * For BUA: hardware oversample ×256, sample-shift 8 → 16-bit @ 28 ksps,
 * 50 ms window = 1400 samples (after digital I/Q demod at 1 MHz).
 */
#define ADC1_FULL_RATE     3600000u   /* 3.6 Msps */
#define ADC1_OVER_RATE     28000u     /* 28 ksps oversampled */
#define TOF_WINDOW_MS      32u        /* 32 ms raw capture */
#define BUA_WINDOW_MS      50u        /* 50 ms oversampled capture */
#define TOF_SAMPLES        (ADC1_FULL_RATE * TOF_WINDOW_MS / 1000u)   /* 115200 */
#define BUA_SAMPLES        (ADC1_OVER_RATE * BUA_WINDOW_MS / 1000u)    /* 1400 */
#define ADC_FULLSCALE_V    3.0f       /* VREF = 3.0 V (REF3030) */

/* ---- HRTIM (TX pulse trigger) ----
 * HRTIM clock: 170 MHz × 32 = 5.44 GHz equivalent → 184 ps resolution.
 * 1 MHz burst, 5 cycles → 5 µs burst, edge-triggered.
 */
#define HRTIM_TRIG_FREQ    1000000u   /* 1 MHz TX carrier */
#define TX_BURST_CYCLES    5u         /* 5-cycle 1 MHz burst */

/* ---- HV pulser ---- */
#define HV_TARGET_V        200u       /* 200 V TX pulse */
#define HV_TOLERANCE_V     20u         /* ±20 V (180–220 V) */
#define HV_BLEEDER_R_OHM   100000u     /* 100 kΩ bleeder */
#define HV_RESERVOIR_C_F   1e-6f      /* 1 µF reservoir cap */
#define HV_DISCHARGE_MS    500u       /* Discharge within 500 ms (5τ) */

/* ---- RX chain (AD8331) ---- */
#define VGA_GAIN_MIN_DB    0.0f       /* AD8331 minimum gain */
#define VGA_GAIN_MAX_DB    48.0f      /* AD8331 maximum gain */
#define VGA_GAIN_STEP_DB   1.0f       /* 1 dB step (DAC1 resolution) */
#define TGC_RAMP_START_DB  10.0f      /* TGC start gain */
#define TGC_RAMP_END_DB    45.0f      /* TGC end gain (depth compensation) */
#define BPF_LOW_HZ         500000u    /* 0.5 MHz band-pass low cut */
#define BPF_HIGH_HZ        2000000u   /* 2 MHz band-pass high cut */

/* ---- SOS measurement ---- */
#define SOS_MIN_MPS        1400.0f    /* Min valid SOS (soft tissue) */
#define SOS_MAX_MPS        2200.0f    /* Max valid SOS (cortical bone) */
#define SOS_CALIPER_MIN_MM 20.0f      /* Min heel width */
#define SOS_CALIPER_MAX_MM 80.0f      /* Max heel width */
#define PHANTOM_SOS_MPS    2700.0f    /* Acrylic phantom SOS (calibration) */
#define PHANTOM_THICK_MM   25.0f      /* Phantom thickness */

/* ---- BUA measurement ----
 * Fit band: 0.2–0.6 MHz (relative to the 1 MHz carrier).
 * After I/Q demod at 1 MHz, the band of interest is 0.8–1.6 MHz absolute,
 * which the BPF passes cleanly. We fit the slope A(f) vs f over this band.
 */
#define BUA_FIT_LOW_MHZ    0.2f       /* 0.2 MHz fit lower edge */
#define BUA_FIT_HIGH_MHZ   0.6f       /* 0.6 MHz fit upper edge */
#define BUA_MIN_DB_MHZ     0.0f       /* Min valid BUA */
#define BUA_MAX_DB_MHZ     80.0f      /* Max valid BUA */
#define BUA_FIT_R2_MIN     0.75f      /* Min R² for valid BUA fit */

/* ---- Stiffness Index (Langton 1996, configurable) ---- */
#define SI_COEF_BUA        0.67f
#define SI_COEF_SOS        0.28f
#define SI_OFFSET          420.0f

/* ---- Patient / demographics ----
 * 4 ethnicity options × 2 sex × 9 age groups = 72 reference entries.
 * Age groups: 20-29, 30-39, 40-49, 50-59, 60-69, 70-79, 80+,
 * plus young-adult (20-29) reference for T-score.
 */
#define ETHNICITY_COUNT    4
#define SEX_COUNT          2
#define AGE_GROUP_COUNT    7

#endif /* STM32G474_CONF_H */