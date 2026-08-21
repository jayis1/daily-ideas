/*
 * calibrate.h — OSLT (Open/Short/Load/Through) calibration
 */

#ifndef QUARTZ_TUNER_CALIBRATE_H
#define QUARTZ_TUNER_CALIBRATE_H

#include "types.h"

int calibrate_short(calibration_t *cal);
int calibrate_open(calibration_t *cal);
int calibrate_load(calibration_t *cal);
int calibrate_through(calibration_t *cal);

#endif