# Phase Scope — API Reference

## BLE Protocol

Phase Scope communicates over Bluetooth Low Energy using the Nordic UART Service (NUS). The service UUID is `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`.

### Characteristics

| Characteristic | UUID | Direction | Description |
|---|---|---|---|
| RX | 6E400002-B5A3-... | Phone → Device | Commands to Phase Scope |
| TX | 6E400003-B5A3-... | Device → Phone | Data from Phase Scope |

### Packet Framing

All packets use the following framing:

```
[0xAA] [0x55] [payload...] [0x0D] [0x0A]
```

- Start bytes: `0xAA 0x55`
- End bytes: `0x0D 0x0A`
- Payload length varies by command/response type

---

## Commands (Phone → Device)

### 0x01 — GET_STATUS

**Description**: Request current measurement status

**Payload**: None (command byte only)

**Response**: 64-byte status packet (see below)

### 0x02 — GET_WAVEFORM

**Description**: Request raw waveform data for all 6 channels

**Payload**: None

**Response**: 6144 bytes (6 channels × 1024 samples × 2 bytes, Q12.4 fixed-point)

### 0x03 — GET_HARMONICS

**Description**: Request harmonic magnitudes for all channels

**Payload**: None

**Response**: 600 bytes (3 phases × 50 harmonics × 4 bytes, float32)

### 0x04 — GET_TRANSIENT

**Description**: Request last captured transient event

**Payload**: None

**Response**: Variable, includes pre-trigger samples and timestamp

### 0x10 — START_LOG

**Description**: Begin SD card logging

**Payload**: None

**Response**: 1 byte acknowledgment (0x00 = OK, 0x01 = error)

### 0x11 — STOP_LOG

**Description**: Stop SD card logging

**Payload**: None

**Response**: 1 byte acknowledgment

### 0x20 — SET_RANGE_V

**Description**: Set voltage measurement range

**Payload**: 1 byte
- `0x00` = 400V L-N range (default)
- `0x01` = 690V L-L range

**Response**: 1 byte acknowledgment

### 0x21 — SET_RANGE_I

**Description**: Set current measurement range

**Payload**: 1 byte
- `0x00` = 10A low range
- `0x01` = 100A medium range
- `0x02` = 1000A high range

**Response**: 1 byte acknowledgment

### 0x30 — SET_DISPLAY

**Description**: Set OLED display page

**Payload**: 1 byte
- `0x00` = Phasor diagram
- `0x01` = Waveform view
- `0x02` = Harmonic bar graph
- `0x03` = Numeric readout
- `0x04` = Transient log

**Response**: 1 byte acknowledgment

### 0x40 — CALIBRATE

**Description**: Enter calibration mode

**Payload**: 1 byte (calibration type)
- `0x00` = Voltage calibration
- `0x01` = Current calibration
- `0x02` = Phase calibration
- `0x03` = Save calibration to flash
- `0x04` = Reset calibration to defaults

**Response**: 4 bytes (calibration constant as float32)

---

## Response Packets (Device → Phone)

### Status Packet (64 bytes)

Sent automatically every 500ms when BLE streaming is active, or in response to GET_STATUS command.

| Offset | Length | Type | Field | Description |
|--------|--------|------|-------|-------------|
| 0 | 1 | uint8 | type | 0x01 (status) |
| 1-2 | 2 | int16 | V1_rms | L1 voltage RMS (Q12.4, ×0.1V) |
| 3-4 | 2 | int16 | V2_rms | L2 voltage RMS |
| 5-6 | 2 | int16 | V3_rms | L3 voltage RMS |
| 7-8 | 2 | int16 | I1_rms | L1 current RMS (Q12.4, ×0.01A) |
| 9-10 | 2 | int16 | I2_rms | L2 current RMS |
| 11-12 | 2 | int16 | I3_rms | L3 current RMS |
| 13-16 | 4 | int32 | P1 | L1 active power (W) |
| 17-20 | 4 | int32 | P2 | L2 active power (W) |
| 21-24 | 4 | int32 | P3 | L3 active power (W) |
| 25-26 | 2 | int16 | PF1 | L1 power factor (Q1.15, ×32767) |
| 27-28 | 2 | int16 | PF2 | L2 power factor |
| 29-30 | 2 | int16 | PF3 | L3 power factor |
| 31-32 | 2 | int16 | freq | Frequency (Q8.8, ×0.01Hz) |
| 33-36 | 4 | uint32 | timestamp | System tick (ms) |
| 37-38 | 2 | int16 | THD1 | L1 voltage THD (Q4.12, ×0.01%) |
| 39-40 | 2 | int16 | THD2 | L2 voltage THD |
| 41-42 | 2 | int16 | THD3 | L3 voltage THD |
| 43-44 | 2 | int16 | φ_VI1 | L1 V-I phase angle (Q4.12, ×0.01°) |
| 45-46 | 2 | int16 | φ_VI2 | L2 V-I phase angle |
| 47-48 | 2 | int16 | φ_VI3 | L3 V-I phase angle |
| 49-50 | 2 | uint16 | flags | Status flags (see below) |
| 51-64 | 14 | — | reserved | Zero-padded |

