# API Reference — Bone Echo

## BLE GATT Characteristics

The ESP32-C3 BLE bridge exposes a GATT server with the following
characteristics:

### Service: `0000FE20-0000-1000-8000-00805F9B34FB` (Bone Echo)

| UUID | Name | Type | Direction | Description |
|------|------|------|-----------|-------------|
| `FE21` | Results | String | Notify | `R:<sos>,<bua>,<si>,<t>,<z>,<class>\n` |
| `FE22` | Waveform | Bytes | Notify | Chunked raw A-scan (115200 × 2 bytes) |
| `FE23` | Status | String | Notify | `S:<bat_v>,<state>,<sos>,<bua>\n` |
| `FE24` | Command | String | Write | `SCAN`, `STOP`, `PHANTOM`, `ID:<n>`, `AGE:<n>`, `SEX:<0/1>`, `ETH:<0-3>` |

### Result Format

```
R:1562.0,58.4,84.2,-1.20,-0.30,1
```

| Field | Value | Units |
|-------|-------|-------|
| sos | 1562.0 | m/s |
| bua | 58.4 | dB/MHz |
| si | 84.2 | dimensionless |
| t | -1.20 | T-score (SD) |
| z | -0.30 | Z-score (SD) |
| class | 1 | 0=normal, 1=osteopenia, 2=osteoporosis, 3=severe |

### Waveform Format

The waveform is sent in chunks:
```
W:START
W:0
W:256
W:512
...
W:114944
W:END
```
Each `W:<offset>` line is followed by 512 bytes of raw 16-bit
little-endian ADC samples (256 samples × 2 bytes). The full
waveform is 115200 samples × 2 bytes = 230,400 bytes.

### Status Format

```
S:3.90,4,1562.0,58.4
```

| Field | Value | Description |
|-------|-------|-------------|
| bat_v | 3.90 | Battery voltage (V) |
| state | 4 | 0=idle, 1=menu, 2=patient, 3=phantom, 4=scan, 5=report, 6=done |
| sos | 1562.0 | Last SOS (m/s) |
| bua | 58.4 | Last BUA (dB/MHz) |

## SD Card File Format

Each scan produces two files:

### `PT_NNNN.csv`

```csv
scan_id,patient_id,age,sex,ethnicity,sos_mps,bua_db_mhz,si,t_score,z_score,class
1,1001,55,1,0,1562.0,58.4,84.2,-1.20,-0.30,1
```

### `PT_NNNN.bin`

Raw 16-bit little-endian ADC samples (115200 samples × 2 bytes =
230,400 bytes). The first 100 samples are pre-trigger noise; the
TX burst arrives at the HRTIM trigger timestamp.

## UART Bridge Protocol

The STM32G474 ↔ ESP32-C3 UART runs at 921600 baud, 8N1.

**STM32 → ESP32-C3:**
- `R:<sos>,<bua>,<si>,<t>,<z>,<class>\n` — Results (after scan)
- `W:START\n` / `W:<offset>\n` / `W:END\n` — Waveform chunks
- `S:<bat>,<state>,<sos>,<bua>\n` — Status (10 Hz)

**ESP32-C3 → STM32:**
- `SCAN\n` — Start a scan
- `STOP\n` — Stop / abort
- `PHANTOM\n` — Run phantom reference
- `ID:<n>\n` — Set patient ID
- `AGE:<n>\n` — Set patient age
- `SEX:<0|1>\n` — Set sex
- `ETH:<0-3>\n` — Set ethnicity

## Firmware Build

### Prerequisites

- `arm-none-eabi-gcc` (GCC 12+)
- `cmake` 3.22+
- CMSIS-DSP library (`libarm_cortexM4lf_math.a`)
- STM32Cube HAL for STM32G4
- OpenOCD + ST-Link V2 (for flashing)

### Build with CMake

```bash
cd firmware
mkdir build && cd build
cmake ..
make -j$(nproc)
```

Output: `bone_echo.elf`, `bone_echo.hex`, `bone_echo.bin`

### Build with Make

```bash
cd firmware
make -j$(nproc)
```

### Flash

```bash
make flash
# or
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program bone_echo.elf verify reset exit"
```

### ESP32-C3 BLE Bridge Firmware

The ESP32-C3 runs a minimal BLE GATT server (Arduino or ESP-IDF).
See the companion app `scripts/boneecho_app.py` for the BLE protocol.