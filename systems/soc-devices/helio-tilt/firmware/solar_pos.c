/*
 * solar_pos.c — Solar position computation (NOAA/SPA truncated)
 *
 * Implements the NOAA Solar Position Algorithm (truncated to ~0.01°
 * accuracy) using CORDIC-accelerated trig functions. Computes solar
 * azimuth, elevation, declination, hour angle, air mass, and
 * atmospheric refraction correction from GPS coordinates + UTC time.
 *
 * Reference:
 *   NOAA Solar Position Calculator (https://gml.noaa.gov/grad/solcalc/)
 *   Meeus, "Astronomical Algorithms", 2nd ed.
 *   Kasten & Young, "Revised optical air mass tables and approximation
 *     formula", Applied Optics 28(22), 1989.
 */

#include "solar_pos.h"
#include "stm32g474_conf.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define DEG2RAD(x)  ((x) * M_PI / 180.0)
#define RAD2DEG(x)  ((x) * 180.0 / M_PI)

double solar_julian_day(int year, int month, int day,
                         int hour, int min, int sec)
{
    /* Astronomical Julian Day from Gregorian calendar date.
     * Valid for dates >= 1582-10-15.
     */
    int a = (14 - month) / 12;
    int y = year + 4800 - a;
    int m = month + 12 * a - 3;
    double jd = (double)day + (hour - 12) / 24.0 + min / 1440.0
                + sec / 86400.0;
    jd += (153 * m + 2) / 5 + 365 * y + y / 4 - y / 100 + y / 400
          - 32045;
    return jd;
}

double solar_air_mass(double zenith_deg)
{
    /* Kasten-Young 1989 formula.
     * m = 1 / (cos(θ) + 0.50572 × (96.07995 - θ)^-1.6364)
     * Valid for zenith 0–90°. Returns 99999 below horizon.
     */
    if (zenith_deg >= 90.0) return 99999.0;
    double z = DEG2RAD(zenith_deg);
    double cos_z = cos(z);
    double term = 0.50572 * pow(96.07995 - zenith_deg, -1.6364);
    return 1.0 / (cos_z + term);
}

int solar_pos_compute(double lat_deg, double lon_deg, double elev_m,
                       int year, int month, int day,
                       int hour, int min, int sec,
                       solar_pos_t *pos)
{
    double jd = solar_julian_day(year, month, day, hour, min, sec);
    double t = (jd - 2451545.0) / 36525.0;    /* Julian Century */

    /* Geometric Mean Longitude of Sun (degrees) */
    double l0 = fmod(280.46646 + t * 36000.76983, 360.0);
    if (l0 < 0) l0 += 360.0;

    /* Geometric Mean Anomaly of Sun (degrees) */
    double m_anom = 357.52911 + t * 35999.05029;

    /* Eccentricity of Earth's orbit */
    double e = 0.016708634 - t * 0.000042037;

    /* Sun's Equation of Center (degrees) */
    double m_rad = DEG2RAD(m_anom);
    double c = sin(m_rad) * (1.914602 - t * 0.004817)
             + sin(2 * m_rad) * (0.019993 - t * 0.000101)
             + sin(3 * m_rad) * 0.000289;

    /* Sun's True Longitude and True Anomaly */
    double true_long = l0 + c;
    double true_anom = m_anom + c;

    /* Sun's Apparent Longitude (corrected for nutation + aberration) */
    double omega = 125.04 - 1934.136 * t;
    double app_long = true_long - 0.00569 - 0.00478 * sin(DEG2RAD(omega));

    /* Mean Obliquity of Ecliptic (degrees) */
    double obliq0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059
                   - t * 0.001813))) / 60.0) / 60.0;

    /* Corrected Obliquity (with nutation) */
    double obliq_corr = obliq0 + 0.00256 * cos(DEG2RAD(omega));

    /* Sun's Declination (degrees) */
    double sin_decl = sin(DEG2RAD(obliq_corr)) * sin(DEG2RAD(app_long));
    double decl = RAD2DEG(asin(sin_decl));

    /* Equation of Time (minutes) — difference between solar and clock time */
    double y = tan(DEG2RAD(obliq_corr / 2.0));
    y *= y;
    double l0_rad = DEG2RAD(l0);
    double eot = y * sin(2 * l0_rad)
               - 2.0 * e * sin(m_rad)
               + 4.0 * e * y * sin(m_rad) * cos(2 * l0_rad)
               - 0.5 * y * y * sin(4 * l0_rad)
               - 1.25 * e * e * sin(2 * m_rad);
    eot = RAD2DEG(eot) * 4.0;   /* Convert to minutes */

    /* Solar Noon (minutes from local midnight, LST) */
    /* We use UTC directly; the observer longitude accounts for time zone. */
    double solar_time = (double)hour * 60.0 + min + sec / 60.0
                       + eot + lon_deg * 4.0;

    /* Hour Angle (degrees): 0 at solar noon, negative morning, positive afternoon */
    double hour_angle = (solar_time / 4.0) - 180.0;
    if (hour_angle < -180) hour_angle += 360.0;
    if (hour_angle > 180) hour_angle -= 360.0;

    /* Solar Zenith Angle */
    double lat_rad = DEG2RAD(lat_deg);
    double decl_rad = DEG2RAD(decl);
    double ha_rad = DEG2RAD(hour_angle);
    double cos_zenith = sin(lat_rad) * sin(decl_rad)
                      + cos(lat_rad) * cos(decl_rad) * cos(ha_rad);
    if (cos_zenith > 1.0) cos_zenith = 1.0;
    if (cos_zenith < -1.0) cos_zenith = -1.0;
    double zenith = RAD2DEG(acos(cos_zenith));
    double elevation = 90.0 - zenith;

    /* Solar Azimuth Angle (degrees, 0=N, clockwise) */
    double sin_az = -cos(decl_rad) * sin(ha_rad) / sin(DEG2RAD(zenith));
    double cos_az = (sin(decl_rad) - sin(lat_rad) * cos_zenith)
                   / (cos(lat_rad) * sin(DEG2RAD(zenith)));
    double azimuth = RAD2DEG(atan2(sin_az, cos_az));
    if (azimuth < 0) azimuth += 360.0;
    /* atan2 convention adjustment: we want 0=N, 90=E */
    azimuth = fmod(azimuth + 180.0, 360.0);

    /* Atmospheric Refraction (Saemundsson formula) */
    double refraction = 0.0;
    if (elevation > -1.0 && elevation < 85.0) {
        double e = elevation + 10.3 / (elevation + 5.11);
        refraction = 1.02 * 283.0 / (273.0 + 15.0) / 60.0
                    / tan(DEG2RAD(e));
        if (elevation < 5.0) refraction *= 1.5;  /* Higher error near horizon */
    }
    elevation += refraction;
    zenith = 90.0 - elevation;

    /* Fill output */
    pos->azimuth = azimuth;
    pos->elevation = elevation;
    pos->zenith = zenith;
    pos->declination = decl;
    pos->hour_angle = hour_angle;
    pos->right_ascen = fmod(true_long + 180.0, 360.0);
    pos->air_mass = solar_air_mass(zenith);
    pos->refraction = refraction;

    if (elevation < SOLAR_MIN_ELEV_DEG)
        return -1;
    return 0;
}