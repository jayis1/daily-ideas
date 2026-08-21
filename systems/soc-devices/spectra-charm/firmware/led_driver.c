/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * led_driver.c — LED current control via DAC and GPIO
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "led_driver.h"
#include "stm32g4xx_hal.h"

extern DAC_HandleTypeDef hdac1;

void LEDDriver_Init(void)
{
    /* Both LEDs off at startup */
    LEDDriver_SetWhiteLED(false);
    LEDDriver_SetUVLED(false);
    LEDDriver_SetWhiteCurrent(0);
    LEDDriver_SetUVCurrent(0);
}

void LEDDriver_SetWhiteLED(bool on)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

void LEDDriver_SetUVLED(bool on)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

void LEDDriver_SetWhiteCurrent(uint16_t dac_value)
{
    /* DAC channel 1 (PA4) controls AL8805 ADJ pin */
    /* DAC range 0-4095 → LED current 0-350 mA */
    if (dac_value > 4095) dac_value = 4095;
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R, dac_value);
}

void LEDDriver_SetUVCurrent(uint8_t current_ma)
{
    /* DAC channel 2 (PA5) sets UV LED current via MOSFET gate */
    /* Map current_ma (0-50) to DAC value (0-4095) */
    uint16_t dac_val = (uint16_t)((float)current_ma / 50.0f * 4095.0f);
    if (dac_val > 4095) dac_val = 4095;
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_2, DAC_ALIGN_12B_R, dac_val);
}

uint16_t LEDDriver_GetWhiteCurrentDAC(void)
{
    return HAL_DAC_GetValue(&hdac1, DAC_CHANNEL_1);
}

bool LEDDriver_CheckFault(void)
{
    /* Read LED driver fault flag (PB8) */
    return (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_8) == GPIO_PIN_SET);
}