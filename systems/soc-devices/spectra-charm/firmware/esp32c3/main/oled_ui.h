/*
 * Spectra Charm — oled_ui.h
 */
#ifndef OLED_UI_H
#define OLED_UI_H

#include "driver/i2c.h"
#include <stdint.h>

typedef enum {
    SCREEN_HOME = 0,
    SCREEN_SCANNING,
    SCREEN_RESULT,
    SCREEN_LIBRARY,
    SCREEN_SETTINGS,
    SCREEN_LOW_BATTERY,
    SCREEN_COUNT
} OLEDScreen_t;

void OLED_Init(i2c_port_t port, uint8_t addr, int8_t reset_gpio);
void OLED_Clear(void);
void OLED_Refresh(void);
void OLED_DrawPixel(int x, int y, int on);
void OLED_DrawChar(int x, int y, char c, int scale);
void OLED_DrawString(int x, int y, const char *str, int scale);
void OLED_DrawLine(int x0, int y0, int x1, int y1);
void OLED_ShowSplash(void);
void OLED_ShowScreen(OLEDScreen_t screen);
void OLED_UpdateBattery(uint8_t pct);

#endif