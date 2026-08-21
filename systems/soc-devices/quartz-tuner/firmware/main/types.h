/*
 * types.h — shared types for the Quartz Tuner firmware
 *
 * All signal-path modules share these structs so the sweep,
 * parameter extraction, admittance fitting, Allan deviation,
 * turnover, and classification stages can pass a single
 * measurement descriptor through the pipeline without copying.
 */
#ifndef QUARTZ_TUNER_TYPES_H
#define QUARTZ_TUNER_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Sweep parameters */
#define SWEEP_POINTS_MAX    1024    /* max frequency points per sweep */
#define SWEEP_FREQ_MIN_HZ    1000   /* 1 kHz minimum */
#define SWEEP_FREQ_MAX_HZ    30000000  /* 30 MHz maximum */
#define CAL_STANDARDS        4       /* open, short, load, through */

/* Temperature sweep */
#define TEMP_POINTS_MAX     64      /* max points in turnover curve */
#define HEATER_POWER_W      1.0     /* max heater power (watts) */
#define TEMP_RANGE_MIN_C     -20.0f  /* min temperature for turnover sweep */
#define TEMP_RANGE_MAX_C      80.0f  /* max temperature for turnover sweep */

/* Allan deviation */
#define ALLAN_TAU_COUNT      3       /* tau = 0.1s, 1s, 10s */
#define ALLAN_BUF_SIZE       1024    /* frequency samples for Allan dev */

/* Classification */
#define XTAL_CLASS_COUNT    7       /* AT, BT, XY-fork, SC, ceramic, SAW, unknown */
#define CLASS_CONF_THRESH    0.70f   /* minimum confidence for classification */

/* Crystal type labels */
enum {
    CLASS_AT_CUT = 0,
    CLASS_BT_CUT = 1,
    CLASS_XY_FORK = 2,
    CLASS_SC_CUT = 3,
    CLASS_CERAMIC = 4,
    CLASS_SAW = 5,
    CLASS_UNKNOWN = 6
};

/* Complex number (real + imaginary) */
typedef struct {
    float re;
    float im;
} complex_t;

/* One frequency point in a sweep (from AD5933) */
typedef struct {
    float freq_hz;          /* frequency (Hz) */
    complex_t admittance;   /* Y(f) = G + jB (siemens), calibrated */
    complex_t raw;          /* raw DFT output before calibration */
    float mag;              /* |Y| */
    float phase_deg;        /* phase in degrees */
} sweep_point_t;

/* Full sweep result */
typedef struct {
    sweep_point_t points[SWEEP_POINTS_MAX];
    int n_points;                    /* number of valid points */
    float f_start_hz;               /* sweep start frequency */
    float f_step_hz;                 /* frequency step */
    float f_center_hz;               /* center (nominal) frequency */
    float span_hz;                   /* total sweep span */
    uint64_t timestamp_ms;          /* measurement timestamp */
} sweep_t;

/* Calibration coefficients (4 standards × complex) */
typedef struct {
    complex_t gain;         /* gain correction */
    complex_t offset;       /* offset correction */
    float system_phase;     /* system phase offset (radians) */
    float system_gain;      /* system gain factor */
    bool valid;             /* calibration has been performed */
} calibration_t;

/* Motional parameters (IEC 444 extraction) */
typedef struct {
    float f_s;              /* series resonant frequency (Hz) */
    float R1;               /* motional resistance (ohms) */
    float C1;               /* motional capacitance (farads) */
    float L1;               /* motional inductance (henries) */
    float C0;               /* shunt capacitance (farads) */
    float Q;                /* quality factor */
    float ESR;              /* equivalent series resistance (ohms) */
    float pullability;      /* pullability (ppm/pF) */
    float circle_residual;  /* admittance circle fit residual (ohms) */
    bool valid;             /* parameters are valid */
} motional_t;

/* Temperature turnover point */
typedef struct {
    float temp_c;           /* temperature (°C) */
    float delta_f_ppm;     /* Δf/f₀ in ppm */
    float f_measured_hz;   /* measured frequency at this temp */
} turnover_point_t;

/* Temperature turnover curve */
typedef struct {
    turnover_point_t points[TEMP_POINTS_MAX];
    int n_points;
    float T0;               /* turnover temperature (°C) */
    float Tc;               /* temperature coefficient (ppm/°C²) */
    float a0, a1, a2, a3;  /* polynomial coefficients */
    bool valid;
} turnover_t;

/* Allan deviation result */
typedef struct {
    float tau[ALLAN_TAU_COUNT];   /* gate times: 0.1, 1, 10 s */
    float sigma_y[ALLAN_TAU_COUNT]; /* Allan deviation at each tau */
    int n_samples;                 /* number of frequency samples used */
    bool valid;
} allan_dev_t;

/* Classification result */
typedef struct {
    int label;              /* CLASS_AT_CUT, etc. */
    float confidence;       /* 0..1 */
    float prob[XTAL_CLASS_COUNT]; /* probability per class */
    const char *name;       /* human-readable name */
} classify_t;

/* A complete crystal characterization */
typedef struct {
    sweep_t sweep;           /* frequency sweep data */
    calibration_t cal;       /* calibration state */
    motional_t params;      /* extracted motional parameters */
    turnover_t turnover;     /* temperature turnover curve */
    allan_dev_t allan;       /* Allan deviation */
    classify_t classification; /* crystal type */
    char label[32];          /* user label (from SD card) */
    uint32_t id;              /* measurement counter */
} crystal_t;

/* Device state */
typedef enum {
    STATE_IDLE = 0,
    STATE_CALIBRATING,
    STATE_SWEEPING,
    STATE_TEMPERATURE_SWEEP,
    STATE_ALLAN_MEASUREMENT,
    STATE_DISPLAY_RESULTS,
    STATE_ERROR
} device_state_t;

/* Display modes */
typedef enum {
    DISPLAY_PARAMS = 0,     /* motional parameters table */
    DISPLAY_CIRCLE = 1,     /* admittance circle G-jB */
    DISPLAY_TURNOVER = 2,   /* Δf/f₀ vs T */
    DISPLAY_ALLAN = 3,      /* σ_y(τ) vs τ */
    DISPLAY_CLASSIFY = 4    /* classification result */
} display_mode_t;

#endif /* QUARTZ_TUNER_TYPES_H */