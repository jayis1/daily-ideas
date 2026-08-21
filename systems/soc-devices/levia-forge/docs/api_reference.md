# Levia Forge — Firmware API Reference

## Modules

### phase_compute

Phase computation for acoustic focusing.

#### Functions

```c
void phase_compute_init(void);
```
Initialize the phase computation engine. Clears the phase buffer and
phase step array. Call once at startup.

```c
void phase_compute_point(float px, float py, float pz);
```
Compute phase delays for a single focal point at (px, py, pz) in mm.
Updates the internal phase buffer. The focal point should be within
the working volume (±15mm X/Y, 0–20mm Z).

```c
void phase_compute_twin(float px, float py, float pz, float delta);
```
Compute twin trap: two focal points at (px - delta/2, py, pz) and
(px + delta/2, py, pz). Even-indexed transducers focus on point A,
odd-indexed on point B.

```c
void phase_compute_vortex(float px, float py, float pz, int topological_charge);
```
Compute vortex trap with azimuthal phase gradient. `topological_charge`
(ℓ) determines the number of phase singularities (1 = single vortex,
2 = double). Creates a rotating pressure field that spins the
levitated particle.

```c
void phase_compute_bending(float px, float py, float pz, float gradient);
```
Compute bending trap with linear phase gradient along X. The
`gradient` parameter (rad/mm) controls the tilt direction and
magnitude. Used for particle transport.

```c
void phase_compute_transport(float py, float pz, float progress, float sweep_range);
```
Compute moving line trap for conveyor operation. `progress` (0.0–1.0)
sweeps the trap along X from -sweep_range to +sweep_range. Call
repeatedly with increasing `progress` to move particles.

```c
void phase_pack_buffer(void);
```
Pack the current phase steps into the DMA buffer. Called automatically
by all `phase_compute_*` functions, but can be called manually after
modifying phase steps directly.

```c
uint8_t *phase_get_buffer(void);
```
Returns a pointer to the 2304-byte DMA phase buffer.

---

### phase_engine

PIO + DMA hardware driver for the 72-channel serial phase stream.

#### Functions

```c
void phase_engine_init(void);
```
Initialize the PIO state machine and DMA channels. Call once at
startup, after `phase_compute_init()`.

```c
void phase_engine_start(void);
```
Start the continuous DMA transfer and PIO bitstream. Unblanks the
transducer outputs (OE low). Transducers begin emitting immediately.

```c
void phase_engine_stop(void);
```
Stop the DMA transfer and PIO state machine. Blanks the transducer
outputs (OE high).

```c
void phase_engine_set_blank(bool blanked);
```
Enable/disable transducer output without stopping DMA. When `blanked`
is true, OE goes high and all transducers are silent. When false,
transducers emit the current phase pattern. This is the primary
on/off control during normal operation.

```c
bool phase_engine_is_underrun(void);
```
Returns true if the DMA buffer has underrun (PIO FIFO emptied faster
than DMA could refill). Indicates a performance problem.

```c
uint32_t phase_engine_get_cycles(void);
```
Returns the number of complete DMA buffer cycles since start.

---

### transducer_layout

3D positions of all 72 transducers.

#### Functions

```c
void transducer_layout_init(void);
```
Compute the 3D positions of all 72 transducers based on the array
geometry (6×6 grid, 10mm spacing, 40mm curvature radius, ±35mm
Z offset).

```c
const transducer_pos_t *transducer_get_positions(void);
```
Returns a pointer to the array of 72 transducer positions.

```c
const transducer_pos_t *transducer_get(int idx);
```
Returns a pointer to the position of transducer `idx` (0–71).

#### Data Structure

```c
typedef struct {
    float x, y, z;      // position in mm
    float nx, ny, nz;   // unit normal (toward trap center)
} transducer_pos_t;
```

---

### display

SSD1306 OLED display driver (128×64, I2C1, address 0x3C).

#### Functions

```c
void display_init(void);
void display_show_boot(void);
void display_update(void *state);
```

