/*
 * Melody Sprite — RP2040 FM Synthesizer
 * synth_engine.h — FM synthesis voice definitions and engine API
 */

#ifndef SYNTH_ENGINE_H
#define SYNTH_ENGINE_H

#include <stdint.h>
#include <stdbool.h>

#define NUM_VOICES       8
#define NUM_OPERATORS    2   /* carrier + modulator per voice */
#define MAX_POLY         NUM_VOICES
#define SAMPLE_RATE      44100
#define BUFFER_SIZE      256
#define MIDI_NOTE_MIN    12   /* C0 */
#define MIDI_NOTE_MAX    95   /* B7 */

/* ADSR state machine */
typedef enum {
    ENV_IDLE = 0,
    ENV_ATTACK,
    ENV_DECAY,
    ENV_SUSTAIN,
    ENV_RELEASE
} env_state_t;

/* Single ADSR envelope */
typedef struct {
    env_state_t state;
    float       attack;      /* seconds */
    float       decay;       /* seconds */
    float       sustain;     /* 0.0–1.0 */
    float       release;     /* seconds */
    float       level;       /* current envelope level */
    float       phase;       /* phase accumulator for timing */
} adsr_t;

/* FM operator (one per operator per voice) */
typedef struct {
    float    ratio;         /* frequency ratio relative to base note */
    float    mod_index;     /* modulation depth */
    float    feedback;      /* self-feedback amount (0–15) */
    float    phase;         /* current phase [0, 2π) */
    float    phase_inc;     /* phase increment per sample */
    float    last_output;   /* for feedback calculation */
    adsr_t   envelope;      /* per-operator envelope */
} fm_operator_t;

/* A single FM voice (2 operators: modulator + carrier) */
typedef struct {
    bool            active;
    uint8_t         note;        /* MIDI note number */
    uint8_t         velocity;    /* 0–127 */
    float           base_freq;   /* Hz, derived from note */
    float           volume;      /* 0.0–1.0 */
    fm_operator_t   modulator;   /* operator 0 */
    fm_operator_t   carrier;     /* operator 1 */
    int64_t         trigger_time;/* timestamp of note-on */
} fm_voice_t;

/* Effects chain */
typedef struct {
    /* Delay */
    bool    delay_on;
    float   delay_time;      /* ms (10–1000) */
    float   delay_feedback;  /* 0–0.9 */
    float   delay_mix;       /* 0–1.0 */
    float   delay_buffer[44100]; /* 1 second max delay */
    int     delay_write_idx;
    int     delay_read_offset;

    /* Bit-crusher */
    bool    crush_on;
    int     crush_bits;       /* 1–16 */
    int     crush_downsample;  /* 1–64 */
    int     crush_counter;
    float   crush_last;

    /* Low-pass filter (state variable filter) */
    bool    lpf_on;
    float   lpf_cutoff;      /* Hz (100–20000) */
    float   lpf_resonance;   /* Q (0–8.0) */
    float   lpf_low;
    float   lpf_high;
    float   lpf_band;
} fx_chain_t;

/* Full synth engine state */
typedef struct {
    fm_voice_t   voices[NUM_VOICES];
    fx_chain_t   fx;
    float        master_volume;
    int16_t      audio_buffer[BUFFER_SIZE * 2]; /* stereo interleaved */
    volatile bool buffer_ready;
    uint8_t      active_voices;
    uint8_t      octave_offset;  /* -2 to +2 */
    bool          hold_active;
} synth_engine_t;

/* --- API --- */

/* Initialize the synthesis engine */
void synth_init(synth_engine_t *engine);

/* Note on: allocate a voice and start playing */
void synth_note_on(synth_engine_t *engine, uint8_t note, uint8_t velocity);

/* Note off: release the voice envelope */
void synth_note_off(synth_engine_t *engine, uint8_t note);

/* Release all voices (panic) */
void synth_note_all_off(synth_engine_t *engine);

/* Set a voice parameter by name */
void synth_set_voice_param(synth_engine_t *engine, int voice,
                           const char *param, float value);

/* Set an effect parameter */
void synth_set_fx_param(synth_engine_t *engine, const char *fx_name,
                         const char *param, float value);

/* Toggle an effect on/off */
void synth_toggle_fx(synth_engine_t *engine, const char *fx_name, bool on);

/* Process one audio buffer (fills engine->audio_buffer) */
void synth_process(synth_engine_t *engine);

/* MIDI note number to frequency */
float midi_to_freq(uint8_t note);

#endif /* SYNTH_ENGINE_H */