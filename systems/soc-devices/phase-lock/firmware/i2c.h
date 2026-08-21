/*
 * i2c.h — minimal bit-banged I2C driver (PA11=SDA, PA12=SCL)
 *         for the SH1106 OLED + ADS1115 aux ADC.
 */
#ifndef I2C_H
#define I2C_H

#include <stdint.h>
#include <stddef.h>

void i2c_init(void);
int  i2c_write(uint8_t addr, const uint8_t *data, size_t len);
int  i2c_read(uint8_t addr, uint8_t *data, size_t len);

#endif /* I2C_H */