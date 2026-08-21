/*
 * fluorometer.h — Fluorescence measurement engine
 */

#ifndef FLUOROMETER_H
#define FLUOROMETER_H

#include <stdint.h>
#include "config.h"
#include "ccd_driver.h"
#include "led_wheel.h"

/**
 * Single-wavelength fluorescence measurement result.
 */
typedef struct {
    ex_wavelength_t ex_wl;         /* excitation wavelength enum */
    uint16_t ex_nm;                /* excitation wavelength in nm */
    ccd_frame_t emission;           /* dark-subtracted emission spectrum */
    uint16_t ref_counts;           /* reference photodiode reading */
    float    peak_wl;              /* peak emission wavelength (nm) */
    uint16_t peak_intensity;       /* peak emission intensity (counts) */
    uint16_t integration_ms;       /* integration time used */
    float    snr;                  /* signal-to-noise ratio */
} fluor_result_t;

/**
 * Initialize fluorometer subsystem.
 */
void fluorometer_init(void);

/**
 * Perform a single-wavelength fluorescence measurement.
 * @param ex  Excitation wavelength
 * @param params  Acquisition parameters
 * @param result  Output measurement
 * @return 0 on success, -1 on error
 */
int fluorometer_measure(ex_wavelength_t ex, const acq_params_t *params, fluor_result_t *result);

/**
 * Perform HDR (multi-exposure) measurement at one wavelength.
 * Combines short + long exposures to extend dynamic range.
 */
int fluorometer_measure_hdr(ex_wavelength_t ex, const acq_params_t *params, fluor_result_t *result);

/**
 * Apply reference normalization: divide emission by reference counts.
 * Compensates for LED intensity variation and aging.
 */
void fluorometer_normalize(fluor_result_t *result);

/**
 * Check safety interlocks before measurement.
 * @return 1 if safe to proceed, 0 if interlock triggered
 */
int fluorometer_check_safety(void);

#endif /* FLUOROMETER_H */