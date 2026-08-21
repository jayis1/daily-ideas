/**
 * lumen_cast/firmware/flashlog.c — W25Q128 SPI flash scan logging
 *
 * Winbond W25Q128JVIQ: 16 MB SPI flash, 4 KB sectors, 64 KB blocks.
 *
 * Flash layout:
 *   0x000000: Header (magic, scan count, calibration factor)
 *   0x001000: Scan records (1024 × 512 bytes = 512 KB)
 *   0x080000: Raw scan data archive (15 MB)
 *
 * Each scan record stores the photo_result_t + scan_config_t.
 * Raw angular data (photo_sample_t array) is stored separately.
 *
 * The calibration factor is stored in the header and preserved across
 * power cycles.
 */

#include "main.h"
#include <string.h>

#define TAG "FLASH"

#define FLASH_MAGIC        0x4C434154  /* "LCAT" */
#define FLASH_HEADER_ADDR  0x000000
#define FLASH_RECORD_ADDR  0x001000
#define FLASH_RAW_ADDR     0x080000
#define MAX_SCANS          1024
#define RECORD_SIZE        512

/* W25Q128 commands */
#define W25Q_CMD_READ      0x03
#define W25Q_CMD_READ_ID   0x9F
#define W25Q_CMD_WREN      0x06
#define W25Q_CMD_PP        0x02   /* page program */
#define W25Q_CMD_SE        0x20   /* sector erase 4K */
#define W25Q_CMD_RDSR      0x05
#define W25Q_CMD_RST       0x66
#define W25Q_CMD_RST_EN    0x99

/* Flash header (stored at 0x000000) */
typedef struct {
    uint32_t magic;
    uint16_t scan_count;
    uint16_t reserved;
    float    cal_factor;
    uint8_t  padding[500];
} flash_header_t;

static flash_header_t s_header;

/* ── SPI2 low-level ────────────────────────────────────────────────── */

static void spi_cs_low(void)
{
    GPIOB->ODR &= ~(1 << PIN_FLASH_CS);
}

static void spi_cs_high(void)
{
    GPIOB->ODR |= (1 << PIN_FLASH_CS);
}

static uint8_t spi_xfer(uint8_t tx)
{
    SPI2->DR = tx;
    while (!(SPI2->SR & SPI_SR_RXNE));
    return (uint8_t)SPI2->DR;
}

static void spi_read(uint8_t *buf, uint32_t addr, uint32_t len)
{
    spi_cs_low();
    spi_xfer(W25Q_CMD_READ);
    spi_xfer((addr >> 16) & 0xFF);
    spi_xfer((addr >> 8) & 0xFF);
    spi_xfer(addr & 0xFF);
    for (uint32_t i = 0; i < len; i++)
        buf[i] = spi_xfer(0x00);
    spi_cs_high();
}

static void spi_write_enable(void)
{
    spi_cs_low();
    spi_xfer(W25Q_CMD_WREN);
    spi_cs_high();
}

static void spi_wait_busy(void)
{
    uint8_t status;
    do {
        spi_cs_low();
        spi_xfer(W25Q_CMD_RDSR);
        status = spi_xfer(0x00);
        spi_cs_high();
    } while (status & 0x01);  /* WIP bit */
}

static void spi_page_program(uint32_t addr, const uint8_t *data, uint32_t len)
{
    if (len > 256) len = 256;  /* page size = 256 bytes */
    spi_write_enable();
    spi_cs_low();
    spi_xfer(W25Q_CMD_PP);
    spi_xfer((addr >> 16) & 0xFF);
    spi_xfer((addr >> 8) & 0xFF);
    spi_xfer(addr & 0xFF);
    for (uint32_t i = 0; i < len; i++)
        spi_xfer(data[i]);
    spi_cs_high();
    spi_wait_busy();
}

static void spi_sector_erase(uint32_t addr)
{
    spi_write_enable();
    spi_cs_low();
    spi_xfer(W25Q_CMD_SE);
    spi_xfer((addr >> 16) & 0xFF);
    spi_xfer((addr >> 8) & 0xFF);
    spi_xfer(addr & 0xFF);
    spi_cs_high();
    spi_wait_busy();
}

