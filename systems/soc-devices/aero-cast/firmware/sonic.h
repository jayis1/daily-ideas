/* sonic.h — ultrasonic time-of-flight measurement API */

#ifndef SONIC_H
#define SONIC_H

#include <stdint.h>
#include <stdbool.h>

/* Result of a single path measurement */
typedef struct {
    float t_forward_us;   /* forward transit time (µs) */
    float t_reverse_us;   /* reverse transit time (µs) */
    float v_path;         /* wind component along path (m/s) */
    float c_path;         /* speed of sound along path (m/s) */
    bool  valid;          /* true if both TOF measurements succeeded */
} path_result_t;

/* Complete measurement across all paths */
typedef struct {
    path_result_t paths[NUM_PATHS];
    uint32_t timestamp_us;  /* RP2040 microsecond timer */
} sonic_sample_t;

/* Initialize PIO, HV driver, mux, comparator threshold DAC */
void sonic_init(void);

/* Measure all paths. Returns true if all valid */
bool sonic_measure(sonic_sample_t *sample);

/* Fire a single path (for calibration/debug) */
bool sonic_measure_path(int path_idx, float *t_fwd_us, float *t_rev_us);

/* Set comparator threshold (0-4095 for MCP4911 DAC) */
void sonic_set_threshold(uint16_t dac_value);

/* Enable/disable HV driver */
void sonic_hv_enable(bool en);

/* Select active path via analog mux (0-2) */
void sonic_select_path(int path_idx);

#endif /* SONIC_H */