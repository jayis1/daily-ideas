/**
 * scl3300.h — Murata SCL3300-D01 precision inclinometer (SPI)
 */
#ifndef SCL3300_H
#define SCL3300_H

#include "stm32g4xx_hal.h"

#define SCL3300_OK    0
#define SCL3300_ERR  -1

int scl3300_init(SPI_HandleTypeDef *spi);
int scl3300_read_tilt(SPI_HandleTypeDef *spi, float *tilt_x_deg, float *tilt_y_deg);

#endif