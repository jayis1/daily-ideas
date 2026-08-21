# Lode Sweep — API Reference

## UART Protocol (STM32 ↔ ESP32-C3)

Binary, little-endian, 460800 baud, 8N1. All frames:
```
[0xAA][0x55][len_lo][len_hi][type][payload...][crc16_lo][crc16_hi]
```
`len` = payload bytes (excluding sync, len, crc). `crc16` = CRC16-CCITT over payload.

### Type 0x01 — Result (STM32 → ESP32)

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0 | type | u8 | 0x01 |
| 1 | target_class | u8 | 0=iron, 1=foil, 2=nickel, 3=pull-tab, 4=zinc, 5=copper, 6=silver, 7=gold |
| 2 | confidence | f32 | 0..1 (fraction of k nearest neighbors) |
| 6 | depth_cm | f32 | estimated depth in cm |
| 10 | signal_strength | f32 | sum of 16 gates (normalized) |
| 14 | tilt_deg | f32 | coil tilt from horizontal |
| 18 | decay[16] | 16×f32 | normalized 16-gate decay curve |
| 82 | lat | f32 | GPS latitude |
| 86 | lon | f32 | GPS longitude |
| 90 | hdop | f32 | GPS HDOP |
| 94 | unix_ts | u32 | GPS time |
| 98 | crc16 | u16 | |

### Type 0x02 — GPS (ESP32 → STM32)

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0 | type | u8 | 0x02 |
| 1 | lat | f32 | decimal degrees |
| 5 | lon | f32 | decimal degrees |
| 9 | hdop | f32 | |
| 13 | fix | u8 | 0/1 |
| 14 | unix_ts | u32 | |
| 18 | crc16 | u16 | |

### Type 0x03 — Command (ESP32 → STM32)

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0 | type | u8 | 0x03 |
| 1 | cmd | u8 | 0=IDLE, 1=ACTIVE, 2=DRIFT, 3=SLEEP, 4=SET_SENS, 5=SET_DISC |
| 2 | arg | u8 | sensitivity (1-10 for cmd=4), 0/1 for discrim (cmd=5) |
| 3 | crc16 | u16 | |

## BLE GATT (ESP32-C3 → phone)

| UUID | Property | Description |
|------|----------|-------------|
| `00009401-1212-efde-1523-785feabcd123` | Service | Lode Sweep service |
| `00009402-...` | Notify | Target results stream (98 bytes/frame) |
| `00009403-...` | Write | Command (1 byte cmd + 1 byte arg) |
| `00009404-...` | Read | Device info (version, battery, state, sensitivity) |

## microSD files

### `survey_YYYYMMDD.csv`
```csv
unix_ts,lat,lon,hdop,target_class,depth_cm,confidence,signal,tilt_deg
```

## Wi-Fi web dashboard

AP mode: SSID `LodeSweep-XXXX`, password `lodesweep`.
`http://192.168.4.1/` → leaflet.js map with class-colored detection pins + depth labels.

## Audio feedback

| Class | Pitch (Hz) | Character |
|-------|-----------|-----------|
| Iron | 150 | Low growl |
| Foil | 220 | Low buzz |
| Nickel | 330 | Medium |
| Pull-Tab | 440 | Medium |
| Zinc | 550 | Medium-high |
| Gold | 880 | Bright |
| Copper | 990 | High |
| Silver | 1100 | Crisp bell |

Volume is proportional to signal strength (log-scaled). In discrimination mode,
iron and foil targets are silenced.