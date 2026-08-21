/*
 * experiment.h — Guided experiment engine
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#ifndef EXPERIMENT_H
#define EXPERIMENT_H

#include <stdint.h>
#include <stdbool.h>
#include "spike_detect.h"

#define MAX_EXPERIMENTS 8
#define MAX_INSTRUCTION_LEN 64

typedef enum {
    EXP_VENUS_SNAP = 0,
    EXP_MIMOSA_FOLD,
    EXP_LIGHT_DARK,
    EXP_WOUNDING,
    EXP_COLD_SHOCK,
    EXP_ELECTRO_STIM,
    EXP_CIRCADIAN,
    EXP_DROUGHT,
} experiment_id_t;

typedef struct {
    uint8_t       id;
    const char   *name;
    const char   *plant;
    const char   *instructions[MAX_INSTRUCTION_LEN / 16];
    uint8_t       num_instructions;
    uint32_t      duration_ms;
    float         expected_ap_min;     /* min AP amplitude (mV) */
    float         expected_ap_max;     /* max AP amplitude (mV) */
    uint16_t      expected_event_count; /* expected number of events */
    bool          uses_stimulus;        /* needs stimulus probe */
} experiment_t;

/* Get experiment definition by ID */
const experiment_t *experiment_get(uint8_t id);

/* Get total number of experiments */
uint8_t experiment_count(void);

/* Start an experiment — sets up gain, thresholds, stimulus */
int experiment_start(uint8_t id);

/* Check if experiment is running */
bool experiment_is_running(void);

/* Get current experiment ID (or -1) */
int8_t experiment_current(void);

/* Update experiment state (call every loop iteration) */
void experiment_update(uint32_t timestamp_ms, const spike_event_t *events, int n_events);

/* Get experiment result: did it pass? */
bool experiment_check_pass(uint8_t id, const spike_event_t *events, int n_events,
                            float *out_amplitude, uint16_t *out_count);

/* Stop the current experiment */
void experiment_stop(void);

/* Trigger stimulus (if experiment uses it) */
void experiment_trigger_stimulus(void);

#endif /* EXPERIMENT_H */