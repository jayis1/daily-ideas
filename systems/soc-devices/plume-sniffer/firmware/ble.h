/* ble.h — BLE GATT server for chromatogram streaming + run control */
#ifndef BLE_H
#define BLE_H

#include "identify.h"

/* Initialize BLE peripheral with GATT services:
 *   - Plume Control  (write: start/stop run, set method)
 *   - Plume Chromato (notify: live chromatogram samples)
 *   - Plume Results  (notify: peak table after run)
 */
void ble_init(void);

/* Notify connected clients of a new chromatogram data batch. */
void ble_send_chromatogram(const float *data, int n);

/* Notify connected clients of the final peak table. */
void ble_send_results(const identification_t *ids, int n);

/* Is a client currently connected? */
bool ble_is_connected(void);

#endif /* BLE_H */