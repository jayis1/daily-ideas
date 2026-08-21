/*
 * Hive Mind — OLED Display Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include "main.h"
#include "acoustic_analyzer.h"

/* Forward declaration — sensor_data_t defined in main.h */
typedef struct {
    float weight_g;
    float temp_floor;
    float temp_mid;
    float temp_crown;
    float ambient_t;
    float ambient_h;
    float ambient_p;
    float vbat;
    float vsolar;
    acoustic_class_t acoustic_class;
    uint16_t dominant_freq;
    uint16_t bee_in;
    uint16_t bee_out;
    float health_score;
} sensor_data_t;

void oled_display_init(void);
void oled_display_show(const sensor_data_t *data);
void oled_display_off(void);
void oled_display_on(void);

#endif /* OLED_DISPLAY_H */