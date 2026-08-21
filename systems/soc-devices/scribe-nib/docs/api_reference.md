# Scribe Nib — API Reference

## BLE Services

### HID Keyboard Service (Standard)

The Scribe Nib appears as a standard Bluetooth LE HID keyboard.

- **Service UUID**: `0x1812` (HID)
- **Appearance**: Keyboard (0x03C1)
- **Connection**: Just Works pairing (no PIN required)

The device sends standard HID keyboard reports:
- Modifier byte (shift, ctrl, alt, etc.)
- Reserved byte
- Up to 6 simultaneous keycodes

This works with any BLE-capable OS (iOS, Android, Windows, macOS, Linux)
without installing custom drivers or apps.

### Custom Scribe Service

For advanced features, a custom GATT service is provided.

- **Service UUID**: `0xFFB0` (short) / `0000ffb0-0000-1000-8000-00805f9b34fb` (full)

| Characteristic | UUID | Properties | Type | Description |
|---------------|------|-----------|------|-------------|
| Recognized Text | 0xFFB1 | Read, Notify | UTF-8 string | Cumulative recognized text buffer |
| Last Character | 0xFFB2 | Read, Notify | uint8 | Index of last recognized character (0-61) |
| Confidence | 0xFFB3 | Read | float32 | CNN confidence for last character (0.0-1.0) |
| Raw Stroke Data | 0xFFB4 | Notify | Blob | Raw (x,y) pairs as uint16 pairs |
| Active Profile | 0xFFB5 | Read, Write | uint8 | User profile index (0-3) |
| Recognition Mode | 0xFFB6 | Read, Write | uint8 | 0=auto, 1=letters, 2=numbers |
| Battery Level | 0xFFB7 | Read | uint8 | Battery percentage (0-100%) |
| Firmware Version | 0xFFB8 | Read | String | Semantic version string |

### Character Index Mapping

The `Last Character` (0xFFB2) and `Raw Stroke Data` (0xFFB4) use an index into
the following character set:

| Index Range | Characters | Category |
|------------|-----------|----------|
| 0-9 | `0123456789` | Digits |
| 10-35 | `ABCDEFGHIJKLMNOPQRSTUVWXYZ` | Uppercase |
| 36-61 | `abcdefghijklmnopqrstuvwxyz` | Lowercase |

## Firmware API

### IMU Driver (`imu_driver.h`)

```c
// Initialize ICM-42688-P over SPI
esp_err_t imu_driver_init(spi_host_device_t host, imu_odr_t odr,
                           imu_accel_range_t accel_range,
                           imu_gyro_range_t gyro_range);

// Read samples from FIFO (returns count read)
int imu_driver_read_fifo(imu_sample_t *samples, int max_samples);

// Get current configuration
const imu_config_t *imu_driver_get_config(void);
```

**ODR values**: `IMU_ODR_8HZ`, `IMU_ODR_32HZ`, `IMU_ODR_50HZ`, `IMU_ODR_100HZ`, `IMU_ODR_200HZ`, `IMU_ODR_1KHZ`

**Accelerometer ranges**: `IMU_ACCEL_RANGE_2G`, `IMU_ACCEL_RANGE_4G`, `IMU_ACCEL_RANGE_8G`, `IMU_ACCEL_RANGE_16G`

**Gyroscope ranges**: `IMU_GYRO_RANGE_250DPS`, `IMU_GYRO_RANGE_500DPS`, `IMU_GYRO_RANGE_1000DPS`, `IMU_GYRO_RANGE_2000DPS`

### Stroke Segmenter (`stroke_segmenter.h`)

```c
// Initialize segmenter
void stroke_segmenter_init(void);

// Set Z-axis gravity baseline for pen detection
void stroke_segmenter_set_baseline(float z_gravity);

// Feed IMU sample; returns true when a complete stroke is detected
bool stroke_segmenter_update(const imu_sample_t *sample, stroke_event_t *out_stroke);

// Query pen state
bool stroke_segmenter_is_pen_down(void);
```

### Trajectory Reconstruction (`trajectory_recon.h`)

```c
// Initialize reconstructor
void trajectory_recon_init(void);

// Set magnetometer heading for yaw correction
void trajectory_recon_set_mag_heading(float heading_rad);

// Project 3D stroke to 2D normalized trajectory
void trajectory_recon_project(const stroke_event_t *stroke, traj_2d_t *traj);
```

