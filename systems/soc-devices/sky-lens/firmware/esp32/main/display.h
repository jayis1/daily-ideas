/* display.h — SSD1306 OLED 128×64 dashboard / zenith / skymap views */
#ifndef DISPLAY_H
#define DISPLAY_H
#include "sky_lens.h"

typedef enum {
    VIEW_DASH = 0,
    VIEW_ZENITH,
    VIEW_SKYMAP,
    VIEW_LIFETIME,
    VIEW_COUNT
} display_view_t;

void display_init(void);
void display_set_view(display_view_t v);
display_view_t display_get_view(void);
void display_next_view(void);
void display_update(const daily_t *d, const skymap_t *m,
                    const zenith_fit_t *z, const lifetime_result_t *lf);

#endif