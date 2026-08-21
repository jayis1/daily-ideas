/*
 * display.h — SSD1306 128×64 polar radar + status
 */
#ifndef BOLT_COMPASS_DISPLAY_H
#define BOLT_COMPASS_DISPLAY_H

#include "types.h"

void display_init(void);

/* Draw the polar radar with the current storm cells + last stroke. */
void display_radar(const storm_t *storm, const stroke_t *last);

/* Draw a status line (boot, fault, etc). */
void display_status(const char *line1, const char *line2);

#endif /* BOLT_COMPASS_DISPLAY_H */