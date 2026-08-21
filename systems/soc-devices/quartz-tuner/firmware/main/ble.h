/*
 * ble.h — BLE GATT service for Quartz Tuner
 *
 * GATT service "QuartzTuner" with characteristics:
 * - SweepData: notify (live sweep data during measurement)
 * - Parameters: read (motional parameters after extraction)
 * - Classification: read (crystal type classification)
 * - Command: write (start sweep, calibrate, etc.)
 */

#ifndef QUARTZ_TUNER_BLE_H
#define QUARTZ_TUNER_BLE_H

#include "types.h"

int ble_init(void);
void ble_advertise(const char *name);
void ble_process(void);
void ble_notify_results(const crystal_t *crystal);

#endif