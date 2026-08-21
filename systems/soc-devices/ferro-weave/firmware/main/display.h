/*
 * display.h — SSD1306 OLED B-H loop plot
 */
#ifndef FERRO_WEAVE_DISPLAY_H
#define FERRO_WEAVE_DISPLAY_H

#include "bh.h"

void display_init(void);

/* Plot a B-H loop on the 128×64 OLED, with axis ticks and a numeric
 * readout of B_sat / H_c / P_v. H and B are n samples in engineering
 * units (A/m, T). */
void display_plot_loop(const float *H, const float *B, int n,
                       const bh_result_t *r);

/* Show a status line (idle / charging / fault). */
void display_status(const char *line1, const char *line2);

#endif /* FERRO_WEAVE_DISPLAY_H */