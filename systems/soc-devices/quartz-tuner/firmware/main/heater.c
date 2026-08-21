/*
 * heater.c — PID heater control with DS18B20
 */

#include "heater.h"
#include "stm32g4xx_hal.h"

static bool heater_enabled = false;
static float target_temp = 25.0f;

void heater_init(void)
{
    /* Configure DS18B20 1-Wire on PC12 */
    /* Configure heater MOSFET on PC6 (PWM via TIM8 CH2) */
    /* Configure DAC on PA4 for heater power control */
}

void heater_enable(bool enable)
{
    heater_enabled = enable;
    if (enable) {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_SET);
    } else {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_RESET);
    }
}

void heater_set_target(float temp_c)
{
    target_temp = temp_c;
}

float heater_read_temp(void)
{
    /* Read DS18B20 on PC12 (1-Wire)
     * In real implementation: send reset, skip ROM, convert T,
     * wait 750 ms, read scratchpad.
     * Returns temperature in °C with ±0.1 °C resolution. */
    return 25.0f;  /* placeholder */
}