/*
 * kappa-pin / firmware / main / flash_store.h
 * NVS-backed persistent storage for calibration and settings
 *
 * MIT License.
 */
#ifndef FLASH_STORE_H
#define FLASH_STORE_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float calibration_factor;    /* single-point CF (default 1.0) */
    float cal_offset;            /* two-point offset (default 0.0) */
    float heater_resistance;     /* probe heater R at 25°C */
    float rtd_r0;                /* RTD R0 (ohms) */
    uint8_t last_material;       /* last selected material preset */
    uint32_t cal_timestamp;      /* calibration date (Unix) */
    char cal_ref_material[16];   /* reference material name */
    uint32_t total_measurements; /* lifetime counter */
} flash_config_t;

/* Initialize NVS and load config */
void flash_store_init(void);

/* Get current config (loaded from NVS) */
const flash_config_t *flash_store_get(void);

/* Save config to NVS */
void flash_store_save(const flash_config_t *cfg);

/* Update calibration factor */
void flash_store_set_calibration(float cf, float offset, const char *ref);

/* Update probe parameters */
void flash_store_set_probe(float heater_r, float rtd_r0);

/* Increment measurement counter */
void flash_store_increment_measurements(void);

/* Reset to defaults */
void flash_store_reset(void);

#endif /* FLASH_STORE_H */