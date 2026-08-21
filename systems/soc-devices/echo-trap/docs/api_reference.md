# Echo Trap — API Reference

This document describes the LoRaWAN payload format (uplink/downlink) and the BLE provisioning protocol used by the companion scripts.

---

## LoRaWAN Payload Format

### Uplink: Summary (Port 1)

Sent every 15 minutes (configurable via downlink). Contains species counts and environmental data for the reporting period.

| Byte | Field | Type | Description |
|------|-------|------|-------------|
| 0 | type | uint8 | 0x01 (summary) |
| 1 | battery_pct | uint8 | Battery state-of-charge (0–100) |
| 2 | temperature_c | uint8 | Temperature + 40 (e.g., 25°C → 65) |
| 3 | humidity_pct | uint8 | Relative humidity (0–100) |
| 4–5 | target_captures | uint16 BE | Total target pest captures this period |
| 6–7 | beneficial_sighted | uint16 BE | Total beneficial insect sightings |
| 8–19 | species_counts | 12× uint8 | Per-species counts (mod 256) |

Total: 20 bytes (fits in one LoRaWAN frame at SF7/125 kHz).

### Uplink: Detection (Port 1)

Sent immediately when a target pest is detected (between summaries).

| Byte | Field | Type | Description |
|------|-------|------|-------------|
| 0 | type | uint8 | 0x02 (detection) |
| 1 | species_id | uint8 | Species class ID (0–11) |
| 2–5 | timestamp_s | uint32 BE | Uptime in seconds |
| 6 | temperature_c | uint8 | Temperature + 40 |
| 7 | humidity_pct | uint8 | Relative humidity |

Total: 8 bytes.

### Downlink: Commands (Port 2)

| Byte | Command | Value | Description |
|------|---------|-------|-------------|
| 0 | cmd_id | uint8 | Command ID |
| 1 | value | uint8 | Command value |

Commands:

| Cmd ID | Name | Value | Description |
|--------|------|-------|-------------|
| 0x01 | Set UV override | 0–255 | UV LED duty (0 = auto, 255 = 100%) |
| 0x02 | Set reporting interval | 1–60 | Interval in minutes (× 60 s) |
| 0x03 | Set confidence threshold | 50–100 | Top-1 confidence % ÷ 100 (e.g., 70 → 0.70) |
| 0x04 | Fan test | 1 | Trigger fan for 2 s (diagnostic) |
| 0x05 | Reset counts | 1 | Zero all species counters |

---

## BLE Provisioning Protocol

The Echo Trap exposes a BLE GATT server for initial provisioning (LoRaWAN keys) and diagnostic streaming.

### Service: Echo Trap Configuration

```
Service UUID:  6e41ec00-b5a3-f393-e0a9-e50e24dcca9e
```

### Characteristics

| UUID | Name | Properties | Format |
|------|------|------------|--------|
| 6e41ec01-... | Device Info | Read | uint8 fw_version, uint8 hw_version, uint8 battery, char[16] device_name |
| 6e41ec02-... | AppEUI | Read/Write | 8 bytes (big-endian) |
| 6e41ec03-... | AppKey | Read/Write | 16 bytes |
| 6e41ec04-... | DevEUI | Read/Write | 8 bytes |
| 6e41ec05-... | Save Config | Write | uint8 (1 = save to NVS, trigger OTAA join) |
| 6e41ec06-... | Species Counts | Read | 12× uint16 (current period counts) |
| 6e41ec07-... | Audio Stream | Notify | Raw I²S frames (for dataset recording) |
| 6e41ec08-... | Command | Write | uint8 cmd_id + uint8 value (same as LoRa downlink) |
| 6e41ec09-... | LoRa Status | Read | uint8 joined, int8 rssi, uint8 uplink_count |

### Provisioning flow

1. Connect to the Echo Trap over BLE (advertised as "EchoTrap-XXXX").
2. Read the **Device Info** characteristic to verify firmware version.
3. Write the **AppEUI** (8 bytes), **AppKey** (16 bytes), **DevEUI** (8 bytes).
4. Write 0x01 to **Save Config** — the device saves to NVS and attempts OTAA join.
5. Read **LoRa Status** — `joined` should become 1 within 30 seconds.
6. Disconnect. The device operates autonomously.

### Audio streaming (for dataset collection)

1. Write 0x01 to the **Command** characteristic with cmd_id=0x10 (start stream).
2. Subscribe to **Audio Stream** notifications — raw I²S frames arrive in chunks.
3. Each notification: uint16 frame_idx + uint16 count + 64× int16 samples (128 bytes).
4. Reassemble frames and save to disk (see `scripts/record_wingbeats.py`).
5. Write 0x01 with cmd_id=0x11 (stop stream) to end.

---

## License

MIT.