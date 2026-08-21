/*
 * spike_detect.h — Adaptive threshold spike detection
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Detects action potentials and variation potentials in the 1 kHz
 * plant electrophysiology signal using an adaptive threshold (μ + k·σ)
 * with a refractory period.
 */

#ifndef SPIKE_DETECT_H
#define SPIKE_DETECT_H

#include <stdint.h>
#include <stdbool.h>

/* Ring buffer size (must be power of 2) */
#define SPIKE_BUF_SIZE 2048

/* Maximum events held in queue */
#define MAX_EVENTS 64

/* Event types (matches CNN output classes) */
typedef enum {
    EVENT_NONE = 0,
    EVENT_AP,        /* Action potential: 10-100 ms, symmetric */
    EVENT_VP,        /* Variation potential: 1-10 s, asymmetric */
    EVENT_ARTIFACT,  /* Mains pickup, motion, electrode pop */
} event_type_t;

/* Detected spike event */
typedef struct {
    uint32_t      timestamp_ms;   /* millis since session start */
    int32_t       sample_index;   /* sample number in session */
    float         amplitude_mv;   /* peak amplitude (mV, signed) */
    float         duration_ms;    /* event duration (ms) */
    float         area_mvms;      /* area under curve (mV·ms) */
    float         rise_time_ms;   /* 10% → 90% rise time */
    float         decay_tau_ms;   /* decay time constant (ms) */
    float         asymmetry;      /* rise/decay ratio */
    event_type_t  classification; /* CNN class */
    float         confidence;     /* CNN confidence 0-1 */
} spike_event_t;

/* Initialize detector */
void spike_detect_init(void);

/* Feed a new sample (input-referred voltage in mV) */
void spike_detect_feed(float voltage_mv, uint32_t timestamp_ms, int32_t sample_idx);

/* Check if a new event is available */
bool spike_detect_event_available(void);

/* Get the next event (returns false if none) */
bool spike_detect_get_event(spike_event_t *event);

/* Get running statistics */
float spike_detect_get_baseline(void);
float spike_detect_get_threshold(void);
float spike_detect_get_noise(void);

/* Set detection sensitivity (k multiplier, default 5.0) */
void spike_detect_set_sensitivity(float k);

/* Get current waveform display value (for OLED) */
float spike_detect_get_display_value(void);

/* Ring buffer access for display/windowing */
int spike_detect_get_window(float *buffer, int max_samples);

#endif /* SPIKE_DETECT_H */