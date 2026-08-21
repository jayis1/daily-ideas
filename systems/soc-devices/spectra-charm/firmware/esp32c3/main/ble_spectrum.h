/*
 * Spectra Charm — ble_spectrum.h
 */
#ifndef BLE_SPECTRUM_H
#define BLE_SPECTRUM_H

#include <stdint.h>

void BLE_Spectrum_Init(void);
void BLE_NotifySpectrum(const uint8_t *data, uint16_t len);
void BLE_UpdateBattery(uint8_t pct);

#endif