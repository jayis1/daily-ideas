/*
 * Spectra Charm — eeprom.h
 */
#ifndef EEPROM_H
#define EEPROM_H

#include "stm32g4xx_hal.h"
#include <stdint.h>

typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t flags;
    float dark_offset[9];
    float wavelength_correction[9];
    float intensity_calibration[9];
    float led_warmup_delay_ms;
    uint8_t num_scans_total;
    uint8_t reserved[3];
    uint8_t crc8;
} CalibrationData_t;

HAL_StatusTypeDef EEPROM_WriteByte(uint8_t addr, uint8_t data);
HAL_StatusTypeDef EEPROM_ReadByte(uint8_t addr, uint8_t *data);
HAL_StatusTypeDef EEPROM_WriteBuffer(uint8_t addr, const uint8_t *data, uint16_t len);
HAL_StatusTypeDef EEPROM_ReadBuffer(uint8_t addr, uint8_t *data, uint16_t len);
void EEPROM_LoadCalibration(I2C_HandleTypeDef *hi2c, void *state);
HAL_StatusTypeDef EEPROM_SaveCalibration(const CalibrationData_t *cal);
HAL_StatusTypeDef EEPROM_GetEUI48(uint8_t eui48[6]);

#endif