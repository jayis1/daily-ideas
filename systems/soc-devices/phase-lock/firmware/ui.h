/*
 * ui.h — button + rotary encoder menu
 */
#ifndef UI_H
#define UI_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    UI_FREQ, UI_AMPL, UI_TC, UI_SLOPE,
    UI_GAIN, UI_SWEEP, UI_RUN, UI_LOG, UI_COUNT
} ui_item_t;

void ui_init(void);
void ui_poll(void);   /* call from main loop; debounces encoder + buttons */
ui_item_t ui_current(void);
int  ui_encoder_delta(void);
bool ui_select_pressed(void);
bool ui_mode_pressed(void);
bool ui_run_pressed(void);

#endif /* UI_H */