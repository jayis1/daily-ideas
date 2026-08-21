/*
 * kappa-pin / firmware / main / probe.h
 * Probe interface — probe detection, RTD temperature, probe parameters
 *
 * MIT License.
 */
#ifndef PROBE_H
#define PROBE_H

#include <stdint.h>
#include <stdbool.h>

/* Probe ID detection pin (ADC2) */
#define PROBE_ID_PIN        37
#define PROBE_ID_ADC        ADC2_CHANNEL_0  /* GPIO37 = ADC2_CH0 on S3 */

/* Probe types identified by ID resistor */
typedef enum {
    PROBE_NONE = 0,     /* disconnected (open) */
    PROBE_NEEDLE,       /* 0Ω  → NP-100 needle probe */
    PROBE_HOTWIRE,      /* 10kΩ → HW-60 hot-wire probe */
    PROBE_SURFACE,      /* 22kΩ → SP-40 surface probe */
} probe_type_t;

/* Probe parameters */
typedef struct {
    probe_type_t type;
    float heater_resistance;  /* ohms at 25°C */
    float active_length;      /* meters */
    float rtd_r0;             /* ohms (PT1000 = 1000) */
    const char *name;
    const char *standard;
} probe_info_t;

/* Detect probe type via ID resistor ADC reading */
probe_type_t probe_detect(void);

/* Get full probe info (detects if needed) */
const probe_info_t *probe_get_info(void);

/* Read current probe temperature in °C */
float probe_read_temperature(void);

/* Check thermal equilibrium (drift < threshold for duration) */
bool probe_is_equilibrium(float drift_threshold_c_per_s, float duration_s);

/* Update probe (call periodically to track temperature) */
void probe_update(void);

/* String representation of probe type */
const char *probe_type_name(probe_type_t t);

#endif /* PROBE_H */