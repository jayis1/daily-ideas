/*
 * dent-scope / Core/Inc/flash_store.h
 * Dent Scope — NV flash parameter storage
 * MIT License.
 */
#ifndef FLASH_STORE_H
#define FLASH_STORE_H

#include "main.h"

void flash_load(void);
void flash_save(void);
void flash_defaults(void);

#endif /* FLASH_STORE_H */