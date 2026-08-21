/*
 * injection.h — Sample injection (electrokinetic / hydrodynamic)
 */

#ifndef INJECTION_H
#define INJECTION_H

#include <stdbool.h>

/* Initialize injection peripherals */
void injection_init(void);

/* Electrokinetic injection: apply HV at reduced voltage for duration_s.
 * Uses hv_supply_ramp at INJ_EK_VOLTAGE_KV, then ramp back to 0. */
void injection_electrokinetic(float voltage_kv, float duration_s);

/* Hydrodynamic injection: lift inlet vial by lift_mm for duration_s
 * using NEMA8 stepper (vial_lift module), then lower. */
void injection_hydrodynamic(float lift_mm, float duration_s);

#endif /* INJECTION_H */