/*
 * power_amp.h — OPA569 power-amplifier control for excitation output
 */
#ifndef POWER_AMP_H
#define POWER_AMP_H

#include <stdint.h>
#include <stdbool.h>

void power_amp_init(void);
void power_amp_enable(void);
void power_amp_disable(void);
bool power_amp_is_enabled(void);

/* Set the output current limit (mA), 0..500 */
void power_amp_set_ilimit(uint16_t ma);

/* Read the OPA569 output current (mA) via the current-sense monitor (PA6) */
float power_amp_read_current(void);

/* Read the OPA569 output voltage (V) via the monitor (PC0) */
float power_amp_read_voltage(void);

/* Safety: shut down if output > ±11 V or current > 250 mA */
bool power_amp_safety_check(void);

#endif /* POWER_AMP_H */