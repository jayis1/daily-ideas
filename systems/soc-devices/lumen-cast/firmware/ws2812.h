/**
 * lumen_cast/firmware/ws2812.h — WS2812B RGB LED
 */
#ifndef LUMEN_CAST_WS2812_H
#define LUMEN_CAST_WS2812_H

void ws2812_init(void);
void ws2812_set(uint8_t r, uint8_t g, uint8_t b);

#endif