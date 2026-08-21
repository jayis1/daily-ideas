/*
 * Spectra Charm — ESP32-C3 UART Communication with STM32G491
 *
 * uart_comm.c
 */

#include "uart_comm.h"
#include <string.h>
#include "esp_log.h"
#include "driver/uart.h"

static const char *TAG = "UART_Comm";

#define UART_NUM        UART_NUM_0
#define UART_BAUD       115200
#define UART_BUF_SIZE   1024
#define UART_PKT_BUF    512

static uint8_t rx_buffer[UART_BUF_SIZE];

void UART_Init(int tx_pin, int rx_pin)
{
    uart_config_t config = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };

    uart_driver_install(UART_NUM, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_NUM, &config);
    uart_set_pin(UART_NUM, tx_pin, rx_pin, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    ESP_LOGI(TAG, "UART initialized at %d baud", UART_BAUD);
}

void UART_SendScanRequest(uint8_t scan_type)
{
    /* Build UART protocol packet for scan request */
    uint8_t pkt[9] = {
        0xA5, 0x5A,       /* Sync bytes */
        0x00, 0x03,       /* Length: 3 bytes payload */
        0x01,             /* Command: scan request */
        scan_type,        /* Scan type */
        0x09,             /* Gain: 256x */
        0x1D, 0x00,       /* Integration: 29 (ATIME default) */
    };
    /* CRC8 would go at end in real implementation */

    uart_write_bytes(UART_NUM, pkt, sizeof(pkt));
    ESP_LOGI(TAG, "Scan request sent: type=%d", scan_type);
}

int UART_ReceivePacket(uint8_t *buf, int max_len)
{
    /* Look for sync bytes, then read header + payload */
    int len = uart_read_bytes(UART_NUM, buf, 2, pdMS_TO_TICKS(5000));
    if (len < 2) return 0;

    if (buf[0] != 0xA5 || buf[1] != 0x5A) return 0;

    /* Read length field */
    len = uart_read_bytes(UART_NUM, &buf[2], 2, pdMS_TO_TICKS(100));
    if (len < 2) return 0;

    uint16_t payload_len = ((uint16_t)buf[2] << 8) | buf[3];

    if (payload_len + 5 > max_len) return 0;

    /* Read command + payload + CRC */
    len = uart_read_bytes(UART_NUM, &buf[4], payload_len + 1, pdMS_TO_TICKS(500));
    if (len < payload_len) return 0;

    return 4 + payload_len + 1;
}