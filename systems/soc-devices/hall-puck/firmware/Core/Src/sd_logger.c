/*
 * hall-puck / firmware / Core / Src / sd_logger.c
 * MicroSD FAT32 CSV logging (SPI2)
 *
 * MIT License.
 */
#include "sd_logger.h"
#include "main.h"
#include "vdp_switch.h"
#include <stdio.h>
#include <string.h>

extern SPI_HandleTypeDef hspi2;

static bool sd_mounted = false;
static char current_filename[32] = "";

/* SD card commands (SPI mode, simplified) */
#define SD_CMD0    0
#define SD_CMD8    8
#define SD_CMD17   17
#define SD_CMD24   24
#define SD_CMD55   55
#define SD_ACMD41  41

static sd_err_t sd_send_command(uint8_t cmd, uint32_t arg, uint8_t *response)
{
    /* Simplified SD SPI protocol — production would use FATFS library */
    return SD_OK;
}

static void sd_cs_low(void)
{
    GPIOB->BSRR = (1 << SD_CS_PIN) << 16;
}

static void sd_cs_high(void)
{
    GPIOB->BSRR = (1 << SD_CS_PIN);
}

sd_err_t sd_logger_init(void)
{
    /* Configure SD_CS as output */
    GPIOB->MODER &= ~(3 << (SD_CS_PIN * 2));
    GPIOB->MODER |= (1 << (SD_CS_PIN * 2));
    sd_cs_high();

    /* In production: initialize FATFS filesystem */
    /* f_mount(&fatfs, "", 1) */
    sd_mounted = true;  /* Assume mounted for now */
    return SD_OK;
}

sd_err_t sd_logger_start(const meas_result_t *header, const meas_params_t *params)
{
    if (!sd_mounted) return SD_ERR_NOTMOUNTED;

    /* Generate filename: HP_YYYYMMDD_HHMMSS.csv */
    /* In production: use RTC or timestamp from ESP32-C3 */
    snprintf(current_filename, sizeof(current_filename),
             "HP_%06lu.csv", (unsigned long)(sys_tick_ms / 1000));

    /* Open file and write header (would use f_open + f_printf in FATFS) */
    /* Header lines:
     * # Hall Puck measurement log
     * # Date: ...
     * # Thickness: X mm
     * # Temperature: Y C
     * # B-field: Z T
     * # Current: I mA
     * # Columns: step, config, I_mA, V_uV, B_T, note
     */

    return SD_OK;
}

sd_err_t sd_logger_write_point(const meas_point_t *p, int idx)
{
    if (!sd_mounted) return SD_ERR_NOTMOUNTED;

    /* Write CSV line:
     * idx, config_name, current_mA, voltage_uV, b_field_T, note
     */
    const char *config_name = vdp_switch_config_name(p->config);

    /* In production: f_printf(&file, "%d,%s,%.3f,%.2f,%.4f,\n",
     *                        idx, config_name, p->current_ma,
     *                        p->voltage_uv, p->b_field_t); */
    (void)config_name;
    (void)idx;

    return SD_OK;
}

sd_err_t sd_logger_write_result(const meas_result_t *r)
{
    if (!sd_mounted) return SD_ERR_NOTMOUNTED;

    /* Write result summary:
     * # Result: Rs=X, RH=Y, n=Z, mu=W, type=n/p
     */

    return SD_OK;
}

sd_err_t sd_logger_close(void)
{
    if (!sd_mounted) return SD_ERR_NOTMOUNTED;
    /* f_close(&file) */
    return SD_OK;
}

bool sd_logger_is_mounted(void)
{
    return sd_mounted;
}

const char *sd_logger_last_filename(void)
{
    return current_filename;
}