/*
 * hv_supply.h — HV supply (Cockcroft-Walton 30 kV) control
 */

#ifndef HV_SUPPLY_H
#define HV_SUPPLY_H

#include <stdbool.h>
#include <stdint.h>

/* Initialize HV supply peripherals (DAC1, ADC2, ADC3, GPIO) */
void hv_supply_init(void);

/* Ramp HV from 0 to target_kV over ramp_time_s (soft-start) */
void hv_supply_ramp(float target_kv, float ramp_time_s);

/* Turn off HV (DAC1 = 0, oscillator disabled) */
void hv_supply_off(void);

/* Activate bleeder to discharge HV node to GND */
void hv_supply_discharge(void);

/* Read current HV voltage (kV) via 10000:1 divider → ADC3 */
float hv_supply_read_voltage(void);

/* Read HV current (µA) via sense resistor → AD8629 → ADC2 */
float hv_supply_read_current(void);

/* Arm/disarm HV (gates CW oscillator) */
void hv_supply_arm(bool en);

#endif /* HV_SUPPLY_H */