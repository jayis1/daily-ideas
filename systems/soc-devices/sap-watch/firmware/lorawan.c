/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * lorawan.c — STM32WL internal sub-GHz radio driver + LoRaWAN MAC
 *             Uplink packet assembly, downlink config parsing
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 *
 * NOTE: This module interfaces with the STM32WL LoRaWAN stack (STM32Cube
 * "LoRaWAN End Node" example basis). The radio is the internal SX1262-
 * equivalent core; no external SPI radio chip is used.
 */

#include "config.h"
#include "lorawan.h"
#include "heat_ratio.h"
#include <string.h>
#include <math.h>

/* ---- Platform radio stubs (STM32WL LoRaWAN stack wrappers) ---- */
extern int  radio_init(uint8_t region);
extern int  radio_join_otaa(const uint8_t *appeui, const uint8_t *appkey,
                             const uint8_t *deveui, uint32_t timeout_ms);
extern int  radio_send(uint8_t port, const uint8_t *data, uint8_t len,
                       uint8_t confirmed);
extern int  radio_recv(uint8_t *port, uint8_t *data, uint8_t maxlen);
extern int  radio_is_joined(void);
extern uint32_t radio_get_downlink_count(void);

/* ---- Module state ---- */
static int lorawan_joined = 0;
static uint32_t uplink_counter = 0;

/* LoRaWAN credentials (provisioned via program button + serial console) */
static uint8_t dev_eui[8] = {0};
static uint8_t app_eui[8] = {0};
static uint8_t app_key[16] = {0};

int lorawan_init(void)
{
#if LORA_REGION_868
    return radio_init(0);  /* EU 868 */
#else
    return radio_init(1);  /* US 915 */
#endif
}

int lorawan_join(void)
{
    /* Read credentials from flash (storage module) */
    extern int storage_get_credentials(uint8_t *deveui, uint8_t *appeui,
                                        uint8_t *appkey);
    if (storage_get_credentials(dev_eui, app_eui, app_key) != 0)
        return -1;

    int ret = radio_join_otaa(app_eui, app_key, dev_eui, LORA_JOIN_TIMEOUT_MS);
    lorawan_joined = (ret == 0);
    return ret;
}

int lorawan_is_joined(void)
{
    return lorawan_joined = radio_is_joined();
}

/*
 * Pack a port-1 periodic report.
 * All numeric fields are scaled to int16/uint16 to save airtime.
 */
int lorawan_send_report(const report_data_t *r)
{
    if (!lorawan_is_joined())
        return -1;

    uint8_t pkt[UPLINK_PORT1_BYTES];
    int idx = 0;

    /* sap_flux_velocity: cm/h × 100 → int16 */
    int16_t sf = (int16_t)(r->sap_flux_cmh * 100.0f);
    pkt[idx++] = (sf >> 8) & 0xFF;
    pkt[idx++] = sf & 0xFF;

    /* daily_transpiration: L × 100 → uint16 */
    uint16_t dt = (uint16_t)(r->daily_transpiration_L * 100.0f);
    pkt[idx++] = (dt >> 8) & 0xFF;
    pkt[idx++] = dt & 0xFF;

    /* sapwood_temp: °C × 100 → int16 */
    int16_t st = (int16_t)(r->sapwood_temp * 100.0f);
    pkt[idx++] = (st >> 8) & 0xFF;
    pkt[idx++] = st & 0xFF;

    /* air_temp: °C × 100 → int16 */
    int16_t at = (int16_t)(r->air_temp * 100.0f);
    pkt[idx++] = (at >> 8) & 0xFF;
    pkt[idx++] = at & 0xFF;

    /* humidity: % × 100 → uint16 */
    uint16_t rh = (uint16_t)(r->humidity * 100.0f);
    pkt[idx++] = (rh >> 8) & 0xFF;
    pkt[idx++] = rh & 0xFF;

    /* light_lux: uint16 (capped) */
    uint16_t lux = (uint16_t)(r->light_lux > 65535.0f ? 65535 : r->light_lux);
    pkt[idx++] = (lux >> 8) & 0xFF;
    pkt[idx++] = lux & 0xFF;

    /* vpd: kPa × 100 → uint16 */
    uint16_t vpd = (uint16_t)(r->vpd_kpa * 100.0f);
    pkt[idx++] = (vpd >> 8) & 0xFF;
    pkt[idx++] = vpd & 0xFF;

    /* battery_pct: uint8 */
    pkt[idx++] = (uint8_t)r->battery_pct;

    /* probe_health: bitfield */
    uint8_t health = 0;
    if (r->heater_ok)     health |= 0x01;
    if (r->adc_ok)        health |= 0x02;
    if (r->therm1_ok)     health |= 0x04;
    if (r->therm2_ok)     health |= 0x08;
    if (r->zero_cal_ok)   health |= 0x10;
    pkt[idx++] = health;

    /* measurement_count: uint16 */
    uint16_t mc = r->measurement_count;
    pkt[idx++] = (mc >> 8) & 0xFF;
    pkt[idx++] = mc & 0xFF;

    /* flags: bitfield */
    uint8_t flags = 0;
    if (r->drought_stress)  flags |= 0x01;
    if (r->heater_fault)    flags |= 0x02;
    if (r->low_battery)     flags |= 0x04;
    pkt[idx++] = flags;

    uplink_counter++;
    return radio_send(1, pkt, idx, 0);  /* unconfirmed */
}

