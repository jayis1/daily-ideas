/*
 * hall-puck / firmware / Core / Inc / flash_store.h
 * Flash-based persistent storage (emulated EEPROM)
 *
 * STM32G474 flash sector used for config storage.
 *
 * MIT License.
 */
#ifndef FLASH_STORE_H
#define FLASH_STORE_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float b_field_calibration;      /* B-field in Tesla (default 0.482) */
    float current_calibration;      /* Current source calibration factor */
    float voltage_offset_uv;        /* ADC zero-point offset (µV) */
    float sample_thickness_mm;      /* Last used sample thickness */
    float measurement_current_ma;   /* Last used current */
    uint8_t last_mode;              /* Last measurement mode */
    uint32_t cal_timestamp;         /* Calibration date (Unix) */
    uint32_t total_measurements;    /* Lifetime counter */
} flash_config_t;

void flash_store_init(void);
const flash_config_t *flash_store_get(void);
void flash_store_save(const flash_config_t *cfg);
void flash_store_set_b_calibration(float b_t);
void flash_store_set_current_calibration(float cf);
void flash_store_set_voltage_offset(float offset_uv);
void flash_store_set_thickness(float mm);
void flash_store_set_current(float ma);
void flash_store_increment_measurements(void);
void flash_store_reset(void);

#endif /* FLASH_STORE_H */