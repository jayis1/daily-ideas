# Pulse Hound — API Reference

## BLE GATT Interface

The Pulse Hound exposes a custom BLE GATT service for streaming real-time RF data to a companion app (phone, PC, or laptop).

### Service

| Property | Value |
|----------|-------|
| Service UUID | `8e7f1a01-b000-1000-8000-00805f9b34fb` |
| Device Name | `Pulse Hound` |

### Characteristics

#### 1. RSSI Stream (`8e7f1a02-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Notify | Device → Client | int16 (2 bytes) |

**Format**: `int16 dBm × 100` (little-endian)

Example: `0x4E8 0x03` = 0x034E = 846 → 8.46 dBm... wait, it's signed: `0x34 0xFE` = −468 → −4.68 dBm.

| RSSI (dBm) | int16 value | Hex |
|------------|-------------|-----|
| +5.00 | +500 | `F4 01` |
| −30.00 | −3000 | `48 F4` |
| −78.00 | −7800 | `E1 E1` |

**Notify rate**: 10 Hz (every 100 ms)

#### 2. Spectrum Frame (`8e7f1a03-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Notify | Device → Client | 64 bytes (one waterfall row) |

**Format**: 64 bytes of 8-bit intensity (0–255), representing the newest waterfall row. The client should assemble these into a scrolling waterfall display.

**Notify rate**: 10 Hz (one row per 100 ms)

#### 3. Bearing (`8e7f1a04-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Notify | Device → Client | 4 bytes |

**Format**: 
- Bytes 0–1: `uint16 bearing_deg × 10` (little-endian) — e.g., 1234 = 123.4°
- Bytes 2–3: `int16 peak_rssi_dbm × 100` (little-endian, signed)

**Notify rate**: on completion of a DF sweep (every ~30 s in DF mode)

#### 4. Classification (`8e7f1a05-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Read / Notify | Device → Client | 1 byte |

**Format**: `uint8` enum

| Value | Class | Description |
|-------|-------|-------------|
| 0 | CW | Continuous wave / analog bug |
| 1 | WiFi/BLE | Bursty, 10–100 ms on, 1–4 s off |
| 2 | Cellular | Pulsed, 0.5–5 ms on |
| 3 | Radar | UWB / motion sensor pulses |
| 4 | Thermal | Slow drift, not a real signal |
| 5 | Unknown | Unclassified emitter |

#### 5. Mode Control (`8e7f1a06-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Write | Client → Device | 1 byte |

**Format**: `uint8` mode enum

| Value | Mode | Description |
|-------|------|-------------|
| 0 | SWEEP | Waterfall + audio (default) |
| 1 | DF | Direction finding with rotating antenna |
| 2 | MONITOR | Fixed-frequency monitoring with peak hold |
| 3 | POWER_SAVE | Low-power 1 Hz sampling |

#### 6. Battery (`8e7f1a07-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Read / Notify | Device → Client | 1 byte |

**Format**: `uint8` percent (0–100)

#### 7. Log Control (`8e7f1a08-...`)

| Property | Direction | Format |
|----------|-----------|--------|
| Write | Client → Device | 1 byte |

| Value | Action |
|-------|--------|
| 0 | Stop SD card logging |
| 1 | Start SD card logging |

---

## SD Card Log Format

The SD card logs sweep data in CSV format (FAT32, append-only):

### File: `pulse_hound.log`

```csv
timestamp_ms,rssi_dbm,peak_rssi_dbm,classification,bearing_deg,battery_pct,mode
0,-78.3,-45.1,0,0,87,0
200,-77.9,-45.1,0,0,87,0
400,-76.5,-45.1,0,0,87,0
600,-74.2,-45.1,1,0,87,0
800,-68.1,-45.1,1,0,87,0
1000,-55.3,-45.1,1,0,87,0
```

| Field | Type | Range | Notes |
|-------|------|-------|-------|
| timestamp_ms | uint32 | 0–2³² | Milliseconds since logging started |
| rssi_dbm | float | −80 to +5 | Current RSSI |
| peak_rssi_dbm | float | −80 to +5 | Peak hold |
| classification | uint8 | 0–5 | See classification enum above |
| bearing_deg | float | 0–359 | Last DF bearing (0 if not in DF mode) |
| battery_pct | uint8 | 0–100 | Battery state of charge |
| mode | uint8 | 0–3 | See mode enum above |

**Log rate**: every 200 ms (5 Hz). A 2 GB card holds ~7 days of continuous logging.

---

## UART Debug Interface

The USB-C port provides a USB-CDC serial interface at 115200 baud for debugging:

```
[Pulse Hound] Boot v1.0
[Pulse Hound] ESP32-S3 OK, flash=8MB
[Pulse Hound] I2C init OK (SDA=1 SCL=2)
[Pulse Hound] ADS1115 found at 0x48
[Pulse Hound] AD8318 powered ON
[Pulse Hound] MAX17048 SoC=87%
[Pulse Hound] OLED SSD1306 init OK
[Pulse Hound] SD card mounted, FAT32, 1.9 GB free
[Pulse Hound] BLE advertising as "Pulse Hound"
[Pulse Hound] Mode=SWEEP, audio=ON
[Pulse Hound] RSSI: -76.2 dBm class=Unknown
[Pulse Hound] RSSI: -74.8 dBm class=Unknown
[Pulse Hound] RSSI: -55.1 dBm class=WiFi/BLE  <-- signal detected!
```

---

## Button Functions

| Button | Short Press | Long Press (>2 s) |
|--------|-------------|-------------------|
| MODE | Cycle mode: SWEEP → DF → MONITOR → POWER_SAVE → SWEEP | Toggle BLE advertising |
| SCAN | Toggle audio on/off | Toggle sensitivity boost (raise click rate) |
| DF | Trigger one DF sweep (returns to previous mode after) | Start continuous DF mode (stays in DF) |

---

## Firmware Build

### ESP-IDF Build (production)

```bash
# Set up ESP-IDF v5.1+
idf.py set-target esp32s3
idf.py menuconfig   # enable BT, FATFS on SPI, I2C, LEDC
idf.py build
idf.py flash monitor
```

### Required ESP-IDF components

- `driver` (I²C, SPI, LEDC PWM, GPIO)
- `bt` (BLE GATT server)
- `fatfs` (SD card via SPI)
- `nvs_flash` (calibration storage)
- `esp_timer` (millisecond timing)

### sdkconfig settings

```
CONFIG_BT_ENABLED=y
CONFIG_BT_NIMBLE_ENABLED=y
CONFIG_BT_NIMBLE_ROLE_PERIPHERAL=y
CONFIG_FATFS_SPI_FLASH=y
CONFIG_SPIRAM=n    # not needed, all fits in SRAM
```

### Simulation Build (host, for algorithm testing)

```bash
PULSE_HOUND_SIM=1 cmake -B build && cmake --build build
./build/pulse_hound_sim
```