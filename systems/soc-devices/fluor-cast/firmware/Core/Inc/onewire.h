/*
 * onewire.h — DS18B20 1-wire temperature sensor driver
 */

#ifndef ONEWIRE_H
#define ONEWIRE_H

#include <stdint.h>

/**
 * Initialize 1-wire bus.
 */
void ow_init(void);

/**
 * Reset bus and detect presence of devices.
 * @return 1 if device present, 0 if not
 */
int ow_reset(void);

/**
 * Write one bit to bus.
 */
void ow_write_bit(int bit);

/**
 * Read one bit from bus.
 */
int ow_read_bit(void);

/**
 * Write one byte.
 */
void ow_write_byte(uint8_t byte);

/**
 * Read one byte.
 */
uint8_t ow_read_byte(void);

/**
 * Start temperature conversion on all devices.
 * @return 0 on success
 */
int ds18b20_start_conversion(void);

/**
 * Read temperature from DS18B20.
 * @param temp_c  Output temperature in °C
 * @return 0 on success, -1 on error
 */
int ds18b20_read_temp(float *temp_c);

/**
 * Get temperature with blocking conversion (takes ~750 ms).
 */
int ds18b20_read_temp_blocking(float *temp_c);

#endif /* ONEWIRE_H */