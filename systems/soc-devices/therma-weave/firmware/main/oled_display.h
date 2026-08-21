/*
 * Therma Weave — OLED Display
 * oled_display.h — SSD1306 128×64 display for status monitoring
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"
#include "zone_controller.h"
#include "ambient_sensor.h"
#include "activity_detect.h"
#include "safety_watchdog.h"

#define SSD1306_I2C_ADDR    0x3C
#define SSD1306_WIDTH       128
#define SSD1306_HEIGHT      64

typedef struct {
    i2c_port_t i2c_num;
    uint8_t framebuffer[SSD1306_WIDTH * SSD1306_HEIGHT / 8];
    bool initialized;
} oled_display_t;

/**
 * Initialize SSD1306 OLED display via I²C.
 */
void oled_display_init(oled_display_t *oled, i2c_port_t i2c_num);

/**
 * Update display with current zone data, ambient, activity, and safety status.
 */
void oled_display_update(oled_display_t *oled, zone_controller_t *zones,
                          ambient_sensor_t *ambient, activity_detect_t *activity,
                          safety_watchdog_t *safety);

/**
 * Flush framebuffer to display via I²C.
 */
void oled_display_flush(oled_display_t *oled);

/**
 * Clear the framebuffer.
 */
void oled_display_clear(oled_display_t *oled);

/**
 * Draw a string at position (x, y) using 6×8 font.
 */
void oled_draw_string(oled_display_t *oled, int x, int y, const char *str);

/**
 * Draw a large temperature reading at position.
 */
void oled_draw_temp(oled_display_t *oled, int x, int y, float temp, bool active);

#endif /* OLED_DISPLAY_H */