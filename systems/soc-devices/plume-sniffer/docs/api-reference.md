# Plume Sniffer — API Reference

## BLE GATT Services

### Service: Plume Control (UUID 0x1840)

| Characteristic | UUID | Properties | Description |
|----------------|------|------------|-------------|
| Control | 0x1841 | Write | Run control commands |
| Chromatogram | 0x1842 | Notify | Live chromatogram data stream |
| Results | 0x1843 | Notify | Post-run peak table |

### Control Characteristic (0x1841) — Write

Write a 1–2 byte command:

| Byte 0 | Byte 1 | Action |
|--------|--------|--------|
| 0x01 | — | Start a run with the current method |
| 0x02 | — | Stop / abort current run |
| 0x03 | 0–3 | Select method: 0=M_ETHOS, 1=M_FAST, 2=M_ISOTH, 3=M_HIGH |
| 0x04 | — | Enter calibration mode |
| 0x05 | 0–255 | Set sample volume (byte × 5 mL, so 50 = 250 mL) |

### Chromatogram Characteristic (0x1842) — Notify

Sends batches of up to 20 floats (80 bytes) during a run. Each float is
the baseline-corrected TCD signal in µV, little-endian IEEE 754.

The stream starts when the RAMP phase begins and continues until the run
ends. A gap of >2 s between notifications indicates the run is over.

### Results Characteristic (0x1843) — Notify

After a run completes, sends one notification per detected peak:

```
Offset  Size  Field
  0     4     retention_s (float, LE)
  4     4     retention_index (float, LE)
  8     4     est_conc_ppm (float, LE)
 12     2     library_index (int16, -1 = unknown)
 14     2     padding (0)
```

Total: 16 bytes per peak. The stream ends when no more notifications
arrive for >1 s.

## SD Card File Format

All files are on a FAT32-formatted microSD card, mounted at `/sdcard`.

### RUN_NNNN.csv — Chromatogram

```
# Plume Sniffer Run 0001
# Method: M_ETHOS
# Sample volume: 250.0 mL
# Battery: 3850 mV
# Ambient: 23.4 C
# Samples: 12000 @ 50 Hz
time_s,raw_uv,baseline_uv,corrected_uv
0.000,5120,5120,0.0
0.020,5121,5120,1.0
0.040,5119,5120,-1.0
...
```

### RUN_NNNN_meta.txt — Peak Table

```
Plume Sniffer Run 0001
Method: M_ETHOS
Sample volume: 250.0 mL
Battery: 3850 mV
Ambient temp: 23.4 C
Peaks detected: 3

tR_s    RI      Compound            Conc_ppm    Area_uVs    Height_uV
72.3    692     Cyclohexane         45          12000       380
108.5   810     Hexanal             12          3200        95
195.0   1000    Decane              8           2100        60
```

## Firmware Build

### Prerequisites

- ESP-IDF v5.1+ (with RISC-V toolchain for ESP32-C3)
- Python 3.8+

### Build & Flash

```bash
cd plume-sniffer/firmware
idf.py set-target esp32c3
idf.py build
idf.py flash -p /dev/ttyUSB0 -b 460800
idf.py monitor -p /dev/ttyUSB0
```

### Configuration

Key settings in `sdkconfig.h` (override via `idf.py menuconfig`):

| Define | Default | Description |
|--------|---------|-------------|
| PLUME_TCD_SAMPLE_HZ | 50 | ADS122U04 data rate |
| PLUME_COLUMN_RAMP_DEFAULT_CPM | 10 | °C per minute |
| PLUME_COLUMN_T_MAX | 180 | Max column temp (°C) |
| PLUME_PRECONC_DESORB_TEMP | 220 | Desorb temp (°C) |
| PLUME_SAMPLE_VOLUME_DEFAULT_ML | 250 | Default sample volume |
| PLUME_BATTERY_MIN_MV | 3500 | Min battery for RUN |
| PLUME_HEATER_WATCHDOG_TEMP_C | 220 | Emergency cutoff (°C) |

## Firmware Modules

| File | Responsibility |
|------|----------------|
| main.c | State machine, run orchestration |
| tcd.c | ADS122U04 SPI driver, TCD bridge sampling, baseline tracking |
| column.c | PID column heater, temperature program executor |
| preconc.c | Flash desorb controller |
| pump.c | Pump PWM + 3-way valve + sample volume integration |
| peak.c | Chromatogram peak detection (derivative + 2nd-derivative) |
| identify.c | Kovats RI computation + library matching + conc estimate |
| library.c | 40-compound retention-index library + NVS anchor storage |
| display.c | SSD1306 OLED driver (I2C) |
| sd_log.c | microSD FATFS logging (SPI2) |
| ble.c | NimBLE GATT server |
| bme280.c | Ambient T/H/P sensor (I2C) |
| battery.c | 18650 voltage monitor (ADC divider) |
| ui.c | Button input + menu |

## Methods

| ID | Name | Start | Ramp | Final | Hold | Use case |
|----|------|-------|------|-------|------|----------|
| 0 | M_ETHOS | 35°C | 10°C/min | 180°C | 30s | General purpose |
| 1 | M_FAST | 35°C | 20°C/min | 120°C | 15s | Quick screening (~4 min) |
| 2 | M_ISOTH | 80°C | — | 80°C | 300s | Isothermal for volatiles |
| 3 | M_HIGH | 50°C | 15°C/min | 180°C | 60s | Semivolatiles |

## UART Console

At 115200 baud, the firmware logs:

```
I (1234) plume: Plume Sniffer booting...
I (1240) tcd: ADS122U04 configured: reg0=0x01 reg1=0x04 reg2=0x09 reg3=0x00
I (1300) column: PID task started at 10 Hz
I (1350) sd: SD mounted: /sdcard
I (1400) ble: BLE connected: handle=0
I (2000) plume: === RUN START: M_ETHOS  bat=3850mV  amb=23.4C  250ml ===
...
I (78000) peak: Peak 1: tR=72.3s area=12000 h=380µV w=4.1s
I (78100) identify: Peak 0: tR=72.3s RI=692 → Cyclohexane (45 ppm)
I (79000) sd: Run 0001 saved: 12000 samples, 3 peaks
```