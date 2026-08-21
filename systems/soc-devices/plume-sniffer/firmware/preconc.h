/* preconc.h — Preconcentrator flash desorb controller
 *
 * The Tenax TA preconcentrator tube is heated by a separate nichrome wire
 * (2.5 W) on GPIO3 via MOSFET. A 10 kΩ NTC on GPIO6 (ADC1_CH6) monitors
 * the tube temperature. Flash desorb ramps to 220 °C in ~3 seconds.
 */
#ifndef PRECONC_H
#define PRECONC_H

#include <stdbool.h>

void preconc_init(void);

/* Read preconcentrator tube temperature (°C). */
float preconc_read_temp_c(void);

/* Execute flash desorb: ramp to 220°C, hold for PLUME_PRECONC_DESORB_TIME_S,
 * then cut heater. Blocks until complete. */
void preconc_flash_desorb(void);

/* Force heater off (emergency). */
void preconc_heater_off(void);

bool preconc_heater_active(void);

#endif /* PRECONC_H */