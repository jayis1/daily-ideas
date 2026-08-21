/*
 * ble.c — BLE GATT service (stub for STM32 HAL BLE or external module)
 *
 * Full implementation requires STM32WB or external BLE module.
 * This stub provides the API interface.
 */

#include "ble.h"
#include <string.h>

int ble_init(void) { return 0; }
void ble_advertise(const char *name) { (void)name; }
void ble_process(void) { }
void ble_notify_results(const crystal_t *crystal) { (void)crystal; }