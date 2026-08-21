/*
 * Tremor Tile — RTC Manager Header
 * rtc_manager.h
 */

#ifndef TREMOR_TILE_RTC_MANAGER_H
#define TREMOR_TILE_RTC_MANAGER_H

#include <stdint.h>

typedef enum {
    ALARM_EVERY_SEC = 1,
    ALARM_EVERY_10_SEC = 10,
    ALARM_EVERY_MIN = 60,
    ALARM_EVERY_HOUR = 3600,
} alarm_period_t;

void rtc_manager_init(void);
int64_t rtc_manager_get_unix_time(void);
void rtc_manager_set_periodic(alarm_period_t period);

#endif // TREMOR_TILE_RTC_MANAGER_H