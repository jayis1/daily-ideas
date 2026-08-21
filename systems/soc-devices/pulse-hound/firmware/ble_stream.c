/*
 * Pulse Hound — RF Signal Hunter
 * ble_stream.c — BLE GATT server, stream RSSI + spectrum + bearing to phone
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "ble_stream.h"
#include "config.h"
#include <string.h>

/* ---- BLE state ---- */
static int ble_initialized = 0;
static int ble_connected = 0;
static int ble_logging_enabled = 0;
static ble_notification_cb_t notify_cb = NULL;

/* ---- HAL stubs (platform BLE layer provides these) ---- */
extern int  ble_stack_init(void);
extern int  ble_gatt_register_service(const char *service_uuid,
                                        const char *char_uuids[], int num_chars,
                                        ble_notification_cb_t callback);
extern int  ble_advertising_start(const char *device_name);
extern int  ble_notify_char(const char *char_uuid, const uint8_t *data, uint8_t len);
extern int  ble_is_connected(void);
extern void ble_set_mode_write_cb(ble_mode_write_cb_t cb);

static ble_mode_write_cb_t mode_cb = NULL;

/* ---- Characteristic UUID list ---- */
static const char *char_uuids[] = {
    BLE_CHAR_RSSI,
    BLE_CHAR_SPECTRUM,
    BLE_CHAR_BEARING,
    BLE_CHAR_CLASS,
    BLE_CHAR_MODE,
    BLE_CHAR_BATTERY,
    BLE_CHAR_LOG_CTRL,
};
#define NUM_CHARS (sizeof(char_uuids) / sizeof(char_uuids[0]))

/* ---- Init ---- */
int ble_stream_init(ble_notification_cb_t callback, ble_mode_write_cb_t mode_callback)
{
    if (ble_initialized) return 0;
    notify_cb = callback;
    mode_cb = mode_callback;

    if (ble_stack_init() != 0)
        return -1;

    if (ble_gatt_register_service(BLE_SERVICE_UUID, char_uuids, NUM_CHARS, callback) != 0)
        return -1;

    if (ble_advertising_start(BLE_DEVICE_NAME) != 0)
        return -1;

    ble_set_mode_write_cb(mode_callback);

    ble_initialized = 1;
    return 0;
}

/* ---- Stream data ---- */
void ble_stream_rssi(float rssi_dbm)
{
    if (!ble_initialized || !ble_is_connected()) return;
    /* int16 dBm × 100 */
    int16_t val = (int16_t)(rssi_dbm * 100.0f);
    uint8_t data[2];
    data[0] = (uint8_t)(val & 0xFF);
    data[1] = (uint8_t)((val >> 8) & 0xFF);
    ble_notify_char(BLE_CHAR_RSSI, data, 2);
}

void ble_stream_spectrum_row(const uint8_t *row_data, int len)
{
    if (!ble_initialized || !ble_is_connected()) return;
    if (len > 64) len = 64; /* BLE MTU limit safety */
    ble_notify_char(BLE_CHAR_SPECTRUM, row_data, (uint8_t)len);
}

void ble_stream_bearing(float bearing_deg, float peak_rssi)
{
    if (!ble_initialized || !ble_is_connected()) return;
    uint8_t data[4];
    uint16_t brg = (uint16_t)(bearing_deg * 10.0f);
    int16_t  pk  = (int16_t)(peak_rssi * 100.0f);
    data[0] = (uint8_t)(brg & 0xFF);
    data[1] = (uint8_t)((brg >> 8) & 0xFF);
    data[2] = (uint8_t)(pk & 0xFF);
    data[3] = (uint8_t)((pk >> 8) & 0xFF);
    ble_notify_char(BLE_CHAR_BEARING, data, 4);
}

void ble_stream_classification(signal_class_t cls)
{
    if (!ble_initialized || !ble_is_connected()) return;
    uint8_t val = (uint8_t)cls;
    ble_notify_char(BLE_CHAR_CLASS, &val, 1);
}

void ble_stream_battery(int pct)
{
    if (!ble_initialized || !ble_is_connected()) return;
    uint8_t val = (uint8_t)pct;
    ble_notify_char(BLE_CHAR_BATTERY, &val, 1);
}

int ble_stream_is_connected(void)
{
    return ble_initialized && ble_is_connected();
}

/* ---- Log control ---- */
void ble_stream_set_logging(int enabled)
{
    ble_logging_enabled = enabled;
}

int ble_stream_is_logging(void)
{
    return ble_logging_enabled;
}