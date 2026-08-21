/*
 * ble_bridge.h — UART protocol to ESP32-C3 BLE bridge
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include "radiometry.h"
#include "solar_pos.h"
#include <stdint.h>
#include <stdbool.h>

/* Initialize UART1 to ESP32-C3 (921600 baud) */
void ble_bridge_init(void);

/* Send live measurement data (DNI + AOD at all wavelengths) */
void ble_bridge_send_measurement(const radiometry_result_t *result,
                                  const solar_pos_t *pos,
                                  float bat_v, const char *state);

/* Send Langley calibration progress */
void ble_bridge_send_langley(uint16_t points, float r2, float v0_870);

/* Send status */
void ble_bridge_send_status(const char *state, float sun_az, float sun_el,
                             float bat_v, bool gps_fix);

/* Send error */
void ble_bridge_send_error(const char *msg);

#endif /* BLE_BRIDGE_H */