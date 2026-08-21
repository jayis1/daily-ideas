/*
 * kappa-pin / firmware / main / measurement.h
 * Thermal conductivity / diffusivity measurement engine
 *
 * Transient line-source method:
 *   λ = Q / (4π · m)   where m = dΔT/d(ln t)
 *   α from full curve fit (Levenberg-Marquardt)
 *   ρcₚ = λ / α
 *   e = √(λ · ρcₚ)
 *
 * MIT License.
 */
#ifndef MEASUREMENT_H
#define MEASUREMENT_H

#include <stdint.h>
#include <stdbool.h>

#define MEAS_MAX_SAMPLES    7200    /* 60s @ 120 Hz */
#define MEAS_BASELINE_S     5.0f
#define MEAS_COOLING_MULT   2.0f    /* cooling = 2× pulse duration */

/* Material presets */
typedef enum {
    MAT_LIQUID = 0,
    MAT_WET_SOIL,
    MAT_DRY_SOIL,
    MAT_POLYMER,
    MAT_INSULATION,
    MAT_METAL_POWDER,
    MAT_CUSTOM,
    MAT_COUNT
} material_t;

typedef struct {
    const char *name;
    float power_w;
    float pulse_s;
    int sample_rate_hz;
    int probe_type;         /* -1 = any */
} material_preset_t;

/* Measurement state */
typedef enum {
    MEAS_IDLE = 0,
    MEAS_ARMING,            /* waiting for thermal equilibrium */
    MEAS_BASELINE,          /* recording T0 */
    MEAS_HEATING,           /* heat pulse active */
    MEAS_COOLING,           /* post-pulse sampling */
    MEAS_ANALYZING,         /* computing λ/α */
    MEAS_DONE,
    MEAS_ERROR,
} meas_state_t;

/* Measurement result */
typedef struct {
    float lambda;           /* thermal conductivity W/(m·K) */
    float alpha;             /* thermal diffusivity mm²/s */
    float rho_cp;           /* volumetric heat capacity J/(m³·K) */
    float effusivity;        /* J/(m²·K·s^0.5) */
    float t0_c;              /* baseline temperature °C */
    float avg_power_w;      /* average heater power */
    float dt_max_c;         /* max temperature rise */
    float slope;             /* dΔT/d(ln t) */
    float r_squared;        /* regression R² */
    float fit_alpha_r2;     /* α fit quality */
    int n_points;           /* samples in regression window */
    int fit_start_idx;      /* regression window start */
    int fit_end_idx;        /* regression window end */
    float pulse_duration_s;
    float total_duration_s;
    meas_state_t final_state;
    uint8_t material_id;
    uint8_t probe_type;
    uint32_t timestamp;     /* Unix time */
} meas_result_t;

/* Sample point (for streaming/logging) */
typedef struct {
    float t_s;       /* time since pulse start (s) */
    float temp_c;    /* temperature °C */
    float dt_mk;     /* ΔT in mK */
    float v_heater;  /* heater voltage */
    float i_heater;  /* heater current */
    float q_w;       /* heater power W */
} meas_sample_t;

/* Get material preset */
const material_preset_t *measurement_get_preset(material_t mat);

/* Start a measurement with given material preset */
void measurement_start(material_t mat);

/* Stop/cancel current measurement */
void measurement_cancel(void);

/* Main measurement task loop — call from FreeRTOS task */
void measurement_task(void *arg);

/* Get current state */
meas_state_t measurement_get_state(void);

/* Get result (valid after MEAS_DONE) */
const meas_result_t *measurement_get_result(void);

/* Get sample buffer for logging/streaming */
const meas_sample_t *measurement_get_samples(int *count);

/* Get current sample count (for live streaming) */
int measurement_get_sample_count(void);

/* Apply calibration factor */
void measurement_set_calibration(float cf);

/* Get calibration factor */
float measurement_get_calibration(void);

/* Blackwell axial correction factor */
float measurement_blackwell_correction(float q, float lambda_probe,
                                        float lambda_medium, float t_s);

#endif /* MEASUREMENT_H */