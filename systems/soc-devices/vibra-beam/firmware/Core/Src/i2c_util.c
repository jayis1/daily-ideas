/*
 * i2c_util.c — shared I2C helpers
 */

#include "i2c_util.h"
#include "stm32g4xx_hal.h"

extern I2C_HandleTypeDef hi2c1;

int i2c_util_init(void)
{
    return (HAL_I2C_IsDeviceReady(&hi2c1, CONFIG_OLED_I2C_ADDR, 3, 100) == HAL_OK) ? 0 : -1;
}

int i2c_write(uint8_t addr, const uint8_t *data, uint16_t len)
{
    return (HAL_I2C_Master_Transmit(&hi2c1, addr << 1, (uint8_t *)data, len, 100) == HAL_OK)
           ? 0 : -1;
}

int i2c_read(uint8_t addr, uint8_t *data, uint16_t len)
{
    return (HAL_I2C_Master_Receive(&hi2c1, addr << 1, data, len, 100) == HAL_OK)
           ? 0 : -1;
}

int i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint16_t len)
{
    uint8_t buf[1 + 32];
    if (len > 32) return -1;
    buf[0] = reg;
    for (uint16_t i = 0; i < len; i++) buf[1 + i] = data[i];
    return i2c_write(addr, buf, 1 + len);
}

int i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint16_t len)
{
    if (HAL_I2C_Master_Transmit(&hi2c1, addr << 1, &reg, 1, 100) != HAL_OK) return -1;
    return i2c_read(addr, data, len);
}