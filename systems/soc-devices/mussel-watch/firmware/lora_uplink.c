/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * lora_uplink.c — SX1262 LoRa radio driver, packet formatting, AES-128
 *
 * Implements:
 *  - SX1262 SPI register/buffer access
 *  - LoRa modem configuration (frequency, SF, BW, coding rate, TX power)
 *  - 34-byte telemetry packet construction (see README for format)
 *  - AES-128 payload encryption (lightweight, for basic confidentiality)
 *  - CRC32 integrity check
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "lora_uplink.h"
#include "config.h"
#include <string.h>

/* ---- Platform HAL stubs ---- */
extern void spi_init(int mosi, int miso, int sck, int cs, int freq_hz);
extern int  spi_write_read(const uint8_t *tx, uint8_t *rx, int len);
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);
extern uint32_t rtc_get_time_s(void);

/* ---- SX1262 command set (subset) ---- */
#define SX1262_CMD_SET_STANDBY    0x80
#define SX1262_CMD_SET_PACKET_TYPE 0x8A  /* 0x00 = LoRa */
#define SX1262_CMD_SET_RF_FREQ     0x86
#define SX1262_CMD_SET_TX_PARAMS   0x8E
#define SX1262_CMD_SET_MOD_CONFIG  0x8B  /* LoRa modulation params */
#define SX1262_CMD_SET_PACKET_PARAMS 0x8C
#define SX1262_CMD_SET_TX          0x83
#define SX1262_CMD_SET_RX          0x82
#define SX1262_CMD_WRITE_BUFFER    0x0E
#define SX1262_CMD_READ_BUFFER     0x1E
#define SX1262_CMD_GET_STATUS      0xC0
#define SX1262_CMD_SET_DIO_IRQ     0x08
#define SX1262_CMD_CLEAR_IRQ       0x02
#define SX1262_CMD_SET_PA_CONFIG   0x95

/* SX1262 registers */
#define SX1262_REG_IRQ_FLAGS       0x03
#define SX1262_REG_PKT_STATUS      0x08

/* IRQ flags */
#define IRQ_TX_DONE    0x0001
#define IRQ_RX_DONE    0x0040
#define IRQ_TIMEOUT    0x0008

/* ---- AES-128 (compact, educational implementation) ---- */
/* This is a minimal AES-128 ECB encrypt for LoRaWAN-style payload encryption.
 * In production, use the nRF Crypto library (nrf_crypto) for hardware-accelerated AES.
 * The S-box, key schedule, and round constants are defined below. */

static const uint8_t aes_sbox[256] = {
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
};

static const uint8_t aes_rcon[11] = {
    0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36
};

static void aes_key_expansion(const uint8_t key[16], uint8_t round_keys[176])
{
    memcpy(round_keys, key, 16);
    for (int i = 16; i < 176; i += 4) {
        uint8_t t[4];
        memcpy(t, &round_keys[i - 4], 4);
        if (i % 16 == 0) {
            /* Rotate left */
            uint8_t tmp = t[0];
            t[0] = t[1]; t[1] = t[2]; t[2] = t[3]; t[3] = tmp;
            /* SubBytes */
            t[0] = aes_sbox[t[0]]; t[1] = aes_sbox[t[1]];
            t[2] = aes_sbox[t[2]]; t[3] = aes_sbox[t[3]];
            /* Rcon */
            t[0] ^= aes_rcon[i / 16];
        }
        for (int j = 0; j < 4; j++)
            round_keys[i + j] = round_keys[i - 16 + j] ^ t[j];
    }
}

static void aes_add_round_key(uint8_t state[16], const uint8_t *rk)
{
    for (int i = 0; i < 16; i++) state[i] ^= rk[i];
}

static void aes_sub_bytes(uint8_t state[16])
{
    for (int i = 0; i < 16; i++) state[i] = aes_sbox[state[i]];
}

static uint8_t xtime(uint8_t x)
{
    return (uint8_t)((x << 1) ^ ((x >> 7) * 0x1b));
}

