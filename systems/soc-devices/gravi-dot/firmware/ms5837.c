/**
 * ms5837.c — MS5837-02BA I2C pressure sensor driver
 *
 * Reads pressure in hPa (mbar) for the atmosphere correction in the
 * gravity pipeline. The MS5837 is a 16-bit pressure + temperature
 * sensor with I2C interface. This is a minimal read implementation.
 */

#include "ms5837.h"

#define MS5837_ADDR        (0x76 << 1)   /* 7-bit 0x76, HAL expects 8-bit */
#define MS5837_CMD_RESET   0x1E
#define MS5837_CMD_CONV_D1 0x40  /* OSR 256 */
#define MS5837_CMD_CONV_D2 0x50
#define MS5837_CMD_ADC_READ 0x00
#define MS5837_CMD_PROM    0xA0

static uint16_t prom[8];

int ms5837_init(I2C_HandleTypeDef *i2c)
{
    HAL_I2C_Master_Transmit(i2c, MS5837_ADDR, (uint8_t[]){MS5837_CMD_RESET}, 1, 50);
    HAL_Delay(10);

    /* Read calibration PROM (8 × 16-bit words) */
    for (int i = 0; i < 8; i++) {
        uint8_t cmd = MS5837_CMD_PROM + i * 2;
        HAL_I2C_Master_Transmit(i2c, MS5837_ADDR, &cmd, 1, 50);
        uint8_t buf[2];
        HAL_I2C_Master_Receive(i2c, MS5837_ADDR, buf, 2, 50);
        prom[i] = (buf[0] << 8) | buf[1];
    }
    return 0;
}

float ms5837_read_pressure(I2C_HandleTypeDef *i2c)
{
    /* Convert D1 (pressure) */
    uint8_t cmd = MS5837_CMD_CONV_D1;
    HAL_I2C_Master_Transmit(i2c, MS5837_ADDR, &cmd, 1, 50);
    HAL_Delay(5);
    cmd = MS5837_CMD_ADC_READ;
    HAL_I2C_Master_Transmit(i2c, MS5837_ADDR, &cmd, 1, 50);
    uint8_t buf[3];
    HAL_I2C_Master_Receive(i2c, MS5837_ADDR, buf, 3, 50);
    uint32_t D1 = ((uint32_t)buf[0] << 16) | (buf[1] << 8) | buf[2];

    /* Convert D2 (temperature) */
    cmd = MS5837_CMD_CONV_D2;
    HAL_I2C_Master_Transmit(i2c, MS5837_ADDR, &cmd, 1, 50);
    HAL_Delay(5);
    cmd = MS5837_CMD_ADC_READ;
    HAL_I2C_Master_Transmit(i2c, MS5837_ADDR, &cmd, 1, 50);
    HAL_I2C_Master_Receive(i2c, MS5837_ADDR, buf, 3, 50);
    uint32_t D2 = ((uint32_t)buf[0] << 16) | (buf[1] << 8) | buf[2];

    /* Calculate pressure (MS5837 datasheet formulas) */
    int64_t dT = (int64_t)D2 - ((int64_t)prom[5] << 8);
    int64_t OFF = ((int64_t)prom[2] << 17) + (((int64_t)prom[4] * dT) >> 5);
    int64_t SENS = ((int64_t)prom[1] << 16) + (((int64_t)prom[3] * dT) >> 7);
    /* Temperature in °C (for reference, not used directly here) */
    int32_t TEMP = 2000 + ((int64_t)dT * prom[6]) >> 23;

    /* Pressure in mbar (×10 in datasheet → divide by 10) */
    int64_t P = (((int64_t)D1 * SENS) >> 21) - (OFF >> 5);
    return (float)P / 10.0f;  /* hPa */
}