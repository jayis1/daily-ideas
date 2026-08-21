/*
 * sd_log.c — microSD SPI logging for Thermo Trace DSC
 *
 * Uses SPI2 for microSD card communication in SPI mode.
 * Logs DSC scan data as CSV: time, temperature, heat_flow, setpoint
 */

#include "stm32g491_conf.h"
#include "sd_log.h"
#include <string.h>

static bool sd_card_present = false;
static bool sd_initialized = false;

/* ---- SPI2 helpers ---- */
static void spi2_wait_tx(void) {
    while (!(SPI2_SR & (1U << 1))) ;
}

static void spi2_wait_rx(void) {
    while (!(SPI2_SR & (1U << 0))) ;
}

static uint8_t spi2_xfer(uint8_t tx) {
    spi2_wait_tx();
    *(volatile uint8_t *)&SPI2_DR = tx;
    spi2_wait_rx();
    return (uint8_t)SPI2_DR;
}

static void sd_cs_low(void) { GPIO_CLR(SD_CS_PORT, SD_CS_PIN); }
static void sd_cs_high(void) { GPIO_SET(SD_CS_PORT, SD_CS_PIN); }

void sd_init(void) {
    /* Enable SPI2 clock */
    RCC_APB1ENR1 |= (1U << 14);  /* SPI2EN */

    /* PB2 SCK, PB3 MISO, PB4 MOSI as AF5 (SPI2) */
    /* Note: PB2 is actually an alternate function for SPI2 on G4 */
    GPIO_MODER(GPIOB_BASE) &= ~((3U << (2*2)) | (3U << (3*2)) | (3U << (4*2)));
    GPIO_MODER(GPIOB_BASE) |=  (2U << (2*2)) | (2U << (3*2)) | (2U << (4*2));
    GPIO_AFRL(GPIOB_BASE) = (GPIO_AFRL(GPIOB_BASE) & ~((0xF << (2*4)) | (0xF << (3*4)) | (0xF << (4*4))))
                           | (5U << (2*4)) | (5U << (3*4)) | (5U << (4*4));

    /* PB5 CS output, default HIGH */
    GPIO_MODER(GPIOB_BASE) |= (1U << (5*2));
    sd_cs_high();

    /* SPI2: master, mode 0, baud rate /256 (for init, will speed up later) */
    SPI2_CR1 = 0;
    SPI2_CR1 = (1U << 2) | (7U << 3) | (1U << 6);  /* master, BR=/256, enable */
    SPI2_CR2 = (1U << 12);  /* FRXTH */
}

/* Send 80 dummy clocks to initialize SD card in SPI mode */
static bool sd_send_init(void) {
    sd_cs_high();
    for (int i = 0; i < 10; i++) spi2_xfer(0xFF);  /* 80 clocks */

    sd_cs_low();
    /* CMD0: GO_IDLE_STATE */
    spi2_xfer(0x40 | 0);  /* CMD */
    spi2_xfer(0x00); spi2_xfer(0x00); spi2_xfer(0x00); spi2_xfer(0x00);
    spi2_xfer(0x95);  /* CRC for CMD0 */

    uint8_t response = 0xFF;
    for (int i = 0; i < 100; i++) {
        response = spi2_xfer(0xFF);
        if (response == 0x01) break;  /* idle response */
    }
    return (response == 0x01);
}

