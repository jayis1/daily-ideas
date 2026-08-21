/* flash_log.c — littlefs-backed session logging to W25Q128 SPI flash.
 * Each session is a CSV file in /sessions. The flash is 16 MB and
 * holds roughly 36 hours of 1 Hz data.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "flash_log.h"
#include <stdio.h>
#include <string.h>

extern SPI_HandleTypeDef hspi1;

static int log_enabled = 0;
static uint32_t session_id = 0;

/* The W25Q128 is driven in SPI1 (PB3/PB4/PB5/PB6). Full littlefs
 * integration is beyond this stub; we use a simple sector-based
 * append log. Each 4 KB sector holds ~180 records. A session is
 * a sequence of sectors. */

#define SECTOR_SIZE 4096
#define LOG_BASE   0x000000

static uint32_t write_addr = LOG_BASE;

static void w25_cs(int on)
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, on ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

static void w25_write_enable(void)
{
    uint8_t cmd = 0x06;
    w25_cs(1);
    HAL_SPI_Transmit(&hspi1, &cmd, 1, 100);
    w25_cs(0);
}

static void w25_wait_busy(void)
{
    uint8_t cmd = 0x05;  /* read status */
    uint8_t st = 0;
    do {
        w25_cs(1);
        HAL_SPI_Transmit(&hspi1, &cmd, 1, 100);
        HAL_SPI_Receive(&hspi1, &st, 1, 100);
        w25_cs(0);
    } while (st & 0x01);
}

static void w25_sector_erase(uint32_t addr)
{
    w25_write_enable();
    uint8_t cmd[4] = { 0x20, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF };
    w25_cs(1);
    HAL_SPI_Transmit(&hspi1, cmd, 4, 100);
    w25_cs(0);
    w25_wait_busy();
}

static void w25_page_program(uint32_t addr, const uint8_t *data, int len)
{
    w25_write_enable();
    uint8_t cmd[4] = { 0x02, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF };
    w25_cs(1);
    HAL_SPI_Transmit(&hspi1, cmd, 4, 100);
    HAL_SPI_Transmit(&hspi1, (uint8_t *)data, len, 500);
    w25_cs(0);
    w25_wait_busy();
}

void log_init(void)
{
    /* Erase first 256 sectors (1 MB) for new session */
    for (int s = 0; s < 256; s++) {
        w25_sector_erase(LOG_BASE + s * SECTOR_SIZE);
    }
    write_addr = LOG_BASE;
    session_id++;
}

void log_start(void)
{
    log_init();
    log_enabled = 1;
}

void log_stop(void)
{
    log_enabled = 0;
}

void log_append(const log_record_t *rec)
{
    if (!log_enabled) return;
    char line[128];
    int n = snprintf(line, sizeof(line),
        "%lu,%.2f,%.2f,%.2f,%.2f,%.0f,%u,%.3f,%.2f,%.2f,%d,%d\r\n",
        rec->ts_ms, rec->dew_c, rec->rh_pct, rec->ah_gm3, rec->w_gkg,
        rec->pressure_pa, rec->co2_ppm, rec->mirror_c, rec->tec_i,
        rec->tec_v, rec->phase, rec->state);

    /* Program up to 256 bytes per page */
    if (write_addr + n > LOG_FLASH_SIZE) return;
    w25_page_program(write_addr, (uint8_t *)line, n);
    write_addr += n;
}

uint32_t log_session_id(void)
{
    return session_id;
}