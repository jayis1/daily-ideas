/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * eeprom.c — 24AA02E48 EEPROM driver for calibration storage
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "eeprom.h"
#include "stm32g4xx_hal.h"

extern I2C_HandleTypeDef hi2c1;

#define EEPROM_I2C_ADDR  0x50  /* 24AA02E48 base address */
#define EEPROM_SIZE      256   /* 2 Kb = 256 bytes */

/* Calibration data structure — stored at offset 0 */
typedef struct {
    uint32_t magic;                  /* 0x53434C42 "SCLB" */
    uint16_t version;
    uint16_t flags;
    float dark_offset[9];            /* Per-channel dark offset correction */
    float wavelength_correction[9];  /* Per-channel wavelength offset (nm) */
    float intensity_calibration[9];  /* Per-channel intensity correction factor */
    float led_warmup_delay_ms;       /* LED stabilization time */
    uint8_t num_scans_total;         /* Lifetime scan counter (mod 256) */
    uint8_t reserved[3];
    uint8_t crc8;                    /* CRC8 over entire structure */
} CalibrationData_t;

#define CAL_MAGIC      0x53434C42
#define CAL_VERSION    1
#define CAL_SIZE       sizeof(CalibrationData_t)

HAL_StatusTypeDef EEPROM_WriteByte(uint8_t addr, uint8_t data)
{
    return HAL_I2C_Mem_Write(&hi2c1, EEPROM_I2C_ADDR << 1, addr,
                              I2C_MEMADD_SIZE_8BIT, &data, 1, 100);
}

HAL_StatusTypeDef EEPROM_ReadByte(uint8_t addr, uint8_t *data)
{
    return HAL_I2C_Mem_Read(&hi2c1, EEPROM_I2C_ADDR << 1, addr,
                             I2C_MEMADD_SIZE_8BIT, data, 1, 100);
}

HAL_StatusTypeDef EEPROM_WriteBuffer(uint8_t addr, const uint8_t *data, uint16_t len)
{
    /* 24AA02E48 supports page write of 8 bytes */
    while (len > 0) {
        uint16_t chunk = 8; /* Page size */
        if (len < chunk) chunk = len;

        HAL_StatusTypeDef status = HAL_I2C_Mem_Write(&hi2c1, EEPROM_I2C_ADDR << 1,
                                                       addr, I2C_MEMADD_SIZE_8BIT,
                                                       (uint8_t *)data, chunk, 100);
        if (status != HAL_OK) return status;

        addr += chunk;
        data += chunk;
        len -= chunk;
        HAL_Delay(10); /* Write cycle time */
    }
    return HAL_OK;
}

HAL_StatusTypeDef EEPROM_ReadBuffer(uint8_t addr, uint8_t *data, uint16_t len)
{
    return HAL_I2C_Mem_Read(&hi2c1, EEPROM_I2C_ADDR << 1, addr,
                             I2C_MEMADD_SIZE_8BIT, data, len, 200);
}

void EEPROM_LoadCalibration(I2C_HandleTypeDef *hi2c, void *state)
{
    CalibrationData_t cal;
    HAL_StatusTypeDef status = EEPROM_ReadBuffer(0, (uint8_t *)&cal, CAL_SIZE);

    if (status == HAL_OK && cal.magic == CAL_MAGIC && cal.version == CAL_VERSION) {
        /* Valid calibration found — apply corrections */
        /* (In real firmware, apply cal.dark_offset, wavelength_correction, etc.) */
    } else {
        /* No valid calibration — use defaults */
    }
}

HAL_StatusTypeDef EEPROM_SaveCalibration(const CalibrationData_t *cal)
{
    return EEPROM_WriteBuffer(0, (const uint8_t *)cal, CAL_SIZE);
}

HAL_StatusTypeDef EEPROM_GetEUI48(uint8_t eui48[6])
{
    /* 24AA02E48 has a factory-programmed EUI-48 at addresses 0xFA-0xFF */
    return EEPROM_ReadBuffer(0xFA, eui48, 6);
}