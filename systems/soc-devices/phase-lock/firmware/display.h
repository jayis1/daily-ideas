/*
 * display.h — SH1106 OLED 128×64: live R/θ/X/Y + sweep plot
 */
#ifndef DISPLAY_H
#define DISPLAY_H

#include "demod.h"
#include "sweep.h"

void display_init(void);
void display_clear(void);
void display_show_status(const char *mode, float f, const char *tc_label);
void display_show_demod(demod_result_t r, float gain);
void display_show_sweep(sweep_state_t *s);
void display_show_menu(int item);
void display_show_message(const char *line1, const char *line2);

#endif /* DISPLAY_H */