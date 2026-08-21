/*
 * Flux Ring — ble_service.c
 * BLE GATT service for Flux Ring field data streaming.
 *
 * SPDX-License-Identifier: MIT
 */

#include "ble_service.h"
#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(ble_service, LOG_LEVEL_INF);

/* Connection reference */
static struct bt_conn *current_conn;
static bool is_connected = false;

/* Notification enabled flags */
static bool field_notify_enabled = false;

/* GATT characteristic value storage */
static float field_x, field_y, field_z, magnitude_val;
static uint16_t heading_val;
static uint8_t pole_val, sample_rate_val, mode_val, battery_val;
static char device_info[] = "Flux Ring v1.0";

/* Stream packet buffer (24 bytes) */
static uint8_t stream_buf[24];

/*---------------------------------------------------------------------------*/
/* Connection callbacks                                                       */
/*---------------------------------------------------------------------------*/
static void connected(struct bt_conn *conn, uint8_t err)
{
    if (err) {
        LOG_ERR("BLE connection failed (err 0x%02X)", err);
        return;
    }
    current_conn = bt_conn_ref(conn);
    is_connected = true;
    LOG_INF("BLE client connected");
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
    LOG_INF("BLE client disconnected (reason 0x%02X)", reason);
    if (current_conn) {
        bt_conn_unref(current_conn);
        current_conn = NULL;
    }
    is_connected = false;
    field_notify_enabled = false;
}

static struct bt_conn_cb conn_callbacks = {
    .connected    = connected,
    .disconnected = disconnected,
};

/*---------------------------------------------------------------------------*/
/* GATT service definition                                                    */
/*---------------------------------------------------------------------------*/

/* Custom 16-bit UUIDs */
static struct bt_uuid_16 flux_service_uuid = BT_UUID_INIT_16(FLUX_RING_SERVICE_UUID);

/* CCC descriptor callback (for notifications) */
static void field_ccc_cfg_changed(const struct bt_uuid *uuid,
                                  uint16_t attr_val,
                                  uint16_t handle)
{
    field_notify_enabled = (attr_val == BT_GATT_CCC_NOTIFY);
    LOG_INF("Field notifications %s", field_notify_enabled ? "enabled" : "disabled");
}

/* GATT service with all characteristics */
BT_GATT_SERVICE_DEFINE(flux_service,
    BT_GATT_PRIMARY_SERVICE(&flux_service_uuid),

    /* Field X (read/notify) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_FIELD_X),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &field_x),
    BT_GATT_CCC(field_ccc_cfg_changed,
                BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    /* Field Y (read/notify) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_FIELD_Y),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &field_y),
    BT_GATT_CCC(field_ccc_cfg_changed,
                BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    /* Field Z (read/notify) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_FIELD_Z),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &field_z),
    BT_GATT_CCC(field_ccc_cfg_changed,
                BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    /* Magnitude (read/notify) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_MAGNITUDE),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &magnitude_val),
    BT_GATT_CCC(field_ccc_cfg_changed,
                BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    /* Heading (read/notify) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_HEADING),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &heading_val),
    BT_GATT_CCC(field_ccc_cfg_changed,
                BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    /* Dominant Pole (read) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_POLE),
                           BT_GATT_CHRC_READ,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &pole_val),

    /* Sample Rate (read/write) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_SAMPLE_RATE),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_WRITE,
                           BT_GATT_PERM_READ | BT_GATT_PERM_WRITE,
                           NULL, NULL, &sample_rate_val),

    /* Mode (read/write) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_MODE),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_WRITE,
                           BT_GATT_PERM_READ | BT_GATT_PERM_WRITE,
                           NULL, NULL, &mode_val),

    /* Battery Level (read) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_BATTERY),
                           BT_GATT_CHRC_READ,
                           BT_GATT_PERM_READ,
                           NULL, NULL, &battery_val),

    /* Device Info (read) */
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(FLUX_CHAR_DEVICE_INFO),
                           BT_GATT_CHRC_READ,
                           BT_GATT_PERM_READ,
                           NULL, NULL, device_info),
);

/* Advertising data */
static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA(BT_DATA_UUID16_ALL, (uint8_t[]){ 0xB0, 0xFF }, 2),
};

