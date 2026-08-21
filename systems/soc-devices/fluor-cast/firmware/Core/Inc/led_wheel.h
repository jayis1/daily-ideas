/*
 * led_wheel.h — Excitation LED wheel control
 */

#ifndef LED_WHEEL_H
#define LED_WHEEL_H

#include "stm32g4xx_hal.h"
#include <stdint.h>
#include "config.h"

/**
 * Initialize LED wheel: stepper motor, LED driver, demux.
 */
void led_wheel_init(void);

/**
 * Move wheel to specified excitation wavelength position.
 * @param wavelength  EX_255NM ... EX_525NM or EX_BLANK
 * @return 0 on success, -1 on error
 */
int led_wheel_goto(ex_wavelength_t wavelength);

/**
 * Turn on current LED with specified current.
 * @param current_ma  LED current (10–80 mA)
 * @return Measured reference photodiode reading (ADC counts)
 */
uint16_t led_on(float current_ma);

/**
 * Turn off current LED.
 */
void led_off(void);

/**
 * Read reference photodiode (OPT101) — measures actual LED output.
 * @return ADC counts (0–4095)
 */
uint16_t led_read_reference(void);

/**
 * Home the wheel using Hall sensor.
 * @return 0 on success, -1 on timeout
 */
int led_wheel_home(void);

/**
 * Get current wheel position.
 * @return Current ex_wavelength_t or EX_BLANK
 */
ex_wavelength_t led_wheel_get_position(void);

/**
 * Set LED current via digital potentiometer (MCP4131).
 * @param current_ma  Target current 10–80 mA
 */
void led_set_current(float current_ma);

/**
 * Get available excitation wavelength in nm for a given enum.
 * @param wl  Wavelength enum
 * @return Wavelength in nm, or 0 for blank
 */
uint16_t led_wavelength_nm(ex_wavelength_t wl);

#endif /* LED_WHEEL_H */