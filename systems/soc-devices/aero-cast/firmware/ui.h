/* ui.h — button handling and mode state machine */

#ifndef UI_H
#define UI_H

#include "display.h"
#include "wind.h"

typedef enum {
    UI_MODE_WIND,     /* continuous measurement display */
    UI_MODE_GUST,     /* peak hold tracking */
    UI_MODE_FLUX,     /* eddy covariance / turbulence */
    UI_MODE_PROFILE,  /* long averaging */
    UI_MODE_CALIB,    /* zero-wind calibration */
    UI_MODE_STREAM,   /* raw data streaming only */
    UI_MODE_NUM
} ui_mode_t;

typedef enum {
    AVG_1S,
    AVG_10S,
    AVG_1MIN,
    AVG_10MIN,
    AVG_30MIN,
    AVG_NUM
} ui_avg_window_t;

void ui_init(void);

/* Called periodically (~100 ms) to poll buttons */
void ui_poll(void);

/* Get current mode */
ui_mode_t ui_get_mode(void);

/* Get current averaging window */
ui_avg_window_t ui_get_avg_window(void);

/* Get averaging window in seconds */
uint32_t ui_avg_seconds(void);

/* Cycle to next mode (called by button press) */
void ui_next_mode(void);

/* Cycle to next averaging window */
void ui_next_avg(void);

/* Check if power button is held (for shutdown) */
bool ui_power_held(void);

#endif /* UI_H */