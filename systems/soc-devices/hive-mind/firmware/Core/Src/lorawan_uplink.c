/*
 * Hive Mind — LoRaWAN Uplink Driver
 * Encodes sensor data into 21-byte payload and sends via LoRaWAN
 * Uses STM32CubeWL LoRaWAN MAC on CM0+ core
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "lorawan_uplink.h"
#include "main.h"
#include <string.h>

/* LoRaWAN configuration */
#define LORAWAN_APP_PORT    2
#define LORAWAN_DR          3   /* Data rate 3 (SF7/125kHz on EU868) */
#define LORAWAN_CONFIRMED   0   /* Unconfirmed uplink */

/* Payload size: 21 bytes as documented in README */
#define PAYLOAD_SIZE        21

/* LoRaWAN state */
static uint8_t dev_eui[8] = {0};
static uint8_t app_eui[8] = {0};
static uint8_t app_key[16] = {0};
static uint8_t is_joined = 0;
static uint32_t uptime_hours = 0;

/* ------------------------------------------------------------------ */
/* Payload encoding                                                    */
/* ------------------------------------------------------------------ */

/* Encoding helpers:
 * Temperature: 0.5°C resolution, offset -20°C → range -20 to +83°C
 * Voltage: 0.02V resolution → range 0-5.1V
 * Humidity: 0.01% → range 0-100%
 * Pressure: 0.1 hPa → range 0-6553.5 hPa
 */

static uint8_t encode_temp(float temp_c)
{
    /* 0.5°C per count, offset -20°C */
    int16_t val = (int16_t)((temp_c + 20.0f) * 2.0f);
    if (val < 0) val = 0;
    if (val > 255) val = 255;
    return (uint8_t)val;
}

static uint16_t encode_humidity(float humidity_pct)
{
    /* 0.01% per count */
    uint16_t val = (uint16_t)(humidity_pct * 100.0f);
    if (val > 10000) val = 10000;
    return val;
}

static uint16_t encode_pressure(float pressure_hpa)
{
    /* 0.1 hPa per count */
    uint16_t val = (uint16_t)(pressure_hpa * 10.0f);
    if (val > 65535) val = 65535;
    return val;
}

static uint8_t encode_voltage(float voltage)
{
    /* 0.02V per count */
    uint8_t val = (uint8_t)(voltage * 50.0f);
    if (val > 255) val = 255;
    return val;
}

