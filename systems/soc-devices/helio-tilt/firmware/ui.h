/*
 * ui.h — Encoder + buttons + menu
 */

#ifndef UI_H
#define UI_H

#include <stdint.h>

typedef enum {
    UI_EVENT_NONE,
    UI_EVENT_MODE,         /* Mode button pressed */
    UI_EVENT_START,        /* Start/Stop button pressed */
    UI_EVENT_CALIBRATE,    /* Calibrate button pressed */
    UI_EVENT_ENCODER_CW,   /* Encoder rotated clockwise */
    UI_EVENT_ENCODER_CCW,  /* Encoder rotated counter-clockwise */
} ui_event_t;

/* Initialize UI GPIO (encoder + 3 buttons) */
void ui_init(void);

/* Poll for UI event (non-blocking) */
ui_event_t ui_poll(void);

/* Get encoder position (cumulative steps) */
int32_t ui_encoder_pos(void);

#endif /* UI_H */