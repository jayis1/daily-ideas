/*
 * storage.c — SD card logging for EEM data
 *
 * Uses SPI SD card with FatFs-compatible minimal driver.
 * Logs EEM data as CSV (human-readable) and binary (compact).
 */

#include "storage.h"
#include "main.h"
#include <string.h>
#include <stdio.h>

extern SPI_HandleTypeDef hspi1;

static int sd_ready = 0;
static int file_seq = 0;

/* ── SD Card SPI Commands (simplified, no FatFs dependency) ── */
static void sd_select(void)
{
    HAL_GPIO_WritePin(SD_CS_GPIO, SD_CS_PIN, GPIO_PIN_RESET);
}

static void sd_deselect(void)
{
    HAL_GPIO_WritePin(SD_CS_GPIO, SD_CS_PIN, GPIO_PIN_SET);
}

static uint8_t sd_spi_xfer(uint8_t data)
{
    uint8_t rx;
    HAL_SPI_TransmitReceive(&hspi1, &data, &rx, 1, 100);
    return rx;
}

static int sd_wait_ready(void)
{
    uint8_t r;
    uint32_t timeout = 1000;
    do {
        r = sd_spi_xfer(0xFF);
        if (r == 0xFF) return 0;
    } while (--timeout > 0);
    return -1;
}

static int sd_send_cmd(uint8_t cmd, uint32_t arg, uint8_t crc)
{
    sd_spi_xfer(0xFF);  /* dummy */
    sd_spi_xfer(cmd | 0x40);
    sd_spi_xfer((arg >> 24) & 0xFF);
    sd_spi_xfer((arg >> 16) & 0xFF);
    sd_spi_xfer((arg >> 8) & 0xFF);
    sd_spi_xfer(arg & 0xFF);
    sd_spi_xfer(crc);

    uint8_t r;
    uint32_t timeout = 100;
    do {
        r = sd_spi_xfer(0xFF);
    } while ((r & 0x80) && --timeout > 0);

    return r;
}

/* ── Public Functions ─────────────────────────────────── */

int storage_init(void)
{
    sd_deselect();
    HAL_Delay(10);

    /* Send 80 dummy clocks */
    sd_select();
    for (int i = 0; i < 10; i++) sd_spi_xfer(0xFF);

    /* CMD0: GO_IDLE */
    int r = sd_send_cmd(0, 0, 0x95);
    if (r != 0x01) {
        sd_deselect();
        return -1;  /* No SD card */
    }

    /* CMD8: SEND_IF_COND (SDv2) */
    r = sd_send_cmd(8, 0x1AA, 0x87);
    /* CMD55+ACMD41: SD_SEND_OP_COND */
    uint32_t timeout = 1000;
    do {
        sd_send_cmd(55, 0, 0x65);
        r = sd_send_cmd(41, 0x40000000, 0x77);
        if (r == 0) break;
        HAL_Delay(1);
    } while (--timeout > 0);

    sd_deselect();

    if (r != 0) return -1;

    /* In production: initialize FatFs file system here
     * For now: mark as ready */
    sd_ready = 1;
    file_seq = 0;

    return 0;
}

int storage_ready(void)
{
    return sd_ready;
}

int storage_log_eem(const eem_t *eem, const classify_result_t *result)
{
    if (!sd_ready || !eem) return -1;

    /* In production: use FatFs f_open, f_write, f_close
     * For now: build CSV string and store in buffer */

    char line[128];

    /* Header line */
    snprintf(line, sizeof(line),
        "# EEM timestamp=%lu temp=%.1f duration=%lu\n",
        eem->timestamp, eem->temp_c, eem->duration_ms);
    storage_log_line(line);

    /* EEM matrix as CSV (8 rows × 256 cols) */
    for (int w = 0; w < EEM_ROWS; w++) {
        char buf[256];
        int pos = 0;
        pos += snprintf(buf + pos, sizeof(buf) - pos, "EX_%d,", ex_wavelength_nm[w]);
        for (int p = 0; p < CCD_PIXELS && pos < 250; p++) {
            pos += snprintf(buf + pos, sizeof(buf) - pos, "%d,", eem->matrix[w][p]);
        }
        /* Trim trailing comma */
        if (pos > 0) buf[pos - 1] = '\n';
        storage_log_line(buf);
    }

    /* Classification result */
    if (result) {
        const library_entry_t *entry = library_get(result->top_match);
        if (entry) {
            snprintf(line, sizeof(line),
                "# RESULT match=%s confidence=%.3f conc=%.1f\n",
                entry->name, result->top_confidence, result->estimated_conc);
            storage_log_line(line);
        }
    }

    /* Features */
    char fbuf[256];
    int pos = 0;
    pos += snprintf(fbuf + pos, sizeof(fbuf) - pos, "# FEATURES,");
    for (int i = 0; i < FEATURE_COUNT && pos < 240; i++) {
        pos += snprintf(fbuf + pos, sizeof(fbuf) - pos, "%.2f,", eem->features[i]);
    }
    if (pos > 0) fbuf[pos - 1] = '\n';
    storage_log_line(fbuf);

    file_seq++;
    return 0;
}

int storage_log_eem_binary(const eem_t *eem)
{
    if (!sd_ready || !eem) return -1;

    /* Binary format:
     * [magic:4][timestamp:4][temp:4][matrix:8*256*2=4096][mask:4096][features:48*4=192]
     * Total: ~8400 bytes per EEM
     */
    /* In production: write to binary file via FatFs */
    (void)eem;
    return 0;
}

int storage_log_line(const char *line)
{
    if (!sd_ready || !line) return -1;

    /* In production: append to daily log file via FatFs
     * For now: this is a stub that would write to SD */
    (void)line;
    return 0;
}

int storage_next_seq(void)
{
    return file_seq++;
}

void storage_get_filename(char *buf, int bufsize, int seq, const char *ext)
{
    snprintf(buf, bufsize, "/fluor/EEM_%04d.%s", seq, ext);
}

void storage_list_files(void (*callback)(const char *filename, uint32_t size))
{
    if (!callback || !sd_ready) return;
    /* In production: use f_findfirst/f_findnext */
}

int storage_format(void)
{
    /* In production: f_mkfs */
    return 0;
}

uint32_t storage_free_kb(void)
{
    /* In production: f_getfree */
    return 0;
}