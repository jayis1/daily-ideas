/*
 * solar_pos.h — Solar position computation (NOAA/SPA truncated)
 */

#ifndef SOLAR_POS_H
#define SOLAR_POS_H

typedef struct {
    double azimuth;       /* Solar azimuth angle (degrees, 0=N, 90=E) */
    double elevation;     /* Solar elevation angle (degrees, above horizon) */
    double zenith;        /* Solar zenith angle (degrees, = 90 - elevation) */
    double declination;   /* Solar declination (degrees) */
    double hour_angle;    /* Solar hour angle (degrees) */
    double right_ascen;   /* Right ascension (degrees) */
    double air_mass;      /* Relative optical air mass (Kasten-Young) */
    double refraction;    /* Atmospheric refraction correction (degrees) */
} solar_pos_t;

/* Compute solar position from GPS coordinates + UTC time.
 * lat_deg, lon_deg: observer latitude/longitude (degrees, N/E positive)
 * elev_m: observer elevation above sea level (meters)
 * year, month, day, hour, min, sec: UTC time
 * Returns 0 on success, -1 if elevation < SOLAR_MIN_ELEV_DEG.
 */
int solar_pos_compute(double lat_deg, double lon_deg, double elev_m,
                       int year, int month, int day,
                       int hour, int min, int sec,
                       solar_pos_t *pos);

/* Compute relative optical air mass (Kasten-Young formula).
 * m = 1 / (cos(θ) + 0.50572 × (96.07995 - θ)^-1.6364)
 * where θ is the zenith angle in degrees.
 */
double solar_air_mass(double zenith_deg);

/* Compute Julian Day from UTC date/time.
 * Returns JD (double, e.g. 2460000.5).
 */
double solar_julian_day(int year, int month, int day,
                         int hour, int min, int sec);

#endif /* SOLAR_POS_H */