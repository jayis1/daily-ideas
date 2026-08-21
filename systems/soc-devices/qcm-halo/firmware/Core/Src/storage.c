/*
 * storage.c — SD card CSV logging + W25Q128 parameter storage
 */

#include "main.h"
#include <stdio.h>
#include <string.h>
#include "storage.h"

extern SPI_HandleTypeDef hspi3;

static uint8_t sd_present = 0;
static char current_logfile[32] = "";

/* ── W25Q128 SPI helpers ────────────────────────────────── */
extern SPI_HandleTypeDef hspi1;

static void flash_cs_low(void)  { HAL_GPIO_WritePin(FLASH_CS_PORT, FLASH_CS_PIN, GPIO_PIN_RESET); }
static void flash_cs_high(void) { HAL_GPIO_WritePin(FLASH_CS_PORT, FLASH_CS_PIN, GPIO_PIN_SET); }

static void flash_write_enable(void)
{
    flash_cs_low();
    uint8_t cmd = 0x06; /* WREN */
    HAL_SPI_Transmit(&hspi1, &cmd, 1, 100);
    flash_cs_high();
}

static void flash_wait_busy(void)
{
    flash_cs_low();
    uint8_t cmd = 0x05; /* RDSR */
    HAL_SPI_Transmit(&hspi1, &cmd, 1, 100);
    uint8_t status = 0;
    do {
        HAL_SPI_Receive(&hspi1, &status, 1, 100);
    } while (status & 0x01); /* WIP bit */
    flash_cs_high();
}

static void flash_erase_sector(uint32_t addr)
{
    flash_write_enable();
    flash_cs_low();
    uint8_t cmd[4] = {0x20, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    HAL_SPI_Transmit(&hspi1, cmd, 4, 100);
    flash_cs_high();
    flash_wait_busy();
}

static void flash_write_page(uint32_t addr, const uint8_t *data, uint16_t len)
{
    flash_write_enable();
    flash_cs_low();
    uint8_t cmd[4] = {0x02, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    HAL_SPI_Transmit(&hspi1, cmd, 4, 100);
    HAL_SPI_Transmit(&hspi1, (uint8_t *)data, len, 1000);
    flash_cs_high();
    flash_wait_busy();
}

static void flash_read(uint32_t addr, uint8_t *data, uint16_t len)
{
    flash_cs_low();
    uint8_t cmd[4] = {0x03, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    HAL_SPI_Transmit(&hspi1, cmd, 4, 100);
    HAL_SPI_Receive(&hspi1, data, len, 1000);
    flash_cs_high();
}

/* ── SD card (simplified — would use FatFs in full implementation) ── */

int storage_init(void)
{
    /* Check SD card presence (detect pin is active low) */
    sd_present = (HAL_GPIO_ReadPin(SD_DETECT_PORT, SD_DETECT_PIN) == GPIO_PIN_RESET) ? 1 : 0;

    /* In full implementation: f_mount() FatFs here */
    return 0;
}

int storage_is_present(void)
{
    return sd_present;
}

int storage_open_log(const char *filename)
{
    strncpy(current_logfile, filename, sizeof(current_logfile) - 1);
    /* In full implementation: f_open() here */
    return 0;
}

void result_to_csv(const qcm_result_t *r, char *buf, uint16_t len)
{
    snprintf(buf, len,
             "%lu,%d,%d,%.3f,%.3f,%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\n",
             (unsigned long)r->timestamp_ms,
             r->channel + 1,
             r->overtone_n,
             r->frequency,
             r->delta_f,
             r->dissipation,
             r->delta_d,
             r->temperature,
             r->sauerbrey_mass,
             r->sauerbrey_thick,
             r->voigt_thick,
             r->voigt_viscosity,
             r->voigt_shear_mod);
}

void sweep_to_csv(const overtone_sweep_t *s, char *buf, uint16_t len)
{
    /* Header + one line per overtone */
    int pos = snprintf(buf, len, "# Sweep t=%lu T=%.2f\n",
                       (unsigned long)s->timestamp, s->temperature);
    const char *labels[] = {"1st", "3rd", "5th", "7th", "9th", "11th"};
    for (uint8_t i = 0; i < QCM_OVERtones && pos < len; i++) {
        pos += snprintf(buf + pos, len - pos, "%s,%.3f,%.3f,%.6f\n",
                        labels[i], s->freq[i], s->delta_f[i], s->delta_d[i]);
    }
}

int storage_log_result(const qcm_result_t *r)
{
    if (!sd_present) return -1;

    char line[128];
    result_to_csv(r, line, sizeof(line));

    /* In full implementation: f_puts(line, &file) */
    /* For now, the data is also sent via BLE for live logging */
    return 0;
}

int storage_log_sweep(const overtone_sweep_t *s)
{
    if (!sd_present) return -1;

    char buf[256];
    sweep_to_csv(s, buf, sizeof(buf));

    /* In full implementation: f_puts(buf, &file) */
    return 0;
}

int storage_log_raw(const char *line)
{
    if (!sd_present) return -1;
    /* In full implementation: f_puts(line, &file) */
    (void)line;
    return 0;
}

void storage_close_log(void)
{
    /* In full implementation: f_close(&file) */
    current_logfile[0] = 0;
}

/* ── W25Q128 parameter storage ──────────────────────────── */

int storage_save_params(const acq_params_t *params)
{
    /* Erase sector 0 and write params */
    flash_erase_sector(PARAMS_FLASH_ADDR);

    /* Write magic + params */
    uint8_t buf[sizeof(acq_params_t) + 4];
    buf[0] = 'Q'; buf[1] = 'C'; buf[2] = 'M'; buf[3] = '1';
    memcpy(buf + 4, params, sizeof(acq_params_t));

    flash_write_page(PARAMS_FLASH_ADDR, buf, sizeof(buf));
    return 0;
}

int storage_load_params(acq_params_t *params)
{
    uint8_t buf[sizeof(acq_params_t) + 4];
    flash_read(PARAMS_FLASH_ADDR, buf, sizeof(buf));

    /* Check magic */
    if (buf[0] != 'Q' || buf[1] != 'C' || buf[2] != 'M' || buf[3] != '1') {
        return -1; /* no saved params */
    }

    memcpy(params, buf + 4, sizeof(acq_params_t));
    return 0;
}