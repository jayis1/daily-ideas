/*
 * polarimeter.h — Core polarimetry measurement engine
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Performs Malus's law curve fitting to find the null angle, computes
 * optical rotation, applies temperature compensation, and calculates
 * concentration from specific rotation.
 */
#ifndef POLARIMETER_H
#define POLARIMETER_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    double angle_deg;        /* analyzer null angle */
    double intensity;        /* photodiode intensity at null */
    double fit_rms;          /* curve fit residual */
    uint8_t wavelength_idx;  /* 0=405, 1=520, 2=589 */
    double wavelength_nm;
    double temperature_c;   /* sample temperature */
    bool valid;
} polarimeter_result_t;

/* API */
void polarimeter_init(void);
void polarimeter_set_wavelength(double nm);
double polarimeter_get_wavelength(void);

/* Auto-zero: store reference null angle with empty tube */
void polarimeter_auto_zero(void);
bool polarimeter_is_zeroed(void);
double polarimeter_get_zero_angle(uint8_t wl_idx);

/* Single measurement at current wavelength */
polarimeter_result_t polarimeter_measure(void);

/* Full 3-wavelength measurement (for Drude analysis) */
void polarimeter_measure_multi(polarimeter_result_t results[3]);

/* Compute optical rotation from a measurement (degrees) */
double polarimeter_compute_rotation(const polarimeter_result_t *result);

/* Compute concentration (g/100mL) given specific rotation */
double polarimeter_compute_concentration(double rotation_deg,
                                          double specific_rotation,
                                          double path_length_dm,
                                          double temperature_c,
                                          double temp_coeff);

/* Malus's law curve fit: find null angle from intensity vs angle data */
double malus_fit_null(const double *angles, const double *intensities,
                      int n_points);

#endif /* POLARIMETER_H */