static void aes_mix_columns(uint8_t state[16])
{
    for (int c = 0; c < 4; c++) {
        uint8_t *col = &state[c * 4];
        uint8_t a0 = col[0], a1 = col[1], a2 = col[2], a3 = col[3];
        col[0] = (uint8_t)(xtime(a0) ^ (xtime(a1) ^ a1) ^ a2 ^ a3);
        col[1] = (uint8_t)(a0 ^ xtime(a1) ^ (xtime(a2) ^ a2) ^ a3);
        col[2] = (uint8_t)(a0 ^ a1 ^ xtime(a2) ^ (xtime(a3) ^ a3));
        col[3] = (uint8_t)((xtime(a0) ^ a0) ^ a1 ^ a2 ^ xtime(a3));
    }
}

static void aes_shift_rows(uint8_t state[16])
{
    /* Row 1: shift left by 1, Row 2: by 2, Row 3: by 3 (state is column-major) */
    uint8_t tmp;
    tmp = state[1]; state[1] = state[5]; state[5] = state[9]; state[9] = state[13]; state[13] = tmp;
    tmp = state[2]; state[2] = state[10]; state[10] = tmp;
    tmp = state[6]; state[6] = state[14]; state[14] = tmp;
    tmp = state[15]; state[15] = state[11]; state[11] = state[7]; state[7] = state[3]; state[3] = tmp;
}

void aes128_encrypt_block(const uint8_t key[16], uint8_t block[16])
{
    uint8_t round_keys[176];
    aes_key_expansion(key, round_keys);

    aes_add_round_key(block, round_keys);
    for (int round = 1; round < 10; round++) {
        aes_sub_bytes(block);
        aes_shift_rows(block);
        aes_mix_columns(block);
        aes_add_round_key(block, &round_keys[round * 16]);
    }
    aes_sub_bytes(block);
    aes_shift_rows(block);
    aes_add_round_key(block, &round_keys[160]);
}

/* ---- CRC32 (IEEE 802.3 polynomial) ---- */

uint32_t crc32(const uint8_t *data, int len)
{
    uint32_t crc = 0xFFFFFFFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1) crc = (crc >> 1) ^ 0xEDB88320;
            else crc >>= 1;
        }
    }
    return crc ^ 0xFFFFFFFF;
}

/* ---- SX1262 SPI access ---- */

int sx1262_write_reg(uint16_t addr, uint8_t val)
{
    uint8_t tx[3] = { (uint8_t)(addr >> 8), (uint8_t)(addr & 0xFF), val };
    uint8_t rx[3];
    gpio_set(PIN_SX1262_CS, 0);
    spi_write_read(tx, rx, 3);
    gpio_set(PIN_SX1262_CS, 1);
    return 0;
}

int sx1262_read_reg(uint16_t addr, uint8_t *val)
{
    uint8_t tx[3] = { (uint8_t)(addr >> 8), (uint8_t)(addr & 0xFF), 0x00 };
    uint8_t rx[3];
    gpio_set(PIN_SX1262_CS, 0);
    spi_write_read(tx, rx, 3);
    gpio_set(PIN_SX1262_CS, 1);
    *val = rx[2];
    return 0;
}

int sx1262_write_buffer(uint8_t offset, const uint8_t *data, uint8_t len)
{
    uint8_t tx[2 + 64];
    tx[0] = SX1262_CMD_WRITE_BUFFER;
    tx[1] = offset;
    memcpy(&tx[2], data, len);
    gpio_set(PIN_SX1262_CS, 0);
    spi_write_read(tx, NULL, 2 + len);
    gpio_set(PIN_SX1262_CS, 1);
    return 0;
}

int sx1262_read_buffer(uint8_t offset, uint8_t *data, uint8_t len)
{
    uint8_t tx[2] = { SX1262_CMD_READ_BUFFER, offset };
    uint8_t rx[2 + 64];
    gpio_set(PIN_SX1262_CS, 0);
    spi_write_read(tx, rx, 2 + len);
    gpio_set(PIN_SX1262_CS, 1);
    memcpy(data, &rx[2], len);
    return 0;
}

int sx1262_send_command(uint8_t *cmd, uint8_t cmd_len, uint8_t *status, uint8_t status_len)
{
    gpio_set(PIN_SX1262_CS, 0);
    spi_write_read(cmd, status, cmd_len);
    gpio_set(PIN_SX1262_CS, 1);
    return 0;
}

/* ---- SX1262 initialization ---- */

