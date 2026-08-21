/*
 * sensors.h — SHT40 (T/RH), TSL2591 (light), MAX17048 (fuel gauge) I2C drivers
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_SENSORS_H
#define ECHO_TRAP_SENSORS_H

void sensors_init(void);
void sensors_read_all(float *temp_c, float *humidity_pct,
                      float *light_lux, uint8_t *battery_pct);

#endif /* ECHO_TRAP_SENSORS_H */