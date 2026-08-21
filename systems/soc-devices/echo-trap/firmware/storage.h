/*
 * storage.h — NVS storage for LoRaWAN credentials, config, species counts
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_STORAGE_H
#define ECHO_TRAP_STORAGE_H

#include <stdint.h>
#include "esp_err.h"

void storage_init(void);
esp_err_t storage_load_credentials(uint8_t *app_eui, uint8_t *app_key, uint8_t *dev_eui);
esp_err_t storage_save_credentials(const uint8_t *app_eui, const uint8_t *app_key, const uint8_t *dev_eui);
void storage_load_lorawan_keys(void);

#endif /* ECHO_TRAP_STORAGE_H */