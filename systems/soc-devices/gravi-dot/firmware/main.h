/**
 * gravi_dot/main.h — pin definitions and constants
 */
#ifndef MAIN_H
#define MAIN_H

#include "stm32g4xx_hal.h"

/* Station types */
#define STATION_BASE    1
#define STATION_SURVEY  0

/* ADC handles (defined in CubeMX-generated adc.c) */
extern ADC_HandleTypeDef hadc1;  /* NTC on PA0  */
extern ADC_HandleTypeDef hadc2;  /* Battery on PC4 */

/* Function prototypes */
static float adc_read_ntc_voltage(void);
static float ntc_to_celsius(float v);
static float adc_read_battery_voltage(void);
static void  peltier_set_pwm(uint8_t pct);

#endif /* MAIN_H */