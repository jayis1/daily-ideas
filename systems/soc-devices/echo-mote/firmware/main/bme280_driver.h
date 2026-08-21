/**
 * bme280_driver.h — BME280 temperature/humidity/pressure sensor driver (I²C)
 */

#ifndef BME280_DRIVER_H
#define BME280_DRIVER_H

/**
 * Initialize BME280 on I²C bus (address 0x76).
 */
int bme280_init(void);

/**
 * Read temperature, humidity, and pressure.
 *
 * @param temp  Output: temperature in °C
 * @param hum   Output: relative humidity in %
 * @param pres  Output: pressure in hPa
 * @return 0 on success
 */
int bme280_read(float *temp, float *hum, float *pres);

#endif /* BME280_DRIVER_H */