/*
 * battery.c — battery voltage monitor + low-charge gating
 */
#include "battery.h"
#include "adc.h"

float battery_read(void) { return adc_read_battery(); }
bool  battery_ok(void)  { return battery_read() > 3.5f; }
bool  battery_low(void) { return battery_read() < 3.4f; }