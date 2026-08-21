/*
 * Tremor Tile — LoRa Radio Header
 * lora_radio.h
 */

#ifndef TREMOR_TILE_LORA_RADIO_H
#define TREMOR_TILE_LORA_RADIO_H

#include <stdint.h>
#include <stdbool.h>
#include "anomaly_detect.h"

// Packet types
#define PKT_TYPE_HEARTBEAT       0x01
#define PKT_TYPE_SPECTRAL        0x02
#define PKT_TYPE_ALERT           0x03
#define PKT_TYPE_RAW_DATA        0x04

// Maximum payload size
#define LORA_MAX_PAYLOAD         255

// LoRa packet structure
typedef struct {
    uint8_t type;               // Packet type
    uint16_t device_id;          // Device identifier
    uint16_t length;             // Payload length
    uint8_t data[LORA_MAX_PAYLOAD];  // Payload data
} lora_packet_t;

// Initialize SX1262 LoRa radio
void lora_radio_init(void);

// Send a heartbeat packet
void lora_radio_send_heartbeat(uint16_t device_id, uint8_t battery_pct, uint8_t status_flags);

// Enqueue a packet for transmission
void lora_radio_enqueue(lora_packet_t *pkt);

// Enqueue an alert packet (high priority, SF12)
void lora_radio_enqueue_alert(alert_t *alert);

// Check if there are packets pending in the TX queue
bool lora_radio_tx_pending(void);

// Send the next packet in the TX queue
void lora_radio_send_next(void);

#endif // TREMOR_TILE_LORA_RADIO_H