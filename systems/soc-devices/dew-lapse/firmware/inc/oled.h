/* oled.h — SH1106 OLED driver */
#ifndef OLED_H
#define OLED_H

#include "dewpoint.h"

void oled_init(void);
void oled_update(const humidity_t *h, float mirror_c, float t_air,
                 float tec_i, int state, const char *state_str);

#endif