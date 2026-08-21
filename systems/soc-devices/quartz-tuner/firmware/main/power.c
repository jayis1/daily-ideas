/*
 * power.c — MAX17048 fuel gauge + sleep management
 */

#include "power.h"
#include "stm32g4xx_hal.h"

#define MAX17048_ADDR  0x36

extern I2C_HandleTypeDef hi2c1;

int power_init(void)
{
    /* Initialize MAX17048 fuel gauge */
    return 0;
}

float power_get_voltage(void)
{
    uint8_t reg = 0x02;  /* VCELL register */
    uint8_t data[2];
    HAL_I2C_Master_Transmit(&hi2c1, MAX17048_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, MAX17048_ADDR << 1, data, 2, 100);
    uint16_t raw = (data[0] << 8) | data[1];
    return (float)raw * 1.25e-3f;  /* 78.125 µV/LSB → mV */
}

float power_get_soc(void)
{
    uint8_t reg = 0x04;  /* SOC register */
    uint8_t data[2];
    HAL_I2C_Master_Transmit(&hi2c1, MAX17048_ADDR << 1, &reg, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, MAX17048_ADDR << 1, data, 2, 100);
    uint16_t raw = (data[0] << 8) | data[1];
    return (float)raw / 256.0f;  /* 1/256 % per LSB */
}

void power_sleep(void)
{
    /* Enter STOP mode with RTC wake-up */
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);
}