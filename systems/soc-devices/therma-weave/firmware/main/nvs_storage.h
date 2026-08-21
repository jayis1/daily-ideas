/*
 * Therma Weave — NVS Storage
 * nvs_storage.h — Non-volatile storage for settings persistence
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef NVS_STORAGE_H
#define NVS_STORAGE_H

#include "zone_controller.h"

#define NVS_NAMESPACE "therma_weave"

/**
 * Initialize NVS storage.
 */
void nvs_storage_init(void);

/**
 * Save all zone settings to NVS.
 * Stores: target_temp, enabled, kp, ki, kd for each zone.
 */
void nvs_storage_save_zones(zone_controller_t *zones);

/**
 * Load zone settings from NVS.
 * Returns default values if no stored settings found.
 */
void nvs_storage_load_zones(zone_controller_t *zones);

/**
 * Get target temperature for a zone from NVS.
 * Returns 0 if not found (caller should use default).
 */
float nvs_storage_get_target(uint8_t zone);

/**
 * Save a single zone's target temperature.
 */
void nvs_storage_set_target(uint8_t zone, float target);

#endif /* NVS_STORAGE_H */