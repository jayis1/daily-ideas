/* ui.h — Button input + menu navigation */
#ifndef UI_H
#define UI_H

#include <stdbool.h>

typedef enum {
    UI_CMD_NONE = 0,
    UI_CMD_RUN,
    UI_CMD_STOP,
    UI_CMD_MENU_NEXT,
    UI_CMD_MENU_SELECT,
    UI_CMD_CALIBRATE,
} ui_cmd_t;

/* Trigger queue — other tasks wait on this. */
#define UI_TRIGGER_QUEUE  ui_trigger_queue()
QueueHandle_t ui_trigger_queue(void);

void ui_init(void);

/* Get the current menu selection (0=RUN, 1=METHOD, 2=LIBRARY, 3=LOG). */
int ui_menu_selected(void);

/* Blocking wait for a command (with timeout). Returns UI_CMD_NONE on timeout. */
ui_cmd_t ui_wait_cmd(uint32_t timeout_ms);

#endif /* UI_H */