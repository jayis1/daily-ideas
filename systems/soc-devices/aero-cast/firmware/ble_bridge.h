/* ble_bridge.h — UART protocol to ESP32-C3 BLE/Wi-Fi bridge */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include "sonic.h"
#include "wind.h"
#include "bme280.h"

/* Initialize UART to ESP32-C3 */
void ble_bridge_init(void);

/* Send wind data packet (20 Hz) */
void ble_send_wind(const wind_vector_t *wind, const bme280_data_t *atm, uint32_t timestamp);

/* Send turbulence stats packet */
void ble_send_turbulence(const turbulence_stats_t *stats, uint32_t elapsed_s);

/* Send status message (string) */
void ble_send_status(const char *msg);

/* Poll for incoming commands from phone (via ESP32-C3) */
bool ble_poll_command(uint8_t *cmd, uint8_t *arg, uint8_t *arg_len);

/* Send raw TOF data (for calibration mode) */
void ble_send_raw(const sonic_sample_t *sample);

#endif /* BLE_BRIDGE_H */