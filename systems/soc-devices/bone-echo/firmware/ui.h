/*
 * ui.h — Button + rotary encoder + numeric pad menu
 */

#ifndef UI_H
#define UI_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    UI_PATIENT = 0,
    UI_3SCAN = 1,
    UI_PHANTOM = 2,
    UI_SCAN = 3,
    UI_LOG = 4,
} ui_menu_t;

void  ui_init(void);
void  ui_poll(void);
int   ui_current(void);
int   ui_encoder_delta(void);
bool  ui_select_pressed(void);
bool  ui_scan_pressed(void);
bool  ui_mode_pressed(void);

#endif