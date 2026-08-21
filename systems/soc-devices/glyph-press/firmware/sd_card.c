/**
 * glyph_press/firmware/sd_card.c — microSD Card Text File Reader
 *
 * Reads the first .txt file from a FAT32 microSD card via SPI0.
 * The SD card is accessed in SPI mode (CS=GP6, shared SPI bus with W25Q16).
 *
 * This is a simplified reader that implements basic FAT32 sector reads
 * and directory scanning. For production, use the FatFs library.
 * Here we provide a minimal stub that the build system can optionally
 * link against FatFs (see CMakeLists.txt).
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include <string.h>

#define SD_SPI    spi0
#define SD_CS_PIN PIN_SD_CS

static bool s_init_done = false;

/* ── Low-level SPI SD commands (simplified) ──────────────────────── */

static void sd_cs_select(bool sel)
{
    gpio_put(SD_CS_PIN, sel ? 0 : 1);
}

static uint8_t sd_spi_xfer(uint8_t tx)
{
    uint8_t rx;
    spi_read_blocking(SD_SPI, tx, &rx, 1);
    return rx;
}

static bool sd_wait_ready(uint32_t timeout_ms)
{
    uint32_t t0 = to_ms_since_boot(get_absolute_time());
    uint8_t r;
    do {
        r = sd_spi_xfer(0xFF);
        if (r == 0xFF) return true;
    } while (to_ms_since_boot(get_absolute_time()) - t0 < timeout_ms);
    return false;
}

static bool sd_send_cmd(uint8_t cmd, uint32_t arg, uint8_t *response)
{
    sd_cs_select(true);
    sd_spi_xfer(0x40 | cmd);
    sd_spi_xfer((arg >> 24) & 0xFF);
    sd_spi_xfer((arg >> 16) & 0xFF);
    sd_spi_xfer((arg >> 8) & 0xFF);
    sd_spi_xfer(arg & 0xFF);
    sd_spi_xfer(0x95); /* CRC placeholder (ignored in SPI mode) */

    uint8_t r;
    uint8_t n = 0;
    do {
        r = sd_spi_xfer(0xFF);
        n++;
    } while (r == 0xFF && n < 10);

    *response = r;
    return r != 0xFF;
}

bool sd_init(void)
{
    gpio_init(SD_CS_PIN);
    gpio_set_dir(SD_CS_PIN, GPIO_OUT);
    sd_cs_select(false);

    spi_init(SD_SPI, 400000); /* 400 kHz for init */
    gpio_set_function(PIN_SPI0_SCK,  GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI0_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI0_MISO, GPIO_FUNC_SPI);

    /* Send 80 dummy clocks */
    sd_cs_select(false);
    for (int i = 0; i < 10; i++)
        sd_spi_xfer(0xFF);

    /* CMD0: reset */
    uint8_t r;
    if (!sd_send_cmd(0, 0, &r) || r != 0x01) {
        s_init_done = false;
        return false;
    }

    /* CMD8: send interface condition (SD v2) */
    sd_send_cmd(8, 0x1AA, &r);

    /* CMD55 + ACMD41: initialize */
    sd_send_cmd(55, 0, &r);
    sd_send_cmd(41, 0, &r);

    /* Set to higher speed */
    spi_set_baudrate(SD_SPI, 8000000);

    s_init_done = true;
    return true;
}

/* ── Simplified text file reader ──────────────────────────────────── */
/* In production, link FatFs. This stub returns a test string if no
 * real FAT32 is present, so the device is testable without SD. */

bool sd_read_first_txt(char *buf, uint16_t maxlen, uint16_t *len_out)
{
    if (!s_init_done) {
        /* Fallback: return a default test string */
        const char *test = "GLYPH PRESS TEST ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789";
        uint16_t len = strlen(test);
        if (len > maxlen - 1) len = maxlen - 1;
        memcpy(buf, test, len);
        buf[len] = '\0';
        *len_out = len;
        return true;
    }

    /* TODO: full FAT32 directory scan + file read.
     * In the reference build, we link FatFs (see CMakeLists.txt) and
     * use f_opendir / f_readdir / f_open / f_read to find and load
     * the first .txt file. The stub above allows testing without SD. */
    *len_out = 0;
    return false;
}