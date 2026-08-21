/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * fuel_gauge.c — BQ27441 fuel gauge driver
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "fuel_gauge.h"
#include "stm32g4xx_hal.h"

#define BQ27441_I2C_ADDR  0x55

/* BQ27441 command addresses */
#define BQ27441_CMD_SOC       0x1C  /* State of charge (%) */
#define BQ27441_CMD_VOLTAGE   0x08  /* Voltage (mV) */
#define BQ27441_CMD_CURRENT   0x10  /* Current (mA) */
#define BQ27441_CMD_TEMP      0x02  /* Temperature (0.1 K) */
#define BQ27441_CMD_FLAGS    0x06  /* Status flags */
#define BQ27441_CMD_NOM_CAPACITY 0x0C /* Nominal available capacity (mAh) */
#define BQ27441_CMD_FULL_CAPACITY 0x0E /* Full available capacity (mAh) */
#define BQ27441_CMD_TTE      0x16  /* Time to empty (min) */
#define BQ27441_CMD_TTF      0x18  /* Time to full (min) */
#define BQ27441_CMD_CTRL     0x00  /* Control register */
#define BQ27441_CMD_DEV_TYPE 0x01  /* Device type */

extern I2C_HandleTypeDef hi2c1;

static HAL_StatusTypeDef BQ27441_ReadWord(uint8_t cmd_addr, uint16_t *value)
{
    uint8_t buf[2];
    HAL_StatusTypeDef status = HAL_I2C_Mem_Read(&hi2c1, BQ27441_I2C_ADDR << 1,
                                                   cmd_addr, I2C_MEMADD_SIZE_8BIT,
                                                   buf, 2, 200);
    if (status == HAL_OK) {
        *value = (uint16_t)buf[0] | ((uint16_t)buf[1] << 8);
    }
    return status;
}

HAL_StatusTypeDef FuelGauge_Init(I2C_HandleTypeDef *hi2c)
{
    uint16_t dev_type;
    HAL_StatusTypeDef status = BQ27441_ReadWord(BQ27441_CMD_DEV_TYPE, &dev_type);
    if (status != HAL_OK) return status;
    /* BQ27441 device type should be 0x0421 */
    if (dev_type != 0x0421) return HAL_ERROR;
    return HAL_OK;
}

uint8_t FuelGauge_GetSOC(I2C_HandleTypeDef *hi2c)
{
    uint16_t soc;
    if (BQ27441_ReadWord(BQ27441_CMD_SOC, &soc) == HAL_OK) {
        return (uint8_t)(soc & 0xFF);
    }
    return 0;
}

uint16_t FuelGauge_GetVoltage(I2C_HandleTypeDef *hi2c)
{
    uint16_t voltage;
    if (BQ27441_ReadWord(BQ27441_CMD_VOLTAGE, &voltage) == HAL_OK) {
        return voltage;
    }
    return 0;
}

int16_t FuelGauge_GetCurrent(I2C_HandleTypeDef *hi2c)
{
    uint16_t current;
    if (BQ27441_ReadWord(BQ27441_CMD_CURRENT, &current) == HAL_OK) {
        return (int16_t)current;
    }
    return 0;
}

uint16_t FuelGauge_GetFlags(I2C_HandleTypeDef *hi2c)
{
    uint16_t flags;
    if (BQ27441_ReadWord(BQ27441_CMD_FLAGS, &flags) == HAL_OK) {
        return flags;
    }
    return 0;
}

bool FuelGauge_IsCharging(I2C_HandleTypeDef *hi2c)
{
    uint16_t flags = FuelGauge_GetFlags(hi2c);
    return (flags & 0x01) != 0; /* DSG bit: 0=charging, 1=discharging */
}

uint16_t FuelGauge_GetTimeToEmpty(I2C_HandleTypeDef *hi2c)
{
    uint16_t tte;
    if (BQ27441_ReadWord(BQ27441_CMD_TTE, &tte) == HAL_OK) {
        return tte;
    }
    return 0xFFFF;
}