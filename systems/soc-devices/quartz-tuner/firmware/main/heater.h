/*
 * heater.h — PID-controlled crystal heater + DS18B20 temperature sensor
 */

#ifndef QUARTZ_TUNER_HEATER_H
#define QUARTZ_TUNER_HEATER_H

void heater_init(void);
void heater_enable(bool enable);
void heater_set_target(float temp_c);
float heater_read_temp(void);

#endif