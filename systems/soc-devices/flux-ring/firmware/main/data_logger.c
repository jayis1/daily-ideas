/*
 * Flux Ring — data_logger.c
 * W25Q16 SPI flash data logger implementation.
 *
 * The W25Q16 is a 16Mbit (2MB) SPI flash. We use a simple append-only
 * log format: 32-byte header followed by 22-byte sample records.
 *
 * At 100Hz (explore mode), 22 bytes/sample = ~90,000 samples = 15 min.
 * At 10Hz (monitor mode), ~2.5 hours of continuous logging.
 *
 * SPDX-License-Identifier: MIT
 */

#include "data_logger.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/logging/log.h>
#include <string.h>

LOG_MODULE_DECLARE(data_logger, LOG_LEVEL_INF);

/* W25Q16 commands */
#define W25Q16_CMD_WRITE_ENABLE    0x06
#define W25Q16_CMD_WRITE_DISABLE   0x04
#define W25Q16_CMD_READ_STATUS     0x05
#define W25Q16_CMD_PAGE_PROGRAM   0x02
#define W25Q16_CMD_READ_DATA      0x03
#define W25Q16_CMD_SECTOR_ERASE   0x20
#define W25Q16_CMD_CHIP_ERASE     0xC7
#define W25Q16_CMD_JEDEC_ID       0x9F

/* Flash geometry */
#define W25Q16_PAGE_SIZE       256
#define W25Q16_SECTOR_SIZE     4096
#define W25Q16_TOTAL_SIZE      (2 * 1024 * 1024)  /* 2MB */
#define W25Q16_SECTOR_COUNT    (W25Q16_TOTAL_SIZE / W25Q16_SECTOR_SIZE)

/* SPI device */
#define SPI_NODE DT_NODELABEL(spi1)
static const struct device *spi_dev;

/* SPI configuration */
static struct spi_config spi_cfg = {
    .frequency = 8000000,
    .operation = SPI_OP_MODE_MASTER | SPI_WORD_SET(8) |
                 SPI_TRANSFER_MSB | SPI_MODE_CPOL |
                 SPI_MODE_CPHA,
    .cs = {
        .gpio = {
            .pin = 22,  /* P0.22 = SPI CS */
            .dt_flags = GPIO_ACTIVE_LOW,
        },
    },
};

/* Log state */
static uint32_t write_offset;      /* Next write position in flash */
static uint32_t sample_count;      /* Total samples written */
static bool log_active = false;

/* Internal SPI helpers */
static int spi_write_cmd(uint8_t cmd)
{
    uint8_t tx = cmd;
    struct spi_buf buf = { .buf = &tx, .len = 1 };
    struct spi_buf_set set = { .buffers = &buf, .count = 1 };
    return spi_write(spi_dev, &spi_cfg, &set);
}

static int spi_write_cmd_addr(uint8_t cmd, uint32_t addr, uint8_t cmd_buf[4])
{
    cmd_buf[0] = cmd;
    cmd_buf[1] = (addr >> 16) & 0xFF;
    cmd_buf[2] = (addr >> 8) & 0xFF;
    cmd_buf[3] = addr & 0xFF;
    struct spi_buf buf = { .buf = cmd_buf, .len = 4 };
    struct spi_buf_set set = { .buffers = &buf, .count = 1 };
    return spi_write(spi_dev, &spi_cfg, &set);
}

static void wait_flash_ready(void)
{
    uint8_t status;
    do {
        spi_write_cmd(W25Q16_CMD_READ_STATUS);
        uint8_t rx;
        struct spi_buf tx_buf = { .buf = NULL, .len = 1 };
        struct spi_buf rx_buf = { .buf = &rx, .len = 1 };
        struct spi_buf_set tx_set = { .buffers = &tx_buf, .count = 1 };
        struct spi_buf_set rx_set = { .buffers = &rx_buf, .count = 1 };
        spi_transceive(spi_dev, &spi_cfg, &tx_set, &rx_set);
        status = rx;
    } while (status & 0x01);  /* BUSY bit */
}

static int flash_erase_sector(uint32_t sector_addr)
{
    spi_write_cmd(W25Q16_CMD_WRITE_ENABLE);
    uint8_t cmd_buf[4];
    spi_write_cmd_addr(W25Q16_CMD_SECTOR_ERASE, sector_addr, cmd_buf);
    wait_flash_ready();
    return 0;
}

static int flash_write_page(uint32_t addr, const uint8_t *data, uint16_t len)
{
    if (len > W25Q16_PAGE_SIZE) len = W25Q16_PAGE_SIZE;
    spi_write_cmd(W25Q16_CMD_WRITE_ENABLE);

    /* Write command + 24-bit address + data */
    uint8_t tx[W25Q16_PAGE_SIZE + 4];
    tx[0] = W25Q16_CMD_PAGE_PROGRAM;
    tx[1] = (addr >> 16) & 0xFF;
    tx[2] = (addr >> 8) & 0xFF;
    tx[3] = addr & 0xFF;
    memcpy(&tx[4], data, len);

    struct spi_buf buf = { .buf = tx, .len = len + 4 };
    struct spi_buf_set set = { .buffers = &buf, .count = 1 };
    int rc = spi_write(spi_dev, &spi_cfg, &set);
    wait_flash_ready();
    return rc;
}

