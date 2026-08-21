/*
 * pyro-balance / Core/Inc/furnace.h
 * Nichrome furnace PID temperature control + ramp generator.
 */
#ifndef FURNACE_H
#define FURNACE_H

#include "main.h"

void     furnace_init(void);
void     furnace_start(uint16_t final_temp_c, uint16_t rate_c_per_min_x10, uint16_t hold_min);
void     furnace_stop(void);
float    furnace_get_temp(void);       /* °C from ADS122U04 PT1000 */
float    furnace_get_target(void);
void     furnace_pid_tick(void);       /* call at 10 Hz */
void     furnace_cooling_tick(void);    /* active cooling until < 60 °C */
bool     furnace_is_stable(float tol_c);
void     furnace_set_duty(uint16_t pct_x10);  /* 0..1000, direct duty */

/* Safety */
bool     furnace_overtemp_hw(void);    /* TLV3201 comparator state */
bool     furnace_fuse_ok(void);        /* thermal fuse not blown */
void     furnace_emergency_cut(void);  /* relay + PWM=0 + fan ON */

#endif /* FURNACE_H */