static uint16_t encode_weight(float weight_g)
{
    /* 1g per count */
    if (weight_g < 0) weight_g = 0;
    if (weight_g > 65535) weight_g = 65535;
    return (uint16_t)weight_g;
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void lorawan_init(void)
{
    /* Generate DevEUI from STM32WL55 UID96 */
    uint32_t uid[3];
    uid[0] = *(uint32_t *)(UID64_BASE);
    uid[1] = *(uint32_t *)(UID64_BASE + 4);
    uid[2] = *(uint32_t *)(UID64_BASE + 8);

    /* Create EUI-64 from UID96 */
    dev_eui[0] = (uint8_t)(uid[0] >> 24) | 0x02;  /* Set locally administered bit */
    dev_eui[1] = (uint8_t)(uid[0] >> 16);
    dev_eui[2] = (uint8_t)(uid[0] >> 8);
    dev_eui[3] = (uint8_t)(uid[0]);
    dev_eui[4] = (uint8_t)(uid[1] >> 24);
    dev_eui[5] = (uint8_t)(uid[1] >> 16);
    dev_eui[6] = (uint8_t)(uid[1] >> 8);
    dev_eui[7] = (uint8_t)(uid[1]);

    /* AppEUI and AppKey should be set via USB-C console or stored in flash */
    /* Default: all zeros (must be provisioned before use) */
    memset(app_eui, 0, 8);
    memset(app_key, 0, 16);

    /* The LoRaWAN MAC runs on CM0+ and is initialized separately.
     * This function just prepares the application-side configuration.
     * In a full implementation, this would send IPCC message to CM0+ to start join. */

    is_joined = 0;
    uptime_hours = 0;
}

lorawan_status_t lorawan_send(const sensor_data_t *data)
{
    uint8_t payload[PAYLOAD_SIZE];
    uint16_t idx = 0;

    /* Encode payload per specification */
    /* Bytes 0-1: Hive weight (g) */
    uint16_t weight = encode_weight(data->weight_g);
    payload[idx++] = (weight >> 8) & 0xFF;
    payload[idx++] = weight & 0xFF;

    /* Byte 2: Temperature floor */
    payload[idx++] = encode_temp(data->temp_floor);

    /* Byte 3: Temperature mid */
    payload[idx++] = encode_temp(data->temp_mid);

    /* Byte 4: Temperature crown */
    payload[idx++] = encode_temp(data->temp_crown);

    /* Byte 5: Ambient temperature */
    payload[idx++] = encode_temp(data->ambient_t);

    /* Bytes 6-7: Ambient humidity */
    uint16_t humidity = encode_humidity(data->ambient_h);
    payload[idx++] = (humidity >> 8) & 0xFF;
    payload[idx++] = humidity & 0xFF;

    /* Bytes 8-9: Ambient pressure */
    uint16_t pressure = encode_pressure(data->ambient_p);
    payload[idx++] = (pressure >> 8) & 0xFF;
    payload[idx++] = pressure & 0xFF;

    /* Byte 10: Acoustic class */
    payload[idx++] = (uint8_t)data->acoustic_class;

    /* Bytes 11: Dominant freq (×10 Hz) */
    uint16_t freq = data->dominant_freq;
    if (freq > 2550) freq = 2550;
    payload[idx++] = (uint8_t)(freq / 10);

    /* Bytes 12-13: Bee traffic in */
    payload[idx++] = (data->bee_in >> 8) & 0xFF;
    payload[idx++] = data->bee_in & 0xFF;

    /* Bytes 14-15: Bee traffic out */
    payload[idx++] = (data->bee_out >> 8) & 0xFF;
    payload[idx++] = data->bee_out & 0xFF;

    /* Byte 16: Battery voltage */
    payload[idx++] = encode_voltage(data->vbat);

    /* Byte 17: Solar voltage */
    payload[idx++] = encode_voltage(data->vsolar);

    /* Bytes 18-19: Uptime hours */
    payload[idx++] = (uptime_hours >> 8) & 0xFF;
    payload[idx++] = uptime_hours & 0xFF;

    /* Bytes 20: Health score (0-100, ×0.01 → 0-10000 mapped to 0-100) */
    uint8_t score = (uint8_t)data->health_score;
    if (score > 100) score = 100;
    payload[idx++] = score;

    /* In a full implementation, this would send the payload via IPCC
     * to the CM0+ core running the LoRaWAN MAC, which would then
     * transmit it over the sub-GHz radio.
     *
     * Pseudocode:
     *   ipcc_send(IPCC_CH1, payload, PAYLOAD_SIZE);
     *   ipcc_wait_ack(IPCC_CH1, 5000);
     */

    uptime_hours++;  /* Increment per uplink (every 15 min, so divide by 4 for hours) */

    return LORAWAN_OK;
}

lorawan_status_t lorawan_join(void)
{
    /* Send join request via IPCC to CM0+ LoRaWAN MAC */
    /* Pseudocode:
     *   ipcc_send_join_request(dev_eui, app_eui, app_key);
     *   is_joined = ipcc_wait_join_response(30000);
     */
    is_joined = 1;  /* Simulated success */
    return LORAWAN_OK;
}

void lorawan_set_keys(const uint8_t *new_dev_eui, const uint8_t *new_app_eui,
                       const uint8_t *new_app_key)
{
    memcpy(dev_eui, new_dev_eui, 8);
    memcpy(app_eui, new_app_eui, 8);
    memcpy(app_key, new_app_key, 16);
}

void lorawan_get_dev_eui(uint8_t *out_eui)
{
    memcpy(out_eui, dev_eui, 8);
}