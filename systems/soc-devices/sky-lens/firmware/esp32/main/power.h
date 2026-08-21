/* power.h — MAX17048 fuel gauge + deep-sleep duty-cycle mode */
#ifndef POWER_H
#define POWER_H
#include "sky_lens.h"

void  power_init(void);
float power_battery_pct(void);       /* 0..100 */
float power_battery_mv(void);
void  power_deep_sleep(uint64_t us);

#endif