/*
 * laser.h — 650 nm laser diode constant-power control
 *
 * The laser diode (5 mW @ 650 nm) is driven by a constant-current
 * controller. A monitor photodiode (sampled via ADC2) provides
 * closed-loop power feedback so the scattering intensity is stable
 * across temperature and battery voltage. A software interlock
 * disables the laser when the cell cover is open (reed switch).
 */

#ifndef LASER_H
#define LASER_H

#include <stdbool.h>
#include <stdint.h>

#define LASER_TARGET_MW      5.0f     /* target optical power */
#define LASER_DRIVE_MAX_MA   60.0f   /* max drive current */
#define LASER_DRIVE_MIN_MA   5.0f

void     laser_init(void);
void     laser_on(void);
void     laser_off(void);
bool     laser_ok(void);            /* power within 10% of target */
float    laser_read_mw(void);       /* current optical power */

#endif /* LASER_H */