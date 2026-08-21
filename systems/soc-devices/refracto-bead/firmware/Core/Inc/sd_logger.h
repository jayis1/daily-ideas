/**
 * sd_logger.h — microSD card CSV logging (SPI + FatFS)
 */
#ifndef SD_LOGGER_H
#define SD_LOGGER_H

#include "stm32g4xx_hal.h"
#include "refract_calc.h"

void sd_logger_init(SPI_HandleTypeDef *hspi);
void sd_logger_write(const ri_result_t *result);

#endif /* SD_LOGGER_H */