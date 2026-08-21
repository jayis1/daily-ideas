/*
 * gps.h — NEO-M9N UART parser + PPS microsecond time-tagging
 */
#ifndef BOLT_COMPASS_GPS_H
#define BOLT_COMPASS_GPS_H

#include <stdint.h>

/* Init UART1 + PPS GPIO interrupt. */
void gps_init(void);

/* The GPS TOW (time of week) in microseconds at the last PPS edge. */
uint64_t gps_pps_last(void);

/* Number of ADC samples since the last PPS edge (for sub-second time). */
uint64_t gps_sample_count(void);

/* Whether we have a valid GPS fix. */
int gps_fix_valid(void);

/* Last fix: lat/lon in degrees × 1e7, altitude cm. */
void gps_position(int32_t *lat_e7, int32_t *lon_e7, int32_t *alt_cm);

/* Set the sample counter (called by the ADC ISR once per sample). */
void gps_tick_sample(void);

#endif /* BOLT_COMPASS_GPS_H */