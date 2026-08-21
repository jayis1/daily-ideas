/*
 * Melody Sprite — RP2040 FM Synthesizer
 * sequencer.h — Step sequencer definitions and API
 */

#ifndef SEQUENCER_H
#define SEQUENCER_H

#include <stdint.h>
#include <stdbool.h>
#include "synth_engine.h"

#define SEQ_NUM_STEPS      16
#define SEQ_NUM_BANKS      4
#define SEQ_TOTAL_STEPS    (SEQ_NUM_STEPS * SEQ_NUM_BANKS)  /* 64 */
#define SEQ_MAX_PATTERNS   128
#define SEQ_PATTERN_SIZE   256   /* bytes per pattern in flash */
#define SEQ_DEFAULT_TEMPO  120
#define SEQ_MIN_TEMPO      40
#define SEQ_MAX_TEMPO      300

typedef enum {
    SEQ_MODE_LIVE = 0,   /* Live record: keyboard → pattern */
    SEQ_MODE_EDIT,        /* Step edit: encoder places notes */
    SEQ_MODE_PLAY         /* Play: pattern loops, drives synth */
} seq_mode_t;

typedef struct {
    uint8_t note;     /* 0–127, 0xFF = empty/rest */
    uint8_t velocity; /* 0–127 */
    uint8_t gate;     /* 0–100% (as 0–100) */
    bool    accent;   /* accented step */
} seq_step_t;

typedef struct {
    seq_step_t steps[SEQ_TOTAL_STEPS];
    uint16_t   tempo;       /* BPM */
    uint8_t    swing;       /* 0–100% */
    uint8_t    current_bank;/* 0–3 */
    uint8_t    pattern_num; /* 0–127 */
} seq_pattern_t;

typedef struct {
    seq_pattern_t pattern;
    seq_mode_t    mode;
    bool          recording;
    bool          playing;
    uint8_t       current_step;   /* 0–63 */
    int64_t       last_step_time; /* us since last step */
    uint32_t      step_interval_us;
    bool          step_changed;    /* flag for UI */
    uint8_t       pending_note;    /* note waiting to be recorded */
    uint8_t       pending_vel;     /* velocity of pending note */
} sequencer_t;

/* Initialize sequencer with defaults */
void seq_init(sequencer_t *seq);

/* Set tempo in BPM */
void seq_set_tempo(sequencer_t *seq, uint16_t bpm);

/* Set swing amount (0–100) */
void seq_set_swing(sequencer_t *seq, uint8_t swing);

/* Start playback */
void seq_play(sequencer_t *seq);

/* Stop playback */
void seq_stop(sequencer_t *seq);

/* Start live recording */
void seq_record_start(sequencer_t *seq);

/* Stop recording */
void seq_record_stop(sequencer_t *seq);

/* Process one sequencer tick (call at audio rate or faster) */
void seq_tick(sequencer_t *seq, synth_engine_t *synth);

/* Set a step's note in edit mode */
void seq_set_step(sequencer_t *seq, uint8_t step, uint8_t note,
                  uint8_t velocity, uint8_t gate, bool accent);

/* Clear a step */
void seq_clear_step(sequencer_t *seq, uint8_t step);

/* Clear entire pattern */
void seq_clear_pattern(sequencer_t *seq);

/* Save pattern to flash */
int seq_save_pattern(sequencer_t *seq, uint8_t pattern_num);

/* Load pattern from flash */
int seq_load_pattern(sequencer_t *seq, uint8_t pattern_num);

/* Convert pattern to/from byte array for flash storage */
void seq_pattern_to_bytes(const seq_pattern_t *pat, uint8_t *buf);
void seq_bytes_to_pattern(const uint8_t *buf, seq_pattern_t *pat);

#endif /* SEQUENCER_H */