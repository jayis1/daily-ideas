/*
 * Spectra Charm — uart_proto.h
 */
#ifndef UART_PROTO_H
#define UART_PROTO_H

#include "stm32g4xx_hal.h"
#include "spectrometer.h"

#define UART_PKT_MAX_SIZE  512

typedef struct {
    uint8_t data[UART_PKT_MAX_SIZE];
    uint16_t length;
} UartPacket_t;

uint16_t UartProto_EncodeResult(const SpectrumResult_t *result, UartPacket_t *pkt);
HAL_StatusTypeDef UartProto_DecodeRequest(const uint8_t *data, uint16_t len,
                                            ScanRequest_t *req);
uint16_t UartProto_EncodeAck(uint8_t original_cmd, uint8_t status, UartPacket_t *pkt);

#endif