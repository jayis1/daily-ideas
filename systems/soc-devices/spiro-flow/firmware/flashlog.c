/**
 * spiro_flow/flashlog.c — W25Q128 SPI flash session logging
 *
 * Stores up to 500 spirometry sessions in external SPI flash.
 * Each session record = sizeof(spiro_result_t) + maneuver metadata.
 *
 * Flash layout (W25Q128 = 16 MB):
 *   0x000000 - 0x0000FF  : Header / magic / session count
 *   0x000100 - 0x07FFFF  : Session records (512 records × ~128 bytes)
 *   0x080000 - 0xFFFFFF  : Raw flow data archives (optional)
 *
 * The W25Q128 is accessed via SPI2 (software CS on PB12).
 */

#include "main.h"
#include "flashlog.h"
#include <string.h>

#define TAG "FLASH"

#define W25Q128_CS_LOW()   /* GPIO_ResetBits(GPIOB, GPIO_Pin_12) */
#define W25Q128_CS_HIGH()  /* GPIO_SetBits(GPIOB, GPIO_Pin_12) */

#define W25Q_CMD_READ      0x03
#define W25Q_CMD_PAGE_PROG 0x02
#define W25Q_CMD_SECTOR_ER 0x20
#define W25Q_CMD_READ_ID   0x9F
#define W25Q_CMD_WRITE_EN  0x06
#define W25Q_CMD_WAIT_BUSY 0x05

#define FLASH_MAGIC        0x53465031  /* "SFP1" */
#define HEADER_ADDR        0x000000
#define SESSION_BASE       0x000100
#define MAX_SESSIONS       512
#define SESSION_RECORD_SIZE 256  /* padded size per session */

typedef struct {
    uint32_t magic;
    uint16_t session_count;
    uint16_t reserved;
} flash_header_t;

static uint16_t s_session_count = 0;

/* ── SPI helpers (CH32V203 HAL) ────────────────────────────────────── */

static void spi2_send(uint8_t *data, int len)
{
    /* CH32V203 HAL:
     * for (int i = 0; i < len; i++) {
     *     SPI_I2S_SendData(SPI2, data[i]);
     *     while (SPI_I2S_GetFlagStatus(SPI2, SPI_I2S_FLAG_TXE) == RESET);
     * }
     */
    (void)data; (void)len;
}

static void spi2_recv(uint8_t *data, int len)
{
    /* CH32V203 HAL:
     * for (int i = 0; i < len; i++) {
     *     SPI_I2S_SendData(SPI2, 0xFF);  // dummy
     *     while (SPI_I2S_GetFlagStatus(SPI2, SPI_I2S_FLAG_RXNE) == RESET);
     *     data[i] = SPI_I2S_ReceiveData(SPI2);
     * }
     */
    memset(data, 0xFF, len);
}

static void w25q_write_enable(void)
{
    uint8_t cmd = W25Q_CMD_WRITE_EN;
    W25Q128_CS_LOW();
    spi2_send(&cmd, 1);
    W25Q128_CS_HIGH();
}

static void w25q_wait_busy(void)
{
    /* Poll status register for busy bit */
    uint8_t cmd = W25Q_CMD_WAIT_BUSY;
    uint8_t status;
    do {
        W25Q128_CS_LOW();
        spi2_send(&cmd, 1);
        spi2_recv(&status, 1);
        W25Q128_CS_HIGH();
    } while (status & 0x01);
}

static void w25q_read(uint32_t addr, uint8_t *buf, int len)
{
    uint8_t cmd[4] = {W25Q_CMD_READ,
                      (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr};
    W25Q128_CS_LOW();
    spi2_send(cmd, 4);
    spi2_recv(buf, len);
    W25Q128_CS_HIGH();
}

static void w25q_page_prog(uint32_t addr, const uint8_t *data, int len)
{
    /* Page program: max 256 bytes per page, must not cross page boundary */
    w25q_write_enable();
    uint8_t cmd[4] = {W25Q_CMD_PAGE_PROG,
                      (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr};
    W25Q128_CS_LOW();
    spi2_send(cmd, 4);
    spi2_send((uint8_t *)data, len);
    W25Q128_CS_HIGH();
    w25q_wait_busy();
}

static void w25q_sector_erase(uint32_t addr)
{
    w25q_write_enable();
    uint8_t cmd[4] = {W25Q_CMD_SECTOR_ER,
                      (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr};
    W25Q128_CS_LOW();
    spi2_send(cmd, 4);
    W25Q128_CS_HIGH();
    w25q_wait_busy();
}

/* ── Flash log API ─────────────────────────────────────────────────── */

int flashlog_init(void)
{
    /* Read header */
    flash_header_t hdr;
    w25q_read(HEADER_ADDR, (uint8_t *)&hdr, sizeof(hdr));

    if (hdr.magic != FLASH_MAGIC) {
        ESP_LOGI(TAG, "Flash uninitialized, formatting...");
        /* Erase first sector and write header */
        w25q_sector_erase(HEADER_ADDR);
        hdr.magic = FLASH_MAGIC;
        hdr.session_count = 0;
        hdr.reserved = 0;
        w25q_page_prog(HEADER_ADDR, (uint8_t *)&hdr, sizeof(hdr));
        s_session_count = 0;
    } else {
        s_session_count = hdr.session_count;
    }

    ESP_LOGI(TAG, "Flash log initialized: %d sessions", s_session_count);
    return 0;
}

int flashlog_write_session(const spiro_result_t *r, const maneuver_buffer_t *m)
{
    if (s_session_count >= MAX_SESSIONS) {
        ESP_LOGW(TAG, "Flash full, wrapping to 0");
        /* In production: erase oldest sector and wrap */
        s_session_count = 0;
    }

    uint32_t addr = SESSION_BASE + (uint32_t)s_session_count * SESSION_RECORD_SIZE;

    /* Pack result into 256-byte record */
    uint8_t record[SESSION_RECORD_SIZE];
    memset(record, 0, sizeof(record));
    memcpy(record, r, sizeof(spiro_result_t));
    /* Store sample count at end of record */
    int16_t n_samples = (int16_t)m->n_samples;
    memcpy(record + sizeof(spiro_result_t), &n_samples, 2);

    /* Erase sector if needed (4KB = 16 records) */
    if ((s_session_count % 16) == 0) {
        w25q_sector_erase(addr);
    }

    /* Write record (256 bytes fits in one page) */
    w25q_page_prog(addr, record, SESSION_RECORD_SIZE);

    /* Update header */
    s_session_count++;
    flash_header_t hdr = {FLASH_MAGIC, s_session_count, 0};
    w25q_page_prog(HEADER_ADDR, (uint8_t *)&hdr, sizeof(hdr));

    ESP_LOGI(TAG, "Session #%d written to flash @ 0x%06X", s_session_count, addr);
    return 0;
}

int flashlog_read_session(uint16_t id, spiro_result_t *r)
{
    if (id >= s_session_count) return -1;

    uint32_t addr = SESSION_BASE + (uint32_t)id * SESSION_RECORD_SIZE;
    uint8_t record[SESSION_RECORD_SIZE];
    w25q_read(addr, record, SESSION_RECORD_SIZE);
    memcpy(r, record, sizeof(spiro_result_t));

    return 0;
}

uint16_t flashlog_get_count(void)
{
    return s_session_count;
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#define ESP_LOGW(tag, fmt, ...) do { printf("[%s W] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif