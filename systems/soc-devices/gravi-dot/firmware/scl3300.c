/**
 * scl3300.c — SCL3300-D01 SPI inclinometer driver
 *
 * The SCL3300 uses a command-response SPI protocol: send a 4-byte
 * command, then read 4 bytes on the next transfer. Each read returns
 * a status word + data. Tilt angles are computed from acceleration
 * axes: tilt_x = atan(acc_y / acc_z), tilt_y = atan(acc_x / acc_z).
 */

#include "scl3300.h"
#include <math.h>

#define SCL3300_CS_PORT  GPIOB
#define SCL3300_CS_PIN   GPIO_PIN_0

static void cs_low(void)  { HAL_GPIO_WritePin(SCL3300_CS_PORT, SCL3300_CS_PIN, GPIO_PIN_RESET); }
static void cs_high(void) { HAL_GPIO_WritePin(SCL3300_CS_PORT, SCL3300_CS_PIN, GPIO_PIN_SET); }

/* CRC-4 lookup for SCL3300 (used in 4-bit CRC of each byte) */
static uint8_t crc4(uint8_t *data)
{
    uint8_t crc = 0x0F;
    for (int i = 0; i < 3; i++) {
        crc = crc ^ data[i];
        for (int b = 0; b < 8; b++) {
            if (crc & 0x08) crc = (crc << 1) ^ 0x03;
            else            crc <<= 1;
            crc &= 0x0F;
        }
    }
    return (crc ^ data[3]) & 0x0F;
}

static void spi_write_cmd(SPI_HandleTypeDef *spi, uint16_t cmd)
{
    uint8_t tx[4] = { (cmd >> 8) & 0xFF, cmd & 0xFF, 0x00, 0x00 };
    /* pad with appropriate CRC bits (simplified) */
    cs_low();
    HAL_SPI_Transmit(spi, tx, 4, 10);
    cs_high();
}

static int spi_read4(SPI_HandleTypeDef *spi, uint8_t *rx)
{
    uint8_t tx[4] = {0, 0, 0, 0};
    cs_low();
    HAL_StatusTypeDef st = HAL_SPI_TransmitReceive(spi, tx, rx, 4, 10);
    cs_high();
    return (st == HAL_OK) ? SCL3300_OK : SCL3300_ERR;
}

int scl3300_init(SPI_HandleTypeDef *spi)
{
    /* Power mode 4 (low-noise, tilt mode) */
    spi_write_cmd(spi, 0x2413);  /* Set Power Mode */
    HAL_Delay(1);
    spi_write_cmd(spi, 0xB1E2);  /* Enable angle output */
    HAL_Delay(1);
    return SCL3300_OK;
}

int scl3300_read_tilt(SPI_HandleTypeDef *spi, float *tilt_x_deg, float *tilt_y_deg)
{
    /* Read axis X (cmd 0x1004), Y (0x2005), Z (0x3006) */
    /* Each read is a two-step: send read command, then NOP to get data */
    int32_t ax = 0, ay = 0, az = 0;

    spi_write_cmd(spi, 0x1004);
    uint8_t rx[4];
    spi_read4(spi, rx);
    ax = ((int16_t)((rx[1] << 8) | rx[0])) >> 2;  /* 14-bit signed */

    spi_write_cmd(spi, 0x2005);
    spi_read4(spi, rx);
    ay = ((int16_t)((rx[1] << 8) | rx[0])) >> 2;

    spi_write_cmd(spi, 0x3006);
    spi_read4(spi, rx);
    az = ((int16_t)((rx[1] << 8) | rx[0])) >> 2;

    /* Scale: SCL3300 outputs at ±1g range, sensitivity ~6000 LSB/g */
    double gx = (double)ax / 6000.0;
    double gy = (double)ay / 6000.0;
    double gz = (double)az / 6000.0;

    /* Tilt angles in degrees */
    if (fabs(gz) < 0.01) gz = 0.01;  /* avoid div-by-zero */
    *tilt_x_deg = (float)(atan(gy / gz) * 180.0 / M_PI);
    *tilt_y_deg = (float)(atan(gx / gz) * 180.0 / M_PI);

    return SCL3300_OK;
}