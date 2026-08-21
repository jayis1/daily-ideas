/*
 * ble.c — FerroWeave BLE GATT service (NimBLE)
 *
 * Exposes one service with two characteristics:
 *   - FW_CMD_UUID   (write):  client → device commands (ASCII)
 *   - FW_SWEEP_UUID (notify): device → client sweep frames + status
 *
 * Sweep frames are chunked into 180-byte notify payloads (BLE MTU minus
 * overhead); the client reassembles using the frame header.
 */
#include "ble.h"
#include "proto.h"
#include <string.h>
#include <stdio.h>

/* NimBLE headers (ESP-IDF) — included in the real build:
 * #include "esp_log.h"
 * #include "host/ble_hs.h"
 * #include "services/gap/ble_svc_gap.h"
 * #include "services/gatt/ble_svc_gatt.h"
 */

static ble_cmd_cb_t g_cmd_cb = NULL;

void ble_set_cmd_callback(ble_cmd_cb_t cb) { g_cmd_cb = cb; }

void ble_init(void)
{
    /* NimBLE host config, service registration, advertising start.
     * Device name: "FerroWeave". */
}

void ble_notify_sweep(const uint8_t *payload, uint16_t len)
{
    /* Chunk into 180-byte notify payloads. The first chunk carries the
     * full frame header so the client knows the total length. */
    (void)payload; (void)len;
}

void ble_notify_status(const char *s)
{
    /* Notify a STATUS frame: [SYNC][type=0x02][len_hi][len_lo][bytes][crc][TAIL] */
    (void)s;
}