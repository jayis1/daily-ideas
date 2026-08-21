/*
 * display.h — SH1106 OLED: SOS/BUA/SI/T-score + waveform
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

void display_init(void);
void display_show_message(const char *line1, const char *line2);
void display_show_menu(int menu_idx);
void display_show_results(float sos, float bua, float si, float t, float z, int cls);
void display_show_waveform(const uint16_t *buf, uint32_t n);

#endif