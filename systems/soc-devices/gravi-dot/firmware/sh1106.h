/** sh1106.h — SH1106 1.3" OLED (128×64, I2C) display driver */
#ifndef SH1106_H
#define SH1106_H
#include "stm32g4xx_hal.h"
void sh1106_init(I2C_HandleTypeDef *i2c);
void sh1106_clear(void);
void sh1106_draw_string(uint8_t x, uint8_t y, const char *str, uint8_t size);
void sh1106_flush(void);
#endif