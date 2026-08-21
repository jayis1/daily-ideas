/*
 * laser.h — laser diode driver + shutter control + safety
 */

#ifndef LASER_H
#define LASER_H

#include <stdint.h>
#include "config.h"

void laser_init(void);
void laser_set_power_mw(float mw);
void laser_enable(void);
void laser_disable(void);
void shutter_open(void);
void shutter_close(void);
uint8_t laser_safety_check(void);   /* returns 1 if safe to fire */
float laser_get_power_mw(void);

#endif /* LASER_H */