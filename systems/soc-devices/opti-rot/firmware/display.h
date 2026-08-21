/*
 * display.h — SSD1306 OLED display driver
 * Opti Rot — Pocket Digital Polarimeter
 */
#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

void display_init(void);
void display_splash(const char *title, const char *subtitle);
void display_main_menu(uint8_t mode);
void display_message(const char *line1, const char *line2);
void display_measurement(double rotation, double concentration,
                          const char *compound, double confidence);
void display_drude(double K, double lambda0, double alpha405,
                    double alpha520, double alpha589);
void display_temperature(double temp_c);
void display_library(int index, int total, const char *name,
                       double alpha_d);
void display_off(void);
void display_on(void);

#endif /* DISPLAY_H */