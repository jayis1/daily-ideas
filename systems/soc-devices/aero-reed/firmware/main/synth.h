/*
 * synth.h — wavetable synth + bore resonator
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define SYNTH_N_VOICES   16
#define SYNTH_SR         44100
#define N_WAVETABLES     8

typedef enum {
    WT_SINE = 0,
    WT_TRIANGLE,
    WT_SAW,
    WT_SQUARE,
    WT_FORMANT_A,
    WT_FORMANT_B,
    WT_BRIGHT_PULSE,
    WT_BREATH_NOISE,
} wavetable_id_t;

typedef struct {
    int8_t  note;        /* -1 = free */
    float   freq;       /* Hz */
    float   phase;
    float   amp;        /* current amplitude (envelope) */
    float   target_amp;
    float   bore_filt;  /* one-pole filter state */
    int8_t  wt;          /* wavetable index */
} synth_voice_t;

typedef struct {
    uint8_t  wt_index;
    int8_t   transpose;
    uint8_t  breath_curve_exp;   /* exponent ×4 (1=linear, 8=very steep) */
    uint8_t  breath_cc_exp;
    uint8_t  bore_q_x10;         /* Q ×10 */
    uint8_t  noise_mix;           /* 0..127 */
    uint8_t  bend_range_semi;
    uint8_t  growl_depth;
    uint8_t  tilt_mod;
    uint8_t  vibrato_rate_x2;
    uint8_t  vibrato_depth_cents;
    uint8_t  attack, decay, sustain, release;
    int8_t   octave_base;
    char     name[16];
} patch_t;

void  synth_init(void);
void  synth_note_on(int8_t note, uint8_t vel, const patch_t *patch);
void  synth_note_off(int8_t note);
void  synth_set_breath(float v01, const patch_t *patch);
void  synth_set_bend_cents(int16_t cents);
void  synth_set_modulation(uint8_t cc1);
void  synth_set_vibrato(float rate_hz, float depth_cents);
void  synth_render_block(int16_t *stereo, int n_frames);
void  synth_task(void *arg);

/* Global shared state (filled by sensor task, consumed by synth+midi tasks) */
typedef struct {
    int8_t    current_note;
    uint8_t   breath_vel;
    bool      breath_gate;
    int16_t   bend_cents;
    uint8_t   modulation;
    float     vibrato_rate;
    float     vibrato_depth;
    int8_t    patch_idx;
    patch_t   patch;
    uint8_t   battery_pct;
    bool      charging;
    bool      ble_connected;
    bool      usb_connected;
} aero_state_t;

extern aero_state_t g_state;
extern synth_voice_t synth_voices[SYNTH_N_VOICES];
extern const int16_t *wavetables[N_WAVETABLES];   /* 256-sample tables */
extern const int     WAVETABLE_LEN;