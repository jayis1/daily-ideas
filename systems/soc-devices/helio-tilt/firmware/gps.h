/*
 * gps.h — NEO-M9N GPS NMEA parsing
 */

#ifndef GPS_H
#define GPS_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    double latitude;    /* Degrees, N positive */
    double longitude;   /* Degrees, E positive */
    double elevation_m; /* Meters above sea level */
    int    year;
    int    month;
    int    day;
    int    hour;
    int    min;
    int    sec;
    int    satellites;
    bool   fix_valid;
    bool   time_valid;
} gps_data_t;

/* Initialize UART2 for GPS (38400 baud) */
void gps_init(void);

/* Parse one NMEA sentence from the GPS UART buffer.
 * Called from UART2 RX ISR for each complete line.
 */
void gps_parse_nmea(const char *sentence);

/* Get the latest GPS data (thread-safe copy) */
void gps_get_data(gps_data_t *data);

/* Check if GPS has a valid fix */
bool gps_has_fix(void);

/* Wait for GPS fix (blocking, up to GPS_FIX_TIMEOUT_S seconds) */
int gps_wait_fix(uint32_t timeout_s);

/* Get PPS-corrected UTC time (millisecond precision) */
uint32_t gps_get_pps_ms(void);

#endif /* GPS_H */