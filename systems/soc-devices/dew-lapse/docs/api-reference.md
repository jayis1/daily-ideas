# Frost Point — API Reference

## BLE GATT profile

| Service | UUID | Description |
|---------|------|-------------|
| Generic Access | 0x1800 | Device name, appearance |
| Environmental Sensing | 0x181A | Humidity measurements |

### Characteristics (Environmental Sensing Service)

| UUID | Name | Type | Unit | Notes |
|------|------|------|------|-------|
| 0x2A01 | Appearance | uint16 | — | 0x832 (Humidity Sensor) |
| 0x2A6E | Temperature | int16 | 0.01 °C | Mirror temperature |
| 0x2A6F | Humidity | uint16 | 0.01 %RH | Relative humidity |
| 0x2A77 | Pressure | uint32 | 0.1 Pa | Atmospheric pressure |
| 0x2A78 | Absolute Humidity | uint16 | 0.01 g/m³ | Custom |
| 0x2A7C | Dew Point | int16 | 0.01 °C | Standard dew point char |
| 0xFFE0 | Mirror Status | uint8 | — | bit 0: phase (0=dew, 1=frost), bit 1: valid, bit 2: tracking |
| 0xFFE0 | TEC Drive | int8 | % | −100 to +100 |
| 0xFFE0 | CO₂ | uint16 | ppm | Sanity check |
| 0xFFE0 | Mixing Ratio | uint16 | 0.01 g/kg | Custom |
| 0xFFE1 | Command | uint8 write | — | 1=start, 2=stop, 3=defrost, 4=set rate (1 byte follows) |

### Notify packet (custom, on 0xFFE0)

ASCII format, newline-terminated:
```
DEW <dew_c> RH <rh> AH <ah> W <w> M <mirror_c> S <state> TEC <pct> P <phase>\r\n
```

## UART (debug, USART3 @ 115200 baud)

Plain-text log of state transitions, mirror temperature, dew point, and faults. Useful for bench debugging.

## USB-CDC (when connected via USB)

Exposes the same log stream as UART3, plus a binary command interface for dumping the flash log.

## Log format (W25Q128)

CSV, one record per line:
```
ts_ms,dew_c,rh_pct,ah_gm3,w_gkg,pressure_pa,co2_ppm,mirror_c,tec_i,tec_v,phase,state
```

## Configuration

All tunable parameters live in `firmware/inc/config.h`:

- `PID_KP/KI/KD` — PID gains for the mirror tracking loop
- `FILM_SETPOINT_K` — target |ΔT| for film stability (0.10 K typical)
- `TRACK_STABLE_DT` — rate-of-change threshold for "stable" (0.005 K/s)
- `TRACK_STABLE_COUNT` — consecutive stable samples to declare VALID (10)
- `TEC_CURRENT_LIMIT_A` — over-current cutout (3.5 A)
- `TEC_HOT_LIMIT_C` — over-temperature cutout (70 °C)
- `LOG_RATE_HZ` — logging rate (1 Hz default)