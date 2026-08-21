/**
 * calibration.h — Sensor Calibration Manager
 * 
 * Manages two-point densitometer calibration (air + water)
 * and pH probe calibration (pH 4 + pH 7 buffers).
 * Stores calibration data in STM32L4 flash (FLASH page 31).
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <stdint.h>
#include <stdbool.h>
#include "densitometer.h"

/* Calibration data stored in flash */
typedef struct {
    /* Densitometer calibration */
    float dens_f_air;           /* Resonant frequency in air (Hz) */
    float dens_f_water;         /* Resonant frequency in water (Hz) */
    float dens_t_cal;           /* Water calibration temperature (°C) */
    bool dens_valid;            /* Densitometer calibration is valid */
    
    /* pH probe calibration */
    float ph_v4;               /* ADC voltage at pH 4.0 */
    float ph_v7;               /* ADC voltage at pH 7.0 */
    bool ph_valid;              /* pH calibration is valid */
    
    /* DS18B20 offset */
    float temp_offset;          /* Temperature correction offset (°C) */
    
    /* Metadata */
    uint32_t magic;             /* Magic number to verify valid data */
    uint32_t timestamp;         /* Unix timestamp of last calibration */
    uint16_t crc16;             /* CRC16 checksum */
} calibration_data_t;

#define CALIBRATION_MAGIC 0xB5205E51  /* "BREW SENSE" in hex */

/**
 * Initialize calibration module.
 * Loads stored calibration from flash on first call.
 * @return 0 on success, negative if no calibration found
 */
int calibration_init(void);

/**
 * Load calibration data from flash.
 * @param data Pointer to structure to fill
 * @return true if valid calibration was found
 */
bool calibration_load(calibration_data_t *data);

/**
 * Save calibration data to flash.
 * This erases the calibration flash page and rewrites it.
 * @param data Pointer to calibration data to save
 * @return 0 on success, negative on error
 */
int calibration_save(const calibration_data_t *data);

/**
 * Perform densitometer air calibration.
 * Reads resonant frequency in air and stores it.
 * @return Resonant frequency in Hz, or 0 on error
 */
float calibration_densitometer_air(void);

/**
 * Perform densitometer water calibration.
 * Reads resonant frequency in water and stores it.
 * @param water_temp Temperature of distilled water in °C
 * @return Resonant frequency in Hz, or 0 on error
 */
float calibration_densitometer_water(float water_temp);

/**
 * Perform pH probe calibration at a known pH.
 * @param ph_value Known pH of the buffer solution (4.0 or 7.0)
 * @return true if calibration was accepted
 */
bool calibration_ph_buffer(float ph_value);

/**
 * Set a temperature offset for DS18B20 correction.
 * @param offset Temperature offset in °C (added to reading)
 */
void calibration_set_temp_offset(float offset);

/**
 * Check if densitometer calibration is valid.
 * @return true if calibrated
 */
bool calibration_is_densitometer_ready(void);

/**
 * Check if pH calibration is valid.
 * @return true if calibrated
 */
bool calibration_is_ph_ready(void);

/**
 * Erase all calibration data from flash.
 * Used for factory reset.
 * @return 0 on success, negative on error
 */
int calibration_erase(void);

/**
 * Calculate CRC16 for calibration data integrity.
 * @param data Pointer to calibration data (CRC field excluded)
 * @param len Length of data in bytes
 * @return CRC16 value
 */
uint16_t calibration_crc16(const uint8_t *data, uint32_t len);

#endif /* CALIBRATION_H */