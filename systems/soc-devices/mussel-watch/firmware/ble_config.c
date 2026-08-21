/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * ble_config.c — BLE GATT service for phone-based configuration
 *
 * This file defines the Mussel Watch BLE GATT service with the following
 * characteristics (see README for the full UUID table):
 *
 *   0x1901  deployment_id       (R/W, 16 bytes ASCII)
 *   0x1902  sample_interval_s    (R/W, uint16)
 *   0x1903  uplink_interval_s    (R/W, uint16)
 *   0x1904  gape_threshold_deg  (R/W, float32)
 *   0x1905  closure_duration_s   (R/W, uint16)
 *   0x1906  calibrate_closed     (W only, trigger)
 *   0x1907  calibrate_open       (W only, trigger)
 *   0x1908  gape_live            (R, notify, float[4])
 *   0x1909  water_quality_live   (R, notify, struct)
 *   0x190A  alert_flags          (R, notify, uint16)
 *   0x190B  firmware_version    (R, string)
 *
 * In a production nRF Connect SDK build, these map to Zephyr BT GATT
 * service definitions. This portable C file provides the logic layer
 * that the SoftDevice callback handlers invoke.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "ble_config.h"
#include "config.h"
#include <string.h>
#include <stdio.h>

/* ---- Platform HAL stubs ---- */
extern void ble_softdevice_init(void);
extern void ble_advertise_start(const char *name);
extern void ble_advertise_stop(void);
extern void ble_notify(uint16_t uuid, const uint8_t *data, uint8_t len);
extern uint32_t rtc_get_time_ms(void);

/* BLE command queue (filled by SoftDevice write callbacks) */
typedef enum {
    BLE_CMD_NONE = 0,
    BLE_CMD_CAL_CLOSED,
    BLE_CMD_CAL_OPEN,
    BLE_CMD_SET_INTERVAL,
    BLE_CMD_SET_THRESHOLD,
    BLE_CMD_SET_DEPLOYMENT_ID,
} ble_cmd_t;

static volatile ble_cmd_t pending_cmd = BLE_CMD_NONE;
static volatile uint8_t  pending_channel = 0;
static volatile uint16_t  pending_value_u16 = 0;
static volatile float     pending_value_f = 0;

#define FIRMWARE_VERSION "1.0.0-mussel-watch"

/* ---- GATT service initialization ---- */

int ble_config_init(mussel_watch_state_t *st)
{
    /* In the nRF SDK, this would:
     *  1. Initialize the SoftDevice (sd_softdevice_enable)
     *  2. Set the GAP device name "Mussel Watch"
     *  3. Configure connection parameters (7.5 ms min, 15 ms max, 4000 ms timeout)
     *  4. Register the custom GATT service with all characteristics
     *  5. Set up advertising data (flags + service UUID)
     *
     * Here we call a HAL stub that the port layer implements. */
    ble_softdevice_init();
    return 0;
}

void ble_config_start_advertising(void)
{
    ble_advertise_start("Mussel Watch");
}

void ble_config_stop_advertising(void)
{
    ble_advertise_stop();
}

/* ---- Write handler (called by SoftDevice when a characteristic is written) ---- */

/* This function would be registered as the BLE_GATTS_EVT_WRITE handler.
 * In portable C, we expose it so the port layer can call it. */
void ble_on_write(uint16_t uuid, const uint8_t *data, uint8_t len, mussel_watch_state_t *st)
{
    switch (uuid) {
        case 0x1901:  /* deployment_id */
            if (len >= 1) {
                st->deployment_id = data[0];
            }
            break;

        case 0x1902:  /* sample_interval_s */
            if (len >= 2) {
                uint16_t val = (uint16_t)(data[0] | (data[1] << 8));
                if (val >= 10 && val <= 3600)
                    st->sample_interval_s = val;
            }
            break;

        case 0x1903:  /* uplink_interval_s */
            if (len >= 2) {
                uint16_t val = (uint16_t)(data[0] | (data[1] << 8));
                if (val >= 60 && val <= 86400)
                    st->uplink_interval_s = val;
            }
            break;

        case 0x1904:  /* gape_threshold_deg (float32 LE) */
            if (len >= 4) {
                float val;
                memcpy(&val, data, 4);
                if (val >= 0.5f && val <= 5.0f)
                    st->gape_threshold_deg = val;
            }
            break;

        case 0x1905:  /* closure_duration_s */
            if (len >= 2) {
                uint16_t val = (uint16_t)(data[0] | (data[1] << 8));
                if (val >= 10 && val <= 600)
                    st->closure_duration_s = val;
            }
            break;

        case 0x1906:  /* calibrate_closed (write trigger) */
            if (len >= 1) {
                pending_cmd = BLE_CMD_CAL_CLOSED;
                pending_channel = data[0];
            }
            break;

        case 0x1907:  /* calibrate_open (write trigger) */
            if (len >= 1) {
                pending_cmd = BLE_CMD_CAL_OPEN;
                pending_channel = data[0];
            }
            break;

        default:
            break;
    }
}

