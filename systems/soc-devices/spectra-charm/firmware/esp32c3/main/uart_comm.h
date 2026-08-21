/*
 * Spectra Charm — uart_comm.h
 */
#ifndef UART_COMM_H
#define UART_COMM_H

#include <stdint.h>

void UART_Init(int tx_pin, int rx_pin);
void UART_SendScanRequest(uint8_t scan_type);
int UART_ReceivePacket(uint8_t *buf, int max_len);

#endif