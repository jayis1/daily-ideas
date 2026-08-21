/*
 * Spectra Charm — button.h
 */
#ifndef BUTTON_H
#define BUTTON_H

typedef enum {
    BUTTON_SCAN = 0,
    BUTTON_MODE = 1,
} ButtonType_t;

void Button_Init(int scan_gpio, int mode_gpio);
ButtonType_t Button_WaitPress(void);

#endif