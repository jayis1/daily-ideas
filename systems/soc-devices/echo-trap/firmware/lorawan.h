/*
 * lorawan.h — SX1262 LoRaWAN uplink/downlink
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_LORAWAN_H
#define ECHO_TRAP_LORAWAN_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    UPLINK_SUMMARY = 0,
    UPLINK_DETECTION = 1,
    UPLINK_STATUS = 2,
} uplink_type_t;

typedef struct {
    uint8_t     species_id;
    uint32_t    timestamp_s;
    float       temperature_c;
    float       humidity_pct;
} detection_payload_t;

typedef struct {
    uint16_t    counts[SPECIES_COUNT];
    float       temperature_c;
    float       humidity_pct;
    uint8_t     battery_pct;
    uint16_t    target_captures;
    uint16_t    beneficial_sighted;
} summary_payload_t;

typedef struct {
    uplink_type_t type;
    union {
        detection_payload_t detection;
        summary_payload_t    summary;
    } u;
} lorawan_uplink_t;

void lorawan_init(void);
bool lorawan_join(void);
bool lorawan_send_uplink(const lorawan_uplink_t *pkt);
void lorawan_process_downlink(void);

#endif /* ECHO_TRAP_LORAWAN_H */