/*
 * Spectra Charm — fuel_gauge.h
 */
#ifndef FUEL_GAUGE_H
#define FUEL_GAUGE_H

#include "stm32g4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

HAL_StatusTypeDef FuelGauge_Init(I2C_HandleTypeDef *hi2c);
uint8_t FuelGauge_GetSOC(I2C_HandleTypeDef *hi2c);
uint16_t FuelGauge_GetVoltage(I2C_HandleTypeDef *hi2c);
int16_t FuelGauge_GetCurrent(I2C_HandleTypeDef *hi2c);
uint16_t FuelGauge_GetFlags(I2C_HandleTypeDef *hi2c);
bool FuelGauge_IsCharging(I2C_HandleTypeDef *hi2c);
uint16_t FuelGauge_GetTimeToEmpty(I2C_HandleTypeDef *hi2c);

#endif