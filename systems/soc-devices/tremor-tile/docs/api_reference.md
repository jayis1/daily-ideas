# Tremor Tile — API Reference

## Serial Protocol (USB-C CDC)

The Tremor Tile exposes a USB CDC serial interface at 115200 baud (8N1) for configuration and data streaming.

### Command Format

All commands use the following packet format:

```
[0xAA] [0x55] [CMD] [LEN] [DATA...]
```

| Field | Size | Description |
|-------|------|-------------|
| Header | 2 bytes | Always 0xAA 0x55 |
| CMD | 1 byte | Command code |
| LEN | 1 byte | Length of DATA field |
| DATA | 0-255 bytes | Command-specific data |

### Response Format

Same structure, with CMD being the echoed command + 0x80:

```
[0xAA] [0x55] [CMD+0x80] [LEN] [DATA...]
```

### Command Reference

| CMD | Name | Data In | Data Out | Description |
|-----|------|---------|----------|-------------|
| 0x01 | GET_STATUS | — | 8 bytes | Get device status |
| 0x02 | START_LEARNING | — | 1 byte (ack) | Start baseline learning |
| 0x03 | STOP_LEARNING | — | 1 byte (ack) | Stop learning, save baseline |
| 0x04 | RESET_BASELINE | — | 1 byte (ack) | Reset baseline, restart learning |
| 0x05 | SET_THRESHOLD | 4 bytes (float) | 1 byte (ack) | Set anomaly threshold (σ) |
| 0x06 | GET_BASELINE | — | 128 bytes | Get baseline statistics |
| 0x07 | GET_SPECTRUM | — | 24+ bytes | Get current spectral features |
| 0x10 | SET_SAMPLE_RATE | 1 byte | 1 byte (ack) | Set sample rate (0=100Hz, 1=200Hz, 2=400Hz) |
| 0x11 | SET_FFT_SIZE | 1 byte | 1 byte (ack) | Set FFT size (0=256, 1=512, 2=1024) |
| 0x12 | SET_AXIS | 1 byte | 1 byte (ack) | Set analysis axis (0=X, 1=Y, 2=Z) |
| 0x13 | SET_LORA_FREQ | 4 bytes (float) | 1 byte (ack) | Set LoRa frequency (MHz) |
| 0x14 | SET_LORA_SF | 1 byte | 1 byte (ack) | Set LoRa spreading factor (7-12) |
| 0x15 | SET_HEARTBEAT | 4 bytes (uint32) | 1 byte (ack) | Set heartbeat interval (seconds) |
| 0x20 | STREAM_FFT | 1 byte (0=off, 1=on) | 1 byte (ack) | Enable/disable FFT streaming |
| 0x30 | GET_FIRMWARE | — | 16 bytes | Get firmware version string |
| 0xFF | REBOOT | — | — | Reboot device |

### GET_STATUS Response (8 bytes)

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0 | 1 | mode | 0=sleep, 1=monitor, 2=active, 3=mapping |
| 1 | 1 | battery_pct | Battery percentage (0-100) |
| 2 | 1 | learning | 0=monitoring, 1=learning baseline |
| 3 | 1 | anomaly_state | 0=normal, 1=anomaly alert |
| 4 | 4 | baseline_samples | Number of baseline samples (uint32 LE) |

### GET_SPECTRUM Response (24+ bytes)

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0 | 4 | rms | RMS vibration (float LE, g) |
| 4 | 4 | crest_factor | Crest factor (float LE) |
| 8 | 4 | kurtosis | Kurtosis (float LE) |
| 12 | 4 | spectral_centroid | Spectral centroid (float LE, Hz) |
| 16 | 4 | total_energy | Total spectral energy (float LE) |
| 20 | 4 | num_peaks | Number of detected peaks (uint32 LE) |
| 24+ | N×8 | peaks | Peak frequency (float LE) + amplitude (float LE) |

### STREAM_FFT Data Format

When FFT streaming is enabled, the device sends continuous packets:

```
[0xAA] [0x55] [0x10] [LEN] [FFT_DATA...]
```

FFT_DATA contains 512 float32 LE values (magnitude spectrum, DC to Nyquist).

## LoRa Protocol

### Packet Structure

All LoRa packets have the following structure:

```
[PREAMBLE] [SYNC_WORD] [HEADER] [PAYLOAD] [CRC]
```

| Field | Size | Description |
|-------|------|-------------|
| Preamble | 8 symbols | Standard LoRa preamble |
| Sync Word | 2 bytes | 0x12 (private) or 0x34 (public) |
| Header | Variable | Explicit header mode |
| Payload | 12-256 bytes | See packet types below |
| CRC | 2 bytes | CCITT CRC-16 |

### Packet Types

#### Heartbeat (12 bytes, every 1 hour)

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0 | 1 | type | 0x01 |
| 1 | 2 | device_id | Device identifier (uint16 BE) |
| 3 | 1 | battery_pct | Battery percentage (0-100) |
| 4 | 1 | status_flags | Status bitmask |
| 5 | 4 | uptime_s | Uptime in seconds (uint32 BE) |
| 9 | 3 | reserved | Reserved for future use |

