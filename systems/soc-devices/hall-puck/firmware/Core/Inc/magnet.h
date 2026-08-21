/*
 * hall-puck / firmware / Core / Inc / magnet.h
 * Magnetic field reversal mechanism (28BYJ-48 stepper + DRV5053)
 *
 * Rotates N52 neodymium magnet 180° for Hall field reversal.
 * DRV5053 Hall switch provides position feedback.
 *
 * MIT License.
 */
#ifndef MAGNET_H
#define MAGNET_H

#include <stdint.h>
#include <stdbool.h>

/* Magnet orientations */
typedef enum {
    MAGNET_OFF = 0,     /* Unknown / not positioned */
    MAGNET_B_PLUS,      /* B+ orientation (field up through sample) */
    MAGNET_B_MINUS,     /* B- orientation (field down through sample) */
    MAGNET_PARKED,      /* Magnet rotated away from sample (no field) */
} magnet_state_t;

/* Initialize stepper motor + Hall position sensor */
void magnet_init(void);

/* Rotate magnet to B+ position */
void magnet_set_b_plus(void);

/* Rotate magnet to B- position (180° from B+) */
void magnet_set_b_minus(void);

/* Park magnet away from sample (reduce field to near zero) */
void magnet_park(void);

/* Get current magnet state */
magnet_state_t magnet_get_state(void);

/* Get measured B-field in Tesla (from DRV5053 reading) */
float magnet_get_b_field(void);

/* Calibrate B-field using known reference sample */
void magnet_set_calibration(float b_field_t);

/* Get calibrated B-field */
float magnet_get_calibration(void);

/* Step the motor by N steps (for manual control) */
void magnet_step(int steps);

#endif /* MAGNET_H */