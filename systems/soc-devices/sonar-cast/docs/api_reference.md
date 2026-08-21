# Sonar Cast — API Reference

## UART Protocol (STM32 ↔ ESP32-C3)

Binary, little-endian, 1 Mbaud, 8N1. All frames:
```
[0xAA][0x55][len_lo][len_hi][type][payload...][crc16_lo][crc16_hi]
```
`len` = payload bytes (excluding sync, len, crc). `crc16` = CRC16-CCITT over payload.

### Type 0x01 — Result (STM32 → ESP32)

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| 0 | type | u8 | 0x01 |
| 1 | depth_m | f32 | tilt-corrected bottom depth |
| 5 | depth_pres_m | f32 | pressure-derived depth (cross-check) |
| 9 | bottom_type | u8 | 0=hard, 1=soft, 2=weedy, 3=unknown |
| 10 | bottom_conf | f32 | 0..1 |
| 14 | fish_count | u8 | 0..32 |
| 15 | fish[] | 12×N | depth(f32), length_cm(f32), ts_db(f32) per fish |
| 15+12N | temp_c | f32 | water temp |
| 19+12N | sound_speed | f32 | m/s |
| 23+12N | tilt_deg | f32 | transducer tilt |
| 27+12N | echogram[128] | u8[] | 0..255 water-column intensity |
| 155+12N | crc16 | u16 | |

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
| 1 | cmd | u8 | 0=IDLE, 1=ACTIVE, 2=DRIFT, 3=SLEEP, 4=SET_RATE |
| 2 | arg | u32 | ping rate Hz (for cmd=4) |
| 6 | crc16 | u16 | |

## BLE GATT (ESP32-C3 → phone)

| UUID | Property | Description |
|------|----------|-------------|
| `00009301-1212-efde-1523-785feabcd123` | Service | Sonar Cast service |
| `00009302-...` | Notify | Echogram + results stream (155+12N bytes/frame) |
| `00009303-...` | Write | Command (1 byte cmd + 4 byte arg) |
| `00009304-...` | Read | Device info (version, battery, state) |

## microSD files

### `bathy_YYYYMMDD.csv`
```csv
unix_ts,lat,lon,hdop,depth_m,bottom_type,fish_count,fish_avg_cm,temp_c,sound_speed,tilt_deg
```

### `echo_YYYYMMDD.bin`
Raw 16-bit ADC samples per ping (for offline analysis). Header:
```
[u32 magic=0x534F4E41][u32 ping_count][u32 samples_per_ping][raw data...]
```

## Wi-Fi web dashboard

AP mode: SSID `SonarCast-XXXX`, password `sonarcast`.
`http://192.168.4.1/` → leaflet.js map with depth-colored track + live echogram.