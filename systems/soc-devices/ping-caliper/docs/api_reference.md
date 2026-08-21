# Ping Caliper — API Reference

This document describes the BLE GATT interface, the UART framing protocol between the STM32G474 and ESP32-C3, and the Python helper scripts that talk to the device.

---

## 1. BLE GATT Service

**Service UUID**: `6e40fb10-b5a3-f393-e0a9-e50e24dcca9e`

### Characteristics

| UUID (last 2 bytes) | Name | Properties | Description |
|---------------------|------|------------|-------------|
| `...11fb...` | Measurement | read, notify | Latest thickness + flaw result (binary, ~40 bytes) |
| `...12fb...` | A-scan | read, notify | Chunked A-scan envelope (up to 200 bytes/chunk) |
| `...13fb...` | Status | read, notify | 4 bytes: armed, measuring, battery %, reserved |
| `...14fb...` | Command | write (no response) | Phone → device commands (see §3) |
| `...15fb...` | Config | read, write | 64-byte config blob (see §4) |
| `...16fb...` | Material | read, write | 1 byte index + 23-byte name |

### Device Information Service (0x180A)

Standard DIS with Manufacturer = "SoC Device Inventions", Model = "Ping Caliper v1.0", Firmware = "1.0.0", Battery (0x2A38, uint8 0-100).

---

## 2. UART Frame Protocol (STM32 ↔ ESP32-C3)

```
[SOF0=0xAA][SOF1=0x55][LEN][CMD][payload[LEN]][CRC16 lo][CRC16 hi][EOF0=0x0D][EOF1=0x0A]
```

- **LEN**: payload length (0–250)
- **CMD**: command byte (see §3)
- **CRC16**: CRC-CCITT (poly 0x1021, init 0xFFFF) over [LEN, CMD, payload]
- All multi-byte fields are little-endian

---

## 3. Commands

### 3.1. STM32 → ESP32 (notifications, unsolicited)

| CMD | Name | Payload |
|-----|------|---------|
| 0x01 | Notify Measurement | thickness_mm(f32) + tof_ns(f32) + velocity_mps(u32) + valid(u8) + flaw_detected(u8) + flaw_depth_mm(f32) + flaw_equiv_mm(f32) + material(16 bytes) + battery_pct(i16) |
| 0x02 | Notify Flaw | detected(u8) + depth_mm(f32) + equiv_mm(f32) + peak_amp(f32) |
| 0x03 | Notify A-scan Chunk | chunk_idx(u16) + total_chunks(u16) + count(u16) + 64 samples (u16 each, 128 bytes) |
| 0x04 | Notify Battery | battery_pct(u8) + battery_mv(u16) + charging(u8) |
| 0x05 | Notify Status | armed(u8) + measuring(u8) + battery_pct(u8) + reserved(u8) |
| 0x06 | Notify Log Entry | sequence(u32) + timestamp(u32) + thickness_mm(f32) + ... (matches log_entry_t) |

### 3.2. ESP32 → STM32 (requests)

| CMD | Name | Payload | Response |
|-----|------|---------|----------|
| 0x10 | Get Measurement | (none) | ACK + current measurement blob |
| 0x11 | Get A-scan | (none) | ACK + A-scan chunks (0x03 notifications) |
| 0x12 | Get Config | (none) | ACK + 64-byte config blob |
| 0x13 | Set Config | 64-byte config blob | ACK |
| 0x14 | Set Material | index(u8) + name(23 bytes) | ACK |
| 0x15 | Set Mode | mode(u8): 0=PE, 1=EE, 2=Flaw | ACK |
| 0x16 | Set Gate | start_us(u16) + width_us(u16) + threshold(u16) + enabled(u8) | ACK |
| 0x17 | Calibrate Zero | (none) | ACK (starts zero-probe calibration) |
| 0x18 | Calibrate Velocity | known_thickness_mm(f32) | ACK |
| 0x19 | Fire Single | (none) | ACK + measurement notification |
| 0x1A | Start Continuous | (none) | ACK + periodic notifications |
| 0x1B | Stop Continuous | (none) | ACK |
| 0x1C | List Materials | (none) | ACK + material list (chunked) |
| 0x1D | Get Log | start_seq(u32) + count(u8) | ACK + log entries |
| 0x1E | OTA Reset | url(128 bytes) | ACK + ESP32 reboots into OTA |
| 0x1F | Set TGC | shape(u8) + start_db(f32) + end_db(f32) + window_us(u16) + lna_idx(u8) | ACK |

### 3.3. ACK/NACK

