# Sap Watch — API Reference

## LoRaWAN Payload Formats

### Port 1 — Periodic Report (every 15 min)

| Offset | Bytes | Field | Type | Scaling | Example |
|--------|-------|-------|------|---------|---------|
| 0 | 2 | sap_flux_velocity | int16 (BE) | cm/h × 100 | 0x0802 = 20.50 cm/h |
| 2 | 2 | daily_transpiration | uint16 (BE) | L × 100 | 0x04E2 = 12.50 L |
| 4 | 2 | sapwood_temp | int16 (BE) | °C × 100 | 0x07D0 = 20.00 °C |
| 6 | 2 | air_temp | int16 (BE) | °C × 100 | 0x0A28 = 26.00 °C |
| 8 | 2 | humidity | uint16 (BE) | % × 100 | 0x1770 = 60.00 % |
| 10 | 2 | light_lux | uint16 (BE) | lux | 0x4E20 = 20000 lux |
| 12 | 2 | vpd | uint16 (BE) | kPa × 100 | 0x00DC = 2.20 kPa |
| 14 | 1 | battery_pct | uint8 | % | 0x53 = 83 % |
| 15 | 1 | probe_health | uint8 bitfield | see below | 0x13 = heater_ok + adc_ok + zero_cal |
| 16 | 2 | measurement_count | uint16 (BE) | count | 0x012C = 300 |
| 18 | 1 | flags | uint8 bitfield | see below | 0x01 = drought_stress |

**probe_health bitfield:**
- bit 0: heater_ok (1 = functional)
- bit 1: adc_ok (1 = ADS122U04 responding)
- bit 2: therm1_ok (1 = upstream thermistor connected, reading valid)
- bit 3: therm2_ok (1 = downstream thermistor connected, reading valid)
- bit 4: zero_cal_valid (1 = zero-flow calibration has been run)
- bits 5-7: reserved (0)

**flags bitfield:**
- bit 0: drought_stress (1 = anomaly detected, see port 2 for details)
- bit 1: heater_fault (1 = heater overcurrent or thermal fuse blown)
- bit 2: low_battery (1 = battery < 15 %)
- bits 3-7: reserved (0)

### Port 2 — Anomaly Alert (sent immediately on detection)

| Offset | Bytes | Field | Type | Scaling |
|--------|-------|-------|------|---------|
| 0 | 1 | alert_type | uint8 | see enum |
| 1 | 2 | sap_flux_velocity | int16 (BE) | cm/h × 100 |
| 3 | 2 | predawn_flux | int16 (BE) | cm/h × 100 |
| 5 | 2 | midday_flux | int16 (BE) | cm/h × 100 |
| 7 | 1 | ratio_pct | uint8 | midday/predawn × 100 |

**alert_type enum:**
- 1 = DROUGHT_STRESS (midday flux < 40% of 7-day predawn baseline)
- 2 = HEATER_FAULT (overcurrent trip or thermal fuse blown)
- 3 = PROBE_DISCONNECT (thermistor reading out of range)
- 4 = LOW_BATTERY (battery < 8%)

### Port 3 — Downlink Config (gateway → device)

| Offset | Bytes | Field | Type | Notes |
|--------|-------|-------|------|-------|
| 0 | 1 | command | uint8 | see enum |
| 1 | 2 | value | uint16 (BE) | command-specific |

**command enum:**
| Command | Value | Description | value field |
|---------|-------|-------------|-------------|
| SET_INTERVAL | 1 | Set measurement interval | minutes (1–60) |
| SET_SAPWOOD_AREA | 2 | Set sapwood area | cm² (1–9999) |
| TRIGGER_ZERO_CAL | 3 | Start zero-flow calibration | ignored |
| SET_WOUND_FACTOR | 3 | Set wound correction factor | × 100 (50–300 → 0.50–3.00) |
| FORCE_MEASUREMENT | 5 | Trigger immediate measurement | ignored |

## Debug UART (115200 baud, 8N1)

When connected via the debug UART (PB10/PB11), the firmware outputs:

### Boot log
```
Sap Watch v1.0 starting...
STM32WL55JC @ 48 MHz
Flash: 256 KB | SRAM: 64+32 KB
LoRaWAN region: EU868
Storage: config loaded (magic=SAPW)
  sapwood_area: 180.0 cm²
  wound_factor: 1.35
  zero_cal: invalid
Fuel gauge: 85% | 4.02 V
Solar: 5.8 V (charging)
LoRaWAN: joining OTAA...
LoRaWAN: joined! DevEUI=70B3D57ED005A1B2
```

### Measurement log
```
[MEAS] cycle 001 | baseline T_up=20.12 T_dn=20.08
[MEAS] heat pulse 2.0s @ 0.15A
[MEAS] post-pulse T_up=20.48 T_dn=21.15 (dt_up=0.36 dt_dn=1.07)
[MEAS] V_h=0.018 cm/s | V_sap=0.024 cm/s = 0.86 cm/h
[MEAS] flow=1.55 L/h | daily=12.34 L
[MEAS] sensors: T_air=26.0 RH=60.0 T_sap=20.0 lux=18000 VPD=1.35 bat=84%
```

### Serial provisioning menu (triggered by holding PROG button 3 s)
```
=== Sap Watch Provisioning ===
1) Set LoRaWAN credentials
2) Set sapwood area (cm²)
3) Set wound factor
4) Trigger zero-flow calibration
5) Force measurement
6) Show config
7) Exit
>
```

## Measurement Log Format (flash ring buffer)

Each 16-byte entry in the W25Q16 flash (or STM32WL internal flash):

| Offset | Bytes | Field | Type | Scaling |
|--------|-------|-------|------|---------|
| 0 | 2 | timestamp_min | uint16 (BE) | minutes since boot |
| 2 | 2 | sap_flux | int16 (BE) | cm/h × 100 |
| 4 | 2 | sapwood_temp | int16 (BE) | °C × 100 |
| 6 | 2 | air_temp | int16 (BE) | °C × 100 |
| 8 | 2 | humidity | uint16 (BE) | % × 100 |
| 10 | 1 | battery_pct | uint8 | % |
| 11 | 1 | flags | uint8 | bitfield |
| 12 | 4 | reserved | — | 0x00000000 |

The ring buffer holds 256 entries (5 min interval → 21.3 hours of data). When full, oldest entries are overwritten.

## Sap-Flow Computation Constants

| Constant | Value | Description |
|----------|-------|-------------|
| k_xylem | 0.0025 cm²/s | Thermal diffusivity of wet sapwood (default) |
| ρ_water | 998 kg/m³ | Water density |
| c_water | 4186 J/(kg·K) | Water specific heat |
| ρ_sapwood | 800 kg/m³ | Sapwood density (default, varies 600–1000) |
| c_sapwood | 2500 J/(kg·K) | Sapwood specific heat (default) |
| wound_factor | 1.35 | Wound correction (species-dependent, 1.0–1.8) |
| spacing_up | 5 mm | Upstream thermistor to heater |
| spacing_dn | 10 mm | Downstream thermistor to heater |