/*
 * Levia Forge — BLE Bridge Header
 * SPDX-License-Identifier: MIT
 */
#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

void ble_bridge_init(void);
void ble_bridge_send_state(void *state);
void ble_bridge_poll(void *state);

#endif /* BLE_BRIDGE_H */