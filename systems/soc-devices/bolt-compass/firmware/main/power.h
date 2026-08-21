/*
 * power.h — solar charger + fuel gauge + light-sleep manager
 */
#ifndef BOLT_COMPASS_POWER_H
#define BOLT_COMPASS_POWER_H

/* Init fuel gauge (MAX17048) + solar charger (MCP73871) GPIO reads. */
void power_init(void);

/* Battery state-of-charge (0..100). */
float power_soc(void);

/* Solar input present? */
int   power_solar_present(void);

/* Enter light sleep until the next ADS131M04 DRDY (keeps the ADC running). */
void power_light_sleep(void);

#endif /* BOLT_COMPASS_POWER_H */