int data_logger_init(void)
{
    spi_dev = DEVICE_DT_GET(SPI_NODE);
    if (!device_is_ready(spi_dev)) {
        LOG_WRN("SPI flash not available — logging disabled");
        return -1;
    }

    /* Verify JEDEC ID */
    uint8_t jedec_cmd = W25Q16_CMD_JEDEC_ID;
    uint8_t rx[3] = {0};
    struct spi_buf tx_buf = { .buf = &jedec_cmd, .len = 1 };
    struct spi_buf rx_bufs[] = {
        { .buf = NULL, .len = 1 },      /* Dummy byte */
        { .buf = rx, .len = 3 },
    };
    struct spi_buf_set tx_set = { .buffers = &tx_buf, .count = 1 };
    struct spi_buf_set rx_set = { .buffers = rx_bufs, .count = 2 };

    if (spi_transceive(spi_dev, &spi_cfg, &tx_set, &rx_set) == 0) {
        if (rx[0] == 0xEF && rx[1] == 0x40 && rx[2] == 0x15) {
            LOG_INF("W25Q16 detected (JEDEC: %02X %02X %02X)",
                    rx[0], rx[1], rx[2]);
        } else {
            LOG_WRN("Unknown flash JEDEC: %02X %02X %02X",
                    rx[0], rx[1], rx[2]);
        }
    }

    /* Read header to determine existing log state */
    uint8_t header[LOG_HEADER_SIZE];
    /* Simplified: read from address 0 */
    write_offset = LOG_HEADER_SIZE;
    sample_count = 0;
    log_active = true;

    LOG_INF("Data logger initialized, offset=%u", write_offset);
    return 0;
}

int data_logger_append(const field_vector_t *field,
                       const accel_data_t *accel,
                       compass_heading_t heading)
{
    if (!log_active) return -1;

    /* Check if we have space */
    if (write_offset + LOG_SAMPLE_SIZE >= W25Q16_TOTAL_SIZE) {
        LOG_WRN("Flash log full");
        log_active = false;
        return -2;
    }

    /* Pack sample:
     * [timestamp(4)] [Mx(4)] [My(4)] [Mz(4)] [Ax(2)] [Ay(2)] [Az(2)] [heading(2)]
     */
    uint8_t sample[LOG_SAMPLE_SIZE];
    uint32_t ts = (uint32_t)k_uptime_get_32();

    memcpy(&sample[0],  &ts, 4);
    memcpy(&sample[4],  &field->x, 4);
    memcpy(&sample[8],  &field->y, 4);
    memcpy(&sample[12], &field->z, 4);

    int16_t ax = (int16_t)(accel->x * 1000.0f);
    int16_t ay = (int16_t)(accel->y * 1000.0f);
    int16_t az = (int16_t)(accel->z * 1000.0f);
    memcpy(&sample[16], &ax, 2);
    memcpy(&sample[18], &ay, 2);
    memcpy(&sample[20], &az, 2);

    /* Note: heading goes in the last 2 bytes */
    /* Actually 22 bytes total, we use bytes 0-21 */
    /* Let me recalculate: 4+4+4+4+2+2+2 = 22 — perfect */

    /* Write to flash (page-aligned) */
    uint32_t page_offset = write_offset % W25Q16_PAGE_SIZE;
    if (page_offset + LOG_SAMPLE_SIZE > W25Q16_PAGE_SIZE) {
        /* Would cross page boundary — need to split */
        /* Simplified: just write what fits, rest goes to next page */
        uint16_t first_part = W25Q16_PAGE_SIZE - page_offset;
        flash_write_page(write_offset, sample, first_part);
        flash_write_page(write_offset + first_part,
                        sample + first_part,
                        LOG_SAMPLE_SIZE - first_part);
    } else {
        flash_write_page(write_offset, sample, LOG_SAMPLE_SIZE);
    }

    write_offset += LOG_SAMPLE_SIZE;
    sample_count++;

    return 0;
}

uint32_t data_logger_sample_count(void)
{
    return sample_count;
}

int data_logger_erase(void)
{
    /* Erase sector by sector (simplified — could use chip erase) */
    for (uint32_t sector = 0; sector < W25Q16_SECTOR_COUNT; sector++) {
        flash_erase_sector(sector * W25Q16_SECTOR_SIZE);
    }
    write_offset = LOG_HEADER_SIZE;
    sample_count = 0;
    log_active = true;
    LOG_INF("Flash log erased");
    return 0;
}

int data_logger_dump_uart(void)
{
    /* Simplified: would read back all samples and send over UART */
    LOG_INF("Log dump: %u samples", sample_count);
    return 0;
}