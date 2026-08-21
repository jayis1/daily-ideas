# API Reference — Helio Tilt

## BLE GATT Service

The ESP32-C3 BLE bridge exposes a custom GATT service with the
following characteristics:

| UUID | Name | Type | Direction | Description |
|------|------|------|-----------|-------------|
| `0000fe30-...` | Helio Tilt Service | Service | — | Main service |
| `0000fe31-...` | Measurement | Notify | Device→Phone | Live DNI/AOD data |
| `0000fe32-...` | Langley | Notify | Device→Phone | Langley calibration progress |
| `0000fe33-...` | Command | Write | Phone→Device | Control commands |
| `0000fe34-...` | Status | Read/Notify | Device→Phone | Device status |
| `0000fe35-...` | Settings | Read/Write | Bidirectional | Run parameters |
| `0000fe36-...` | Error | Notify | Device→Phone | Error messages |

## Packet Protocol

All BLE characteristics use a binary framed packet format:

```
[START 0xAA] [TYPE] [LEN_H] [LEN_L] [PAYLOAD...] [CRC8]
```

### Packet Types

#### 0x01 — Measurement (PKT_MEAS)
Live DNI + AOD data, sent at 10 Hz during tracking.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | sun_az | float32 — solar azimuth (degrees) |
| 4 | 4 | sun_el | float32 — solar elevation (degrees) |
| 8 | 4 | zenith | float32 — solar zenith angle (degrees) |
| 12 | 4 | air_mass | float32 — relative optical air mass |
| 16 | 24 | dni[6] | float32[6] — DNI per wavelength (W/m²) |
| 40 | 24 | aod[6] | float32[6] — AOD per wavelength |
| 64 | 4 | angstrom | float32 — Ångström exponent |
| 68 | 4 | pwv_cm | float32 — precipitable water vapor (cm) |
| 72 | 4 | bat_v | float32 — battery voltage (V) |

Total payload: 76 bytes.

### 0x02 — Langley Progress (PKT_LANGLEY)
Langley calibration progress, sent every 2 minutes during calibration.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | points | uint16 — number of data points collected |
| 2 | 4 | r2_870 | float32 — R² at 870 nm |
| 6 | 4 | v0_870 | float32 — V₀ at 870 nm |

Total payload: 10 bytes.

### 0x03 — Error (PKT_ERROR)
Error/fault message.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | N | message | char[] — error message string |

### 0x04 — Status (PKT_STATUS)
Device status, sent at 10 Hz.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | state_len | uint8 — length of state string |
| 1 | 12 | state | char[12] — state name (IDLE, TRACK, LANGLEY, etc.) |
| 13 | 4 | sun_az | float32 — solar azimuth (degrees) |
| 17 | 4 | sun_el | float32 — solar elevation (degrees) |
| 21 | 4 | bat_v | float32 — battery voltage (V) |
| 25 | 1 | gps_fix | uint8 — GPS fix valid (0/1) |

## Commands (Phone → Device)

| Command | Code | Payload | Description |
|---------|------|---------|-------------|
| CMD_START | 0x01 | — | Start tracking |
| CMD_STOP | 0x02 | — | Stop tracking / abort |
| CMD_LANGLEY | 0x03 | — | Start Langley calibration |
| CMD_SET_PRESSURE | 0x04 | float32 | Set atmospheric pressure (hPa) |
| CMD_SET_OZONE | 0x05 | float32 | Set ozone amount (DU) |
| CMD_MAG_CAL | 0x06 | — | Start magnetometer calibration |
| CMD_SET_V0 | 0x07 | uint8 wl + float32 v0 | Set V₀ for a wavelength |

## SD Card Log Format

### Measurement Log (AERONET-compatible CSV)

File: `helio_YYYYMMDD.csv`

Header row:
```
date,time,latitude,longitude,elevation,zenith,azimuth,air_mass,
dni_405,dni_440,dni_675,dni_870,dni_940,dni_1640,
aod_405,aod_440,aod_675,aod_870,aod_940,aod_1640,
angstrom_alpha,pwv_cm,pressure_hpa,temperature_c
```

Data rows:
```
2026-07-13,14:30:00,40.712800,-74.006000,10.0,32.5,180.2,1.18,
823.4,815.2,798.1,790.5,785.3,772.8,
0.12,0.11,0.08,0.07,0.06,0.05,
1.42,2.31,1013.25,25.3
```

### Langley Log

File: `langley_YYYYMMDD.csv`

Header:
```
date,time,air_mass,v_405,v_440,v_675,v_870,v_940,v_1640
```

## Solar Position Algorithm

The firmware implements a truncated NOAA Solar Position Algorithm:

| Parameter | Accuracy |
|-----------|----------|
| Azimuth | ±0.01° |
| Elevation | ±0.01° (above 5°) |
| Air mass | ±0.001 |
| Computation time | ~0.1 ms (CORDIC-accelerated) |

## AOD Computation

```
τ_aero(λ) = [ln(V₀(λ)) - ln(V(λ))] / m(θ) - τ_Rayleigh(λ) - τ_ozone(λ)
```

| Correction | Formula |
|------------|---------|
| Rayleigh | τ_R = 0.00864 × λ⁻⁴ × (P/P₀) |
| Ozone | τ_O₃ = α_O₃(λ) × U_O₃ |
| Air mass | m = 1/(cos(θ) + 0.50572×(96.07995-θ)⁻¹·⁶³⁶⁴) |
| Refraction | Saemundsson formula |

## Firmware Modules

| Module | File | Key Functions |
|--------|------|---------------|
| System | `main.c` | State machine, main loop |
| Solar position | `solar_pos.c` | `solar_pos_compute()`, `solar_air_mass()` |
| GPS | `gps.c` | `gps_init()`, `gps_parse_nmea()`, `gps_has_fix()` |
| IMU | `imu.c` | `imu_read_tilt()`, `imu_read_heading()`, `imu_read_fusion()` |
| Stepper | `stepper.c` | `stepper_move_to()`, `stepper_home()` |
| Filter wheel | `filter_wheel.c` | `filter_wheel_set()`, `filter_wheel_home()` |
| Detector | `detector.c` | `detector_read()`, `detector_read_avg()` |
| Radiometry | `radiometry.c` | `radiometry_compute()`, `radiometry_angstrom()` |
| Langley | `langley.c` | `langley_add_point()`, `langley_regress()` |
| Display | `display.c` | `display_show_tracking()`, `display_show_status()` |
| SD logging | `sd_log.c` | `sd_log_measurement()`, `sd_log_langley()` |
| BLE bridge | `ble_bridge.c` | `ble_bridge_send_measurement()`, `ble_bridge_send_status()` |
| Battery | `battery.c` | `battery_read()`, `battery_low()` |
| UI | `ui.c` | `ui_poll()`, `ui_encoder_pos()` |