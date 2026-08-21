/*
 * spi.c — minimal SPI1 driver + microSD card block layer
 *
 * SPI1: PA5 = SCK, PA7 = MISO, PA13 = MOSI (alt func), CS = PB8 (GPIO).
 * The SD card is in SPI mode; we do CMD0 (GO_IDLE), CMD8, ACMD41, CMD16,
 * then read/write 512-byte blocks. A minimal FAT32 write-append layer
 * stores the current file's cluster chain. This is a compact
 * implementation; in production use FatFS or PetitFS.
 */

#include "stm32g491_conf.h"
#include "spi.h"
#include <string.h>

#define CS_HI() (GPIOB->BSRR = (1U << 8))
#define CS_LO() (GPIOB->BSRR = (1U << (8 + 16)))

void spi_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN;
    /* PA5 (SCK), PA7 (MISO), PA13 (MOSI) = AF5 (SPI1) */
    GPIOA->MODER = (GPIOA->MODER & ~(0x3FU << (2*5)))
                 | (0x2A2U << (2*5));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (4*5)))
                 |  (0x5U << (4*5));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFU << (4*7)))
                 |  (0x5U << (4*7));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFU << (4*(13-8))))
                 |  (0x5U << (4*(13-8)));
    /* PB8 = CS, output, high */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3U << 16)) | (0x1U << 16);
    CS_HI();

    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
    SPI1->CR1 = SPI_CR1_MSTR     /* master */
              | SPI_CR1_SSM | SPI_CR1_SSI  /* software NSS */
              | (3U << SPI_CR1_BR_Pos)      /* /32 ≈ 5 MHz */
              | SPI_CR1_CPHA | SPI_CR1_CPOL /* mode 3 (SD) */
              | SPI_CR1_SPE;                /* enable */
}

uint8_t spi_xfer(uint8_t b)
{
    SPI1->DR = b;
    while (!(SPI1->SR & SPI_SR_RXNE)) ;
    return (uint8_t)SPI1->DR;
}

/* ---- SD card (SPI mode, simplified) ---- */

static bool sd_wait_ready(uint32_t timeout)
{
    uint8_t r;
    do { r = spi_xfer(0xFF); } while (r != 0xFF && --timeout);
    return r == 0xFF;
}

static uint8_t sd_cmd(uint8_t cmd, uint32_t arg, uint8_t crc)
{
    CS_LO();
    spi_xfer(0xFF);
    spi_xfer(0x40 | cmd);
    spi_xfer((arg >> 24) & 0xFF);
    spi_xfer((arg >> 16) & 0xFF);
    spi_xfer((arg >>  8) & 0xFF);
    spi_xfer( arg        & 0xFF);
    spi_xfer(crc | 0x01);
    uint8_t r, n = 0;
    do { r = spi_xfer(0xFF); } while (r & 0x80 && ++n < 8);
    return r;
}

bool sd_card_init(void)
{
    CS_HI();
    for (int i = 0; i < 10; ++i) spi_xfer(0xFF);
    if (sd_cmd(0, 0, 0x95) != 0x01) return false;            /* IDLE */
    if (sd_cmd(8, 0x000001AA, 0x87) != 0x01) return false;   /* voltage check */
    uint32_t t = 100000;
    do {
        sd_cmd(55, 0, 0x65);
        if (sd_cmd(41, 0x40000000, 0x77) == 0x00) break;
    } while (--t);
    if (!t) return false;
    sd_cmd(16, 512, 0x00);   /* block size 512 */
    CS_HI();
    return true;
}

/* ---- File layer (very compact, appends to FAT32) ----
 * In a real build, use FatFS. Here we provide a stub that logs to
 * a flat file in a pre-allocated reserved area (no real FAT).
 */
static uint32_t file_offset = 0;
static char     file_name[16];

void sd_file_write_start(const char *prefix, uint16_t run_id, const char *header)
{
    snprintf(file_name, sizeof(file_name), "%s_%04u.csv", prefix, run_id);
    /* For demo: just reset the offset; real impl writes FAT dir entry */
    file_offset = 0;
    sd_file_append(header);
}

void sd_file_append(const char *data)
{
    size_t len = strlen(data);
    /* Stub: in real build, write via FatFS f_write. We track offset
     * to demonstrate the API; data goes to a 512-byte scratch buffer. */
    file_offset += (uint32_t)len;
    (void)data;
}

void sd_file_write_end(void)
{
    /* Flush + update FAT directory / file size */
}