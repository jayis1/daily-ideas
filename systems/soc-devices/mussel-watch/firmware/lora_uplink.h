/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * lora_uplink.h — SX1262 LoRa radio driver, packet formatting, AES-128
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef LORA_UPLINK_H
#define LORA_UPLINK_H

#include "config.h"

/* Initialize the SX1262 radio and LoRa modem */
int lora_init(void);

/* Build a LoRa packet from the current state.
 * Populates the 34-byte payload buffer. Returns packet length. */
int lora_build_packet(const mussel_watch_state_t *st, uint8_t *pkt);

/* Transmit a packet via the SX1262. Returns 0 on success, -1 on error. */
int lora_tx(const uint8_t *pkt, int len);

/* High-level: build + encrypt + transmit the current state.
 * If `immediate` is nonzero, this is an alert uplink (not periodic). */
int lora_uplink(const mussel_watch_state_t *st, int immediate);

/* SX1262 low-level SPI commands */
int sx1262_write_reg(uint16_t addr, uint8_t val);
int sx1262_read_reg(uint16_t addr, uint8_t *val);
int sx1262_write_buffer(uint8_t offset, const uint8_t *data, uint8_t len);
int sx1262_read_buffer(uint8_t offset, uint8_t *data, uint8_t len);
int sx1262_send_command(uint8_t *cmd, uint8_t cmd_len, uint8_t *status, uint8_t status_len);

/* AES-128 encryption for LoRaWAN payload (in-place, 16-byte blocks) */
void aes128_encrypt_block(const uint8_t key[16], uint8_t block[16]);

/* Simple CRC32 for packet integrity (not LoRaWAN MIC, but a lightweight check) */
uint32_t crc32(const uint8_t *data, int len);

#endif /* LORA_UPLINK_H */