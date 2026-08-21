/**
 * calibration.c — Sensor Calibration Manager Implementation
 * 
 * Manages persistent calibration data in STM32L4 flash.
 * Uses FLASH page 31 (last page of bank 1) for storage.
 */

#include "calibration.h"
#include "stm32l4xx_hal.h"
#include <string.h>

/* Flash address for calibration data (last page of bank 1) */
#define CAL_FLASH_ADDR  0x0807F800  /* Page 255 of 256KB flash */
#define CAL_FLASH_PAGE  255

/* External handles */
extern FLASH_ProcessTypeDef pFlash;

static calibration_data_t s_cal_data;
static bool s_cal_loaded = false;

/*----------------------------------------------------------------------------*/

int calibration_init(void) {
    return calibration_load(&s_cal_data) ? 0 : -1;
}

/*----------------------------------------------------------------------------*/

bool calibration_load(calibration_data_t *data) {
    /* Read calibration data from flash */
    calibration_data_t *flash_data = (calibration_data_t *)CAL_FLASH_ADDR;
    
    /* Check magic number */
    if (flash_data->magic != CALIBRATION_MAGIC) {
        memset(data, 0, sizeof(calibration_data_t));
        return false;
    }
    
    /* Verify CRC */
    uint16_t expected_crc = flash_data->crc16;
    uint16_t computed_crc = calibration_crc16((const uint8_t *)flash_data,
                                               offsetof(calibration_data_t, crc16));
    if (expected_crc != computed_crc) {
        memset(data, 0, sizeof(calibration_data_t));
        return false;
    }
    
    /* Copy to RAM */
    memcpy(data, flash_data, sizeof(calibration_data_t));
    s_cal_loaded = true;
    
    return data->dens_valid || data->ph_valid;
}

/*----------------------------------------------------------------------------*/

int calibration_save(const calibration_data_t *data) {
    HAL_StatusTypeDef status;
    
    /* Prepare data with magic and CRC */
    calibration_data_t data_to_save;
    memcpy(&data_to_save, data, sizeof(calibration_data_t));
    data_to_save.magic = CALIBRATION_MAGIC;
    data_to_save.timestamp = HAL_GetTick() / 1000;  /* Simple timestamp */
    data_to_save.crc16 = calibration_crc16((const uint8_t *)&data_to_save,
                                            offsetof(calibration_data_t, crc16));
    
    /* Unlock flash */
    HAL_FLASH_Unlock();
    
    /* Erase the calibration page */
    FLASH_EraseInitTypeDef erase_init;
    uint32_t page_error = 0;
    
    erase_init.TypeErase = FLASH_TYPEERASE_PAGES;
    erase_init.Banks = FLASH_BANK_1;
    erase_init.Page = CAL_FLASH_PAGE;
    erase_init.NbPages = 1;
    
    status = HAL_FLASHEx_Erase(&erase_init, &page_error);
    if (status != HAL_OK) {
        HAL_FLASH_Lock();
        return -1;
    }
    
    /* Write data to flash (64-bit at a time for STM32L4) */
    uint64_t *src = (uint64_t *)&data_to_save;
    uint32_t addr = CAL_FLASH_ADDR;
    uint32_t num_dwords = (sizeof(calibration_data_t) + 7) / 8;
    
    for (uint32_t i = 0; i < num_dwords; i++) {
        status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, addr, src[i]);
        if (status != HAL_OK) {
            HAL_FLASH_Lock();
            return -2;
        }
        addr += 8;
    }
    
    /* Lock flash */
    HAL_FLASH_Lock();
    
    /* Update cached data */
    memcpy(&s_cal_data, &data_to_save, sizeof(calibration_data_t));
    s_cal_loaded = true;
    
    return 0;
}

/*----------------------------------------------------------------------------*/

float calibration_densitometer_air(void) {
    /* This would call the densitometer module's calibration function */
    /* For now, we store the result here and it gets saved by the caller */
    float f_air = 0.0f;
    
    /* In production: densitometer_calibrate_air() */
    /* For now, this is a placeholder */
    
    if (f_air > 0.0f) {
        s_cal_data.dens_f_air = f_air;
        s_cal_data.dens_valid = (s_cal_data.dens_f_water > 0.0f);
    }
    
    return f_air;
}

/*----------------------------------------------------------------------------*/

float calibration_densitometer_water(float water_temp) {
    float f_water = 0.0f;
    
    /* In production: densitometer_calibrate_water(water_temp) */
    
    if (f_water > 0.0f) {
        s_cal_data.dens_f_water = f_water;
        s_cal_data.dens_t_cal = water_temp;
        s_cal_data.dens_valid = (s_cal_data.dens_f_air > 0.0f);
    }
    
    return f_water;
}

/*----------------------------------------------------------------------------*/

bool calibration_ph_buffer(float ph_value) {
    /* In production: ezo_ph_calibrate(ph_value) */
    /* Store the calibration point */
    
    if (ph_value == 4.0f) {
        /* pH 4.0 calibration — store voltage */
        /* Would read ADC voltage from EZO-pH */
        return true;
    } else if (ph_value == 7.0f) {
        /* pH 7.0 calibration — store voltage */
        return true;
    }
    
    return false;
}

/*----------------------------------------------------------------------------*/

void calibration_set_temp_offset(float offset) {
    s_cal_data.temp_offset = offset;
}

/*----------------------------------------------------------------------------*/

bool calibration_is_densitometer_ready(void) {
    return s_cal_loaded && s_cal_data.dens_valid;
}

/*----------------------------------------------------------------------------*/

bool calibration_is_ph_ready(void) {
    return s_cal_loaded && s_cal_data.ph_valid;
}

/*----------------------------------------------------------------------------*/

int calibration_erase(void) {
    HAL_FLASH_Unlock();
    
    FLASH_EraseInitTypeDef erase_init;
    uint32_t page_error = 0;
    
    erase_init.TypeErase = FLASH_TYPEERASE_PAGES;
    erase_init.Banks = FLASH_BANK_1;
    erase_init.Page = CAL_FLASH_PAGE;
    erase_init.NbPages = 1;
    
    HAL_StatusTypeDef status = HAL_FLASHEx_Erase(&erase_init, &page_error);
    
    HAL_FLASH_Lock();
    
    if (status != HAL_OK) {
        return -1;
    }
    
    memset(&s_cal_data, 0, sizeof(calibration_data_t));
    s_cal_loaded = false;
    
    return 0;
}

/*----------------------------------------------------------------------------*/

uint16_t calibration_crc16(const uint8_t *data, uint32_t len) {
    uint16_t crc = 0xFFFF;
    
    for (uint32_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x0001) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    
    return crc;
}