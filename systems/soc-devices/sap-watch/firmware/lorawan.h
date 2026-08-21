/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * lorawan.h — LoRaWAN interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_LORAWAN_H
#define SAP_WATCH_LORAWAN_H

#include <stdint.h>

/* Data for a periodic uplink report (port 1) */
typedef struct {
    float    sap_flux_cmh;          /* current sap-flux velocity (cm/h) */
    float    daily_transpiration_L; /* cumulative daily water use (L) */
    float    sapwood_temp;          /* °C (DS18B20) */
    float    air_temp;              /* °C (SHT45) */
    float    humidity;              /* %RH (SHT45) */
    float    light_lux;             /* lux (TSL2591) */
    float    vpd_kpa;               /* vapor pressure deficit (kPa) */
    float    battery_pct;           /* % (MAX17048) */
    uint8_t  heater_ok : 1;
    uint8_t  adc_ok : 1;
    uint8_t  therm1_ok : 1;
    uint8_t  therm2_ok : 1;
    uint8_t  zero_cal_ok : 1;
    uint8_t  drought_stress : 1;
    uint8_t  heater_fault : 1;
    uint8_t  low_battery : 1;
    uint16_t measurement_count;
} report_data_t;

/* Alert types for port-2 uplinks */
enum {
    ALERT_DROUGHT_STRESS = 1,
    ALERT_HEATER_FAULT = 2,
    ALERT_PROBE_DISCONNECT = 3,
    ALERT_LOW_BATTERY = 4
};

int lorawan_init(void);
int lorawan_join(void);
int lorawan_is_joined(void);
int lorawan_send_report(const report_data_t *r);
int lorawan_send_alert(uint8_t alert_type, float sap_flux, float predawn,
                       float midday, uint8_t ratio_pct);
int lorawan_check_downlink(void);
uint32_t lorawan_get_uplink_count(void);

#endif /* SAP_WATCH_LORAWAN_H */