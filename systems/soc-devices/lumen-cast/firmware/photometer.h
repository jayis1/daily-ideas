/**
 * lumen_cast/firmware/photometer.h — OPT3001 illuminance sensor
 */
#ifndef LUMEN_CAST_PHOTOMETER_H
#define LUMEN_CAST_PHOTOMETER_H

int opt3001_init(void);
int opt3001_read_lux(float *lux);

#endif