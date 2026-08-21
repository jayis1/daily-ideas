/**
 * oled_display.h — SSD1306 OLED driver (128×64, I2C)
 */
#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include "refract_calc.h"
#include <stdint.h>

void oled_display_init(void);
void oled_display_off(void);
void oled_display_boot_screen(void);
void oled_display_idle_screen(uint8_t battery, float temp, float hum, const char *mode);
void oled_display_measuring(uint8_t progress);
void oled_display_results(int mode, const ri_result_t *result);
void oled_display_mode_select(int mode, const char *mode_name);
void oled_display_calibration_prompt(void);

/* OLED I2C address */
#define SSD1306_ADDR  0x3C << 1

#endif /* OLED_DISPLAY_H */