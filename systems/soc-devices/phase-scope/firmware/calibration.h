/*
 * Phase Scope — Calibration header
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

typedef struct {
    float v_gain[3];       /* Voltage channel gain */
    float i_gain[3];       /* Current channel gain */
    float v_offset[3];     /* Voltage channel offset (ADC counts) */
    float i_offset[3];     /* Current channel offset (ADC counts) */
    float phase_offset[3]; /* Phase angle offsets (radians) */
    float shunt_res[3];    /* CT burden resistance (Ohm) */
    float v_divider_ratio; /* Voltage divider ratio */
    float amc_gain;        /* AMC1301 gain (typically 8.2) */
} calibration_t;

int calibration_load(calibration_t *cal);
int calibration_save(const calibration_t *cal);
int calibration_run(calibration_t *cal, const float *v_known, const float *i_known);

#endif /* CALIBRATION_H */