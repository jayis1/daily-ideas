/*
 * ui.h — Button handling and mode state machine
 * Opti Rot — Pocket Digital Polarimeter
 */
#ifndef UI_H
#define UI_H

#include <stdint.h>

/* UI modes */
#define UI_MODE_MEASURE    0
#define UI_MODE_IDENTIFY   1
#define UI_MODE_MONITOR    2
#define UI_MODE_LIBRARY    3
#define UI_MODE_CALIBRATE  4
#define UI_MODE_CONFIG     5

/* Buttons */
#define UI_BUTTON_NONE    0
#define UI_BUTTON_MEAS    1
#define UI_BUTTON_MODE    2
#define UI_BUTTON_CAL     3

void ui_init(void);
uint8_t ui_poll_buttons(void);
void ui_execute_mode(uint8_t mode);

#endif /* UI_H */