/*
 * Melody Sprite — RP2040 FM Synthesizer
 * touch.h — Capacitive touch keyboard and function buttons driver (MPR121)
 */

#ifndef TOUCH_H
#define TOUCH_H

#include <stdint.h>
#include <stdbool.h>

#define TOUCH_NUM_KEYS      16   /* 2 octaves of chromatic notes */
#define TOUCH_NUM_BUTTONS   8    /* Function buttons */
#define TOUCH_THRESHOLD     12   /* Touch detection threshold */
#define TOUCH_RELEASE       8    /* Release threshold (hysteresis) */
#define TOUCH_DEBOUNCE_MS  5    /* Debounce time in ms */

/* Key event callback type */
typedef void (*touch_event_cb_t)(uint8_t key, uint8_t velocity, bool pressed);

/* Function button callback type */
typedef void (*button_event_cb_t)(uint8_t button, bool pressed);

/* Key state */
typedef struct {
    bool    touched;
    bool    prev_touched;
    int64_t touch_start_us;  /* For velocity calculation */
    uint8_t velocity;        /* Computed from touch duration */
    uint16_t baseline;        /* Calibration baseline */
    uint16_t signal;          /* Current signal level */
} touch_key_t;

/* Button state */
typedef struct {
    bool    pressed;
    bool    prev_pressed;
} touch_button_t;

/* Full touch controller state */
typedef struct {
    touch_key_t     keys[TOUCH_NUM_KEYS];
    touch_button_t  buttons[TOUCH_NUM_BUTTONS];
    touch_event_cb_t  key_callback;
    button_event_cb_t button_callback;
    bool            initialized;
} touch_controller_t;

/* Note mapping: key index → MIDI note number (C4 = 60 base) */
static const uint8_t key_to_midi[TOUCH_NUM_KEYS] = {
    60, 61, 62, 63, 64, 65, 66, 67,   /* C4–G4 */
    68, 69, 70, 71, 72, 73, 74, 75    /* G#4–D#5 */
};

/* Function button definitions */
typedef enum {
    BTN_SEQ    = 0,  /* Toggle sequencer record/play */
    BTN_OCT_DN = 1,  /* Octave down */
    BTN_OCT_UP = 2,  /* Octave up */
    BTN_WAVE   = 3,  /* Cycle waveform preset */
    BTN_FX1    = 4,  /* Toggle delay */
    BTN_FX2    = 5,  /* Toggle bit-crusher */
    BTN_FX3    = 6,  /* Toggle filter */
    BTN_HOLD   = 7   /* Sustain hold */
} func_button_t;

/* Initialize MPR121 controllers and touch sensing */
void touch_init(touch_controller_t *tc);

/* Set key press callback */
void touch_set_key_callback(touch_controller_t *tc, touch_event_cb_t cb);

/* Set button press callback */
void touch_set_button_callback(touch_controller_t *tc, button_event_cb_t cb);

/* Scan all touch sensors (call from main loop) */
void touch_scan(touch_controller_t *tc);

/* Recalibrate baselines (call periodically) */
void touch_recalibrate(touch_controller_t *tc);

/* Get current key state */
bool touch_is_key_pressed(const touch_controller_t *tc, uint8_t key);

/* Get current button state */
bool touch_is_button_pressed(const touch_controller_t *tc, uint8_t button);

#endif /* TOUCH_H */