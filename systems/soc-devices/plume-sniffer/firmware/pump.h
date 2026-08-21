/* pump.h — Sample pump + 3-way valve control
 *
 * The micro-diaphragm pump (6 V DC) is driven through a MOSFET on GPIO2
 * with PWM for flow control. The 3-way solenoid valve on GPIO15 selects
 * between carrier (filtered air, port B) and sample (port A).
 */
#ifndef PUMP_H
#define PUMP_H

#include <stdbool.h>

typedef enum {
    VALVE_CARRIER = 0,   /* filtered air → column (default) */
    VALVE_SAMPLE  = 1,   /* sample inlet → preconcentrator */
} valve_state_t;

void pump_init(void);

/* Set pump on/off and speed (0–100%). */
void pump_set(float speed_pct);
void pump_off(void);

/* Set the 3-way valve state. */
void valve_set(valve_state_t s);

/* Integrate flow to measure sample volume. Call pump_start_sampling() at
 * the beginning of a sampling phase, pump_stop_sampling() at the end. */
void pump_start_sampling(void);
float pump_stop_sampling(void);   /* returns mL sampled */
float pump_sample_volume(void);   /* current mL since start */

#endif /* PUMP_H */