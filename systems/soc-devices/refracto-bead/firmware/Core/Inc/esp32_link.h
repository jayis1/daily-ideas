/**
 * esp32_link.h — UART protocol to ESP32-C3 connectivity MCU
 *
 * The STM32 sends measurement results to the ESP32-C3 over USART1
 * at 460800 baud. The ESP32-C3 relays them via BLE and/or Wi-Fi.
 *
 * Frame format (binary):
 *   [0xAA][0x55][cmd][len_hi][len_lo][payload...][crc8]
 *
 * Commands:
 *   0x01: RESULT — measurement result (ri_result_t serialized)
 *   0x02: STATUS — device status update
 *   0x03: CAL    — calibration data
 */

#ifndef ESP32_LINK_H
#define ESP32_LINK_H

#include "stm32g4xx_hal.h"
#include "refract_calc.h"

void esp32_link_init(UART_HandleTypeDef *huart);
void esp32_link_send_result(const ri_result_t *result);
void esp32_link_send_status(uint8_t status, uint8_t battery);

#endif /* ESP32_LINK_H */