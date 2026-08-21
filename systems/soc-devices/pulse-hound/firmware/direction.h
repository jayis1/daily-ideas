/*
 * Pulse Hound — RF Signal Hunter
 * direction.h — Direction-finding interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_DIRECTION_H
#define PULSE_HOUND_DIRECTION_H

#include <stdint.h>

int direction_init(void);
int direction_home(void);
int direction_find_bearing(float *bearing_deg, float *peak_rssi_dbm);
int direction_get_bearing(void);

#endif /* PULSE_HOUND_DIRECTION_H */