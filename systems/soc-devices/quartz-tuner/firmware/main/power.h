/*
 * power.h — Power management (MAX17048 fuel gauge + sleep)
 */

#ifndef QUARTZ_TUNER_POWER_H
#define QUARTZ_TUNER_POWER_H

int power_init(void);
float power_get_voltage(void);
float power_get_soc(void);
void power_sleep(void);

#endif