/** ms5837.h — MS5837-02BA barometric pressure sensor (I2C) */
#ifndef MS5837_H
#define MS5837_H
#include "stm32g4xx_hal.h"
float ms5837_read_pressure(I2C_HandleTypeDef *i2c);
int   ms5837_init(I2C_HandleTypeDef *i2c);
#endif