### Status Flags (offset 49-50)

| Bit | Flag | Description |
|-----|------|-------------|
| 0 | L1_OVERVOLTAGE | L1 voltage > 110% of nominal |
| 1 | L2_OVERVOLTAGE | L2 voltage > 110% of nominal |
| 2 | L3_OVERVOLTAGE | L3 voltage > 110% of nominal |
| 3 | L1_UNDERVOLTAGE | L1 voltage < 90% of nominal |
| 4 | L2_UNDERVOLTAGE | L2 voltage < 90% of nominal |
| 5 | L3_UNDERVOLTAGE | L3 voltage < 90% of nominal |
| 6 | TRANSIENT_DETECTED | Voltage transient captured |
| 7 | FREQUENCY_ERROR | Frequency outside 45-65 Hz |
| 8 | BATTERY_LOW | Battery < 3.3V |
| 9 | LOGGING_ACTIVE | SD card logging in progress |
| 10 | BLE_STREAMING | BLE data streaming active |
| 11-15 | Reserved | — |

### Waveform Packet (6144 bytes)

| Offset | Length | Type | Field |
|--------|--------|------|-------|
| 0 | 1 | uint8 | type (0x02) |
| 1-2048 | 2048 | int16[1024] | V1 samples (Q12.4) |
| 2049-4096 | 2048 | int16[1024] | V2 samples |
| 4097-6144 | 2048 | int16[1024] | V3 samples |
| 6145-8192 | 2048 | int16[1024] | I1 samples |
| 8193-10240 | 2048 | int16[1024] | I2 samples |
| 10241-12288 | 2048 | int16[1024] | I3 samples |

### Harmonics Packet (600 bytes)

| Offset | Length | Type | Field |
|--------|--------|------|-------|
| 0 | 1 | uint8 | type (0x03) |
| 1-200 | 200 | float32[50] | L1 voltage harmonics |
| 201-400 | 200 | float32[50] | L2 voltage harmonics |
| 401-600 | 200 | float32[50] | L3 voltage harmonics |

---

## SD Card Log Format

### CSV Format

Files are named `LOG_XXXXX.CSV` (sequential numbering).

**Header row:**
```
timestamp,V1_rms,V2_rms,V3_rms,I1_rms,I2_rms,I3_rms,P1,P2,P3,Q1,Q2,Q3,S1,S2,S3,PF1,PF2,PF3,freq,THD1,THD2,THD3,phase_VI1,phase_VI2,phase_VI3
```

**Data row example:**
```
12345,230.1,229.8,230.5,5.20,4.80,5.00,1196,1098,1150,490,514,497,1293,1198,1268,0.923,0.918,0.908,50.01,4.2,3.8,4.1,23.5,24.1,22.8
```

### Binary Format

Files are named `WAV_XXXXX.BIN` (for waveform captures).

**Structure:**
- 4 bytes: Magic (`0x5053` = "PS")
- 4 bytes: Sample rate (uint32, in Hz)
- 4 bytes: Number of channels (uint32, = 6)
- 4 bytes: Samples per channel (uint32, = 1024)
- N bytes: Interleaved sample data (int16, channel order: V1,I1,V2,I2,V3,I3)

---

## Debug UART

The debug UART (PA9=TX, PA10=RX) runs at 115200 8N1 and provides a command-line interface for development:

```
> status          — Show current measurements
> cal v 230.0     — Calibrate voltage (apply 230V)
> cal i 10.0      — Calibrate current (apply 10A)
> cal save         — Save calibration to flash
> cal reset        — Reset to factory defaults
> log start        — Start SD card logging
> log stop         — Stop SD card logging
> display <1-5>    — Set display page
> range v <400|690> — Set voltage range
> range i <10|100|1000> — Set current range
> ble on           — Enable BLE streaming
> ble off          — Disable BLE streaming
> reboot           — Software reset
```