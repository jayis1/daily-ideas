/* column.h — PID-controlled column heating band
 *
 * A nichrome wire wrapped around the 1 m coiled column provides heating.
 * A 10 kΩ NTC thermistor (β=3950) on GPIO5 measures column temperature.
 * PWM drives an IRLML2502 MOSFET low-side at 200 Hz (LEDC peripheral).
 */
#ifndef COLUMN_H
#define COLUMN_H

#include <stdbool.h>

/* Column method / temperature program */
typedef struct {
    float    start_temp_c;    /* initial hold temperature */
    uint16_t hold_start_s;    /* hold at start temp before ramp */
    float    ramp_c_per_min;  /* heating rate */
    float    final_temp_c;    /* target final temperature */
    uint16_t hold_final_s;    /* hold at final temp */
} column_method_t;

void column_init(void);

/* Set the method for the next run. */
void column_set_method(const column_method_t *m);

/* Get the current method. */
const column_method_t *column_get_method(void);

/* Read the current column temperature in °C. */
float column_read_temp_c(void);

/* Read the target temperature for the current phase. */
float column_read_target_c(void);

/* Start the temperature program. Returns immediately; temperature is
 * maintained by a FreeRTOS task. Call column_wait_done() to block. */
void column_start_ramp(void);

/* Block until the temperature program completes. */
void column_wait_done(void);

/* Force-off the heater (emergency stop / cooldown). */
void column_heater_off(void);

/* Active cooldown: turn on blower fan + disable heater until temp < 40°C. */
void column_cooldown(void);

/* Block until cooldown completes (temp < 40°C). */
void column_wait_cooldown(void);

/* Is the heater currently active? */
bool column_heater_active(void);

#endif /* COLUMN_H */