int lora_init(void)
{
    /* Hardware reset the SX1262 */
    gpio_set(PIN_SX1262_NRST, 0);
    delay_ms(10);
    gpio_set(PIN_SX1262_NRST, 1);
    delay_ms(20);

    /* Enable TCXO (3.3V) */
    gpio_set(PIN_SX1262_TCXO, 1);
    delay_ms(5);

    /* Set Standby mode (STDBY_RC) */
    uint8_t cmd = SX1262_CMD_SET_STANDBY;
    sx1262_send_command(&cmd, 1, NULL, 0);
    delay_ms(1);

    /* Set packet type: LoRa (0x00) */
    uint8_t pkt_cmd[2] = { SX1262_CMD_SET_PACKET_TYPE, 0x00 };
    sx1262_send_command(pkt_cmd, 2, NULL, 0);

    /* Set RF frequency: 868.1 MHz
     * freq = rf_freq * 32 / (32 MHz) → rf_freq = freq * 2^25 / 32e6
     * 868100000 * 33554432 / 32000000 = 909,892,096 ≈ 0x3640F500 */
    uint32_t rf_freq = (uint32_t)((uint64_t)LORA_FREQ_HZ * 33554432ULL / 32000000ULL);
    uint8_t freq_cmd[5] = {
        SX1262_CMD_SET_RF_FREQ,
        (uint8_t)(rf_freq >> 24),
        (uint8_t)(rf_freq >> 16),
        (uint8_t)(rf_freq >> 8),
        (uint8_t)(rf_freq)
    };
    sx1262_send_command(freq_cmd, 5, NULL, 0);

    /* Set modulation params: SF7, BW 125 kHz, CR 4/5 */
    uint8_t mod_cmd[4] = {
        SX1262_CMD_SET_MOD_CONFIG,
        (uint8_t)(LORA_SF & 0x0F),     /* Spreading factor */
        (uint8_t)((LORA_BW >> 16) & 0xFF), /* Bandwidth (encoded) */
        (uint8_t)(LORA_CR)             /* Coding rate */
    };
    sx1262_send_command(mod_cmd, 4, NULL, 0);

    /* Set packet params: preamble 8, explicit header, payload length 34, CRC on */
    uint8_t ppkt_cmd[10] = {
        SX1262_CMD_SET_PACKET_PARAMS,
        (uint8_t)(LORA_PREAMBLE_LEN >> 8),
        (uint8_t)(LORA_PREAMBLE_LEN & 0xFF),
        0x00,  /* Explicit header */
        LORA_PKT_LEN,
        0x01,  /* CRC on */
        0x00, 0x00, 0x00, 0x00  /* Invert IQ: standard */
    };
    sx1262_send_command(ppkt_cmd, 10, NULL, 0);

    /* Set TX power to +14 dBm (with PA config for SX1262) */
    uint8_t pa_cmd[4] = { SX1262_CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00 };
    sx1262_send_command(pa_cmd, 4, NULL, 0);
    uint8_t txp_cmd[3] = { SX1262_CMD_SET_TX_PARAMS, (uint8_t)LORA_TX_POWER_DBM, 0x04 /* ramp 200us */ };
    sx1262_send_command(txp_cmd, 3, NULL, 0);

    /* Set DIO1 IRQ mask: TX done */
    uint8_t irq_cmd[4] = { SX1262_CMD_SET_DIO_IRQ, 0x01, 0x03, 0x00 };
    sx1262_send_command(irq_cmd, 4, NULL, 0);

    return 0;
}

/* ---- Packet construction ---- */

/* Helper: pack float as 4 bytes little-endian */
static void pack_float_le(uint8_t *buf, float val)
{
    memcpy(buf, &val, 4);
}

/* Helper: pack uint16 as 2 bytes little-endian */
static void pack_u16_le(uint8_t *buf, uint16_t val)
{
    buf[0] = (uint8_t)(val & 0xFF);
    buf[1] = (uint8_t)(val >> 8);
}