#### Spectral Summary (48 bytes, every 15 min)

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0 | 1 | type | 0x02 |
| 1 | 2 | device_id | Device identifier |
| 3 | 4 | timestamp | Unix timestamp (uint32 BE) |
| 7 | 40 | peaks | 5 peaks × (freq:float32 + amp:float32) |
| 47 | 1 | num_peaks | Number of valid peaks |

#### Anomaly Alert (32 bytes, immediate)

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0 | 1 | type | 0x03 |
| 1 | 2 | device_id | Device identifier |
| 3 | 1 | alert_type | Anomaly type (see alert codes) |
| 4 | 1 | severity | Severity level (1-10) |
| 5 | 2 | affected_bands | Bitmask of affected frequency bands |
| 7 | 4 | timestamp | Unix timestamp (uint32 BE) |
| 11 | 4 | rms | Current RMS (float32 BE) |
| 15 | 4 | peak_freq | Dominant peak frequency (float32 BE) |
| 19 | 13 | reserved | Reserved for future use |

#### Alert Type Codes

| Code | Name | Description |
|------|------|-------------|
| 0x01 | NEW_PEAK | New spectral peak detected |
| 0x02 | PEAK_SHIFT | Existing peak shifted frequency |
| 0x03 | BAND_ENERGY | Band energy exceeds baseline |
| 0x04 | RMS_INCREASE | Overall RMS vibration increased |
| 0x05 | KURTOSIS | Impulsive event detected |
| 0x06 | TAMPER | Case opened (reed switch) |
| 0x07 | TEMPERATURE | Temperature out of range |

#### Affected Bands Bitmask

| Bit | Band | Frequency Range |
|-----|------|----------------|
| 0 | Very Low | 0.1 – 10 Hz |
| 1 | Low | 10 – 50 Hz |
| 2 | Mid | 50 – 200 Hz |
| 3 | High | 200 – 500 Hz |
| 4 | Very High | 500 – 1500 Hz |

## I²C Addresses

| Device | Address | Bus | Description |
|--------|---------|-----|-------------|
| BME280 | 0x77 | I2C0 | Temperature/Humidity/Pressure |
| DS3231 | 0x68 | I2C0 | Real-Time Clock |

## SPI Devices

| Device | Bus | CS Pin | Clock | Description |
|--------|-----|--------|-------|-------------|
| ADXL355 | SPI0 | GPIO1 | 4 MHz | 3-axis accelerometer |
| SX1262 | SPI1 | GPIO5 | 4 MHz | LoRa transceiver |
| W25Q128 | SPI0 | GPIO24 | 24 MHz | QSPI flash (shares SPI0 with ADXL355) |

## ADXL355 Register Map

| Address | Name | R/W | Default | Description |
|---------|------|-----|---------|-------------|
| 0x00 | DEVID_AD | R | 0xAD | Analog Devices ID |
| 0x01 | DEVID_MST | R | 0x1D | MEMS ID |
| 0x02 | PARTID | R | 0xED | Part ID |
| 0x04 | STATUS | R | — | Status flags |
| 0x08-0x10 | X/Y/ZDATA | R | — | 20-bit axis data |
| 0x11 | FIFO_DATA | R | — | FIFO read |
| 0x28 | FILTER | R/W | 0x00 | ODR + HPF settings |
| 0x29 | FIFO_SAMPLES | R/W | 0x0000 | FIFO watermark |
| 0x2C | RANGE | R/W | 0x01 | ±2g/±4g/±8g |
| 0x2D | POWER_CTL | R/W | 0x00 | Standby/measurement |
| 0x2F | RESET | W | — | Reset (write 0x52) |

## SX1262 Key Registers

| Address | Name | R/W | Description |
|---------|------|-----|-------------|
| 0x0740 | LR_SYNCWORD | R/W | LoRa sync word (0x12 private, 0x34 public) |
| 0x0889 | CALIBR | W | Calibration settings |
| 0x088D | PA_CONFIG | R/W | PA configuration |

## Power States

| State | Current | Wake Source | Description |
|-------|---------|-------------|-------------|
| Deep Sleep | 25µA | RTC alarm, GPIO interrupt | All clocks off, RTC running |
| Monitor | 100µA avg | RTC alarm (10s) | Periodic sampling, LoRa RX |
| Active | 12mA | Continuous | FFT processing, streaming |
| LoRa TX | 120mA | Software trigger | Transmitting alert or summary |
| USB Connected | 15-50mA | USB VBUS | Field service, configuration |

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0x01 | ERR_ADXL355 | Accelerometer communication error |
| 0x02 | ERR_SX1262 | LoRa radio communication error |
| 0x04 | ERR_BME280 | Environmental sensor error |
| 0x08 | ERR_DS3231 | RTC communication error |
| 0x10 | ERR_FLASH | QSPI flash write error |
| 0x20 | ERR_BASELINE | Baseline corruption detected |
| 0x40 | ERR_BATTERY | Battery critically low (<5%) |
| 0x80 | ERR_TAMPER | Tamper switch triggered |