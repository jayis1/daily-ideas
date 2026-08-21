/**
 * adxl355.c — ADXL355 SPI driver implementation
 *
 * The ADXL355 outputs 20-bit data per axis in registers XDATA3..1.
 * For the Gravi Dot's 16-bit truncation path we read XDATA3 (upper 8)
 * and XDATA2 (mid 8), discarding XDATA1 (lower 4 bits). This gives
 * 64 LSB/g sensitivity at ±2g range (256 000 LSB/g full 20-bit).
 */

#include "adxl355.h"

static SPI_HandleTypeDef *s_spi = NULL;

static void spi_cs_low(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
}

static void spi_cs_high(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
}

static uint8_t spi_xfer(uint8_t tx)
{
    uint8_t rx = 0;
    HAL_SPI_TransmitReceive(s_spi, &tx, &rx, 1, 10);
    return rx;
}

int adxl355_init(SPI_HandleTypeDef *spi)
{
    s_spi = spi;

    /* Verify device ID */
    spi_cs_low();
    spi_xfer(ADXL355_READ(ADXL355_DEVID_AD));
    uint8_t devid = spi_xfer(0xFF);
    spi_cs_high();

    if (devid != 0xAD) return ADXL355_ERR;

    /* Software reset */
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_RESET));
    spi_xfer(0x52);  /* reset code */
    spi_cs_high();
    HAL_Delay(10);

    /* Standby mode (clear MEASURE bit) for configuration */
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_POWER_CTL));
    spi_xfer(0x00);
    spi_cs_high();

    /* Set filter: ODR 250 Hz, high-pass off (ODR field in FILTER reg)
     * FILTER[7:4] = HPF corner (0 = off), FILTER[3:0] = ODR */
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_FILTER));
    spi_xfer((uint8_t)ADXL355_ODR_250_HZ & 0x0F);
    spi_cs_high();

    /* Range ±2g */
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_RANGE));
    spi_xfer((uint8_t)ADXL355_RANGE_2G);
    spi_cs_high();

    /* Enter measurement mode */
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_POWER_CTL));
    spi_xfer(0x01);  /* MEASURE bit */
    spi_cs_high();

    HAL_Delay(20);  /* settle */
    return ADXL355_OK;
}

int adxl355_set_range(adxl355_range_t r)
{
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_POWER_CTL));
    spi_xfer(0x00);  /* standby */
    spi_cs_high();

    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_RANGE));
    spi_xfer((uint8_t)r);
    spi_cs_high();

    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_POWER_CTL));
    spi_xfer(0x01);  /* measure */
    spi_cs_high();
    return ADXL355_OK;
}

int adxl355_set_odr(adxl355_odr_t odr)
{
    spi_cs_low();
    spi_xfer(ADXL355_WRITE(ADXL355_FILTER));
    spi_xfer((uint8_t)odr & 0x0F);
    spi_cs_high();
    return ADXL355_OK;
}

int adxl355_read_xyz(SPI_HandleTypeDef *spi, int16_t *x, int16_t *y, int16_t *z)
{
    s_spi = spi;
    uint8_t buf[9];

    spi_cs_low();
    spi_xfer(ADXL355_READ(ADXL355_XDATA3));
    /* multi-byte read: XDATA3..ZDATA1 = 9 bytes */
    for (int i = 0; i < 9; i++)
        buf[i] = spi_xfer(0xFF);
    spi_cs_high();

    /* X: XDATA3 (bits 19:12), XDATA2 (bits 11:4) — we take upper 16 */
    int32_t x_raw = ((int32_t)buf[0] << 12) | ((int32_t)buf[1] << 4);
    int32_t y_raw = ((int32_t)buf[3] << 12) | ((int32_t)buf[4] << 4);
    int32_t z_raw = ((int32_t)buf[6] << 12) | ((int32_t)buf[7] << 4);

    /* Sign-extend from 20-bit (bits 19:0) */
    if (x_raw & 0x80000) x_raw |= 0xFFF00000;
    if (y_raw & 0x80000) y_raw |= 0xFFF00000;
    if (z_raw & 0x80000) z_raw |= 0xFFF00000;

    /* Truncate to 16-bit (upper 16 of 20 = shift right 4) */
    *x = (int16_t)(x_raw >> 4);
    *y = (int16_t)(y_raw >> 4);
    *z = (int16_t)(z_raw >> 4);

    return ADXL355_OK;
}

int adxl355_read_status(SPI_HandleTypeDef *spi, uint8_t *status)
{
    s_spi = spi;
    spi_cs_low();
    spi_xfer(ADXL355_READ(ADXL355_STATUS));
    *status = spi_xfer(0xFF);
    spi_cs_high();
    return ADXL355_OK;
}

int adxl355_read_temp(SPI_HandleTypeDef *spi, int16_t *temp_milli_c)
{
    s_spi = spi;
    spi_cs_low();
    spi_xfer(ADXL355_READ(ADXL355_TEMP2));
    uint8_t t2 = spi_xfer(0xFF);
    uint8_t t1 = spi_xfer(0xFF);
    spi_cs_high();

    int16_t raw = ((int16_t)t2 << 8) | (t1 & 0xF0);
    /* ADXL355 temp: raw = -1853 + (T_C × 9.05), approximate */
    *temp_milli_c = (int16_t)((raw + 1853) * 110);  /* rough milli-°C */
    return ADXL355_OK;
}