### Character Recognizer (`char_recognizer.h`)

```c
// Initialize (loads CNN model from flash)
esp_err_t char_recognizer_init(void);

// Classify trajectory
char_pred_t char_recognizer_classify(const traj_2d_t *traj);

// Toggle caps lock / recognition mode
void char_recognizer_toggle_caps(void);
void char_recognizer_toggle_mode(void);
```

### Language Model (`lang_model.h`)

```c
// Initialize (load n-gram from flash)
esp_err_t lang_model_init(void);

// Correct prediction using context
char lang_model_correct(int char_id, float confidence);

// Update context with confirmed character
void lang_model_update_context(char c);
```

### BLE HID (`ble_hid.h`)

```c
// Initialize BLE HID keyboard
esp_err_t ble_hid_init(const char *device_name);

// Send a character as a keystroke
esp_err_t ble_hid_send_key(char c);

// Check connection status
bool ble_hid_is_connected(void);
```

### OLED Display (`oled_display.h`)

```c
// Initialize SSD1306
esp_err_t oled_display_init(void);

// Display single character (large, centered)
esp_err_t oled_display_char(char c);

// Display formatted text (small font)
esp_err_t oled_display_printf(const char *fmt, ...);

// Clear / power control
esp_err_t oled_display_clear(void);
esp_err_t oled_display_off(void);
esp_err_t oled_display_on(void);
```

### Power Manager (`power_manager.h`)

```c
// Initialize
void power_manager_init(void);

// Call periodically to check inactivity
void power_manager_update(void);

// Force wake from sleep
void power_manager_wake(void);

// Record user activity (resets idle timer)
void power_manager_activity(void);
```

### Calibration (`calibration.h`)

```c
// Load / save user profile from NVS
esp_err_t calibration_load_profile(uint8_t profile_id);
esp_err_t calibration_save_profile(uint8_t profile_id);

// Update gravity reference during use
esp_err_t calibration_update_gravity(float z_accel);

// Get calibration parameters
float calibration_get_gravity(void);
float calibration_get_stroke_scale(void);
```

### Gesture Handler (`gesture_handler.h`)

```c
// Initialize
void gesture_handler_init(void);

// Detect gesture from completed stroke
gesture_type_t gesture_handler_detect(const stroke_event_t *stroke);
```

Gesture types: `GESTURE_NONE`, `GESTURE_SPACE`, `GESTURE_BACKSPACE`, `GESTURE_ENTER`, `GESTURE_CAPS_LOCK`, `GESTURE_MODE_SWITCH`, `GESTURE_UNDO`

### Haptic Feedback (`haptic_feedback.h`)

```c
// Initialize vibration motor driver
esp_err_t haptic_feedback_init(gpio_num_t pin, ledc_timer_t timer, ledc_channel_t channel);

// Single / double pulse
esp_err_t haptic_feedback_pulse(uint32_t duration_ms);
esp_err_t haptic_feedback_double(uint32_t pulse_ms);

// Custom pattern
esp_err_t haptic_feedback_pattern(const haptic_pattern_t *pattern, int count);
```

## UART Debug Interface

Serial output at **115200 8N1** on GPIO16 (TX) / GPIO17 (RX).

Log levels:
- `SCRIBE_NIB_DEBUG=1`: Verbose IMU data and stroke details
- `SCRIBE_NIB_DEBUG=0`: Normal operation (recognition results only)

## USB-C Interface

The USB-C port serves dual purpose:
1. **Firmware flash**: ESP32-S3 built-in USB supports DFU mode
2. **Battery charging**: 5V VBUS charges via MCP73831

Hold BOOT button during reset to enter USB download mode.

## Power States

| State | Current | IMU ODR | BLE | OLED | Wake Sources |
|-------|---------|---------|-----|------|-------------|
| ACTIVE | ~12mA | 200Hz | Connected | On | — |
| IDLE | ~4mA | 20Hz | Connected | Off | Motion, touch |
| LIGHT_SLEEP | ~0.8mA | 1Hz | Advertising | Off | Motion, touch, RTC |
| DEEP_SLEEP | ~8µA | Off | Off | Off | Touch, RTC (2s) |