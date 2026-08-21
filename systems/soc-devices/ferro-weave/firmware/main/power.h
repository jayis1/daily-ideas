/*
 * power.h — power-stage, OCP, thermal, fuel-gauge control
 */
#ifndef FERRO_WEAVE_POWER_H
#define FERRO_WEAVE_POWER_H

#include <stdbool.h>
#include <stdint.h>

/* Enable/disable the ±15 V boost (power stage). */
void power_amp_enable(bool en);

/* Read the power-stage NTC temperature (°C). */
float power_get_temp_c(void);

/* Read battery state of charge (0..100 %) via MAX17048. */
uint8_t power_get_soc(void);

/* Read battery voltage (V). */
float power_get_vbat(void);

/* Check the LM5035 fault latch. */
bool power_fault_latched(void);

/* Clear the fault latch (power-cycle the LM5035). */
void power_clear_fault(void);

/* Initialise power subsystem. */
void power_init(void);

#endif /* FERRO_WEAVE_POWER_H */