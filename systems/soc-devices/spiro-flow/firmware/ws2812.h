/**
 * spiro_flow/ws2812.h — WS2812B RGB LED
 */
#ifndef SPIRO_FLOW_WS2812_H
#define SPIRO_FLOW_WS2812_H

#include "main.h"

void ws2812_init(void);
void ws2812_set(uint8_t r, uint8_t g, uint8_t b);

#endif