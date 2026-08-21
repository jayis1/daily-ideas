# API Reference — Thermo Trace Pocket DSC

## BLE Protocol

Thermo Trace communicates with a phone/PC app via BLE using the Nordic
UART Service (NUS) protocol, bridged through the ESP32-C3 module.

### BLE Service

| Property | Value |
|----------|-------|
| Service UUID | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` |
| TX Characteristic (notify) | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` |
| RX Characteristic (write) | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` |
| Device Name | `Thermo Trace` |

### Frame Format

All frames sent from the device have the following format:

```
[0xAA] [0x55] [MSG_TYPE] [LEN] [payload... ] [CRC8]
```

| Field | Size | Description |
|-------|------|-------------|
| 0xAA | 1 | Sync byte 1 |
| 0x55 | 1 | Sync byte 2 |
| MSG_TYPE | 1 | Message type (see below) |
| LEN | 1 | Payload length (0-255) |
| payload | LEN | Message-specific payload |
| CRC8 | 1 | CRC-8 over MSG_TYPE + LEN + payload |

### Message Types

#### BLE_MSG_DATA (0x01) — Real-time DSC data point

Sent at 1 Hz during a scan.

Payload (16 bytes):

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 4 | float32 LE | Temperature (°C) |
| 4 | 4 | float32 LE | Heat flow (mW) |
| 8 | 4 | float32 LE | Time since scan start (s) |
| 12 | 4 | float32 LE | Setpoint temperature (°C) |

#### BLE_MSG_STATUS (0x02) — Device status

Sent on state changes and periodically.

Payload (16 bytes):

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 4 | float32 LE | Current temperature (°C) |
| 4 | 4 | float32 LE | Setpoint (°C) |
| 8 | 4 | float32 LE | Heat flow (mW) |
| 12 | 4 | float32 LE | Ramp rate (°C/min) |
| 14 | 1 | uint8 | Battery (%) |
| 15 | 1 | uint8 | State (0=idle, 1=heating, 2=cooldown, 3=match, 4=abort) |

#### BLE_MSG_MATCH (0x03) — Material identification result

Sent after a scan completes and library matching is done.

Payload (28 bytes):

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 1 | uint8 | Name length |
| 1 | 23 | char | Material name (null-padded) |
| 24 | 4 | float32 LE | Confidence (0.0-1.0) |

Multiple MATCH messages may be sent (up to 3 for top-3 matches).

#### BLE_MSG_DONE (0x04) — Scan complete

No payload. Signals the end of a scan and the end of MATCH messages.

#### BLE_MSG_CALIB (0x05) — Calibration result

Payload (12 bytes):

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 4 | float32 LE | Measured temperature (°C) |
| 4 | 4 | float32 LE | Expected temperature (°C) |
| 8 | 4 | float32 LE | Correction coefficient |

## SD Card Log Format

Data is logged to microSD as a CSV file with the following columns:

```
time_s,temp_C,heat_flow_mW,setpoint_C
0.00,25.03,0.012,25.00
0.10,25.04,0.011,25.08
...
2100.00,299.97,0.003,300.00
```

Each scan creates a new file: `dsc_YYYYMMDD_HHMMSS.csv`

## Firmware API (internal)

### Key functions

```c
/* ADS122U04 ADC */
void ads_init(void);
void ads_read_all(ads_data_t *data);  // reads all 4 channels

/* Heater PID */
void heater_init(void);
void heater_set_pwm(uint8_t channel, float duty);  // 0.0-0.85
void heater_off(void);
float pid_update(pid_t *pid, float measured, float setpoint, float dt);

/* DSC computation */
void dsc_add_point(dsc_scan_t *scan, float temp, float heat_flow, float time);
void dsc_detect_peaks(dsc_scan_t *scan);  // post-scan analysis
float dsc_integrate_peak(dsc_scan_t *scan, uint8_t peak_idx);

/* Library matching */
void library_match(const float *features, dsc_match_t *matches, uint8_t *num);

/* Safety */
bool safety_check(float pan_temp);  // returns true if overtemp
void safety_emergency_cutoff(void);

/* Display */
void display_status(float temp, float setpoint, float heat_flow, float ramp, uint8_t batt);
void display_dsc_curve(const float *temp, const float *hf, uint32_t count, uint32_t max);
void display_match(const char *name, float confidence);
```

### State machine states

| State | Code | Description |
|-------|------|-------------|
| UI_IDLE | 0 | Waiting for user input |
| UI_SET_MASS | 1 | Setting sample mass |
| UI_SET_RAMP | 2 | Setting ramp rate |
| UI_HEATING | 3 | Scan in progress |
| UI_COOLDOWN | 4 | Cooling down after scan |
| UI_ABORT | 5 | Scan aborted |
| UI_MATCH | 6 | Displaying match result |

### Configuration

Firmware configuration constants in `stm32g491_conf.h`:

```c
#define DSC_MAX_TEMP      300.0f   // Maximum scan temperature
#define DSC_RAMP_DEFAULT  5.0f     // Default ramp rate °C/min
#define HEATER_MAX_DUTY   0.85f    // Maximum PWM duty (safety)
#define TEMP_SAFETY_C     320.0f   // Software over-temp cutoff
```

## Python API

The companion Python app (`scripts/thermo_trace_app.py`) provides:

```python
from thermo_trace import ThermoTrace

# Connect via BLE
device = ThermoTrace.connect()

# Subscribe to data stream
device.on_data(lambda temp, heat_flow, time, setpoint: print(f"{temp}°C {heat_flow}mW"))

# Wait for scan to complete
device.wait_done()

# Get match results
matches = device.get_matches()
for m in matches:
    print(f"{m.name}: {m.confidence:.1%}")

# Export data
device.export_csv("scan.csv")
device.export_json("scan.json")
```