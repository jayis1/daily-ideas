# Spiro Flow — API Reference

## Firmware Architecture

The Spiro Flow firmware runs on a CH32V203RBT6 (RISC-V RV32IMAC @ 144 MHz) with a cooperative super-loop architecture. A 250 Hz timer interrupt drives the pressure sampling, while the main loop handles state machine transitions, display updates, and communication.

### Task Overview

| Task | Rate | Description |
|------|------|-------------|
| Sensor sampling | 250 Hz | SDP810 differential pressure → flow |
| Ambient read | 0.2 Hz | BME280 temperature/pressure/humidity |
| Maneuver capture | 250 Hz | Flow integration → volume buffer |
| Display update | 20 Hz | SH1106 OLED framebuffer flush |
| BLE bridge poll | 10 Hz | UART frame parsing from ESP32-C3 |
| Button poll | 100 Hz | Debounced button reading |

### State Machine

```
MODE_IDLE → (MEASURE button) → MODE_READY
MODE_READY → (flow > 0.5 L/s) → MODE_CAPTURE
MODE_CAPTURE → (maneuver end) → MODE_RESULTS
MODE_RESULTS → (MEASURE button) → MODE_READY (if < 3 maneuvers) or MODE_IDLE
```

## Sensor APIs

### SDP810 Differential Pressure Sensor

```c
// Initialize the SDP810 sensor
int sdp810_init(void);

// Start continuous measurement at 250 Hz
int sdp810_start_continuous(void);

// Stop continuous measurement
int sdp810_stop_continuous(void);

// Read one pressure sample (differential pressure in Pa, temperature in °C)
int sdp810_read_pressure(float *diff_pa, float *temp_c);
```

**Flow computation:** `flow (L/s) = ΔP (Pa) / PNEUMO_RESISTANCE (0.0115 Pa·s/L)`

### BME280 Ambient Sensor

```c
// Initialize BME280
int bme280_init(void);

// Read ambient conditions
// temp_c: temperature in °C
// pressure_mmhg: barometric pressure in mmHg (converted from Pa)
// humidity_pct: relative humidity in %
int bme280_read(float *temp_c, float *pressure_mmhg, float *humidity_pct);
```

### SH1106 OLED Display

```c
// Initialize display
int sh1106_init(void);

// Display modes
void sh1106_draw_idle(void);
void sh1106_draw_ready(uint8_t battery_pct);
void sh1106_draw_capture(const maneuver_buffer_t *m, float current_flow, float current_vol);
void sh1106_draw_results(const spiro_result_t *r, uint8_t battery_pct);
void sh1106_draw_settings(const patient_t *p, int field);
```

## Spirometry Computation API

```c
// Compute all spirometry parameters from a maneuver buffer
void spirometry_compute(maneuver_buffer_t *m, const patient_t *p,
                         const float *ambient, spiro_result_t *r);

// Compute BTPS correction factor
float compute_btps(float temp_c, float pressure_mmhg, float humidity_pct);

// Compute predicted values (ECSC/ERS 1993)
void compute_predicted(const patient_t *p, float *fev1_pred, float *fvc_pred,
                        float *fev1_fvc_pred, float *lln_ratio);

// Grade maneuver quality (ATS/ERS 2019)
quality_grade_t grade_maneuver(const maneuver_buffer_t *m, const spiro_result_t *r);
```

### Computed Parameters

| Parameter | Unit | Description |
|-----------|------|-------------|
| FVC | L | Forced Vital Capacity — total expired volume |
| FEV1 | L | Forced Expiratory Volume in 1 second |
| FEV1/FVC | % | Tiffeneau-Pinelli index (ratio) |
| PEF | L/s | Peak Expiratory Flow |
| FEF25-75 | L/s | Forced Expiratory Flow at 25-75% of FVC |
| FET | s | Forced Expiratory Time |
| PIF | L/s | Peak Inspiratory Flow |
| FIVC | L | Forced Inspiratory Vital Capacity |
| BEV | mL | Back-extrapolation volume (quality metric) |
| PEFT | ms | Time to Peak Expiratory Flow |

### BTPS Correction

Volume and flow are corrected from ambient conditions to Body Temperature, Pressure, Saturated with water vapor (37°C, 47 mmHg PH2O):

