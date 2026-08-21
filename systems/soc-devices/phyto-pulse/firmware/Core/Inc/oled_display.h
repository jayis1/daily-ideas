/*
 * oled_display.h — SSD1306 OLED driver
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "spike_detect.h"

/* Display modes */
typedef enum {
    DISP_WAVE = 0,   /* Scrolling waveform + spike markers */
    DISP_STATS,       /* Event count, AP/VP/artifact breakdown */
    DISP_SWP,         /* Slow-wave potential trend */
    DISP_EXP,         /* Experiment selector */
    DISP_CONFIG,      /* Settings: gain, threshold, SD space */
} display_mode_t;

void oled_init(void);
void oled_set_mode(display_mode_t mode);
display_mode_t oled_get_mode(void);
void oled_next_mode(void);

/* Update display (call ~20 Hz) */
void oled_update(float current_value, float threshold, float baseline,
                  uint32_t sample_count, uint16_t event_count,
                  uint16_t ap_count, uint16_t vp_count, uint16_t art_count,
                  float battery_v, float ina_gain,
                  bool recording, int8_t current_experiment);

/* Show a message (e.g., "Recording...", "Error: No SD") */
void oled_show_message(const char *msg, uint32_t duration_ms);

/* Clear display */
void oled_clear(void);

/* Power off display (sleep) */
void oled_off(void);

/* Power on display (wake) */
void oled_on(void);

#endif /* OLED_DISPLAY_H */