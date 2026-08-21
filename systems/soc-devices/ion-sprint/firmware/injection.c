/*
 * injection.c — Sample injection for capillary electrophoresis
 *
 * Two injection modes:
 *
 * 1. Electrokinetic: apply a reduced HV (5 kV) for 1–5 seconds.
 *    Ions migrate into the capillary inlet; the amount injected is
 *    proportional to the ion's electrophoretic mobility (biased
 *    toward high-mobility ions). Simple, no moving parts.
 *
 * 2. Hydrodynamic: lift the inlet vial 10 cm above the outlet for
 *    5–30 seconds. The hydrostatic pressure drives a plug of sample
 *    into the capillary. Unbiased (all species injected equally).
 *    Uses the NEMA8 stepper (vial_lift module) to raise/lower vial.
 */

#include "injection.h"
#include "hv_supply.h"
#include "vial_lift.h"
#include "stm32g474_conf.h"

void injection_init(void)
{
    vial_lift_init();
}

void injection_electrokinetic(float voltage_kv, float duration_s)
{
    /* Quick ramp to injection voltage (1 s), hold, ramp to 0 (1 s) */
    hv_supply_ramp(voltage_kv, 1.0f);

    /* Hold for duration_s (simplified blocking delay) */
    uint32_t hold_us = (uint32_t)(duration_s * 1000000.0f);
    for (volatile uint32_t i = 0; i < hold_us / 10; i++) ;

    /* Ramp back to 0 */
    hv_supply_ramp(0.0f, 1.0f);
    hv_supply_off();
}

void injection_hydrodynamic(float lift_mm, float duration_s)
{
    /* Lift inlet vial */
    vial_lift_up(lift_mm);

    /* Hold for duration_s (simplified blocking delay) */
    uint32_t hold_us = (uint32_t)(duration_s * 1000000.0f);
    for (volatile uint32_t i = 0; i < hold_us / 10; i++) ;

    /* Lower vial back */
    vial_lift_down(lift_mm);
}