```
BTPS = (310.15 / T_ambient_K) × (Pb - PH2O_ambient) / (Pb - 47)
```

### Predicted Values (ECSC/ERS 1993)

**Male:**
- FEV1 = 4.30 × H(m) − 0.029 × Age − 2.89
- FVC = 5.76 × H(m) − 0.026 × Age − 4.34

**Female:**
- FEV1 = 3.95 × H(m) − 0.022 × Age − 2.60
- FVC = 4.43 × H(m) − 0.026 × Age − 2.89

**Ethnicity correction:** African descent ×0.88, Asian ×0.95

**Lower Limit of Normal (LLN):** FEV1/FVC_predicted − 8%

### Quality Grading (ATS/ERS 2019)

| Grade | Criteria |
|-------|----------|
| A (excellent) | BEV ≤ 50mL, FET ≥ 6s, smooth curve |
| B (good) | BEV ≤ 100mL, FET ≥ 3s, minor artifacts |
| C (acceptable) | BEV ≤ 150mL, FET ≥ 3s, some artifacts |
| D (poor) | BEV > 150mL or FET < 3s |
| F (unacceptable) | FVC < 100mL or severe artifacts |

### Diagnostic Classification

| Pattern | Criteria |
|---------|----------|
| Normal | FEV1/FVC ≥ LLN and FVC ≥ 80% predicted |
| Obstructive | FEV1/FVC < LLN and FVC ≥ 80% predicted |
| Restrictive | FEV1/FVC ≥ LLN and FVC < 80% predicted |
| Mixed | FEV1/FVC < LLN and FVC < 80% predicted |

## BLE Bridge Protocol (UART)

Communication between CH32V203 and ESP32-C3 uses binary frames:

```
[SYNC1=0xAA][SYNC2=0x55][TYPE][LEN_LO][LEN_HI][PAYLOAD...][CRC8]
```

### Frame Types

| Type | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x01 | RESULT | CH32→ESP32 | Packed spirometry result (76 bytes) |
| 0x02 | FLOW_DATA | CH32→ESP32 | Raw flow samples (chunked, 50 samples/frame) |
| 0x03 | AMBIENT | CH32→ESP32 | BME280 ambient readings |
| 0x04 | PATIENT | ESP32→CH32 | Patient profile update |
| 0x05 | DEVICE_INFO | CH32→ESP32 | Firmware version, battery, session count |
| 0x06 | TIME_SYNC | ESP32→CH32 | NTP epoch time (4 bytes) |

### RESULT Frame Payload (76 bytes, packed)

```c
struct packed_result_t {
    float fvc_liters;        // 4
    float fev1_liters;       // 4
    float fev1_fvc_ratio;    // 4
    float pef_lps;           // 4
    float fef2575_lps;       // 4
    float fet_sec;           // 4
    float back_extrap_ml;    // 4
    float fev1_pred;         // 4
    float fvc_pred;          // 4
    float fev1_pct_pred;     // 4
    float fvc_pct_pred;      // 4
    uint8_t grade;           // 1
    uint8_t pattern;         // 1
    uint16_t session_id;     // 2
    uint8_t maneuver_count;  // 1
    float btps_factor;       // 4
    float ambient_temp;      // 4
    float ambient_pressure;  // 4
};  // Total: 72 bytes + 4 padding = 76
```

## Flash Logging API

```c
// Initialize flash log (reads header, formats if needed)
int flashlog_init(void);

// Write a session to flash
int flashlog_write_session(const spiro_result_t *r, const maneuver_buffer_t *m);

// Read a past session by index
int flashlog_read_session(uint16_t id, spiro_result_t *r);

// Get total session count
uint16_t flashlog_get_count(void);
```

**Flash layout (W25Q128, 16 MB):**
- 0x000000: Header (magic, session count)
- 0x000100: Session records (512 × 256 bytes)
- 0x080000: Raw flow data archive (optional)

## Python Companion App

```bash
# Demo mode (synthetic data)
python3 spiro_flow_viewer.py --demo --age 35 --height 178 --sex male

# BLE connection
python3 spiro_flow_viewer.py --ble

# CSV export
python3 spiro_flow_viewer.py --demo --export results.csv
```