| CMD | Name | Payload |
|-----|------|---------|
| 0x80 | ACK | original CMD byte |
| 0x81 | NACK | original CMD byte + error_code(u8) |

---

## 4. Config Blob (64 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | pulse_width_ns | u32, 50-200 |
| 4 | 4 | hv_voltage_mv | u32, 30000-200000 |
| 8 | 4 | prf_hz | u32, 10-1000 |
| 12 | 1 | pulse_mode | 0=neg spike, 1=bipolar, 2=burst |
| 13 | 1 | burst_cycles | 1-16 |
| 14 | 4 | tgc_start_db | f32 |
| 18 | 4 | tgc_end_db | f32 |
| 22 | 2 | tgc_window_us | u16 |
| 24 | 1 | tgc_shape | 0=flat, 1=linear, 2=exp, 3=custom |
| 25 | 1 | tgc_lna_idx | 0=low, 1=mid, 2=high |
| 26 | 2 | rx_window_us | u16 |
| 28 | 2 | rx_sample_count | u16 |
| 30 | 1 | rx_source | 0=env, 1=RF, 2=both |
| 32 | 1 | measure_mode | 0=PE, 1=EE, 2=Flaw |
| 33 | 4 | zero_offset_ns | u32 (calibration) |
| 37 | 4 | velocity_mps | u32 (active material) |
| 41 | 2 | gate_start_us | u16 |
| 43 | 2 | gate_width_us | u16 |
| 45 | 2 | gate_threshold | u16 (12-bit ADC count) |
| 47 | 1 | gate_enabled | u8 |
| 48 | 1 | default_material_idx | u8 |
| 49-63 | 15 | reserved | padding |

---

## 5. Measurement Notification (binary, ~40 bytes)

| Offset | Size | Field | Type | Notes |
|--------|------|-------|------|-------|
| 0 | 4 | thickness_mm | f32 | meters→mm result |
| 4 | 4 | tof_ns | f32 | round-trip time |
| 8 | 4 | velocity_mps | u32 | active material velocity |
| 12 | 1 | valid | u8 | 1 = valid reading |
| 13 | 1 | flaw_detected | u8 | 1 = flaw found |
| 14 | 4 | flaw_depth_mm | f32 | flaw depth |
| 18 | 4 | flaw_equiv_mm | f32 | equivalent FBH size |
| 22 | 16 | material | char[16] | null-padded name |
| 38 | 2 | battery_pct | i16 | 0-100 |

---

## 6. A-scan Chunk (binary, ~135 bytes)

| Offset | Size | Field | Type |
|--------|------|-------|------|
| 0 | 2 | chunk_idx | u16 |
| 2 | 2 | total_chunks | u16 |
| 4 | 2 | sample_count | u16 |
| 6 | 128 | samples | u16[64] (12-bit ADC values) |

A full A-scan is sent as ceil(sample_count / 64) chunks. Reassemble in order.

---

## 7. Python Scripts

### 7.1. `read_ascan.py`

Connect over BLE, subscribe to the A-scan characteristic, and plot a live A-scan with matplotlib.

```sh
python scripts/read_ascan.py --addr AA:BB:CC:DD:EE:FF
```

### 7.2. `calibrate.py`

Guided zero-probe and velocity calibration.

```sh
python scripts/calibrate.py --addr ... --zero --thickness 4.0
python scripts/calibrate.py --addr ... --velocity --thickness 10.0
```

### 7.3. `material_db.py`

View and edit the on-device material database.

```sh
python scripts/material_db.py --addr ... --list
python scripts/material_db.py --addr ... --add "Inconel 718" --velocity 5790
```

### 7.4. `log_download.py`

Pull measurement and A-scan logs from the SD card.

```sh
python scripts/log_download.py --addr ... --output ./logs/
```

### 7.5. `report.py`

Render an inspection PDF (readings table + A-scan thumbnails).

```sh
python scripts/report.py --input ./logs/ --output inspection_report.pdf
```

---

## 8. BLE Connection Notes

- The device advertises as `PingCaliper` (connectable, general discoverable).
- Bonding is enabled (NVS-persisted); the phone app may pair with a 6-digit passkey (OOB or numeric comparison depending on the platform).
- MTU is negotiated to 185 bytes (enough for a full A-scan chunk + framing).
- The phone app should subscribe to the Measurement, A-scan, and Status notifications.
- Commands are sent as writes to the Command characteristic (write-without-response for low-latency, write-with-response for critical commands like Set Config).

---

*MIT License — SoC Device Inventions.*