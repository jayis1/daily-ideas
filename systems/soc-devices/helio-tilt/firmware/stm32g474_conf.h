/*
 * stm32g474_conf.h — HAL / clock / peripheral configuration
 * for the STM32G474RET6 in the Helio Tilt tracking pyrheliometer.
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

/* ---- Solar Position (NOAA/SPA truncated) ----
 * Updated at 1 Hz. CORDIC handles sin/cos/atan2 in hardware.
 * Accuracy: ~0.01° in azimuth/elevation (sufficient for 5° FOV collimator).
 */
#define SOLAR_POS_UPDATE_HZ   1u
#define SOLAR_MIN_ELEV_DEG    5.0f     /* Don't track below 5° elevation */
#define SOLAR_REFRACT_CORR    1u       /* Saemundsson refraction correction */

/* ---- Stepper (NEMA8, 200 steps/rev, 1/16 microstep) ----
 * Azimuth: 200 × 16 = 3200 steps/rev, worm gear 60:1 → 192000 steps/rev
 *   → 360° / 192000 = 0.001875° per step
 * Elevation: 200 × 16 = 3200 steps/rev, timing belt 2:1 → 6400 steps/rev
 *   → 180° / 6400 = 0.028125° per step (elevation range 0–90°)
 */
#define STEPPER_MICROSTEP     16u
#define STEPPER_STEPS_PER_REV (200u * 16u)
#define AZ_WORM_RATIO         60u
#define AZ_STEPS_PER_DEG      ((float)(STEPPER_STEPS_PER_REV * AZ_WORM_RATIO) / 360.0f)
#define EL_BELT_RATIO         2u
#define EL_STEPS_PER_DEG      ((float)(STEPPER_STEPS_PER_REV * EL_BELT_RATIO) / 360.0f)
#define STEPPER_MAX_SPEED_SPS 3200u    /* 200 rev/min → 200×16/60 ≈ 53 rev/s */
#define STEPPER_ACCEL_SPS2    1600u    /* Acceleration */

/* ---- Filter Wheel (SG90 servo, 6 positions) ----
 * 50 Hz PWM, 1.0 ms = pos 0, 2.0 ms = pos 5, 0.2 ms per position
 */
#define FILTER_WHEEL_COUNT    6u
#define SERVO_PWM_FREQ_HZ     50u
#define SERVO_PULSE_MIN_US    1000u    /* Position 0 (405 nm) */
#define SERVO_PULSE_MAX_US    2000u    /* Position 5 (1640 nm) */
#define SERVO_PULSE_STEP_US   ((SERVO_PWM_FREQ_HZ == 50) ? \
    ((SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) / (FILTER_WHEEL_COUNT - 1)) : 200u)

/* ---- Wavelengths (nm) ---- */
#define WL_405    0
#define WL_440    1
#define WL_675    2
#define WL_870    3
#define WL_940    4
#define WL_1640   5
#define WL_COUNT  6

/* ---- ADS122U04 ADC (thermopile) ----
 * 24-bit ΔΣ, 20 Hz data rate, PGA 1–128×.
 * Thermopile: ~50 µV/(W/m²), max DNI ~1400 W/m² → 70 mV → PGA=8 fits in 3.3V ref.
 * At PGA=128, LSB = 3.3V / (128 × 2^23) = 0.0031 µV → 0.00006 W/m² (theoretical).
 * Practical noise floor ~0.5 W/m² after averaging.
 */
#define ADC_DATA_RATE_HZ      20u
#define ADC_PGA_DEFAULT       8u
#define ADC_VREF              3.3f
#define ADC_LSB_VOLTS        (ADC_VREF / (float)(1u << 23))   /* 24-bit, ~0.39 µV */
#define THERMOPILE_SENS      50.0e-6f   /* V/(W/m²) — 50 µV per W/m² */
#define THERMOPILE_DNI_MAX   1400.0f    /* W/m² */

/* ---- DNI Calibration ----
 * V₀(λ) extraterrestrial constants, from Langley calibration.
 * Defaults are approximate; must be Langley-calibrated for accuracy.
 */
#define DNI_CAL_DEFAULT_V0   1.0f       /* Placeholder, replaced by Langley */

/* ---- AOD / Atmospheric Correction ----
 * Rayleigh: τ_R = 0.00864 × λ⁻⁴ × (P/P₀)
 * Ozone: τ_O3 = α_O3(λ) × U_O3, U_O3 = 0.3 cm
 * Air mass: Kasten-Young formula: m = 1 / (cos(θ) + 0.50572×(96.07995-θ)⁻¹.6364)
 */
#define RAYLEIGH_COEF        0.00864f
#define OZONE_DEFAULT_DU     300.0f     /* 300 Dobson units = 0.3 cm */
#define P0_HPA               1013.25f   /* Standard pressure */

/* ---- Langley Calibration ----
 * Run for 2–3 hours, log V(λ) vs air mass m(θ).
 * Linear regression: ln(V) = ln(V0) - τ × m
 * Quality: R² > 0.99 required for valid calibration.
 */
#define LANGLEY_MIN_POINTS   60u        /* At least 60 points (1 per 2 min) */
#define LANGLEY_DURATION_S   9000u      /* 2.5 hours max */
#define LANGLEY_INTERVAL_S   120u       /* Sample every 2 minutes */
#define LANGLEY_MIN_R2       0.99f

/* ---- GPS (NEO-M9N) ----
 * UART2 at 38400 baud, NMEA 4.1.
 * PPS on PC4 for microsecond time sync.
 */
#define GPS_BAUD             38400u
#define GPS_NMEA_BUF_SIZE    256u
#define GPS_FIX_TIMEOUT_S    30u        /* Cold start timeout */
#define GPS_PPS_CORRECTION   1u         /* Apply PPS time correction */

/* ---- IMU (LSM6DSO) ----
 * I2C1 at 0x6A. Accelerometer ±2g, gyro ±250 dps for tilt sensing.
 */
#define IMU_I2C_ADDR         0x6A
#define IMU_ACCEL_RANGE      2u         /* ±2g */
#define IMU_GYRO_RANGE       250u       /* ±250 dps */
#define IMU_UPDATE_HZ        100u       /* 100 Hz IMU read */

/* ---- Magnetometer (MMC5603NJ) ----
 * I2C2 at 0x60. ±30 G range, 0.002°/√Hz noise.
 */
#define MAG_I2C_ADDR         0x60
#define MAG_UPDATE_HZ        10u        /* 10 Hz magnetometer read */

/* ---- Battery ----
 * PA0 (ADC1_IN1) reads Vbat via 2:1 divider.
 */
#define BAT_MIN_V            3.5f
#define BAT_LOW_V            3.4f
#define BAT_DIVIDER_RATIO    2.0f

/* ---- Display ---- */
#define OLED_I2C_ADDR        0x3D
#define OLED_WIDTH           128u
#define OLED_HEIGHT          64u

/* ---- BLE bridge ---- */
#define BLE_BAUD             921600u
#define BLE_MAX_PACKET       244u

/* ---- SD Logging ----
 * AERONET-compatible CSV format.
 */
#define SD_LOG_INTERVAL_S    1u         /* Log every 1 second */
#define SD_FILENAME_PREFIX   "helio"

#endif /* STM32G474_CONF_H */