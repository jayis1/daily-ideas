/*
 * buttons.h — debounced mode/scan/cal buttons + encoder
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef BUTTONS_H
#define BUTTONS_H

#include <stdbool.h>

typedef enum { BTN_NONE = 0, BTN_MODE, BTN_SCAN, BTN_CAL } button_t;

void buttons_init(void);
button_t buttons_poll(void);      /* returns pressed button (debounced) */
int buttons_encoder_delta(void);  /* rotary encoder delta since last read */

#endif /* BUTTONS_H */