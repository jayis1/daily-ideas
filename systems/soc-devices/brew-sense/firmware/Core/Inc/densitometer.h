/**
 * densitometer.h — Vibrating Tube Densitometer Interface
 * 
 * Drives a piezo-based vibrating tube densitometer to measure
 * specific gravity of fermenting liquid.
 * 
 * Principle: A stainless steel tube is excited by a piezo driver
 * at its resonant frequency. The resonant frequency shifts with
 * the density of the fluid filling the tube:
 * 
 *   f_res = (1/2π) × √(k / (m_tube + ρ_fluid × V_tube))
 * 
 * By measuring f_res in air and in water (calibration), we can
 * solve for any fluid's specific gravity.
 */

#ifndef DENSITOMETER_H
#define DENSITOMETER_H

#include <stdint.h>
#include <stdbool.h>

/* Calibration constants stored in flash */
typedef struct {
    float f_air;        /* Resonant frequency in air (Hz) */
    float f_water;      /* Resonant frequency in distilled water at T_cal (Hz) */
    float t_cal;        /* Temperature at water calibration (°C) */
    float k;            /* Stiffness constant (computed from calibration) */
    float v_tube;       /* Tube internal volume constant (computed) */
    bool valid;          /* True if calibration data is valid */
} densitometer_cal_t;

/* Densitometer configuration */
typedef struct {
    uint32_t sweep_start_hz;     /* Start frequency for sweep (default: 1000) */
    uint32_t sweep_end_hz;       /* End frequency for sweep (default: 8000) */
    uint32_t sweep_step_hz;      /* Frequency step (default: 10) */
    uint32_t settle_time_us;     /* Settling time per step (default: 500) */
    uint8_t num_averages;        /* Number of sweep averages (default: 3) */
} densitometer_config_t;

/* Densitometer reading result */
typedef struct {
    float sg;                /* Specific gravity (e.g., 1.050) */
    float sg_temperature_compensated; /* SG corrected for temperature */
    float resonant_freq_hz;  /* Raw resonant frequency */
    float amplitude;         /* Peak amplitude at resonance */
    float q_factor;          /* Quality factor of resonance peak */
    bool valid;              /* True if measurement is reliable */
} densitometer_result_t;

/**
 * Initialize densitometer hardware.
 * Configures DAC, PWM, and ADC for piezo drive/sense.
 * @param config Configuration parameters (NULL for defaults)
 * @return 0 on success, negative on error
 */
int densitometer_init(const densitometer_config_t *config);

/**
 * Perform a frequency sweep and measure specific gravity.
 * @param temperature Current temperature in °C (for compensation)
 * @param result Pointer to result structure
 * @return 0 on success, negative on error
 */
int densitometer_read_sg(float temperature, densitometer_result_t *result);

/**
 * Calibrate with air reference point.
 * Call with the probe in air (no liquid).
 * @return Resonant frequency in Hz, or 0 on error
 */
float densitometer_calibrate_air(void);

/**
 * Calibrate with water reference point.
 * Call with the probe submerged in distilled water at known temperature.
 * @param water_temp Temperature of the water in °C
 * @return Resonant frequency in Hz, or 0 on error
 */
float densitometer_calibrate_water(float water_temp);

/**
 * Load calibration constants from flash.
 * @param cal Pointer to calibration structure to fill
 * @return true if valid calibration was found
 */
bool densitometer_load_calibration(densitometer_cal_t *cal);

/**
 * Save calibration constants to flash.
 * @param cal Pointer to calibration structure to save
 * @return 0 on success, negative on error
 */
int densitometer_save_calibration(const densitometer_cal_t *cal);

/**
 * Apply temperature correction to gravity reading.
 * Corrects for the expansion of the vibrating tube with temperature.
 * @param sg_measured Raw specific gravity reading
 * @param t_measured Current temperature in °C
 * @param t_calibration Calibration temperature in °C
 * @return Temperature-corrected specific gravity
 */
float densitometer_temp_compensate(float sg_measured, 
                                    float t_measured, 
                                    float t_calibration);

/**
 * Get last reading without performing a new sweep.
 * @param result Pointer to result structure
 * @return true if a valid reading is available
 */
bool densitometer_get_last_reading(densitometer_result_t *result);

/**
 * Put densitometer in low-power mode.
 * Disables DAC and piezo driver.
 */
void densitometer_sleep(void);

/**
 * Wake densitometer from low-power mode.
 * Re-enables DAC and piezo driver.
 */
void densitometer_wake(void);

#endif /* DENSITOMETER_H */