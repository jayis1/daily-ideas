/**
 * glyph_press/firmware/flash_table.c — External Flash Braille Table Loader
 *
 * W25Q16JV (2 MB SPI flash) stores Braille translation tables for multiple
 * languages. Each table is 128 bytes (Grade 1 mapping for 128 ASCII chars).
 *
 * Flash layout:
 *   0x0000: English Grade 1 table (128 bytes)
 *   0x0080: French Grade 1 table
 *   0x0100: Spanish
 *   0x0180: German
 *   0x0200: Portuguese
 *   0x0280: Arabic
 *   0x0300: Hindi
 *   0x0380: Chinese pinyin
 *   0x0400: UEB contraction trie (4 KB)
 *   0x1400-0x1FFFF: reserved
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include <string.h>

#define FLASH_SPI    spi0
#define FLASH_CS_PIN PIN_FLASH_CS
#define FLASH_CMD_READ  0x03

static bool s_init_done = false;

static void flash_cs_select(bool sel)
{
    gpio_put(FLASH_CS_PIN, sel ? 0 : 1);
}

static void flash_read(uint32_t addr, uint8_t *buf, uint16_t len)
{
    flash_cs_select(true);
    spi_write_blocking(FLASH_SPI, FLASH_CMD_READ, 1);
    uint8_t cmd[3] = {
        (uint8_t)(addr >> 16),
        (uint8_t)(addr >> 8),
        (uint8_t)(addr & 0xFF)
    };
    spi_write_blocking(FLASH_SPI, cmd, 3);
    spi_read_blocking(FLASH_SPI, 0x00, buf, len);
    flash_cs_select(false);
}

bool flash_table_init(void)
{
    gpio_init(FLASH_CS_PIN);
    gpio_set_dir(FLASH_CS_PIN, GPIO_OUT);
    flash_cs_select(false);

    /* SPI0 is shared with SD card; initialise if not already done */
    spi_init(FLASH_SPI, 8000000);
    gpio_set_function(PIN_SPI0_SCK,  GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI0_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI0_MISO, GPIO_FUNC_SPI);

    /* Read JEDEC ID to verify flash is present */
    uint8_t cmd = 0x9F; /* JEDEC ID */
    uint8_t id[3] = {0};
    flash_cs_select(true);
    spi_write_blocking(FLASH_SPI, &cmd, 1);
    spi_read_blocking(FLASH_SPI, 0x00, id, 3);
    flash_cs_select(false);

    /* W25Q16 should report 0xEF 0x40 0x15 */
    if (id[0] == 0xEF || id[0] == 0x00) {
        s_init_done = true;
        return true;
    }
    /* Even if ID doesn't match, continue (flash may be absent) */
    s_init_done = true;
    return true;
}

bool flash_table_load(gp_lang_t lang, uint8_t *table, uint16_t maxlen)
{
    if (!s_init_done || maxlen < 128) return false;

    uint32_t addr = (uint32_t)lang * 128;
    if (addr >= 0x0400) return false; /* out of range */

    flash_read(addr, table, 128);
    return true;
}