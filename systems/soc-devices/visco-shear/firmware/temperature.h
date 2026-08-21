/*
 * visco-shear / firmware / temperature.h
 * Peltier TEC1-12706 PID temperature control + NTC readout
 */
#ifndef VISCO_SHEAR_TEMPERATURE_H
#define VISCO_SHEAR_TEMPERATURE_H

void temperature_init(void);
void temperature_set_target(float temp_c);
float temperature_read(void);
bool temperature_is_stable(void);
void temperature_task(void);
void temperature_disable(void);

#endif