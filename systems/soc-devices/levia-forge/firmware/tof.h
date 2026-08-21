/*
 * Levia Forge — VL53L0X ToF Header
 * SPDX-License-Identifier: MIT
 */
#ifndef TOF_H
#define TOF_H

#include <stdbool.h>

void tof_init(void);
float tof_read_distance_mm(void);
bool tof_is_present(void);

#endif /* TOF_H */