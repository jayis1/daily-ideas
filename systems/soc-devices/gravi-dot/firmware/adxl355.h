/**
 * adxl355.h — Analog Devices ADXL355 ultra-low-noise 3-axis accelerometer
 *             SPI driver (truncated 16-bit mode for Gravi Dot)
 */
#ifndef ADXL355_H
#define ADXL355_H

#include "stm32g4xx_hal.h"

/* Register map (selected) */
#define ADXL355_DEVID_AD      0x00
#define ADXL355_DEVID_MST     0x01
#define ADXL355_PARTID        0x02
#define ADXL355_REVID         0x03
#define ADXL355_STATUS        0x04
#define ADXL355_FIFO_ENTRIES  0x05
#define ADXL355_TEMP2         0x06
#define ADXL355_TEMP1         0x07
#define ADXL355_XDATA3        0x08
#define ADXL355_XDATA2        0x09
#define ADXL355_XDATA1        0x0A
#define ADXL355_YDATA3        0x0B
#define ADXL355_YDATA2        0x0C
#define ADXL355_YDATA1        0x0D
#define ADXL355_ZDATA3        0x0E
#define ADXL355_ZDATA2        0x0F
#define ADXL355_ZDATA1        0x10
#define ADXL355_FILTER        0x38
#define ADXL355_FIFO_SAMPLES  0x39
#define ADXL355_INT_MAP       0x2A
#define ADXL355_SYNC          0x2B
#define ADXL355_RANGE         0x2C
#define ADXL355_POWER_CTL     0x2D
#define ADXL355_SELF_TEST     0x2E
#define ADXL355_RESET         0x2F

/* Read = register | 0x80 ; Write = register & 0x7F (MB bit 0x60 for multibyte) */
#define ADXL355_READ(reg)   ((reg) | 0x80)
#define ADXL355_WRITE(reg)  ((reg) & 0x7F)

/* Range options */
typedef enum {
    ADXL355_RANGE_2G = 0x00,
    ADXL355_RANGE_4G = 0x01,
    ADXL355_RANGE_8G = 0x02,
} adxl355_range_t;

/* ODR / filter settings (high-pass + low-pass) */
typedef enum {
    ADXL355_ODR_4000_HZ = 0x00,
    ADXL355_ODR_2000_HZ = 0x01,
    ADXL355_ODR_1000_HZ = 0x02,
    ADXL355_ODR_500_HZ  = 0x03,
    ADXL355_ODR_250_HZ  = 0x04,
    ADXL355_ODR_125_HZ  = 0x05,
    ADXL355_ODR_62_5_HZ = 0x06,
    ADXL355_ODR_31_25_HZ= 0x07,
} adxl355_odr_t;

#define ADXL355_OK    0
#define ADXL355_ERR  -1

typedef struct {
    SPI_HandleTypeDef *spi;
} adxl355_t;

/* API */
int  adxl355_init(SPI_HandleTypeDef *spi);
int  adxl355_set_range(adxl355_range_t r);
int  adxl355_set_odr(adxl355_odr_t odr);
int  adxl355_read_xyz(SPI_HandleTypeDef *spi, int16_t *x, int16_t *y, int16_t *z);
int  adxl355_read_status(SPI_HandleTypeDef *spi, uint8_t *status);
int  adxl355_read_temp(SPI_HandleTypeDef *spi, int16_t *temp_milli_c);

#endif /* ADXL355_H */