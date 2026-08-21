/*
 * Melody Sprite — RP2040 FM Synthesizer
 * display.h — SSD1306 OLED display driver (128×64, I2C)
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include <stdbool.h>

#define OLED_WIDTH    128
#define OLED_HEIGHT   64
#define OLED_PAGES    (OLED_HEIGHT / 8)  /* 8 pages of 8 pixels each */

/* Display modes */
typedef enum {
    DISPLAY_MODE_WAVEFORM = 0,  /* Oscilloscope-style waveform */
    DISPLAY_MODE_PARAMS,        /* Synth parameter display */
    DISPLAY_MODE_SEQUENCER,     /* Step sequencer grid */
    DISPLAY_MODE_MENU,          /* Settings menu */
    DISPLAY_MODE_BOOT,          /* Boot splash screen */
    DISPLAY_MODE_BLE_PAIRING    /* BLE pairing status */
} display_mode_t;

/* Parameter display layout */
typedef struct {
    char     name[12];      /* Parameter name */
    float    value;          /* Current value */
    float    min_val;        /* Minimum value */
    float    max_val;        /* Maximum value */
    char     unit[6];        /* Unit string (e.g., "ms", "Hz") */
} param_display_t;

/* Sequencer display data */
typedef struct {
    uint8_t  current_step;   /* 0–63 */
    uint8_t  pattern[8];     /* Bit pattern for 64 steps (8 bytes × 8 steps each) */
    uint16_t tempo;          /* BPM */
    bool     playing;
    bool     recording;
} seq_display_t;

/* Full display state */
typedef struct {
    uint8_t       framebuffer[OLED_WIDTH * OLED_PAGES];
    display_mode_t mode;
    bool          dirty;         /* Framebuffer changed, needs refresh */

    /* Waveform mode data */
    int16_t      *waveform_buf;  /* Pointer to synth audio buffer */
    int           waveform_len;

    /* Parameter mode data */
    param_display_t params[4];   /* 4 parameters (one per pot) */
    uint8_t       active_voice;  /* Which voice is shown */

    /* Sequencer mode data */
    seq_display_t seq;

    /* BLE pairing display */
    bool          ble_paired;
    char          ble_name[20];

    /* System status */
    uint8_t       battery_pct;
    bool          usb_connected;
} display_t;

/* Initialize OLED display via I2C */
void display_init(display_t *disp);

/* Set display mode */
void display_set_mode(display_t *disp, display_mode_t mode);

/* Update waveform display data */
void display_set_waveform(display_t *disp, int16_t *buf, int len);

/* Update parameter display */
void display_set_param(display_t *disp, int index, const char *name,
                       float value, float min, float max, const char *unit);

/* Update sequencer display */
void display_set_seq_data(display_t *disp, const seq_display_t *seq_data);

/* Render current mode to framebuffer */
void display_render(display_t *disp);

/* Push framebuffer to OLED via I2C */
void display_flush(display_t *disp);

/* Draw a single pixel in the framebuffer */
void display_set_pixel(display_t *disp, int x, int y, bool on);

/* Draw a horizontal line */
void display_hline(display_t *disp, int x, int y, int w, bool on);

/* Draw a vertical line */
void display_vline(display_t *disp, int x, int y, int h, bool on);

/* Draw a rectangle (outline) */
void display_rect(display_t *disp, int x, int y, int w, int h, bool on);

/* Draw a filled rectangle */
void display_rect_filled(display_t *disp, int x, int y, int w, int h, bool on);

/* Draw a small font character (5×7) */
void display_char(display_t *disp, int x, int y, char c, bool on);

/* Draw a string */
void display_string(display_t *disp, int x, int y, const char *str, bool on);

/* Draw a number (integer) */
void display_number(display_t *disp, int x, int y, int num, bool on);

#endif /* DISPLAY_H */