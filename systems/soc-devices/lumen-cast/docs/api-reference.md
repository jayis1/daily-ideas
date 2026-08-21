# Lumen Cast — API Reference

## Firmware Architecture

The Lumen Cast firmware runs on an STM32G491RET6 (Cortex-M4F @ 170 MHz) with a cooperative super-loop architecture. Timer ISRs drive the stepper motor step generation and button debouncing, while the main loop handles the scan state machine, sensor sampling, display updates, and communication.

### Task Overview

| Task | Rate | Description |
|------|------|-------------|
| Stepper step gen | Timer ISR | TIM2 PWM step pulse generation |
| Servo PWM | 50 Hz (TIM3) | SG90 servo position control |
| Sensor sampling | Per scan step | OPT3001 lux + TCS34725 RGBC at each angle |
| Motor movement | Per scan step | Move-to-angle, wait for completion |
| Goniometry | Post-scan | Spherical integration, beam analysis |
| Display update | Per scan step + post | SH1106 OLED framebuffer flush |
| BLE bridge poll | 20 Hz (main loop) | UART frame parsing from ESP32-C3 |
| Button poll | 20 Hz (main loop) | Debounced button reading |

### Scan State Machine

```
MODE_IDLE → (SCAN button) → MODE_HOMING → MODE_SCANNING → MODE_RESULTS → MODE_IDLE
                                                           ↓
Hold MODE 3s → MODE_CALIBRATION → MODE_IDLE
```

## Sensor APIs

### OPT3001 Illuminance Sensor

```c
// Initialize the OPT3001 sensor
int opt3001_init(void);

// Read illuminance in lux (0.045 – 188,000 lux range)
int opt3001_read_lux(float *lux);
```

**Candela computation:** `I (cd) = E (lux) × r² (m²)` where r = 0.15 m

### TCS34725 Color Sensor

```c
// Initialize the TCS34725
int tcs34725_init(void);

// Read raw RGBC channels (16-bit each)
int tcs34725_read_rgbc(uint16_t *r, uint16_t *g, uint16_t *b, uint16_t *c);

// Compute CCT and Duv from RGBC values
void color_compute_cct_duv(uint16_t r, uint16_t g, uint16_t b, uint16_t c,
                            float *cct_k, float *duv, float *x, float *y);
```

**CCT computation:** McCamy's approximation from CIE 1931 chromaticity (x, y)
**Duv computation:** Signed distance from Planckian locus in CIE 1960 uv space

### Motor Control

```c
void motor_init(void);
void motor_enable(bool en);
void motor_move_to_deg(float target_deg, float rpm);
bool motor_at_target(void);
float motor_get_position_deg(void);
void motor_home(void);
```

**Stepper:** NEMA8, 3200 steps/rev (16 microsteps), driven by TMC2209
**Step generation:** TIM2_CH1 PWM on PA0, frequency = (rpm × 3200) / 60

### Servo Control

```c
void servo_init(void);
void servo_set_elevation(float elev_deg);  // -90° to +90°
```

**Servo:** SG90, 50 Hz PWM on TIM3_CH1 (PA6)
**Mapping:** elev -90° → 500µs, elev 0° → 1450µs, elev +90° → 2400µs

## Goniometry API

```c
// Compute all photometric results from a scan buffer
void goniometry_compute(scan_buffer_t *s, photo_result_t *r);

// Spherical integration: Φ = ∮ I dΩ
float goniometry_integrate_flux(const scan_buffer_t *s);

// Beam angle at fraction of peak (0.5 = FWHM)
float goniometry_beam_angle(const scan_buffer_t *s, float fraction);

// Find peak luminous intensity and its angular position
void goniometry_find_peak(const scan_buffer_t *s, float *peak_cd,
                           float *az, float *el);
```

### Computed Parameters

