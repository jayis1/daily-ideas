/*
 * i2c_util.h — shared I2C helpers
 */

#ifndef I2C_UTIL_H
#define I2C_UTIL_H

#include <stdint.h>
#include "stm32g4xx_hal.h"

int i2c_util_init(void);
int i2c_write(uint8_t addr, const uint8_t *data, uint16_t len);
int i2c_read(uint8_t addr, uint8_t *data, uint16_t len);
int i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint16_t len);
int i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint16_t len);

#endif /* I2C_UTIL_H */