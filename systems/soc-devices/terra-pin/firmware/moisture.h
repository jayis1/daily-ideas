/**
 * terra_pin/moisture.h — Capacitive soil moisture probe driver (PCNT)
 */

#ifndef MOISTURE_H
#define MOISTURE_H

#include "main.h"

/* Calibration endpoints — stored in NVS */
#define MOIST_FREQ_DRY_DEFAULT   850   /* Hz in air-dry soil   */
#define MOIST_FREQ_WET_DEFAULT   350   /* Hz in saturated soil */

#endif /* MOISTURE_H */