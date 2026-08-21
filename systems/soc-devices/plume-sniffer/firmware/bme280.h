/* bme280.h — Ambient T/H/P sensor (I2C) for gas-density correction */
#ifndef BME280_H
#define BME280_H

typedef struct {
    float temp_c;
    float humidity_pct;
    float pressure_hpa;
} bme280_data_t;

void bme280_init(void);
bool bme280_read(bme280_data_t *out);

#endif /* BME280_H */