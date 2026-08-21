/*
 * i2c_util.h — I2C helper functions
 */

#ifndef I2C_UTIL_H
#define I2C_UTIL_H

#include "stm32g4xx_hal.h"

extern I2C_HandleTypeDef hi2c1;

int  i2c_write(uint8_t addr, uint8_t reg, const uint8_t *data, uint16_t len);
int  i2c_read(uint8_t addr, uint8_t reg, uint8_t *data, uint16_t len);
int  i2c_write_reg16(uint8_t addr, uint16_t reg, const uint8_t *data, uint16_t len);
int  i2c_read_reg16(uint8_t addr, uint16_t reg, uint8_t *data, uint16_t len);
int  i2c_probe(uint8_t addr);

#endif /* I2C_UTIL_H */