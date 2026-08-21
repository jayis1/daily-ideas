/*
 * hall-puck / firmware / Core / Inc / measurement.h
 * Van der Pauw + Hall effect measurement engine
 *
 * Computes:
 *   - Sheet resistance R_s (Van der Pauw iterative solver)
 *   - Hall coefficient R_H (4-point field-reversal method)
 *   - Carrier concentration n = 1/(|R_H| * e)
 *   - Carrier type (n or p from sign of R_H)
 *   - Carrier mobility μ = |R_H| / R_s
 *   - Resistivity ρ = R_s * d
 *
 * MIT License.
 */
#ifndef MEASUREMENT_H
#define MEASUREMENT_H

#include <stdint.h>
#include <stdbool.h>
#include "vdp_switch.h"

/* Measurement mode */
typedef enum {
    MODE_SINGLE = 0,        /* Single measurement at current temperature */
    MODE_TEMP_SWEEP,        /* Temperature sweep (25–80°C, multiple points) */
    MODE_CONTINUOUS,        /* Continuous monitoring every 60s */
    MODE_QA,                /* QA pass/fail vs. target specs */
    MODE_COUNT
} meas_mode_t;

/* Measurement state */
typedef enum {
    MEAS_IDLE = 0,
    MEAS_CONTACT_CHECK,
    MEAS_VDP,
    MEAS_HALL_BP,
    MEAS_HALL_BM,
    MEAS_ANALYZING,
    MEAS_DONE,
    MEAS_ERROR,
} meas_state_t;

/* Carrier type */
typedef enum {
    CARRIER_UNKNOWN = 0,
    CARRIER_N_TYPE,
    CARRIER_P_TYPE,
} carrier_type_t;

/* Raw measurement point */
typedef struct {
    vdp_config_t config;
    float current_ma;       /* Forced current (mA) */
    float voltage_uv;       /* Measured voltage (µV) */
    float b_field_t;        /* Magnetic field (T) */
    float temperature_c;    /* Sample temperature (°C) */
} meas_point_t;

/* Measurement result */
typedef struct {
    float sheet_resistance;     /* R_s in Ω/□ */
    float hall_coefficient;     /* R_H in cm³/C (signed) */
    float carrier_conc;         /* n in cm⁻³ */
    float mobility;             /* μ in cm²/V·s */
    float resistivity;          /* ρ in Ω·cm */
    carrier_type_t carrier_type;/* n-type or p-type */
    float temperature_c;        /* Measurement temperature (°C) */
    float b_field_t;            /* B-field (T) */
    float current_ma;           /* Measurement current (mA) */
    float sample_thickness_mm;  /* Sample thickness (mm) */
    float ra_ohm;               /* Van der Pauw R_A */
    float rb_ohm;               /* Van der Pauw R_B */
    float vhall_uv;             /* Hall voltage (µV) */
    int n_points;               /* Number of raw measurement points */
    meas_state_t final_state;
    uint8_t status;             /* 0=ok, 1=error, 2=warning */
} meas_result_t;

/* Measurement parameters */
typedef struct {
    float current_ma;           /* Measurement current */
    float sample_thickness_mm;  /* Sample thickness */
    meas_mode_t mode;           /* Measurement mode */
    float temp_start_c;         /* Temp sweep start (°C) */
    float temp_end_c;           /* Temp sweep end (°C) */
    float temp_step_c;          /* Temp sweep step (°C) */
} meas_params_t;

#define MEAS_MAX_POINTS  16

/* Initialize measurement engine */
void measurement_init(void);

/* Start a measurement with given parameters */
void measurement_start(const meas_params_t *params);

/* Cancel current measurement */
void measurement_cancel(void);

/* Main measurement task (called from main loop) */
void measurement_task(void);

/* Get current state */
meas_state_t measurement_get_state(void);

/* Get result (valid after MEAS_DONE) */
const meas_result_t *measurement_get_result(void);

/* Get raw measurement points */
const meas_point_t *measurement_get_points(int *count);

/* Set sample thickness (mm) */
void measurement_set_thickness(float mm);

/* Get sample thickness */
float measurement_get_thickness(void);

/* Set measurement current (mA) */
void measurement_set_current(float ma);

/* Get measurement current */
float measurement_get_current(void);

/* Set B-field calibration */
void measurement_set_b_calibration(float b_t);

/* Van der Pauw iterative solver: solve for R_s given R_A and R_B */
float vdp_solve_rs(float ra, float rb);

/* Compute Hall coefficient from 4 voltage readings */
float hall_compute_rh(float v_fwd_bp, float v_rev_bp,
                      float v_fwd_bm, float v_rev_bm,
                      float current_ma, float b_field_t,
                      float thickness_mm);

/* Compute carrier concentration from Hall coefficient */
float hall_compute_conc(float rh);

/* Compute mobility from Hall coefficient and sheet resistance */
float hall_compute_mobility(float rh, float rs);

#endif /* MEASUREMENT_H */