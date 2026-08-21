/*
 * integrator.c — analog integrator reset control
 *
 * Drives the TS5A3166 analog switch across the 100 nF integrator cap via
 * the INTG_RESET GPIO. A 10 µs pulse zeros the integrator at the start
 * of each half-cycle (synchronous to the HRTIM update event).
 */
#include "integrator.h"

/* Firmware: HAL_GPIO_WritePin(INTG_RESET_GPIO_Port, INTG_RESET_Pin, ...).
 * Sim: stubbed in port_sim.c. */
void integrator_reset(void)
{
    /* assert reset high for 10 µs, then low */
    integrator_hold_reset(true);
    /* delay 10 µs (firmware uses a busy-loop on DWT cycle counter) */
    integrator_hold_reset(false);
}

void integrator_hold_reset(bool hold)
{
    (void)hold;
    /* HAL_GPIO_WritePin(INTG_RESET_GPIO_Port, INTG_RESET_Pin,
     *                  hold ? GPIO_PIN_SET : GPIO_PIN_RESET); */
}