bool sd_mount(void) {
    if (!sd_send_init()) {
        sd_card_present = false;
        return false;
    }

    /* CMD8: SEND_IF_COND (for SDHC detection) */
    spi2_xfer(0x48);
    spi2_xfer(0x00); spi2_xfer(0x00); spi2_xfer(0x01); spi2_xfer(0xAA);
    spi2_xfer(0x87);
    /* Read R7 response (7 bytes) */
    for (int i = 0; i < 5; i++) spi2_xfer(0xFF);

    /* ACMD41: SD_SEND_OP_COND (initialize) */
    for (int retries = 0; retries < 200; retries++) {
        spi2_xfer(0x77);  /* CMD55 */
        spi2_xfer(0x00); spi2_xfer(0x00); spi2_xfer(0x00); spi2_xfer(0x00);
        spi2_xfer(0xFF);
        spi2_xfer(0xFF);  /* response */

        spi2_xfer(0x69);  /* ACMD41 */
        spi2_xfer(0x40); spi2_xfer(0x00); spi2_xfer(0x00); spi2_xfer(0x00);
        spi2_xfer(0xFF);
        uint8_t r = spi2_xfer(0xFF);
        if (r == 0x00) break;  /* initialization done */
    }

    /* Speed up SPI to /2 or /4 */
    SPI2_CR1 &= ~(7U << 3);
    SPI2_CR1 |=  (1U << 3);  /* BR = /4 */

    sd_card_present = true;
    sd_initialized = true;
    return true;
}

bool sd_is_present(void) {
    return sd_card_present;
}

/* Simplified: write raw bytes via block write (CMD24) */
static bool sd_write_block(uint32_t block_addr, const uint8_t *data, uint16_t len) {
    if (len > 512) len = 512;

    sd_cs_low();
    spi2_xfer(0x58 | 0x00);  /* CMD24 WRITE_BLOCK */
    spi2_xfer((block_addr >> 24) & 0xFF);
    spi2_xfer((block_addr >> 16) & 0xFF);
    spi2_xfer((block_addr >> 8) & 0xFF);
    spi2_xfer(block_addr & 0xFF);
    spi2_xfer(0xFF);  /* CRC (ignored in SPI mode) */

    /* Wait for response 0x00 */
    for (int i = 0; i < 100; i++) {
        if (spi2_xfer(0xFF) == 0x00) break;
    }

    /* Data token */
    spi2_xfer(0xFE);
    /* Data + padding */
    for (int i = 0; i < 512; i++) {
        spi2_xfer((i < len) ? data[i] : 0x00);
    }
    /* CRC */
    spi2_xfer(0xFF); spi2_xfer(0xFF);

    /* Wait for write completion */
    for (int i = 0; i < 1000; i++) {
        uint8_t r = spi2_xfer(0xFF);
        if (r != 0x00) break;
    }

    sd_cs_high();
    return true;
}

void sd_write_string(const char *str) {
    /* Simplified: just accumulate in a buffer for now */
    /* In a full implementation, this would use FAT32/exFAT filesystem */
    (void)str;
}

static uint32_t log_block_addr = 0;  /* current write block */
static uint16_t log_offset = 0;      /* offset within block */

static char log_buffer[512];

static void flush_buffer(void) {
    if (log_offset > 0) {
        sd_write_block(log_block_addr, (uint8_t *)log_buffer, log_offset);
        log_block_addr++;
        log_offset = 0;
        memset(log_buffer, 0, sizeof(log_buffer));
    }
}

void sd_open_session(uint32_t timestamp) {
    if (!sd_initialized) return;
    log_block_addr = 100;  /* start writing at block 100 (arbitrary) */
    log_offset = 0;
    memset(log_buffer, 0, sizeof(log_buffer));
    /* Write header */
    const char *hdr = "time_s,temp_C,heat_flow_mW,setpoint_C\n";
    int hlen = (int)strlen(hdr);
    memcpy(log_buffer, hdr, hlen);
    log_offset = (uint16_t)hlen;
    flush_buffer();
}

void sd_log_point(float temp, float heat_flow, float time, float setpoint) {
    if (!sd_initialized) return;

    /* Format CSV line: time, temp, heat_flow, setpoint */
    char line[48];
    int n = 0;
    /* Simple float-to-string conversion */
    n += (int)sprintf(line + n, "%.2f,%.2f,%.3f,%.2f\n",
                      time, temp, heat_flow, setpoint);

    if (log_offset + n > 511) flush_buffer();
    memcpy(log_buffer + log_offset, line, n);
    log_offset += (uint16_t)n;
}

void sd_close_session(void) {
    if (!sd_initialized) return;
    flush_buffer();
}