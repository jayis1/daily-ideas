/**
 * spiro_flow/sdp810.c — Sensirion SDP810-500Pa differential pressure sensor driver
 *
 * The SDP810 measures the pressure drop across the Fleisch pneumotachograph
 * screen. Flow is proportional to differential pressure (ΔP = R × flow).
 *
 * I2C address: 0x21
 * Continuous measurement: 0x3608 (mass flow, 250 Hz avg)
 * For our purposes we use single-shot at 250 Hz via software timing.
 *
 * Datasheet: Sensirion SDP8xx-500Pa, April 2023
 */

#include "main.h"
#include "sdp810.h"
#include <string.h>

#define TAG "SDP810"

#define SDP810_ADDR            0x21

/* SDP810 commands */
#define SDP810_CMD_CONT_AVG    0x3608   /* continuous measurement, mass flow, 250 Hz */
#define SDP810_CMD_CONT_RAW    0x3615   /* continuous, raw, 250 Hz */
#define SDP810_CMD_STOP        0x3FF9   /* stop continuous */
#define SDP810_CMD_SOFT_RESET  0x0006   /* soft reset */

static bool s_continuous = false;

/* ── I2C helpers (CH32V203 HAL) ────────────────────────────────────── */

/* The CH32V203 I2C1 peripheral is used.
 * In production these would use the WCH HAL I2C_Transfer() functions.
 * Here we provide a clean interface that maps to the HAL.
 */

static int i2c_write_cmd(uint8_t addr, uint8_t cmd_msb, uint8_t cmd_lsb)
{
    /* CH32V203 HAL:
     * while(I2C_GetFlagStatus(I2C1, I2C_FLAG_BUSY));
     * I2C_GenerateSTART(I2C1, ENABLE);
     * ... send addr, cmd_msb, cmd_lsb, STOP
     */
    /* Placeholder: in real firmware, call HAL I2C write */
    (void)addr; (void)cmd_msb; (void)cmd_lsb;
    return 0;
}

static int i2c_read9(uint8_t addr, uint8_t *buf, int len)
{
    /* Read len bytes + CRC from SDP810.
     * SDP810 returns: 2 bytes diff_pressure MSB/LSB, 1 CRC,
     *                 2 bytes temp MSB/LSB, 1 CRC
     * Total: 6 data + 2 CRC = 9 bytes (but we read 9)
     */
    /* CH32V203 HAL:
     * I2C_GenerateSTART(I2C1, ENABLE);
     * ... read len bytes with ACK/NACK on last
     */
    (void)addr;
    /* Placeholder: fill buf with zeros */
    memset(buf, 0, len);
    return 0;
}

/* ── CRC-8 (Sensirion polynomial 0x31) ─────────────────────────────── */

static uint8_t crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0xFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x31;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* ── SDP810 driver functions ───────────────────────────────────────── */

int sdp810_init(void)
{
    /* Soft reset */
    i2c_write_cmd(SDP810_ADDR, 0x00, 0x06);
    /* Wait 0.5ms for reset */
    /* delay_ms(1); */
    ESP_LOGI(TAG, "SDP810 initialized (addr 0x21, 500Pa range)");
    return 0;
}

int sdp810_start_continuous(void)
{
    /* Start continuous measurement at 250 Hz */
    i2c_write_cmd(SDP810_ADDR, 0x36, 0x08);
    s_continuous = true;
    ESP_LOGI(TAG, "SDP810 continuous measurement started (250 Hz)");
    return 0;
}

int sdp810_stop_continuous(void)
{
    i2c_write_cmd(SDP810_ADDR, 0x3F, 0xF9);
    s_continuous = false;
    return 0;
}

int sdp810_read_pressure(float *diff_pa, float *temp_c)
{
    uint8_t buf[9];
    int ret = i2c_read9(SDP810_ADDR, buf, 9);
    if (ret != 0) {
        *diff_pa = 0;
        *temp_c = 25.0f;
        return -1;
    }

    /* Parse differential pressure (first 2 bytes + CRC) */
    int16_t dp_raw = ((int16_t)buf[0] << 8) | buf[1];

    /* Verify CRC */
    if (crc8(buf, 2) != buf[2]) {
        ESP_LOGW(TAG, "SDP810 DP CRC error");
        *diff_pa = 0;
        *temp_c = 25.0f;
        return -2;
    }

    /* Parse temperature (bytes 3-4 + CRC) */
    uint16_t temp_raw = ((uint16_t)buf[3] << 8) | buf[4];
    if (crc8(buf + 3, 2) != buf[5]) {
        ESP_LOGW(TAG, "SDP810 temp CRC error");
    }

    /* Convert raw to physical values:
     * SDP810-500Pa: scale factor = 120 (differential pressure)
     *   diff_pa = dp_raw / scale_factor
     * Temperature: T = -45 + 175 * (temp_raw / 65535)  [°C]
     */
    *diff_pa = (float)dp_raw / SDP810_SCALE_FACTOR;
    *temp_c = -45.0f + 175.0f * ((float)temp_raw / 65535.0f);

    return 0;
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#define ESP_LOGW(tag, fmt, ...) do { printf("[%s W] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#define ESP_LOGE(tag, fmt, ...) do { printf("[%s E] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif