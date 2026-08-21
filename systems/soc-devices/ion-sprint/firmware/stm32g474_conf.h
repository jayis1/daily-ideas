/*
 * stm32g474_conf.h — HAL / clock / peripheral configuration
 * for the STM32G474RET6 in the Ion Sprint CE + C4D instrument.
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

/* ---- C4D Excitation (DAC2) ----
 * 100 kHz AC carrier, ±1.65 V centered on VREF/2 (1.65 V).
 * DAC2 is updated at 4× the carrier (400 kHz) to synthesize a sine.
 * Lock-in I/Q demodulation at 100 kHz extracts the amplitude envelope.
 */
#define C4D_EXCIT_FREQ_HZ  100000u     /* 100 kHz carrier */
#define C4D_DAC_RATE_HZ    400000u     /* 4× oversampled sine (4 pts/cycle) */
#define C4D_ADC_RATE_HZ    200000u     /* 2× oversampled acquisition (Nyquist+margin) */
#define C4D_LOCKIN_TC_MS   10u         /* Low-pass τ = 10 ms → 100 Hz electropherogram */
#define C4D_EPH_RATE_HZ    100u        /* Electropherogram sample rate (100 Hz) */
#define C4D_ADC_FULLSCALE  3.0f        /* VREF = 3.0 V (REF3030) */
#define C4D_SINE_TABLE_LEN 64u         /* Quarter-wave sine table for CORDIC */

/* ---- HV Supply ----
 * Cockcroft-Walton multiplier: 5 V → 30 kV, 200 µA max.
 * DAC1 (0–3.3 V) → V_ctrl → HV output (0–30 kV, 10 kV/V).
 * Soft-start ramp: 0 → target over 5 s.
 */
#define HV_TARGET_KV_MAX   30.0f      /* Max separation voltage 30 kV */
#define HV_CURRENT_MAX_UA  200.0f     /* Max current 200 µA */
#define HW_CUTOFF_UA       250.0f     /* HW comparator trip at 250 µA */
#define HV_VMON_DIVIDER    10000.0f   /* 10000:1 voltage divider (100M/10k) */
#define HV_IMON_GAIN        100.0f     /* AD8629 gain ×100, sense R = 100 Ω */
#define HV_RAMP_TIME_S     5.0f       /* Soft-start ramp time */
#define HV_BLEEDER_R_OHM   1e9f       /* 1 GΩ bleeder */
#define HV_TOLERANCE_KV    2.0f       /* ±2 kV from setpoint → abort */

/* ---- ADC1 (C4D signal) ----
 * 12-bit ADC at 200 kHz (2× oversampled vs 100 kHz carrier).
 * After I/Q lock-in demodulation + low-pass (τ=10 ms),
 * effective electropherogram rate is 100 Hz.
 */
#define ADC1_SAMPLE_RATE   200000u    /* 200 kHz raw ADC */
#define EPH_WINDOW_S_MAX    600u       /* 600 s max run (10 min) */
#define EPH_SAMPLES_MAX     (C4D_EPH_RATE_HZ * EPH_WINDOW_S_MAX)  /* 60000 */

/* ---- ADC2 (HV current monitor) ----
 * AD8629 amplifies the 100 Ω sense resistor voltage by ×100.
 * 1 µA → 100 µV → 10 mV at ADC → 10 µA resolution.
 */
#define ADC2_CURRENT_SCALE  0.01f    /* 1 ADC LSB = 0.01 µA (after gain) */

/* ---- ADC3 (HV voltage monitor) ----
 * 10000:1 divider: 30 kV → 3 V at ADC. 1 V/kV → 0.03 kV/LSB.
 */
#define ADC3_VOLTAGE_SCALE   0.0293f  /* kV per ADC LSB (3.0V ref / 1024 * 10) */

/* ---- Electropherogram processing ----
 * Baseline: asymmetric least squares (ALS), λ=1e5, p=0.001
 * Peak detection: 1st-derivative zero-cross + 2nd-derivative negative
 * + amplitude > 3× baseline noise (σ)
 */
#define ALS_LAMBDA          100000.0f
#define ALS_P               0.001f
#define PEAK_MIN_SNR        3.0f      /* Min peak S/N ratio */
#define PEAK_MIN_WIDTH_MS    50u       /* Min peak width 50 ms */
#define PEAK_MAX_WIDTH_MS    10000u    /* Max peak width 10 s */
#define MAX_PEAKS_PER_RUN    40u       /* Max 40 peaks (matches library) */

/* ---- Ion Library ----
 * 40 ions, k-NN (k=3) over normalized migration time + peak skewness.
 * Migration times calibrated under standard BGE: 20 mM MES/His, pH 6.1, 25°C.
 */
#define ION_LIBRARY_SIZE    40u
#define KNN_K               3u
#define BGE_TEMP_REF_C      25.0f     /* Reference temperature for migration times */
#define MT_NORM_TEMP_COEF   0.02f     /* 2% per °C mobility temperature coefficient */
#define MT_TOLERANCE_PCT    5.0f      /* ±5% migration time window for match */

/* ---- Injection ----
 * Electrokinetic: 5 kV for 1–5 s
 * Hydrodynamic: 10 cm lift for 5–30 s (NEMA8 stepper)
 */
#define INJ_EK_VOLTAGE_KV   5.0f      /* Electrokinetic injection voltage */
#define INJ_EK_DURATION_S   2.0f      /* Default 2 s */
#define INJ_HD_LIFT_MM      100.0f     /* Hydrodynamic lift 100 mm = 10 cm */
#define INJ_HD_DURATION_S   10.0f     /* Default 10 s */

/* ---- Peristaltic Pump ----
 * TIM4 PWM drives peristaltic pump for capillary flush between runs.
 */
#define PUMP_FLUSH_TIME_S   30u        /* 30 s flush between runs */
#define PUMP_PWM_FREQ_HZ    1000u      /* 1 kHz PWM */
#define PUMP_DUTY_FLUSH     70u        /* 70% duty for flush */

/* ---- Vial Lift Stepper ----
 * NEMA8, 200 steps/rev, M3 screw → 0.5 mm/rev → 0.0025 mm/step.
 * Lift 100 mm = 40000 steps (half-step mode = 80000 half-steps).
 */
#define STEPS_PER_MM        400u       /* 200 steps/rev ÷ 0.5 mm/rev */
#define LIFT_SPEED_SPS      400u       /* 400 steps/s → 1 mm/s */

/* ---- Battery ----
 * PA4 (ADC1_IN17) reads Vbat via 2:1 divider.
 * Gate HV arming on Vbat > 3.5 V to avoid brown-out.
 */
#define BAT_MIN_V           3.5f
#define BAT_LOW_V           3.4f
#define BAT_DIVIDER_RATIO   2.0f

/* ---- BGE Recipes (stored in flash, selectable via menu) ---- */
#define BGE_RECIPE_COUNT    8u

/* ---- Display ---- */
#define OLED_I2C_ADDR       0x3D      /* SH1106 I2C address */
#define OLED_WIDTH          128u
#define OLED_HEIGHT         64u

/* ---- BLE bridge ---- */
#define BLE_BAUD            921600u
#define BLE_MAX_PACKET      244u      /* Max BLE packet payload */

#endif /* STM32G474_CONF_H */