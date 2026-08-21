/*
 * Spectra Charm — flash_store.h
 */
#ifndef FLASH_STORE_H
#define FLASH_STORE_H

#include "stm32g4xx_hal.h"
#include <stdint.h>

typedef struct {
    uint16_t compound_id;
    uint8_t name_len;
    char name[32];
    float molar_absorptivity;
    uint8_t num_points;
    float wavelengths[8];
    float absorbances[8];
    uint8_t reserved[411];
} FlashLibraryEntry_t;

HAL_StatusTypeDef FlashStore_Init(void);
HAL_StatusTypeDef FlashStore_EraseSector(uint32_t sector_num);
HAL_StatusTypeDef FlashStore_Read(uint32_t addr, uint8_t *buf, uint16_t len);
HAL_StatusTypeDef FlashStore_WritePage(uint32_t addr, const uint8_t *buf, uint16_t len);
uint16_t FlashStore_GetLibraryCount(void);
HAL_StatusTypeDef FlashStore_WriteCompound(uint16_t index, const FlashLibraryEntry_t *entry);
HAL_StatusTypeDef FlashStore_ReadCompound(uint16_t index, FlashLibraryEntry_t *entry);
HAL_StatusTypeDef FlashStore_UpdateLibraryHeader(uint16_t num_compounds);

#endif