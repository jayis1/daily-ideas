/*
 * Spectra Charm — led_driver.h
 */
#ifndef LED_DRIVER_H
#define LED_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

void LEDDriver_Init(void);
void LEDDriver_SetWhiteLED(bool on);
void LEDDriver_SetUVLED(bool on);
void LEDDriver_SetWhiteCurrent(uint16_t dac_value);
void LEDDriver_SetUVCurrent(uint8_t current_ma);
uint16_t LEDDriver_GetWhiteCurrentDAC(void);
bool LEDDriver_CheckFault(void);

#endif