/* state_machine.h — top-level measurement cycle */
#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

typedef enum {
    ST_IDLE = 0,
    ST_RAMP_DOWN,
    ST_TRACK,
    ST_VALID,
    ST_DEFROST,
} meas_state_t;

void sm_init(void);
void sm_start_measurement(void);
void sm_controller_tick(float dt);
void sm_application_tick(void);
meas_state_t sm_state(void);
const char *state_name(meas_state_t s);

#endif