/* Scan response data */
static uint8_t scan_resp_data[20];
static struct bt_data scan_resp[] = {
    BT_DATA(BT_DATA_MANUFACTURER_DATA, scan_resp_data, 8),
};

int ble_service_init(void)
{
    int rc = bt_enable(NULL);
    if (rc != 0) {
        LOG_ERR("Bluetooth enable failed (rc %d)", rc);
        return rc;
    }

    bt_conn_cb_register(&conn_callbacks);

    /* Start advertising */
    rc = bt_le_adv_start(BT_LE_ADV_CONN_FAST, ad, ARRAY_SIZE(ad),
                         scan_resp, ARRAY_SIZE(scan_resp));
    if (rc != 0) {
        LOG_ERR("Advertising start failed (rc %d)", rc);
        return rc;
    }

    LOG_INF("BLE service initialized, advertising as Flux Ring");
    return 0;
}

void ble_service_update_field(float x, float y, float z,
                              float magnitude,
                              compass_heading_t heading,
                              pole_t pole,
                              uint8_t battery_pct)
{
    field_x = x;
    field_y = y;
    field_z = z;
    magnitude_val = magnitude;
    heading_val = heading;
    pole_val = (uint8_t)pole;
    battery_val = battery_pct;

    /* Send notifications if enabled */
    if (field_notify_enabled && current_conn) {
        bt_gatt_notify(current_conn, &flux_service.attrs[1],
                       &field_x, sizeof(field_x));
    }
}

void ble_service_update_advertising(float magnitude,
                                    compass_heading_t heading,
                                    pole_t pole,
                                    uint8_t mode)
{
    /* Pack manufacturer-specific data into scan response:
     * [mfr_id(2)] [magnitude(2)] [heading(2)] [pole(1)] [mode(1)]
     */
    uint16_t mag_int = (uint16_t)(magnitude * 100.0f);
    if (mag_int > 0xFFFF) mag_int = 0xFFFF;

    scan_resp_data[0] = 0x59;  /* Manufacturer ID low (placeholder) */
    scan_resp_data[1] = 0x00;  /* Manufacturer ID high */
    scan_resp_data[2] = mag_int & 0xFF;
    scan_resp_data[3] = (mag_int >> 8) & 0xFF;
    scan_resp_data[4] = heading & 0xFF;
    scan_resp_data[5] = (heading >> 8) & 0xFF;
    scan_resp_data[6] = (uint8_t)pole;
    scan_resp_data[7] = mode;
}

void ble_stream_sample(const field_vector_t *field,
                       const accel_data_t *accel,
                       const baro_data_t *baro,
                       compass_heading_t heading,
                       uint32_t timestamp_ms)
{
    /* Pack binary stream packet:
     * Offset  Size  Field
     * 0       4     timestamp_ms
     * 4       4     field.x (float)
     * 8       4     field.y (float)
     * 12      4     field.z (float)
     * 16      2     accel.x (int16, 0.001g/LSB)
     * 18      2     accel.y
     * 20      2     accel.z
     * 22      2     heading (uint16 degrees)
     * Total: 24 bytes
     */
    memcpy(&stream_buf[0],  &timestamp_ms, 4);
    memcpy(&stream_buf[4],  &field->x, 4);
    memcpy(&stream_buf[8],  &field->y, 4);
    memcpy(&stream_buf[12], &field->z, 4);

    int16_t ax = (int16_t)(accel->x * 1000.0f);
    int16_t ay = (int16_t)(accel->y * 1000.0f);
    int16_t az = (int16_t)(accel->z * 1000.0f);
    memcpy(&stream_buf[16], &ax, 2);
    memcpy(&stream_buf[18], &ay, 2);
    memcpy(&stream_buf[20], &az, 2);
    memcpy(&stream_buf[22], &heading, 2);

    /* Send via notification on the Field X characteristic */
    if (current_conn && field_notify_enabled) {
        bt_gatt_notify(current_conn, &flux_service.attrs[1],
                       stream_buf, sizeof(stream_buf));
    }
}

bool ble_is_connected(void)
{
    return is_connected;
}