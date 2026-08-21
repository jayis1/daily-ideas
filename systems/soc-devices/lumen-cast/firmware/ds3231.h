/**
 * lumen_cast/firmware/ds3231.h — DS3231 RTC driver
 */
#ifndef LUMEN_CAST_DS3231_H
#define LUMEN_CAST_DS3231_H

int ds3231_init(void);
int ds3231_get_time(uint32_t *epoch);
int ds3231_set_time(uint32_t epoch);

#endif