/* battery.h — Battery voltage monitor + low-charge gating */
#ifndef BATTERY_H
#define BATTERY_H

/* Read battery voltage in mV. */
float battery_read_mv(void);

/* Is the battery above the minimum RUN threshold? */
bool battery_ok_for_run(void);

#endif /* BATTERY_H */