# Flux Ring — API Reference

## BLE GATT Service

The Flux Ring exposes a BLE GATT service for reading field data, controlling the device, and streaming samples.

### Service UUID

`0xFFB0` (Flux Ring Service)

### Characteristics

| UUID | Name | Access | Type | Description |
|------|------|--------|------|-------------|
| 0xFFB1 | Field X | Read/Notify | float32 | Tilt-compensated X component (Gauss) |
| 0xFFB2 | Field Y | Read/Notify | float32 | Tilt-compensated Y component (Gauss) |
| 0xFFB3 | Field Z | Read/Notify | float32 | Tilt-compensated Z component (Gauss) |
| 0xFFB4 | Magnitude | Read/Notify | float32 | Total field magnitude (Gauss) |
| 0xFFB5 | Heading | Read/Notify | uint16 | Compass heading 0–359° |
| 0xFFB6 | Dominant Pole | Read | uint8 | 0=none, 1=N, 2=S |
| 0xFFB7 | Sample Rate | Read/Write | uint8 | 0=10Hz, 1=100Hz, 2=200Hz |
| 0xFFB8 | Mode | Read/Write | uint8 | 0=monitor, 1=explore, 2=mapping, 3=compass |
| 0xFFB9 | Battery | Read | uint8 | Battery level 0–100% |
| 0xFFBA | Device Info | Read | string | "Flux Ring v1.0" |

### Stream Packet Format

When notifications are enabled on Field X (0xFFB1) in mapping mode, the device sends packed binary packets at the configured sample rate:

```
Offset  Size  Type     Field
0       4     uint32   Timestamp (ms since boot)
4       4     float32  Field X (Gauss, tilt-compensated)
8       4     float32  Field Y (Gauss)
12      4     float32  Field Z (Gauss)
16      2     int16    Accel X (0.001 g/LSB)
18      2     int16    Accel Y (0.001 g/LSB)
20      2     int16    Accel Z (0.001 g/LSB)
22      2     uint16   Heading (degrees, 0–359)
Total: 24 bytes
```

At 200Hz, throughput is 4.8 KB/s — well within BLE 5.0 capacity.

### BLE Advertising Data

In non-connected modes (monitor, compass), the device advertises:

```
[Flags: General Discoverable, No BR/EDR]
[Complete 16-bit UUID: 0xFFB0]
[Manufacturer Specific Data (8 bytes)]:
  Byte 0-1: Manufacturer ID (placeholder 0x0059)
  Byte 2-3: Magnitude × 100 (uint16, little-endian)
  Byte 4-5: Heading (uint16, little-endian)
  Byte 6:   Dominant pole (0/1/2)
  Byte 7:   Mode (0-3)
```

---

## UART Console Commands

When connected via USB-C, the following console commands are available:

| Command | Description |
|---------|-------------|
| `status` | Print current sensor readings |
| `mode <0-3>` | Set operating mode |
| `rate <0-2>` | Set sample rate |
| `calibrate` | Trigger figure-8 calibration |
| `cal reset` | Reset calibration to defaults |
| `log dump` | Dump flash log as CSV |
| `log erase` | Erase flash log |
| `log count` | Print number of logged samples |
| `set_reset` | Trigger MMC5983MA SET/RESET cycle |
| `reboot` | Software reset |
| `dfu` | Enter DFU mode for OTA updates |

---

## C API (Firmware)

### Sensor Drivers

#### mag_sensor

```c
int mag_sensor_init(const struct device *i2c_dev);
int mag_sensor_set_reset(void);
int mag_sensor_read(mag_data_t *data);
int mag_sensor_calibrate(mag_calibration_t *cal, uint32_t duration_ms);
```

- `mag_data_t` — `{ float x, y, z; }` in Gauss
- `mag_calibration_t` — `{ float offset_x/y/z, scale_x/y/z; }`
- SET/RESET should be called every ~10 seconds
- Calibration returns 0 on success, negative on failure

#### accel_sensor

```c
int accel_sensor_init(const struct device *i2c_dev);
int accel_sensor_read(accel_data_t *data);
int accel_sensor_set_wom_threshold(uint16_t threshold_mg);
```

- `accel_data_t` — `{ float x, y, z; }` in g
- WOM threshold: minimum motion to wake from sleep (default 32 mg)

#### baro_sensor

```c
int baro_sensor_init(const struct device *i2c_dev);
int baro_sensor_read(baro_data_t *data);
```

- `baro_data_t` — `{ float pressure_mbar, temperature_c, altitude_m; }`

### Field Engine

```c
field_vector_t field_engine_compensate(const mag_data_t *mag,
                                       const accel_data_t *accel);
float field_engine_magnitude(const field_vector_t *field);
pole_t field_engine_dominant_pole(const field_vector_t *field);
```

- `field_vector_t` — `{ float x, y, z, x_raw, y_raw, z_raw; }` (tilt-compensated + raw)
- `pole_t` — `POLE_NONE (0)`, `POLE_N (1)`, `POLE_S (2)`
- Tilt compensation uses roll/pitch from accelerometer to project mag vector onto horizontal plane

