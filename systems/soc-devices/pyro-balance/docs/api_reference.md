# Pyro Balance — API Reference

## UART protocol (STM32 ↔ ESP32-C3 ↔ phone app)

Frame format: `[0xAA][len_lo][len_hi][cmd][payload...][crc8]`

`crc8` = XOR of all preceding bytes.

### Commands (phone → STM32, via ESP32-C3)

| Cmd | Name | Payload | Response |
|-----|------|---------|----------|
| 0x10 | START | `[final_temp_u16][rate_x10_u16][hold_min_u8][purge_u8]` | 0x02 status |
| 0x11 | STOP  | — | 0x02 status |
| 0x12 | TARE  | — | 0x02 status |
| 0x13 | SET_METHOD | `[method_id_u32]` | 0x02 status |
| 0x14 | GET_STATUS | — | 0x02 status |
| 0x15 | GET_RESULT | — | 0x04 result |
| 0x16 | CALIBRATE_MASS | `[ref_mg_f32]` | 0x03 log |
| 0x17 | CALIBRATE_TEMP | `[point_u8][temp_c_f32]` | 0x03 log |
| 0x18 | SET_CONFIG | `flash_store_t` (see `flash_store.h`) | 0x03 log |

### Responses (STM32 → phone)

| Cmd | Name | Payload |
|-----|------|---------|
| 0x01 | DATA_POINT | `[t_ms_u32][temp_c_f32][mass_mg_f32][mass_pct_f32][dtg_f32]` |
| 0x02 | STATUS | `pb_status_t` (see `main.h`) |
| 0x03 | LOG | UTF-8 string |
| 0x04 | RESULT | `[step_count_u8][pad_u8][steps...][residual_pct_f32]` |
| 0x05 | ALARM | `[code_u8][msg...]` |

## BLE GATT

| UUID | Type | Description |
|------|------|-------------|
| 0x1801 | Service | Pyro Balance service |
| 0x2A01 | Char (Notify) | Live data stream (0x01 frames) |
| 0x2A02 | Char (Write)  | Command input (0x10–0x18 frames) |

## Wi-Fi

- SSID: `Pyro-Balance` (open, captive portal)
- `GET /tga.csv` — last run CSV (or live stream)
- `GET /status` — JSON status
- `POST /cmd` — send a command frame (base64)

## Python helpers

See `scripts/`:

- `live_stream.py` — BLE live plotter + CSV export
- `calibrate.py` — mass + temperature calibration
- `analyze_tga.py` — offline TG/DTG analysis, kinetics, buoyancy blank subtraction

## File formats

### SD CSV (`tga_<method>.csv`)

```
# Pyro Balance TGA run method=<id>
time_s,temp_c,mass_mg,mass_pct,dtg_pct_per_min
0,25.000,15.234,100.000,0.0000
1,25.167,15.234,100.000,0.0000
...
# steps=2 residual_pct=12.300
# step 0 onset=120.5 peak=135.2 endset=150.1 dmass=3.200
# step 1 onset=320.0 peak=410.5 endset=480.0 dmass=84.500
```

### Flash store (`flash_store_t`)

See `firmware/Core/Inc/flash_store.h`. Stored in the last flash page.