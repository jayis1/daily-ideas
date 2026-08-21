# Hall Puck — API Reference

## BLE GATT Interface (via ESP32-C3)

### Service: Hall Puck (UUID 0x9201)

| Characteristic | UUID | Properties | Description |
|---|---|---|---|
| Data Stream | 0x9202 | Notify | Live voltage readings during measurement |
| Result | 0x9203 | Read, Notify | Final measurement result (28 bytes) |
| Command | 0x9204 | Write | Send commands to device |
| Info | 0x9205 | Read, Notify | Device info (firmware, B-field, calibration) |

### Data Stream Format (0x9202)

Each notification contains a raw measurement point (20 bytes):

| Offset | Size | Field | Unit | Type |
|--------|------|-------|------|------|
| 0 | 1 | config | enum | uint8 (see measurement config enum) |
| 1 | 1 | step_index | — | uint8 |
| 2 | 4 | voltage | µV | float32 LE |
| 6 | 4 | current | mA | float32 LE (signed) |
| 10 | 4 | b_field | T | float32 LE (signed) |
| 14 | 4 | temperature | °C | float32 LE |
| 18 | 2 | reserved | — | uint16 |

### Result Format (0x9203, 28 bytes)

| Offset | Size | Field | Unit | Type |
|--------|------|-------|------|------|
| 0 | 4 | sheet_resistance | Ω/□ | float32 LE |
| 4 | 4 | hall_coefficient | cm³/C | float32 LE (signed) |
| 8 | 4 | carrier_conc | cm⁻³ | float32 LE |
| 12 | 4 | mobility | cm²/V·s | float32 LE |
| 16 | 4 | resistivity | Ω·cm | float32 LE |
| 20 | 1 | carrier_type | enum | uint8 (0=unknown, 1=n-type, 2=p-type) |
| 21 | 1 | status | enum | uint8 (0=done, 1=error, 2=warning) |
| 22 | 2 | temperature | °C × 100 | int16 LE |
| 24 | 4 | b_field | T | float32 LE |

### Command Format (0x9204)

Write 1+ bytes:

| Command | Byte | Payload | Description |
|---------|------|---------|-------------|
| Start | 0x01 | none | Start measurement with current settings |
| Stop | 0x02 | none | Cancel current measurement |
| Set Current | 0x03 | 4 bytes: float32 mA | Set measurement current (0.001–10 mA) |
| Set Thickness | 0x04 | 4 bytes: float32 mm | Set sample thickness (0.01–1.0 mm) |
| Set Mode | 0x05 | 1 byte: mode ID | Set measurement mode |
| Calibrate | 0x06 | none | Start B-field calibration |
| Get Info | 0x07 | none | Trigger info notification |

### Mode IDs

| ID | Name | Description |
|----|------|-------------|
| 0 | Single | Single measurement at current temperature |
| 1 | Temp Sweep | Temperature sweep (25–80°C) |
| 2 | Continuous | Continuous monitoring every 60s |
| 3 | QA | QA pass/fail vs. target specs |

### Info Format (0x9205)

16 bytes:

| Offset | Size | Field | Type |
|--------|------|-------|------|
| 0 | 8 | firmware_version | char[8] |
| 8 | 4 | b_field_calibration | float32 LE (T) |
| 12 | 4 | calibration_date | uint32 (Unix timestamp) |

## UART Protocol (STM32 ↔ ESP32-C3)

Internal UART link at 460800 baud, 8N1.

### Frame format

```
[0xA5] [type] [len_hi] [len_lo] [payload...] [checksum] [0x5A]
```

- **SOF**: 0xA5 (start of frame)
- **type**: frame type (see below)
- **len**: payload length (big-endian, 0–255)
- **payload**: variable length data
- **checksum**: XOR of type + len_hi + len_lo + all payload bytes
- **EOF**: 0x5A (end of frame)

### Frame types

| Type | Direction | Description |
|------|-----------|-------------|
| 0x01 | STM→ESP | Measurement result |
| 0x02 | STM→ESP | Raw measurement point |
| 0x03 | STM→ESP | Device info |
| 0x04 | ESP→STM | Command |
| 0x05 | STM→ESP | State update |
| 0x06 | ESP→STM | ACK (connection established) |

## Wi-Fi Web Interface

The ESP32-C3 serves a simple HTTP interface on the "HallPuck" AP:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Status page with device info |
| `/results` | GET | Last measurement result (JSON) |
| `/download` | GET | Download SD card CSV log |
| `/start` | POST | Start measurement |
| `/stop` | POST | Cancel measurement |
| `/config` | POST | Set current/thickness/mode |

## SD Card Log Format

CSV file `HP_YYYYMMDD_HHMMSS.csv`:

```csv
# Hall Puck measurement log
# Date: 2026-07-29T10:15:30Z
# Sample: n-Si wafer (unknown doping)
# Thickness: 0.500 mm
# Temperature: 24.3 C
# B-field: 0.482 T
# Current: 1.000 mA
# Result: Rs=4520.0 Ohm/sq, RH=-508.3 cm3/C, n=1.23e16 cm-3, mu=1124 cm2/Vs, type=n
# Columns: step, config, I_mA, V_uV, B_T, note
1, VDP_Ra_fwd, 1.000, 4520.0, 0.000, I=1->2, V=3->4
2, VDP_Ra_rev, -1.000, -4518.0, 0.000, I=2->1, V=4->3
3, VDP_Rb_fwd, 1.000, 3890.0, 0.000, I=2->3, V=4->1
4, VDP_Rb_rev, -1.000, -3892.0, 0.000, I=3->2, V=1->4
5, HALL_B+_fwd, 1.000, 12.40, 0.482, I=1->3, V=2->4, B+
6, HALL_B+_rev, -1.000, -12.38, 0.482, I=3->1, V=4->2, B+
7, HALL_B-_fwd, 1.000, -12.42, -0.482, I=1->3, V=2->4, B-
8, HALL_B-_rev, -1.000, 12.40, -0.482, I=3->1, V=4->2, B-
# END
```