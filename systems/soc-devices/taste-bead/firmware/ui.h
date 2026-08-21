/* ui.h — User interface (buttons, mode state machine) for Taste Bead
 *
 * Manages the three buttons (ID, MODE, LIB) and the mode state machine.
 * Sends trigger commands to the EIS sweep task via a queue.
 */

#ifndef TASTE_BEAD_UI_H
#define TASTE_BEAD_UI_H

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

/* UI modes */
typedef enum {
    UI_MODE_IDLE = 0,
    UI_MODE_IDENTIFY,
    UI_MODE_LIBRARY,
    UI_MODE_LEARN,
    UI_MODE_MONITOR,
    UI_MODE_RAW,
    UI_MODE_CALIBRATE,
    UI_MODE_COUNT
} ui_mode_t;

/* Trigger commands sent to EIS sweep task */
typedef enum {
    UI_CMD_IDLE = 0,
    UI_CMD_TRIGGER_SWEEP,
    UI_CMD_LEARN_SWEEP,
    UI_CMD_MONITOR_SWEEP,
    UI_CMD_STOP_MONITOR,
    UI_CMD_CAL_OPEN,
    UI_CMD_CAL_SHORT,
    UI_CMD_CAL_KCL,
    UI_CMD_NEXT_LIB_ENTRY,
    UI_CMD_DELETE_LIB_ENTRY,
} ui_cmd_t;

/* Initialize UI */
esp_err_t ui_init(void);

/* Start UI task (on core 1) */
esp_err_t ui_start(QueueHandle_t result_queue);

/* Poll buttons (called from UI task) */
void ui_poll(void);

/* Set status message on display */
void ui_set_status(const char *msg);

/* Get trigger queue (for EIS task to receive from) */
QueueHandle_t ui_trigger_queue(void);

/* Get current mode */
ui_mode_t ui_get_mode(void);

/* Set RGB LED color */
void ui_set_led(uint8_t r, uint8_t g, uint8_t b);

#endif /* TASTE_BEAD_UI_H */