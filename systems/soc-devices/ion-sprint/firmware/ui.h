/*
 * ui.h — User interface: encoder + buttons + menu
 */

#ifndef UI_H
#define UI_H

#include <stdbool.h>
#include <stdint.h>

/* Button IDs */
#define BTN_MODE   0
#define BTN_START  1
#define BTN_INJECT 2

/* Initialize UI (encoder + buttons) */
void ui_init(void);

/* Poll UI inputs (call from main loop) */
void ui_poll(void);

/* Check if a button was pressed since last poll */
bool ui_button_pressed(uint8_t btn);

/* Menu update: adjust settings via encoder */
void ui_menu_update(float *hv_kv, uint8_t *bge, uint8_t *inj,
                    float *inj_dur, uint16_t *timeout_s);

#endif /* UI_H */