/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * uart_proto.c — Binary UART protocol between STM32G491 and ESP32-C3
 *
 * Protocol format:
 *   [SYNC1][SYNC2][LEN_H][LEN_L][CMD][PAYLOAD...][CRC8]
 *   SYNC1 = 0xA5, SYNC2 = 0x5A
 *   LEN = payload length (not including header or CRC)
 *   CMD = command byte
 *   CRC8 = CRC-8 over CMD + PAYLOAD
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "uart_proto.h"
#include <string.h>

#define SYNC_BYTE_1  0xA5
#define SYNC_BYTE_2  0x5A
#define HEADER_SIZE  6  /* sync1 + sync2 + len_h + len_l + cmd + (padding) */
#define CRC_POLY     0x07

/* Command IDs */
#define CMD_SCAN_REQUEST    0x01
#define CMD_SCAN_RESULT     0x81
#define CMD_SET_GAIN        0x02
#define CMD_GET_BATTERY     0x03
#define CMD_BATTERY_RESP   0x83
#define CMD_GET_STATUS      0x04
#define CMD_STATUS_RESP    0x84
#define CMD_LIBRARY_LIST   0x05
#define CMD_LIBRARY_RESP   0x85
#define CMD_ADD_COMPOUND   0x06
#define CMD_ACK            0x86

extern UART_HandleTypeDef huart1;

/* CRC-8 calculator */
static uint8_t CRC8_Calculate(const uint8_t *data, uint16_t len)
{
    uint8_t crc = 0x00;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ CRC_POLY;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

/* Encode a spectrum result into a UART packet */
uint16_t UartProto_EncodeResult(const SpectrumResult_t *result, UartPacket_t *pkt)
{
    uint16_t idx = 0;

    pkt->data[idx++] = SYNC_BYTE_1;
    pkt->data[idx++] = SYNC_BYTE_2;

    /* Payload length: status(1) + scan_num(2) + num_peaks(1) + peaks(16*8=128) +
     * match_id(1) + confidence(4) + concentration(4) + name(32) = 173 */
    uint16_t payload_len = 1 + 2 + 1 + (MAX_PEAKS * sizeof(Peak_t)) +
                           1 + 4 + 4 + 32;
    pkt->data[idx++] = (payload_len >> 8) & 0xFF;
    pkt->data[idx++] = payload_len & 0xFF;

    pkt->data[idx++] = CMD_SCAN_RESULT;

    /* Payload */
    pkt->data[idx++] = (uint8_t)result->status;
    pkt->data[idx++] = (result->scan_number >> 8) & 0xFF;
    pkt->data[idx++] = result->scan_number & 0xFF;
    pkt->data[idx++] = result->num_peaks;

    /* Pack peaks (wavelength float32 + absorbance float32 per peak) */
    for (int i = 0; i < MAX_PEAKS; i++) {
        memcpy(&pkt->data[idx], &result->peaks[i].wavelength, 4);
        idx += 4;
        memcpy(&pkt->data[idx], &result->peaks[i].absorbance, 4);
        idx += 4;
    }

    /* Match result */
    pkt->data[idx++] = (uint8_t)result->match.compound_id;
    memcpy(&pkt->data[idx], &result->match.confidence, 4);
    idx += 4;
    memcpy(&pkt->data[idx], &result->concentration, 4);
    idx += 4;
    memcpy(&pkt->data[idx], result->match.name, 32);
    idx += 32;

    /* CRC8 over CMD + payload */
    pkt->data[idx] = CRC8_Calculate(&pkt->data[5], idx - 5);
    idx++;

    pkt->length = idx;
    return idx;
}

/* Decode a scan request from ESP32-C3 */
HAL_StatusTypeDef UartProto_DecodeRequest(const uint8_t *data, uint16_t len,
                                            ScanRequest_t *req)
{
    if (len < 7) return HAL_ERROR;
    if (data[0] != SYNC_BYTE_1 || data[1] != SYNC_BYTE_2) return HAL_ERROR;

    uint16_t payload_len = ((uint16_t)data[2] << 8) | data[3];
    uint8_t cmd = data[4];

    if (cmd != CMD_SCAN_REQUEST) return HAL_ERROR;

    /* Verify CRC */
    uint8_t crc = CRC8_Calculate(&data[4], payload_len);
    if (crc != data[4 + payload_len + 1]) return HAL_ERROR;

    /* Parse scan request */
    req->type = (ScanType_t)data[5];
    req->gain = data[6];
    req->integration = ((uint16_t)data[7] << 8) | data[8];

    return HAL_OK;
}

/* Encode a simple ACK packet */
uint16_t UartProto_EncodeAck(uint8_t original_cmd, uint8_t status, UartPacket_t *pkt)
{
    uint16_t idx = 0;
    pkt->data[idx++] = SYNC_BYTE_1;
    pkt->data[idx++] = SYNC_BYTE_2;
    pkt->data[idx++] = 0; /* len high */
    pkt->data[idx++] = 2; /* len low: original_cmd + status */
    pkt->data[idx++] = CMD_ACK;
    pkt->data[idx++] = original_cmd;
    pkt->data[idx++] = status;
    pkt->data[idx] = CRC8_Calculate(&pkt->data[5], 2);
    idx++;
    pkt->length = idx;
    return idx;
}