| Parameter | Unit | Description |
|-----------|------|-------------|
| luminous_flux_lm | lm | Total luminous flux (spherical integration) |
| peak_candela | cd | Maximum luminous intensity |
| beam_angle_fwhm | ° | Full width at half maximum |
| field_angle_10pct | ° | Angle to 10% of peak |
| cbcp_candela | cd | Center beam candlepower (on-axis) |
| beam_uniformity | ratio | Min/max within FWHM cone |
| throw_m | m | Distance to 0.25 lux (ANSI FL-1) |
| cct_onaxis_k | K | CCT at beam center |
| duv_onaxis | — | Duv at beam center |
| delta_cct_k | K | CCT variation across beam |
| macadam_steps_edge | steps | Color shift at beam edge |

### Spherical Integration Formula

```
Φ (lm) = Σ I(θᵢ, φⱼ) × sin(θᵢ) × Δθ × Δφ
```

Where θ = polar angle (0 = nadir, 180 = zenith), φ = azimuth, dΩ = sin(θ) dθ dφ

### McCamy's CCT Approximation

```
n = (x - 0.3320) / (0.1858 - y)
CCT = 449n³ + 3525n² + 6823.3n + 5520.33
```

## BLE Bridge Protocol (UART)

Communication between STM32G491 and ESP32-C3 uses binary frames:

```
[SYNC1=0xAA][SYNC2=0x55][TYPE][LEN_LO][LEN_HI][PAYLOAD...][CRC8]
```

### Frame Types

| Type | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x01 | RESULT | STM32→ESP32 | Packed photo_result_t (128 bytes) |
| 0x02 | SCAN_DATA | STM32→ESP32 | Live scan samples (chunked) |
| 0x03 | IES_FILE | STM32→ESP32 | IES LM-63 file content (chunked) |
| 0x04 | LDT_FILE | STM32→ESP32 | EULUMDAT file content (chunked) |
| 0x05 | DEVICE_INFO | STM32→ESP32 | Firmware version, battery, scan count |
| 0x06 | TIME_SYNC | ESP32→STM32 | NTP epoch time (4 bytes) |
| 0x07 | CAL_UPDATE | ESP32→STM32 | Calibration factor update (4 bytes float) |

## Flash Logging API

```c
int flashlog_init(void);
float flashlog_load_cal_factor(void);
void flashlog_save_cal_factor(float factor);
int flashlog_write_scan(const photo_result_t *r, const scan_buffer_t *s);
int flashlog_read_scan(uint16_t id, photo_result_t *r);
uint16_t flashlog_get_count(void);
```

**Flash layout (W25Q128, 16 MB):**
- 0x000000: Header (magic, scan count, calibration factor)
- 0x001000: Scan records (1024 × 512 bytes = 512 KB)
- 0x080000: Raw scan data archive (15 MB)

## Scan Configuration

```c
typedef enum {
    SCAN_TYPE_A = 0,     // azimuth only, 0–360° @ 1° (360 samples)
    SCAN_TYPE_C,         // 2-axis: 24 az × 12 el (15° grid)
    SCAN_MERIDIAN,       // elevation sweep at fixed azimuth
    SCAN_NEARFIELD,      // dense ±60° grid at 5° resolution
} scan_type_t;
```

| Scan Type | Grid | Duration | Best For |
|-----------|------|----------|----------|
| Type A | 360×1 | ~30s | Omnidirectional/rotationally symmetric |
| Type C | 24×12 | ~90s | General 3D distribution |
| Meridian | 1×180 | ~45s | Vertical plane cut |
| Near-field | 25×25 | ~100s | Narrow-beam LED profiling |

## Python Companion App

```bash
# Demo mode (synthetic data)
python3 lumen_cast_viewer.py --demo

# With specific scan type
python3 lumen_cast_viewer.py --demo --scan-type "Type C"

# Export IES and LDT files
python3 lumen_cast_viewer.py --demo --export scan.ies

# BLE connection
python3 lumen_cast_viewer.py --ble

# CSV import
python3 lumen_cast_viewer.py --csv data.csv
```