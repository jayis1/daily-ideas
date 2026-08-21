/*
 * Spectra Charm — wifi_api.h
 */
#ifndef WIFI_API_H
#define WIFI_API_H

void WiFi_API_Start(void);
void WiFi_API_UpdateSpectrum(const float *data, int len);
void WiFi_API_UpdateMatch(const char *compound, float confidence, float concentration);

#endif