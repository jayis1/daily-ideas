/*
 * i2c_util.c — I2C helper functions for STM32G4
 */

#include "main.h"
#include "i2c_util.h"

I2C_HandleTypeDef hi2c1;

int i2c_util_init(void)
{
    /* Already initialized in MX_I2C1_Init() */
    return 0;
}

int i2c_write(uint8_t addr, uint8_t reg, const uint8_t *data, uint16_t len)
{
    /* Write register address + data in one transaction */
    uint8_t buf[65];
    if (len > 64) return -1;
    buf[0] = reg;
    if (data && len > 0)
        memcpy(&buf[1], data, len);

    HAL_StatusTypeDef status = HAL_I2C_Master_Transmit(&hi2c1, addr << 1, buf, len + 1, 200);
    return (status == HAL_OK) ? 0 : -1;
}

int i2c_read(uint8_t addr, uint8_t reg, uint8_t *data, uint16_t len)
{
    /* Write register address */
    HAL_StatusTypeDef status = HAL_I2C_Master_Transmit(&hi2c1, addr << 1, &reg, 1, 100);
    if (status != HAL_OK) return -1;

    /* Read data */
    status = HAL_I2C_Master_Receive(&hi2c1, (addr << 1) | 1, data, len, 200);
    return (status == HAL_OK) ? 0 : -1;
}

int i2c_write_reg16(uint8_t addr, uint16_t reg, const uint8_t *data, uint16_t len)
{
    uint8_t buf[66];
    if (len > 64) return -1;
    buf[0] = (reg >> 8) & 0xFF;
    buf[1] = reg & 0xFF;
    if (data && len > 0)
        memcpy(&buf[2], data, len);

    HAL_StatusTypeDef status = HAL_I2C_Master_Transmit(&hi2c1, addr << 1, buf, len + 2, 200);
    return (status == HAL_OK) ? 0 : -1;
}

int i2c_read_reg16(uint8_t addr, uint16_t reg, uint8_t *data, uint16_t len)
{
    uint8_t reg_buf[2] = {(reg >> 8) & 0xFF, reg & 0xFF};
    HAL_StatusTypeDef status = HAL_I2C_Master_Transmit(&hi2c1, addr << 1, reg_buf, 2, 100);
    if (status != HAL_OK) return -1;

    status = HAL_I2C_Master_Receive(&hi2c1, (addr << 1) | 1, data, len, 200);
    return (status == HAL_OK) ? 0 : -1;
}

int i2c_probe(uint8_t addr)
{
    /* Try to write 0 bytes to the address — just check ACK */
    HAL_StatusTypeDef status = HAL_I2C_IsDeviceReady(&hi2c1, addr << 1, 3, 100);
    return (status == HAL_OK) ? 0 : -1;
}