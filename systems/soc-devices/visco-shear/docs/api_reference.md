# Visco Shear — API Reference

## BLE GATT Interface

### Service: Visco Shear (UUID 0xA101)

| Characteristic | UUID | Properties | Description |
|---|---|---|---|
| Torque Stream | 0xA102 | Notify | Real-time torque data (6 bytes per notification) |
| Measurement Result | 0xA103 | Read, Notify | Final measurement summary (up to 32 bytes) |
| Command | 0xA104 | Write | Send commands to the device |
| Device Info | 0xA105 | Read | Firmware version, spindle, temperature |

### Torque Stream Data Format (6 bytes)

| Offset | Field | Type | Units |
|--------|-------|------|-------|
| 0-1 | timestamp | uint16 | sample index |
| 2-3 | torque | int16 | µN·m (×1) |
| 4-5 | omega | int16 | rpm × 100 |

### Measurement Result Format (32 bytes)

| Offset | Field | Type | Units |
|--------|-------|------|-------|
| 0 | model_id | uint8 | model enum (0-6) |
| 1-4 | R² | float32 | unitless |
| 5-8 | avg_viscosity | float32 | mPa·s |
| 9-12 | temperature | float32 | °C |
| 13 | n_points | uint8 | flow curve points |
| 14-29 | model_params | float32[4] | model-dependent |
| 30-31 | reserved | uint16 | 0 |

### Command Format (Write to 0xA104)

| Byte | Value | Description |
|------|-------|-------------|
| 0 | 0x01 | Start measurement |
| 0 | 0x02 | Stop/cancel |
| 0 | 0x03 | Set mode (byte 1 = mode enum) |
| 0 | 0x04 | Set spindle (byte 1 = spindle enum) |
| 0 | 0x05 | Set temperature (bytes 1-4 = float32 °C) |
| 0 | 0x06 | Start calibration |
| 0 | 0x07 | Get device info |

### Device Info Format (48 bytes, Read 0xA105)

| Offset | Field | Type | Description |
|--------|-------|------|-------------|
| 0-23 | version | string (null-terminated) | e.g. "Visco Shear v1.0" |
| 24 | spindle | uint8 | current spindle type |
| 25-28 | temperature | float32 | current cup temperature (°C) |

---

## Wi-Fi Web API

Connect to the **"Visco-Shear"** Wi-Fi network (open, no password), then navigate to `http://192.168.4.1/`.

### Endpoints

| Endpoint | Method | Type | Description |
|---|---|---|---|
| `/` | GET | text/html | Dashboard with live flow curve plot |
| `/data` | GET | application/json | Latest measurement result as JSON |
| `/download` | GET | text/csv | Download last measurement as CSV file |
| `/stream` | GET | text/event-stream | Server-Sent Events live data stream |

### `/data` JSON Response

```json
{
  "model": "Herschel-Bulkley",
  "r_squared": 0.9987,
  "avg_viscosity_mPa_s": 4523.5,
  "temperature_c": 25.0,
  "n_points": 7,
  "params": [2.34, 0.89, 0.62, 0.0],
  "spindle": "CC-13",
  "timestamp": "2026-07-31T10:15:30Z"
}
```

---

## SD Card CSV Format

See README.md "SD Card Log Format" section for the full CSV specification.

---

## UART Protocol (RP2040 ↔ ESP32-C3)

Binary frames at 1 Mbaud (8N1):

```
[0xAA][0x55][cmd][len_lo][len_hi][payload...][crc8]
```

- `cmd`: command/data type
- `len`: payload length (0–256)
- `crc8`: CRC-8 over cmd + len + payload

### Frame Types

| Cmd | Direction | Description |
|-----|-----------|-------------|
| 0x10 | RP2040→C3 | Torque sample (6 bytes) |
| 0x11 | RP2040→C3 | Measurement result |
| 0x12 | RP2040→C3 | Device info response |
| 0x01–0x07 | C3→RP2040 | Commands (forwarded from BLE) |

---

## C API (Firmware)

### Key Functions

```c
/* Start a measurement */
void do_measurement(void);

/* Read torque (µN·m) */
float torque_read_averaged(int n_samples);

/* Set rotation speed */
void stepper_run_rpm(float rpm);

/* Set Peltier target temperature */
void temperature_set_target(float temp_c);

/* Fit rheological models */
void rheology_fit_models(measure_result_t *res);

/* Compute shear rate from angular velocity */
float spindle_shear_rate(spindle_type_t sp, float omega);
```

### Enums

```c
typedef enum { SPINDLE_CC_13, SPINDLE_CP_25, SPINDLE_VN_16, SPINDLE_TB_3 } spindle_type_t;
typedef enum { MODE_FLOW_CURVE, MODE_YIELD_STRESS, MODE_OSCILLATORY, MODE_THIXOTROPY, MODE_SINGLE_SPEED } measure_mode_t;
typedef enum { MODEL_NEWTONIAN, MODEL_POWER_LAW, MODEL_BINGHAM, MODEL_HERSCHEL_BULKLEY, MODEL_CASSON, MODEL_CROSS, MODEL_CARREAU } rheo_model_t;
```