/*
 * kappa-pin / firmware / main / heater.h
 * Constant-power heater driver via MCP4131 digital pot + OPA548
 *
 * PI control loop maintains heater power Q = V*I constant during pulse.
 * Power is set via digital pot wiper position (0-255 → 0..Vref).
 *
 * MIT License.
 */
#ifndef HEATER_H
#define HEATER_H

#include <stdint.h>
#include <stdbool.h>

/* Heater control pins */
#define HEATER_EN_PIN       12      /* MOSFET gate enable */
#define HEATER_VMON_PIN     13      /* ADC1_CH2 — heater voltage monitor */
#define POT_CS_PIN          8       /* MCP4131 chip select */

/* Digital pot parameters */
#define POT_MAX_WIPER       255
#define POT_RESISTANCE      10000.0f  /* 10 kΩ */

/* Heater wire characteristics (default NP-100 needle probe) */
#define HEATER_RESISTANCE_DEFAULT  1.0f    /* ohms, 80mm nichrome 36AWG */
#define HEATER_ACTIVE_LENGTH       0.080f  /* meters */

/* Safety limits */
#define HEATER_MAX_POWER_W     5.0f
#define HEATER_MAX_CURRENT_A   2.0f
#define HEATER_MAX_TEMP_RISE_C 5.0f    /* max ΔT before auto-shutoff (safety) */

typedef enum {
    HEATER_OK = 0,
    HEATER_ERR_POT = -1,
    HEATER_ERR_OVERCURRENT = -2,
    HEATER_ERR_OVERTEMP = -3,
} heater_err_t;

/* Initialize heater control subsystem */
heater_err_t heater_init(void);

/* Set target power (W). Returns actual commanded power or error. */
heater_err_t heater_set_power(float target_w, float *actual_w);

/* Enable/disable heater output */
heater_err_t heater_enable(bool en);

/* Read instantaneous heater voltage (V) and current (A) */
heater_err_t heater_read_vi(float *voltage, float *current);

/* Read instantaneous heater power (W) */
heater_err_t heater_read_power(float *power_w);

/* PI control loop — call at 100 Hz. Maintains constant power. */
heater_err_t heater_pi_update(void);

/* Set heater wire resistance (from probe detection) */
void heater_set_resistance(float r_ohm);

/* Set active heater length (m) for Q computation */
void heater_set_length(float l_m);

/* Emergency stop — immediately disable heater */
void heater_emergency_stop(void);

/* Check if heater is active */
bool heater_is_active(void);

#endif /* HEATER_H */