int lora_build_packet(const mussel_watch_state_t *st, uint8_t *pkt)
{
    memset(pkt, 0, LORA_PKT_LEN);

    /* Byte 0: Device class */
    pkt[0] = 0x01;  /* Mussel Watch */

    /* Byte 1: Deployment ID (hash) */
    pkt[1] = st->deployment_id;

    /* Bytes 2-9: Timestamp (Unix epoch, big-endian uint64 — we use uint32 padded) */
    uint32_t ts = rtc_get_time_s();
    pkt[2] = 0; pkt[3] = 0; pkt[4] = 0; pkt[5] = 0;
    pkt[6] = (uint8_t)(ts >> 24); pkt[7] = (uint8_t)(ts >> 16);
    pkt[8] = (uint8_t)(ts >> 8);  pkt[9] = (uint8_t)(ts);

    /* Byte 10: Flags */
    uint8_t flags = 0;
    if (st->current_alert != ALERT_NONE) flags |= 0x01;
    if (st->battery_pct < BATTERY_LOW_PCT) flags |= 0x02;
    if (st->mode == MODE_CALIBRATE) flags |= 0x04;
    if (st->n_mussels > 1) flags |= 0x08;
    pkt[10] = flags;

    /* Bytes 11-26: Gape angles for 4 mussels (float32 LE each) */
    for (int i = 0; i < MAX_MUSSELS; i++) {
        int offset = 11 + i * 4;
        if (i < st->n_mussels && st->gape_angle[i] >= 0) {
            pack_float_le(&pkt[offset], st->gape_angle[i]);
        } else {
            /* 0xFFFFFFFF = unused/invalid */
            pkt[offset] = 0xFF; pkt[offset+1] = 0xFF;
            pkt[offset+2] = 0xFF; pkt[offset+3] = 0xFF;
        }
    }

    /* Byte 27: Water temp (int8, °C × 2) */
    int16_t temp_x2 = (int16_t)(st->water_temp_c * 2.0f);
    if (temp_x2 > 127) temp_x2 = 127;
    if (temp_x2 < -128) temp_x2 = -128;
    pkt[27] = (uint8_t)(int8_t)temp_x2;

    /* Bytes 28-29: Dissolved O₂ (uint16, mg/L × 100) */
    uint16_t do_x100 = (uint16_t)(st->dissolved_o2_mgl * 100.0f);
    pack_u16_le(&pkt[28], do_x100);

    /* Bytes 30-31: Depth (int16, cm, signed) */
    int16_t depth_cm = (int16_t)(st->water_depth_m * 100.0f);
    pack_u16_le(&pkt[30], (uint16_t)depth_cm);

    /* Byte 32: Battery % */
    pkt[32] = (uint8_t)st->battery_pct;

    /* Byte 33: Alert code */
    pkt[33] = (uint8_t)st->current_alert;

    return LORA_PKT_LEN;
}

int lora_tx(const uint8_t *pkt, int len)
{
    /* Write payload to SX1262 buffer at offset 0 */
    sx1262_write_buffer(0, pkt, (uint8_t)len);

    /* Clear IRQ flags */
    uint8_t clr_cmd[3] = { SX1262_CMD_CLEAR_IRQ, 0x03, 0xFF };
    sx1262_send_command(clr_cmd, 3, NULL, 0);

    /* Set TX with timeout (30 seconds = 30 × 32768 Hz = 983040 = 0x000F0000) */
    uint8_t tx_cmd[4] = {
        SX1262_CMD_SET_TX,
        0x00, 0x0F, 0x00  /* timeout ≈ 30s in 15.625 µs units */
    };
    sx1262_send_command(tx_cmd, 4, NULL, 0);

    /* Wait for TX done (poll DIO1; here we just delay) */
    delay_ms(200);  /* SF7 @ 125 kHz ≈ 99 ms + overhead */

    /* Clear IRQ */
    sx1262_send_command(clr_cmd, 3, NULL, 0);

    return 0;
}

int lora_uplink(const mussel_watch_state_t *st, int immediate)
{
    uint8_t pkt[LORA_PKT_LEN];
    int len = lora_build_packet(st, pkt);

    /* Encrypt the payload (bytes 2-33, 32 bytes = 2 AES blocks) */
    /* In production, use the LoRaWAN AES key from provisioning.
     * Here we use a static demo key. */
    static const uint8_t aes_key[16] = {
        0x2B, 0x7E, 0x15, 0x16, 0x28, 0xAE, 0xD2, 0xA6,
        0xAB, 0xF7, 0x15, 0x88, 0x09, 0xCF, 0x4F, 0x3C
    };
    /* Encrypt bytes 2..17 and 18..33 (two 16-byte blocks) */
    aes128_encrypt_block(aes_key, &pkt[2]);
    aes128_encrypt_block(aes_key, &pkt[18]);

    /* Append CRC32 is not part of the 34-byte packet — SX1262 adds LoRa CRC
     * in the modem, so payload-level CRC is optional. */

    return lora_tx(pkt, len);
}