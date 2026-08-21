# Gravi Dot — API Reference

## UART Protocol (STM32 ↔ ESP32-C3)

### GPS Packet (ESP32-C3 → STM32, 1 Hz)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | sync | `0xAA 0x55` |
| 2 | 8 | lat | double, degrees |
| 10 | 8 | lon | double, degrees |
| 18 | 8 | alt | double, metres |
| 24 | 4 | unix_time | uint32, seconds since epoch |
| 28 | 1 | fix_sats | low nibble: fix (0=none, 2=2D, 3=3D); high nibble: satellite count |

### Station Record (STM32 → ESP32-C3, on station mark)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | sync | `0xAA 0x55` |
| 2 | 1 | station_type | 0=survey, 1=base |
| 3 | 4 | g_corrected | float, mGal |
| 7 | 4 | residual | float, mGal |
| 11 | 8 | lat | double, degrees |
| 19 | 8 | lon | double, degrees |
| 27 | 8 | alt | double, metres |
| 35 | 4 | unix_time | uint32 |
| 39 | 4 | rms_vibration | float, mg |
| 43 | 1 | terminator | `0x0D` |

## BLE GATT

| UUID | Type | Description |
|------|------|-------------|
| 0x181A | Service | Gravi Dot Environmental Sensing (repurposed) |
| 0x2A6E | Characteristic | Station data (notify on new station) |

## SD Card CSV Format

```
#,type,lat,lon,alt,time,g_z,g_x,g_y,temp,press,tilt_x,tilt_y,rms,g_corr,residual
1,BASE,46.810000,-71.200000,45.20,1719000000,981234.5,-12.3,45.6,35.01,1013.2,0.001,0.002,0.45,981234.2,0.0
2,STN,46.810090,-71.200100,45.18,1719000030,981232.1,-11.8,44.9,35.02,1013.1,0.002,0.001,0.52,981231.8,-2.4
...
```

## Python API (`gravi_dot_plot.py`)

```python
from gravi_dot_plot import load_survey, plot_contour, plot_profile, print_summary

stations = load_survey("survey_001.csv")
print_summary(stations, quality_flags(stations))
plot_contour(stations, "map.png", rho=2670)
plot_profile(stations, "profile.png")
```