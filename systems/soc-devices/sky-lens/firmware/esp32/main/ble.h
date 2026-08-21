/* ble.h — GATT SkyLens service */
#ifndef BLE_H
#define BLE_H
#include "sky_lens.h"

void ble_init(void);
void ble_send_event(const event_t *ev);
void ble_send_skymap(const skymap_t *m);
void ble_send_lifetime(const lifetime_result_t *lf);
bool ble_connected(void);

#endif