/*
 * Pack a port-2 anomaly alert (sent immediately).
 */
int lorawan_send_alert(uint8_t alert_type, float sap_flux, float predawn,
                        float midday, uint8_t ratio_pct)
{
    if (!lorawan_is_joined())
        return -1;

    uint8_t pkt[UPLINK_PORT2_BYTES];
    int idx = 0;

    pkt[idx++] = alert_type;

    int16_t sf = (int16_t)(sap_flux * 100.0f);
    pkt[idx++] = (sf >> 8) & 0xFF;
    pkt[idx++] = sf & 0xFF;

    int16_t pd = (int16_t)(predawn * 100.0f);
    pkt[idx++] = (pd >> 8) & 0xFF;
    pkt[idx++] = pd & 0xFF;

    int16_t md = (int16_t)(midday * 100.0f);
    pkt[idx++] = (md >> 8) & 0xFF;
    pkt[idx++] = md & 0xFF;

    pkt[idx++] = ratio_pct;

    return radio_send(2, pkt, idx, 1);  /* confirmed — we want ack */
}

/*
 * Parse a port-3 downlink config command.
 * Returns 0 on success, -1 on unknown command.
 */
int lorawan_handle_downlink(const uint8_t *data, uint8_t len)
{
    if (len < 1)
        return -1;

    uint8_t cmd = data[0];
    uint16_t value = (len >= 3) ? ((data[1] << 8) | data[2]) : 0;

    switch (cmd) {
    case 1:  /* set measurement interval (minutes) */
        extern void scheduler_set_interval(uint16_t minutes);
        scheduler_set_interval(value);
        break;

    case 2:  /* set sapwood area (cm²) */
        heat_ratio_set_sapwood_area((float)value);
        break;

    case 3:  /* trigger zero-flow calibration */
        extern void scheduler_trigger_zero_cal(void);
        scheduler_trigger_zero_cal();
        break;

    case 4:  /* set wound factor (×100) */
        heat_ratio_set_wound_factor((float)value / 100.0f);
        break;

    case 5:  /* force immediate measurement */
        extern void scheduler_force_measurement(void);
        scheduler_force_measurement();
        break;

    default:
        return -1;
    }

    return 0;
}

/*
 * Check for and process pending downlinks.
 */
int lorawan_check_downlink(void)
{
    uint8_t port, data[DOWNLINK_MAX_BYTES];
    int n = radio_recv(&port, data, sizeof(data));
    if (n <= 0)
        return 0;  /* nothing pending */

    if (port == 3)
        return lorawan_handle_downlink(data, (uint8_t)n);

    return 0;
}

uint32_t lorawan_get_uplink_count(void)
{
    return uplink_counter;
}