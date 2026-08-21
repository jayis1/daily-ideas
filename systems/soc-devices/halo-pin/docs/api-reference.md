# Halo Pin — API Reference

## BLE GATT Characteristics

The ESP32-C3 BLE bridge exposes the following GATT characteristics:

| UUID | Name | Direction | Format |
|------|------|-----------|--------|
| `00002a01-...` | Status | Read/Notify | ASCII string (see below) |
| `00002a02-...` | Histogram | Read | 16 × uint32_t (little-endian) |
| `00002a03-...` | Command | Write | ASCII command string |

### Status Characteristic Format

```
S:<state>,B:<battery_v>,F:<flow_lpm>,1:<pm1>,25:<pm25>,10:<pm10>,H:<bin0>,<bin1>,...,<bin15>,
```

Example:
```
S:1,B:3.85,F:1.02,1:2.3,25:8.1,10:12.5,H:0,0,5,12,28,45,32,18,8,3,1,0,0,0,0,0,0,
```

- `S`: State (0=IDLE, 1=SAMPLING, 2=CALIBRATION)
- `B`: Battery voltage (V)
- `F`: Flow rate (L/min)
- `1`: PM1 mass concentration (µg/m³)
- `25`: PM2.5 mass concentration (µg/m³)
- `10`: PM10 mass concentration (µg/m³)
- `H`: 16-bin histogram (particle counts since last 1 s update)

### Commands

| Command | Description |
|---------|-------------|
| `START\n` | Begin sampling |
| `STOP\n` | Stop sampling |
| `CALIB\n` | Enter PSL calibration mode |
| `ZERO\n` | Begin HEPA zero-air test |
| `BINS:v0,v1,...,v16\n` | Update pulse-height bin boundaries (mV) |
| `DENS:rho\n` | Set particle density (g/cm³) for mass calculation |
| `HYGR:1\n` / `HYGR:0\n` | Enable/disable hygroscopic growth correction |

## SD Card Log Format

The SD card stores a CSV file `HALOPIN.CSV` with one row per minute:

```
id,dt_s,vol_l,flow_lpm,temp_c,rh_pct,pres_hpa,bin0,bin1,...,bin15,pm1,pm25,pm10
```

Example:
```
1,60.0,1.00,1.00,23.5,45.2,1013.2,0,0,3,8,15,22,12,5,2,1,0,0,0,0,0,0,0,2.3,8.1,12.5
```

## UART Protocol (STM32 ↔ ESP32-C3)

USART1 at 921600 baud, 8N1.

### STM32 → ESP32-C3 (status push, 1 Hz)

Same ASCII format as the BLE Status characteristic.

### ESP32-C3 → STM32 (commands, ASCII terminated by `\n`)

Same commands as the BLE Command characteristic.

## Firmware Build

### Prerequisites

- `arm-none-eabi-gcc` toolchain (≥ 10.0)
- `make`
- Optional: `cmake` ≥ 3.22 for CMake build
- ST-Link V2 (or compatible) for flashing

### Build

```bash
cd firmware
make          # produces halo_pin.elf, halo_pin.hex, halo_pin.bin
```

Or with CMake:
```bash
cd firmware
mkdir build && cd build
cmake ..
make
```

### Flash

```bash
make flash     # via st-flash
# or
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
        -c "program halo_pin.elf verify reset exit"
```

## Size Bins

| Bin | Range (µm) | Midpoint (µm) | Typical Source |
|-----|-----------|---------------|----------------|
| 0 | 0.30–0.40 | 0.35 | Ultrafine combustion |
| 1 | 0.40–0.50 | 0.45 | Ultrafine combustion |
| 2 | 0.50–0.70 | 0.60 | Vehicle exhaust |
| 3 | 0.70–1.00 | 0.85 | Fine mode aerosol |
| 4 | 1.00–1.30 | 1.15 | Fine mode aerosol |
| 5 | 1.30–1.70 | 1.50 | Fine mode aerosol |
| 6 | 1.70–2.20 | 1.95 | Fine mode aerosol |
| 7 | 2.20–3.00 | 2.60 | Fine/coarse transition |
| 8 | 3.00–4.00 | 3.50 | Coarse mode dust |
| 9 | 4.00–5.00 | 4.50 | Coarse mode dust |
| 10 | 5.00–7.00 | 6.00 | Coarse mode dust |
| 11 | 7.00–10.0 | 8.50 | Coarse dust / pollen |
| 12 | 10.0–15.0 | 12.5 | Coarse dust / pollen |
| 13 | 15.0–20.0 | 17.5 | Large pollen |
| 14 | 20.0–30.0 | 25.0 | Large pollen / spores |
| 15 | 30.0–40.0 | 35.0 | Large particles |