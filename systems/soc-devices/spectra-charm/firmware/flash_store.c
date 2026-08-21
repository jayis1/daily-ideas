/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * flash_store.c — W25Q128 SPI flash driver for spectral library storage
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "flash_store.h"
#include "stm32g4xx_hal.h"
#include <string.h>

extern SPI_HandleTypeDef hspi2;

/* W25Q128 commands */
#define W25Q_CMD_READ        0x03
#define W25Q_CMD_WRITE_EN    0x06
#define W25Q_CMD_PAGE_PROG   0x02
#define W25Q_CMD_SECTOR_ER   0x20   /* 4KB sector erase */
#define W25Q_CMD_BLOCK_ER    0xD8   /* 64KB block erase */
#define W25Q_CMD_CHIP_ER    0xC7
#define W25Q_CMD_RD_SR1     0x05
#define W25Q_CMD_RD_SR2     0x35
#define W25Q_CMD_RD_SR3     0x15
#define W25Q_CMD_JEDEC_ID   0x9F

/* Flash layout (16 MB total) */
#define FLASH_ADDR_LIBRARY_START  0x000000  /* Sector 0-15: spectral library (64 KB) */
#define FLASH_ADDR_BACKUP_START   0x010000  /* Sector 16+: calibration backup */
#define FLASH_SECTOR_SIZE         4096
#define FLASH_PAGE_SIZE          256
#define FLASH_LIBRARY_MAX_COMPOUNDS 200
#define FLASH_LIBRARY_HEADER_MAGIC  0x5343484D  /* "SCHM" */

/* Library entry on flash: 512 bytes per compound */
#define FLASH_ENTRY_SIZE  512

static inline void W25Q_CS_Low(void)
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
}

static inline void W25Q_CS_High(void)
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_SET);
}

static void W25Q_WriteEnable(void)
{
    uint8_t cmd = W25Q_CMD_WRITE_EN;
    W25Q_CS_Low();
    HAL_SPI_Transmit(&hspi2, &cmd, 1, 100);
    W25Q_CS_High();
}

static void W25Q_WaitBusy(void)
{
    uint8_t cmd = W25Q_CMD_RD_SR1;
    uint8_t sr1;
    do {
        W25Q_CS_Low();
        HAL_SPI_Transmit(&hspi2, &cmd, 1, 100);
        HAL_SPI_Receive(&hspi2, &sr1, 1, 100);
        W25Q_CS_High();
    } while (sr1 & 0x01); /* BUSY bit */
}

static uint32_t W25Q_ReadJEDECID(void)
{
    uint8_t cmd = W25Q_CMD_JEDEC_ID;
    uint8_t rx[4] = {0};
    W25Q_CS_Low();
    HAL_SPI_Transmit(&hspi2, &cmd, 1, 100);
    HAL_SPI_Receive(&hspi2, rx, 3, 100);
    W25Q_CS_High();
    return ((uint32_t)rx[0] << 16) | ((uint32_t)rx[1] << 8) | rx[2];
}

HAL_StatusTypeDef FlashStore_Init(void)
{
    uint32_t id = W25Q_ReadJEDECID();
    /* W25Q128: Manufacturer 0xEF, Type 0x40, Capacity 0x18 */
    if (id != 0xEF4018) {
        return HAL_ERROR;
    }
    return HAL_OK;
}

HAL_StatusTypeDef FlashStore_EraseSector(uint32_t sector_num)
{
    uint8_t cmd[4];
    uint32_t addr = sector_num * FLASH_SECTOR_SIZE;

    W25Q_WriteEnable();
    W25Q_WaitBusy();

    cmd[0] = W25Q_CMD_SECTOR_ER;
    cmd[1] = (addr >> 16) & 0xFF;
    cmd[2] = (addr >> 8) & 0xFF;
    cmd[3] = addr & 0xFF;

    W25Q_CS_Low();
    HAL_SPI_Transmit(&hspi2, cmd, 4, 500);
    W25Q_CS_High();

    W25Q_WaitBusy();
    return HAL_OK;
}

