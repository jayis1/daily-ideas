/**
 * alarm.h — Alarm and Notification Manager for Brew Sense
 * 
 * Manages buzzer and LED alerts for fermentation events:
 * stuck fermentation, finished, temperature alarms, etc.
 */

#ifndef ALARM_H
#define ALARM_H

#include <stdint.h>
#include <stdbool.h>
#include "fermentation.h"

/* Alarm patterns */
typedef enum {
    ALARM_PATTERN_NONE       = 0,
    ALARM_PATTERN_SHORT_BEEP = 1,  /* Single 200ms beep */
    ALARM_PATTERN_DOUBLE_BEEP = 2,  /* Two 200ms beeps */
    ALARM_PATTERN_LONG_BEEP  = 3,  /* Single 1000ms beep */
    ALARM_PATTERN_SIREN       = 4,  /* Alternating tone (stuck ferment!) */
    ALARM_PATTERN_HAPPY       = 5,  /* Ascending tone (fermentation done!) */
    ALARM_PATTERN_TICK        = 6,  /* Brief 50ms click (button feedback) */
} alarm_pattern_t;

/* Alarm configuration */
typedef struct {
    bool enable_buzzer;         /* Enable buzzer alarms */
    bool enable_led;            /* Enable LED alarms */
    float temp_high_threshold;  /* High temperature alert (°C), default: 30 */
    float temp_low_threshold;   /* Low temperature alert (°C), default: 10 */
    float ph_low_threshold;     /* Low pH alert, default: 2.5 */
    float ph_high_threshold;   /* High pH alert, default: 4.4 */
    uint32_t stuck_hours;       /* Hours for stuck ferment alert, default: 48 */
    bool alarm_on_finished;     /* Alert when fermentation finished */
    bool alarm_on_stuck;        /* Alert when fermentation stuck */
} alarm_config_t;

/**
 * Initialize alarm hardware (buzzer PWM + RGB LED GPIO).
 * @param config Configuration (NULL for defaults)
 */
void alarm_init(const alarm_config_t *config);

/**
 * Check all alarm conditions based on current fermentation state.
 * Call this on every sample interval.
 * @param stage Current fermentation stage
 * @param gravity Current specific gravity
 * @param temperature Current temperature
 * @param ph Current pH
 * @param alerts Alert flags from fermentation engine
 */
void alarm_check(ferment_stage_t stage, float gravity, 
                  float temperature, float ph, uint8_t alerts);

/**
 * Play an alarm pattern on the buzzer.
 * Non-blocking — pattern plays in background via timer.
 * @param pattern The alarm pattern to play
 */
void alarm_play(alarm_pattern_t pattern);

/**
 * Set RGB LED color.
 * @param r Red (0-255)
 * @param g Green (0-255)
 * @param b Blue (0-255)
 */
void alarm_set_led(uint8_t r, uint8_t g, uint8_t b);

/**
 * Turn off buzzer and LED.
 */
void alarm_silence(void);

/**
 * Check if any alarm is currently active.
 * @return true if buzzer or LED is active
 */
bool alarm_is_active(void);

/**
 * Acknowledge/silence current alarm.
 * Prevents the same alarm from re-triggering for 30 minutes.
 */
void alarm_acknowledge(void);

/**
 * Get a string description of current alarm state.
 * @return Human-readable alarm description
 */
const char *alarm_get_description(void);

#endif /* ALARM_H */