The `state` parameter is a pointer to the main `levia_state_t`
structure. The display reads: actual_x/y/z, pattern, active,
particle_detected, particle_height_mm, battery_mv, temp_c, safety,
uptime_ms.

---

### tof

VL53L0X time-of-flight distance sensor (I2C0, address 0x29).

#### Functions

```c
void tof_init(void);
float tof_read_distance_mm(void);
bool tof_is_present(void);
```

`tof_read_distance_mm()` returns the distance in mm to the nearest
object below the sensor (the levitated particle), or -1.0 if no
object is detected or the sensor is not initialized.

---

### sd_log

SD card logging via SPI0.

#### Functions

```c
void sd_log_init(void);
void sd_log_write(void *state);
```

Logs a CSV line at 10 Hz with: uptime_ms, pattern, x, y, z,
particle_height, battery_mv, temperature, safety_state.

---

### ble_bridge

UART communication with the ESP32-C3 BLE module.

#### Functions

```c
void ble_bridge_init(void);
void ble_bridge_send_state(void *state);
void ble_bridge_poll(void *state);
```

#### Protocol

**RP2040 → ESP32-C3** (state update, 10 Hz):
```
STATE,<x>,<y>,<z>,<pattern>,<particle_detected>,<battery_mv>,<safety>\n
```

**ESP32-C3 → RP2040** (commands from phone app):
```
CMD,SET_XYZ,<x>,<y>,<z>\n
CMD,SET_PATTERN,<pattern_id>\n
CMD,SET_ACTIVE,<0|1>\n
CMD,SET_PARAM,<name>,<value>\n
```

Parameter names: `vortex_charge`, `twin_delta`, `bend_gradient`,
`transport_speed`, `auto_track`.

---

### safety

Safety monitor for lid interlock, tilt, battery, temperature.

#### Functions

```c
void safety_init(void);
int safety_check(void *state);
```

Returns a `safety_state_t` enum value:
- `SAFETY_OK` (0) — all checks pass
- `SAFETY_LID_OPEN` (1) — reed switch open
- `SAFETY_TILT_EXCEEDED` (2) — IMU tilt > 15°
- `SAFETY_BATTERY_LOW` (3) — battery < 6.0V
- `SAFETY_OVERTEMP` (4) — temp > 70°C
- `SAFETY_EMERGENCY_RELEASE` (5) — release button pressed
- `SAFETY_WATCHDOG` (6) — watchdog timeout
- `SAFETY_DISABLED` (7) — manually disabled

---

### input

User input: joystick, rotary encoder, buttons, battery, temperature.

#### Functions

```c
void input_init(void);
input_joystick_t input_read_joystick(void);
float input_read_encoder_delta(void);
bool input_read_button(uint8_t pin);
int input_read_battery_mv(void);
float input_read_temp_c(void);
void input_set_led(bool on);
```

#### Data Structure

```c
typedef struct {
    float x;  // -1.0 to +1.0 (left to right)
    float y;  // -1.0 to +1.0 (down to up)
} input_joystick_t;
```

---

## Configuration

All build-time constants are in `sdkconfig.h`. Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CARRIER_FREQ_HZ` | 40000 | Ultrasonic carrier frequency |
| `PHASE_STEPS` | 256 | Phase quantization resolution |
| `PIO_CLOCK_HZ` | 10240000 | PIO serial bit clock |
| `NUM_TRANSDUCERS` | 72 | Total transducer count |
| `CONTROL_LOOP_HZ` | 50 | Phase recomputation rate |
| `WORK_VOL_X_MM` | 15.0 | Working volume X half-width |
| `WORK_VOL_Y_MM` | 15.0 | Working volume Y half-width |
| `WORK_VOL_Z_MAX_MM` | 20.0 | Working volume Z maximum |
| `BATTERY_LOW_MV` | 6000 | Low battery threshold |
| `TILT_MAX_DEGREES` | 15.0 | Max tilt before safety trip |
| `TEMP_MAX_C` | 70.0 | Max temperature before trip |