/* ── Public API ────────────────────────────────────────────────────── */

int flashlog_init(void)
{
    /* Verify flash ID (W25Q128 = 0xEF4018) */
    spi_cs_low();
    spi_xfer(W25Q_CMD_READ_ID);
    uint8_t id[3];
    id[0] = spi_xfer(0);
    id[1] = spi_xfer(0);
    id[2] = spi_xfer(0);
    spi_cs_high();

    if (id[0] != 0xEF || id[1] != 0x40 || id[2] != 0x18) {
        LOGE(TAG, "W25Q128 not found (ID: %02X %02X %02X)", id[0], id[1], id[2]);
        return -1;
    }
    LOGI(TAG, "W25Q128 detected (16 MB)");

    /* Read header */
    spi_read((uint8_t *)&s_header, FLASH_HEADER_ADDR, sizeof(s_header));

    if (s_header.magic != FLASH_MAGIC) {
        LOGW(TAG, "Flash not formatted — initializing");
        memset(&s_header, 0, sizeof(s_header));
        s_header.magic = FLASH_MAGIC;
        s_header.scan_count = 0;
        s_header.cal_factor = 1.0f;
        spi_sector_erase(FLASH_HEADER_ADDR);
        spi_page_program(FLASH_HEADER_ADDR, (uint8_t *)&s_header,
                         sizeof(s_header));
    }

    LOGI(TAG, "Flash: %d scans, cal=%.4f", s_header.scan_count, s_header.cal_factor);
    return 0;
}

float flashlog_load_cal_factor(void)
{
    return s_header.cal_factor;
}

static void flashlog_save_header(void)
{
    spi_sector_erase(FLASH_HEADER_ADDR);
    spi_page_program(FLASH_HEADER_ADDR, (uint8_t *)&s_header,
                     sizeof(s_header));
}

int flashlog_write_scan(const photo_result_t *r, const scan_buffer_t *s)
{
    if (s_header.scan_count >= MAX_SCANS) {
        LOGE(TAG, "Flash full (%d scans)", MAX_SCANS);
        return -1;
    }

    uint16_t id = s_header.scan_count;
    uint32_t rec_addr = FLASH_RECORD_ADDR + id * RECORD_SIZE;

    /* Pack result + config into 512-byte record */
    uint8_t record[RECORD_SIZE];
    memset(record, 0, sizeof(record));
    memcpy(record, r, sizeof(photo_result_t));
    memcpy(record + 256, &s->config, sizeof(scan_config_t));

    spi_sector_erase(rec_addr);
    /* Page program in 256-byte chunks */
    spi_page_program(rec_addr, record, 256);
    spi_page_program(rec_addr + 256, record + 256, 256);

    /* Store raw samples in raw area */
    uint32_t raw_addr = FLASH_RAW_ADDR + id * (MAX_SAMPLES_TOTAL * sizeof(photo_sample_t));
    if (raw_addr + s->n_samples * sizeof(photo_sample_t) < 0x1000000) {
        uint32_t offset = 0;
        while (offset < s->n_samples * sizeof(photo_sample_t)) {
            uint32_t chunk = s->n_samples * sizeof(photo_sample_t) - offset;
            if (chunk > 256) chunk = 256;
            spi_page_program(raw_addr + offset,
                             (uint8_t *)&s->samples[0] + offset, chunk);
            offset += chunk;
        }
    }

    s_header.scan_count++;
    flashlog_save_header();

    LOGI(TAG, "Scan %d logged to flash", id);
    return 0;
}

int flashlog_read_scan(uint16_t id, photo_result_t *r)
{
    if (id >= s_header.scan_count) return -1;
    uint32_t addr = FLASH_RECORD_ADDR + id * RECORD_SIZE;
    spi_read((uint8_t *)r, addr, sizeof(photo_result_t));
    return 0;
}

uint16_t flashlog_get_count(void)
{
    return s_header.scan_count;
}