### Compass

```c
compass_heading_t compass_compute(const field_vector_t *field,
                                  const accel_data_t *accel);
const char *compass_cardinal(compass_heading_t heading);
```

- Returns heading 0–359° (0=North, 90=East, 180=South, 270=West)
- Cardinal returns 16-point direction string ("N", "NNE", "NE", etc.)

### Haptic Feedback

```c
int haptic_feedback_init(const struct device *i2c_dev);
void haptic_feedback_set_intensity(float magnitude_gauss, pole_t pole);
void haptic_feedback_off(void);
void haptic_pulse(uint32_t duration_ms);
```

- DRV2603L haptic driver with built-in waveform library
- `set_intensity` auto-selects pulse rate and waveform based on field strength
- `haptic_pulse` for UI feedback (mode change acknowledgment)

### LED Feedback

```c
int led_feedback_init(void);
void led_feedback_set_field(float magnitude_gauss, pole_t pole);
void led_feedback_off(void);
```

- WS2812B RGB LED with 6-level color gradient
- N-pole adds warm (red) tint, S-pole adds cool (blue) tint
- Brightness scales with field strength

### OLED Display

```c
int oled_display_init(void);
void oled_display_update(const field_vector_t *field, float magnitude,
                         compass_heading_t heading, pole_t pole,
                         disp_mode_t mode, uint8_t battery_pct);
void oled_display_calibrating(void);
void oled_display_cal_ok(void);
void oled_display_off(void);
void oled_display_on(void);
```

- 64×32 monochrome SSD1306 OLED
- Display layout varies by mode (see README.md for layouts)

### BLE Service

```c
int ble_service_init(void);
void ble_service_update_field(float x, float y, float z,
                              float magnitude,
                              compass_heading_t heading,
                              pole_t pole,
                              uint8_t battery_pct);
void ble_service_update_advertising(float magnitude,
                                    compass_heading_t heading,
                                    pole_t pole,
                                    uint8_t mode);
void ble_stream_sample(const field_vector_t *field,
                       const accel_data_t *accel,
                       const baro_data_t *baro,
                       compass_heading_t heading,
                       uint32_t timestamp_ms);
bool ble_is_connected(void);
```

### Data Logger

```c
int data_logger_init(void);
int data_logger_append(const field_vector_t *field,
                       const accel_data_t *accel,
                       compass_heading_t heading);
uint32_t data_logger_sample_count(void);
int data_logger_erase(void);
int data_logger_dump_uart(void);
```

- W25Q16 2MB SPI flash
- 22 bytes per sample
- ~90,000 samples at 100Hz = 15 minutes
- ~250,000 samples at 10Hz = ~7 hours

### Power Manager

```c
int power_manager_init(void);
uint8_t power_manager_battery_pct(void);
uint16_t power_manager_battery_mv(void);
void power_manager_deep_sleep(void);
void power_manager_idle(void);
bool power_manager_usb_connected(void);
```

- Battery percentage from LiPo voltage curve
- Deep sleep: wake on accelerometer motion interrupt
- Idle: CPU halted, peripherals active

### Touch Input

```c
int touch_input_init(void (*single_tap_cb)(void),
                     void (*double_tap_cb)(void));
void touch_input_poll(void);
```

- Capacitive touch on P0.09
- Single tap: cycle mode
- Double tap: toggle mapping mode

---

## Python API

### read_flux.py

```python
# Scan for devices
python3 scripts/read_flux.py --scan

# Read current values
python3 scripts/read_flux.py --mac AA:BB:CC:DD:EE:FF

# Stream with live plot
python3 scripts/read_flux.py --mac AA:BB:CC:DD:EE:FF --stream

# Save to CSV
python3 scripts/read_flux.py --mac AA:BB:CC:DD:EE:FF --stream -o data.csv
```

### calibrate.py

```python
# 10-second calibration (default)
python3 scripts/calibrate.py --mac AA:BB:CC:DD:EE:FF

# Extended 15-second calibration
python3 scripts/calibrate.py --mac AA:BB:CC:DD:EE:FF --duration 15
```

### export_log.py

```python
# Export binary log to CSV
python3 scripts/export_log.py --input log_data.bin -o field_data.csv

# Export to VTK (for ParaView)
python3 scripts/export_log.py --input log_data.bin -o field_data --format vtk
```

### spatial_map.py

```python
# Live mapping for 60 seconds
python3 scripts/spatial_map.py --mac AA:BB:CC:DD:EE:FF

# Custom duration
python3 scripts/spatial_map.py --mac AA:BB:CC:DD:EE:FF --duration 120

# Process pre-recorded CSV
python3 scripts/spatial_map.py --input field_data.csv -o field_map
```

---

*See also: [Calibration Guide](calibration_guide.md) | [Assembly Guide](assembly_guide.md)*