/* ---- Read handler (called by SoftDevice when a characteristic is read) ---- */

void ble_on_read(uint16_t uuid, uint8_t *data, uint8_t *len, const mussel_watch_state_t *st)
{
    switch (uuid) {
        case 0x1901:  /* deployment_id */
            data[0] = st->deployment_id;
            *len = 1;
            break;

        case 0x1902:
            data[0] = (uint8_t)(st->sample_interval_s & 0xFF);
            data[1] = (uint8_t)(st->sample_interval_s >> 8);
            *len = 2;
            break;

        case 0x1903:
            data[0] = (uint8_t)(st->uplink_interval_s & 0xFF);
            data[1] = (uint8_t)(st->uplink_interval_s >> 8);
            *len = 2;
            break;

        case 0x1904: {
            float val = st->gape_threshold_deg;
            memcpy(data, &val, 4);
            *len = 4;
            break;
        }

        case 0x1905:
            data[0] = (uint8_t)(st->closure_duration_s & 0xFF);
            data[1] = (uint8_t)(st->closure_duration_s >> 8);
            *len = 2;
            break;

        case 0x1908: {  /* gape_live: 4 × float32 = 16 bytes */
            for (int i = 0; i < MAX_MUSSELS; i++) {
                float val = st->gape_angle[i];
                memcpy(&data[i * 4], &val, 4);
            }
            *len = 16;
            break;
        }

        case 0x1909: {  /* water_quality_live: temp(4) + DO(4) + depth(4) + battery(4) = 16 bytes */
            memcpy(&data[0],  &st->water_temp_c, 4);
            memcpy(&data[4],  &st->dissolved_o2_mgl, 4);
            memcpy(&data[8],  &st->water_depth_m, 4);
            memcpy(&data[12], &st->battery_v, 4);
            *len = 16;
            break;
        }

        case 0x190A: {  /* alert_flags: uint16 */
            uint16_t flags = (uint16_t)st->current_alert;
            data[0] = (uint8_t)(flags & 0xFF);
            data[1] = (uint8_t)(flags >> 8);
            *len = 2;
            break;
        }

        case 0x190B:  /* firmware_version */
            strncpy((char *)data, FIRMWARE_VERSION, 31);
            *len = (uint8_t)strlen(FIRMWARE_VERSION);
            break;

        default:
            *len = 0;
            break;
    }
}

/* ---- Poll for pending commands ---- */

int ble_config_get_command(mussel_watch_state_t *st)
{
    if (pending_cmd == BLE_CMD_NONE)
        return 0;

    ble_cmd_t cmd = pending_cmd;
    uint8_t ch = pending_channel;
    pending_cmd = BLE_CMD_NONE;

    switch (cmd) {
        case BLE_CMD_CAL_CLOSED:
            if (ch < st->n_mussels) {
                /* Record current Hall voltage as 0° (closed) */
                extern float gape_read_hall_mv(uint8_t channel);
                st->cal_closed_mv[ch] = gape_read_hall_mv(ch);
                st->cal_valid[ch] = 1;
                extern int gape_cal_save(const mussel_watch_state_t *st);
                gape_cal_save(st);
            }
            break;

        case BLE_CMD_CAL_OPEN:
            if (ch < st->n_mussels) {
                extern float gape_read_hall_mv(uint8_t channel);
                st->cal_open_mv[ch] = gape_read_hall_mv(ch);
                st->cal_valid[ch] = 1;
                extern int gape_cal_save(const mussel_watch_state_t *st);
                gape_cal_save(st);
            }
            break;

        default:
            break;
    }
    return 1;
}

/* ---- Notify updates ---- */

void ble_config_update_notify(const mussel_watch_state_t *st)
{
    /* Send gape_live notification */
    uint8_t gape_data[16];
    for (int i = 0; i < MAX_MUSSELS; i++) {
        float val = st->gape_angle[i];
        memcpy(&gape_data[i * 4], &val, 4);
    }
    ble_notify(0x1908, gape_data, 16);

    /* Send water_quality_live notification */
    uint8_t wq_data[16];
    memcpy(&wq_data[0],  &st->water_temp_c, 4);
    memcpy(&wq_data[4],  &st->dissolved_o2_mgl, 4);
    memcpy(&wq_data[8],  &st->water_depth_m, 4);
    memcpy(&wq_data[12], &st->battery_v, 4);
    ble_notify(0x1909, wq_data, 16);

    /* Send alert_flags notification */
    uint8_t alert_data[2] = {
        (uint8_t)(st->current_alert & 0xFF),
        (uint8_t)(st->current_alert >> 8)
    };
    ble_notify(0x190A, alert_data, 2);
}

void ble_config_poll(mussel_watch_state_t *st)
{
    /* In a SoftDevice-based build, BLE events are handled by callbacks.
     * This poll function is for the cooperative scheduler to check
     * for pending commands from the write handler. */
    ble_config_get_command(st);
}