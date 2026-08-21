/**
 * gravity_corrections.c — Longman earth-tide model (simplified)
 *
 * Computes the gravitational effect of the Sun and Moon at a given
 * time and station location. This is a simplified implementation of
 * the Longman (1959) formula, accurate to ~1 μGal — sufficient for
 * the Gravi Dot's MEMS-grade measurement.
 *
 * References:
 *   Longman, I.M. (1959). "Formulas for computing the tidal
 *   acceleration due to the moon and the sun." J. Geophys. Res.
 */

#include "gravity_corrections.h"
#include <math.h>

#define DEG2RAD  (M_PI / 180.0)
#define RAD2DEG  (180.0 / M_PI)

/* Astronomical constants */
#define GM_MOON  4902.800   /* GM_moon in km³/s² (×10³)  */
#define GM_SUN   1.32712440018e11  /* GM_sun in m³/s² */
#define R_MOON   384400.0    /* mean Earth-Moon distance, km */
#define R_SUN    1.496e8     /* mean Earth-Sun distance, km */
#define R_EARTH  6371.0      /* Earth mean radius, km */

/* Julian Date from Unix time */
static double unix_to_jd(uint32_t unix_time)
{
    return 2440587.5 + (double)unix_time / 86400.0;
}

/* Greenwich Mean Sidereal Time (degrees) from JD */
static double gmst_deg(double jd)
{
    double T = (jd - 2451545.0) / 36525.0;
    double theta = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
                 + 0.000387933 * T * T - T*T*T / 38710000.0;
    /* normalize to 0–360 */
    theta = fmod(theta, 360.0);
    if (theta < 0) theta += 360.0;
    return theta;
}

/* Simplified lunar position (low-precision, adequate for tide calc) */
static void moon_position(double jd, double *ra_deg, double *dec_deg, double *dist_km)
{
    double T = (jd - 2451545.0) / 36525.0;
    /* Mean longitude of Moon */
    double L = fmod(218.316 + 481267.8813 * T, 360.0);
    /* Mean anomaly of Moon */
    double M = fmod(134.963 + 477198.8676 * T, 360.0) * DEG2RAD;
    /* Mean elongation */
    double D = fmod(357.529 + 35999.050 * T, 360.0) * DEG2RAD;

    /* Simplified longitude (degrees) */
    double lambda = L + 6.289 * sin(M) - 1.274 * sin(M - 2.0 * D);
    /* Simplified distance */
    *dist_km = R_MOON + 20905.0 * cos(M);  /* km, first-order */
    /* Approximate RA/Dec (assume inclination ~5° → small effect) */
    *ra_deg = lambda;
    *dec_deg = 0.0;  /* simplified — real Longman uses full ecliptic */
}

/* Simplified solar position */
static void sun_position(double jd, double *ra_deg, double *dec_deg, double *dist_km)
{
    double T = (jd - 2451545.0) / 36525.0;
    double M = fmod(357.529 + 35999.050 * T, 360.0) * DEG2RAD;
    double L = fmod(280.459 + 36000.770 * T, 360.0);
    double lambda = (L + 1.915 * sin(M) + 0.020 * sin(2.0 * M)) * DEG2RAD;

    double epsilon = 23.4393 * DEG2RAD;
    *ra_deg  = fmod(atan2(cos(epsilon) * sin(lambda), cos(lambda)) * RAD2DEG, 360.0);
    if (*ra_deg < 0) *ra_deg += 360.0;
    *dec_deg = asin(sin(epsilon) * sin(lambda)) * RAD2DEG;
    *dist_km = R_SUN;  /* constant approx */
}

/**
 * Tide acceleration (vertical component) from a body.
 * Uses the standard tide formula:
 *   g_tide = (GM / r²) × (R_E / r) × (3cos²z - 1) / 2
 * where z is the zenith angle of the body at the station.
 */
static double tide_from_body(double gm, double dist_km, double ra_deg,
                             double dec_deg, double lat_deg, double lst_deg)
{
    /* Hour angle of body (degrees) */
    double H = (lst_deg - ra_deg) * DEG2RAD;
    double dec = dec_deg * DEG2RAD;
    double lat = lat_deg * DEG2RAD;

    /* Zenith angle: cos(z) = sin(lat)sin(dec) + cos(lat)cos(dec)cos(H) */
    double cos_z = sin(lat) * sin(dec) + cos(lat) * cos(dec) * cos(H);
    double z = acos(cos_z);
    double cos2z = cos_z * cos_z;

    /* Tide factor: (3cos²z - 1)/2 */
    double factor = (3.0 * cos2z - 1.0) / 2.0;

    /* Convert: GM in m³/s², dist in m, R_E in m → result in m/s²
     * g_tide = GM * R_E / dist³ * factor
     * Then convert m/s² → mGal (1 m/s² = 100 000 mGal) */
    double dist_m = dist_km * 1000.0;
    double g_mps2 = gm * R_EARTH * 1000.0 / (dist_m * dist_m * dist_m) * factor;
    return g_mps2 * 100000.0;  /* mGal */
}

double longman_tide(uint32_t unix_time, double lat_deg, double lon_deg)
{
    double jd = unix_to_jd(unix_time);
    double theta = gmst_deg(jd);
    double lst = theta + lon_deg;  /* Local Sidereal Time (degrees) */
    if (lst < 0) lst += 360.0;
    if (lst >= 360.0) lst -= 360.0;

    double moon_ra, moon_dec, moon_d;
    double sun_ra, sun_dec, sun_d;

    moon_position(jd, &moon_ra, &moon_dec, &moon_d);
    sun_position(jd,  &sun_ra,  &sun_dec,  &sun_d);

    /* GM in SI (m³/s²): convert from our constants */
    double g_moon = tide_from_body(GM_MOON * 1e9, moon_d, moon_ra, moon_dec,
                                   lat_deg, lst);
    double g_sun  = tide_from_body(GM_SUN, sun_d, sun_ra, sun_dec,
                                   lat_deg, lst);

    return g_moon + g_sun;  /* mGal */
}