/*
 * ina333.h — INA333 instrumentation amplifier gain control
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Gain is set by a 74HC4051 analog mux selecting one of four Rg resistors.
 */

#ifndef INA333_H
#define INA333_H

#include <stdint.h>
#include <stdbool.h>

/* Gain ranges */
typedef enum {
    INA333_GAIN_2X    = 0,  /* Rg = 100kΩ, ±2.5V range  */
    INA333_GAIN_11X   = 1,  /* Rg = 10kΩ,  ±200mV range  */
    INA333_GAIN_101X  = 2,  /* Rg = 1kΩ,   ±20mV range   */
    INA333_GAIN_1001X = 3,  /* Rg = 100Ω,  ±2mV range    */
} ina333_gain_t;

/* Initialize gain-control GPIOs (PB11/PB12/PB13 → 74HC4051 select) */
void ina333_init(void);

/* Set the gain range */
void ina333_set_gain(ina333_gain_t gain);

/* Get current gain setting */
ina333_gain_t ina333_get_gain(void);

/* Get the numeric gain multiplier for the current setting */
float ina333_get_gain_value(void);

/* Auto-range: given a peak signal amplitude in volts (input-referred),
 * select the best gain range. Returns true if gain changed. */
bool ina333_auto_range(float peak_amplitude_v);

/* Get the input voltage range for the current gain setting */
float ina333_get_input_range(void);

#endif /* INA333_H */