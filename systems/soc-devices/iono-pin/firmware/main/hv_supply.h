/*
 * hv_supply.h — EMCO F50CT 5kV HV supply control + drift-voltage servo
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef HV_SUPPLY_H
#define HV_SUPPLY_H

#include <stdint.h>
#include <stdbool.h>

void hv_init(void);
void hv_enable(bool on);
bool hv_is_enabled(void);

/* Set drift voltage (servo to 2125 V via HV monitor feedback) */
void hv_set_drift_v(float target_v);
float hv_read_drift_v(void);       /* read back actual drift voltage */

/* Safety: immediate shutdown + bleeder discharge */
void hv_emergency_shutdown(void);
bool hv_fault(void);                /* TLV3201 over-current fault latched */

#endif /* HV_SUPPLY_H */