/*
 * ble_bridge.h — UART binary protocol bridge to ESP32-C3 (BLE/Wi-Fi)
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Defines the binary frame protocol between the STM32 main MCU and the
 * ESP32-C3 companion which handles BLE 5.0 and Wi-Fi connectivity.
 */
#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include "polarimeter.h"
#include "drude.h"
#include "library.h"

/* Command opcodes (STM32 → ESP32) */
#define CMD_RESULT_SINGLE   0x01  /* single-wavelength result */
#define CMD_RESULT_MULTI    0x02  /* 3-wavelength result + Drude */
#define CMD_LIBRARY_ENTRY   0x03  /* library entry for phone display */
#define CMD_STATUS          0x04  /* status update (measuring, idle, etc.) */
#define CMD_LOG_ENTRY       0x05  /* SD log entry echo */

/* Command opcodes (ESP32 → STM32) */
#define CMD_MEASURE         0x81  /* trigger single measurement */
#define CMD_IDENTIFY        0x82  /* trigger 3-wavelength identification */
#define CMD_ZERO            0x83  /* auto-zero */
#define CMD_MONITOR_START   0x84  /* start monitoring mode */
#define CMD_MONITOR_STOP    0x85  /* stop monitoring mode */
#define CMD_LIBRARY_LIST    0x86  /* send all library entries */
#define CMD_LIBRARY_ADD    0x87  /* add custom compound */
#define CMD_LIBRARY_REMOVE  0x88  /* remove custom compound */
#define CMD_SET_WAVELENGTH  0x89  /* set active wavelength */
#define CMD_GET_STATUS      0x8A  /* request status */

void ble_bridge_init(void);
void ble_bridge_poll(void);

/* Send results to ESP32-C3 (which relays over BLE) */
void ble_bridge_send_result(const polarimeter_result_t *result,
                             double rotation, double concentration,
                             const char *compound, double confidence);
void ble_bridge_send_multi(const polarimeter_result_t results[3],
                            const double rotations[3],
                            const drude_result_t *drude,
                            const library_match_t *match);
void ble_bridge_send_status(const char *status);

#endif /* BLE_BRIDGE_H */