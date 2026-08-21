/*
 * ui.h — button + rotary encoder user interface
 */

#ifndef UI_H
#define UI_H

#include <stdbool.h>

typedef enum {
    UI_SAMPLE = 0,
    UI_CALIB,
    UI_ZERO,
    UI_VIEW,
    UI_BLE,
    UI_MAX,
} ui_menu_t;

void   ui_init(void);
void   ui_poll(void);
bool   ui_scan_pressed(void);
bool   ui_mode_pressed(void);
bool   ui_select_pressed(void);
int    ui_encoder_delta(void);
ui_menu_t ui_current(void);

#endif /* UI_H */