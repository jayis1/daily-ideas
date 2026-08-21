/*
 * sd_log.h — microSD card logging (FAT32, AERONET-compatible CSV)
 */

#ifndef SD_LOG_H
#define SD_LOG_H

#include "radiometry.h"
#include "solar_pos.h"
#include <stdint.h>
#include <stdbool.h>

/* Initialize SPI1 + microSD */
void sd_log_init(void);

/* Log one measurement record (AERONET-compatible CSV format) */
void sd_log_measurement(const radiometry_result_t *result,
                         const solar_pos_t *pos,
                         double lat, double lon, float elev_m,
                         float temp_c, float pressure_hpa,
                         int year, int month, int day,
                         int hour, int min, int sec);

/* Log Langley calibration data point */
void sd_log_langley(const float voltages[6], double air_mass,
                     int year, int month, int day,
                     int hour, int min, int sec);

/* Check if SD card is present */
bool sd_log_present(void);

#endif /* SD_LOG_H */