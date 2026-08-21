/*
 * dsc.h — DSC heat flow computation and peak detection (header)
 */
#ifndef DSC_H
#define DSC_H

#include <stdint.h>
#include <stdbool.h>

#define DSC_BUFFER_SIZE  32768  /* ~5.5 min at 100 Hz */
#define MAX_PEAKS        32
#define MAX_TRANSITIONS  8

typedef enum {
    PEAK_ENDOTHERMIC,
    PEAK_EXOTHERMIC,
    PEAK_GLASS_TRANSITION,
} peak_type_t;

typedef struct {
    peak_type_t type;
    float onset_temp;    /* °C */
    float peak_temp;     /* °C */
    float end_temp;      /* °C */
    float enthalpy;      /* J/g (normalized by sample mass) */
    float height;        /* mW */
    float delta_cp;      /* J/g/K (for Tg only) */
} dsc_peak_t;

typedef struct {
    float temp;       /* sample temperature (°C) */
    float heat_flow;  /* Φ = P_sample - P_reference (mW) */
    float time;       /* seconds since scan start */
} dsc_point_t;

typedef struct {
    dsc_point_t buffer[DSC_BUFFER_SIZE];
    uint32_t    count;
    float       baseline_start;   /* heat flow at scan start (mW) */
    float       baseline_end;     /* heat flow at scan end (mW) */
    dsc_peak_t  peaks[MAX_PEAKS];
    uint8_t     num_peaks;
    dsc_peak_t  transitions[MAX_TRANSITIONS];  /* Tg events */
    uint8_t     num_transitions;
    float       sample_mass;     /* mg */
} dsc_scan_t;

void    dsc_init(dsc_scan_t *scan);
void    dsc_add_point(dsc_scan_t *scan, float temp, float heat_flow, float time);
void    dsc_compute_heat_flow(float p_sample, float p_ref,
                               float v_supply, float duty_s, float duty_r,
                               float *heat_flow_mw);
void    dsc_detect_peaks(dsc_scan_t *scan);
void    dsc_compute_baseline(dsc_scan_t *scan);
float   dsc_integrate_peak(dsc_scan_t *scan, uint8_t peak_idx);
void    dsc_clear(dsc_scan_t *scan);

#endif /* DSC_H */