/**
 * ds18b20.h — DS18B20 1-Wire temperature sensor driver (prism temperature)
 *
 * The DS18B20 is bonded to the prism body for accurate sample temperature
 * measurement. Resolution is configured to 12-bit (0.0625°C).
 * Accuracy: ±0.1°C over the 0-50°C range.
 */

#ifndef DS18B20_H
#define DS18B20_H

#include "stm32g4xx_hal.h"

/**
 * Initialize the DS18B20 on the specified GPIO pin (1-Wire).
 * Configures 12-bit resolution (0.0625°C, 750ms conversion).
 */
void ds18b20_init(void);

/**
 * Trigger a temperature conversion and read the result.
 * @return Temperature in °C (returns -1000.0f on error)
 */
float ds18b20_read_temperature(void);

/**
 * Check if a DS18B20 is present on the bus.
 * @return 1 if present, 0 if not
 */
uint8_t ds18b20_is_present(void);

#endif /* DS18B20_H */