HAL_StatusTypeDef FlashStore_Read(uint32_t addr, uint8_t *buf, uint16_t len)
{
    uint8_t cmd[4];
    cmd[0] = W25Q_CMD_READ;
    cmd[1] = (addr >> 16) & 0xFF;
    cmd[2] = (addr >> 8) & 0xFF;
    cmd[3] = addr & 0xFF;

    W25Q_CS_Low();
    HAL_SPI_Transmit(&hspi2, cmd, 4, 100);
    HAL_SPI_Receive(&hspi2, buf, len, 1000);
    W25Q_CS_High();

    return HAL_OK;
}

HAL_StatusTypeDef FlashStore_WritePage(uint32_t addr, const uint8_t *buf, uint16_t len)
{
    uint8_t cmd[4];
    if (len > FLASH_PAGE_SIZE) len = FLASH_PAGE_SIZE;
    if ((addr & 0xFF) + len > FLASH_PAGE_SIZE) {
        return HAL_ERROR; /* Cross-page write not supported here */
    }

    W25Q_WriteEnable();
    W25Q_WaitBusy();

    cmd[0] = W25Q_CMD_PAGE_PROG;
    cmd[1] = (addr >> 16) & 0xFF;
    cmd[2] = (addr >> 8) & 0xFF;
    cmd[3] = addr & 0xFF;

    W25Q_CS_Low();
    HAL_SPI_Transmit(&hspi2, cmd, 4, 100);
    HAL_SPI_Transmit(&hspi2, (uint8_t *)buf, len, 500);
    W25Q_CS_High();

    W25Q_WaitBusy();
    return HAL_OK;
}

/* ========================================================================
 * Spectral Library on Flash
 * ======================================================================== */

typedef struct {
    uint32_t magic;          /* FLASH_LIBRARY_HEADER_MAGIC */
    uint16_t num_compounds;
    uint16_t reserved;
    uint32_t crc32;
} FlashLibraryHeader_t;

typedef struct {
    uint16_t compound_id;
    uint8_t name_len;
    char name[32];
    float molar_absorptivity;
    uint8_t num_points;
    float wavelengths[8];
    float absorbances[8];
    uint8_t reserved[411];   /* Pad to 512 bytes */
} FlashLibraryEntry_t;

uint16_t FlashStore_GetLibraryCount(void)
{
    FlashLibraryHeader_t hdr;
    FlashStore_Read(FLASH_ADDR_LIBRARY_START, (uint8_t *)&hdr, sizeof(hdr));
    if (hdr.magic == FLASH_LIBRARY_HEADER_MAGIC) {
        return hdr.num_compounds;
    }
    return 0;
}

HAL_StatusTypeDef FlashStore_WriteCompound(uint16_t index, const FlashLibraryEntry_t *entry)
{
    if (index >= FLASH_LIBRARY_MAX_COMPOUNDS) return HAL_ERROR;

    uint32_t addr = FLASH_ADDR_LIBRARY_START + sizeof(FlashLibraryHeader_t) +
                     index * FLASH_ENTRY_SIZE;

    return FlashStore_WritePage(addr, (const uint8_t *)entry, sizeof(FlashLibraryEntry_t));
}

HAL_StatusTypeDef FlashStore_ReadCompound(uint16_t index, FlashLibraryEntry_t *entry)
{
    if (index >= FLASH_LIBRARY_MAX_COMPOUNDS) return HAL_ERROR;

    uint32_t addr = FLASH_ADDR_LIBRARY_START + sizeof(FlashLibraryHeader_t) +
                     index * FLASH_ENTRY_SIZE;

    return FlashStore_Read(addr, (uint8_t *)entry, sizeof(FlashLibraryEntry_t));
}

HAL_StatusTypeDef FlashStore_UpdateLibraryHeader(uint16_t num_compounds)
{
    FlashLibraryHeader_t hdr;
    hdr.magic = FLASH_LIBRARY_HEADER_MAGIC;
    hdr.num_compounds = num_compounds;
    hdr.reserved = 0;
    hdr.crc32 = 0; /* TODO: calculate CRC32 */

    return FlashStore_WritePage(FLASH_ADDR_LIBRARY_START, (uint8_t *)&hdr, sizeof(hdr));
}