# Aero Reed — API Reference

Firmware API documentation for the Aero Reed electronic wind instrument.

## Module: touch

### `void touch_init(void)`
Initialises the ESP32-S3 touch peripheral for all 14 pads. Reads
initial baselines and sets per-pad press thresholds (25% below baseline).

### `void touch_scan(void)`
Scans all 14 touch pads and updates the held-state array. Called at
100 Hz by `sensor_task`.

### `bool touch_pad_held(pad_id_t p)`
Returns `true` if pad `p` is currently being touched.

### `uint32_t touch_pad_mask(void)`
Returns a 14-bit bitmask of all currently held pads (bit N = pad N).

### `int8_t touch_octave_offset(void)`
Returns octave shift: +1 if OCT_UP held, -1 if OCT_DOWN held, 0 otherwise.

### `int16_t touch_decode_note(void)`
Decodes the current fingering to a MIDI note number. Returns -1 if no
valid fingering is detected. Uses a saxophone-style fingering table.

---

## Module: breath

### `void breath_init(void)`
Initialises ADC1 for the MP3V5004G pressure sensor. Measures a
zero-pressure offset (50-sample average) at boot for calibration.

### `void breath_scan(void)`
Reads and processes the breath pressure sensor. Applies oversampling
(4×), subtracts offset, converts to Pascals, and computes a smoothed
velocity value (0..1) with an exponential curve (x^1.6).

### `uint8_t breath_get_velocity(void)`
Returns MIDI velocity (0-127) from the smoothed breath signal.

### `bool breath_get_gate(void)`
Returns `true` when breath pressure exceeds the note-on gate threshold
(30 Pa). Used to trigger note on/off.

### `float breath_get_pressure_kpa(void)`
Returns raw pressure in kPa (for display/diagnostics).

---

## Module: lip

### `void lip_init(void)`
Initialises the lip FSR-402 sensor (via ADC or ADS1115 I2C ADC in
production builds).

### `void lip_scan(void)`
Reads lip force and applies logarithmic scaling + smoothing.

### `int16_t lip_get_bend_cents(void)`
Returns pitch bend in cents (0..+200 for default ±2 semitone range).

### `uint8_t lip_get_brightness(void)`
Returns CC74 brightness value (0-127), derived from lip force.

### `float lip_get_force(void)`
Returns raw normalised force (0.0..1.0).

---

## Module: imu

### `void imu_init(void)`
Initialises the ICM-42688-P over SPI (8 MHz). Verifies WHO_AM_I (0x47),
configures accel ±4g and gyro ±2000 dps at 1 kHz ODR.

### `void imu_scan(void)`
Reads 6-axis data, computes pitch angle from accelerometer, and detects
vibrato from gyro roll-rate oscillation (4-8 Hz band via 32-sample RMS).

### `uint8_t imu_get_modulation(void)`
Returns MIDI modulation CC1 value (0-127) from |pitch| angle (0..45°).

### `float imu_get_pitch_deg(void)`
Returns tilt pitch angle in degrees.

### `float imu_get_vibrato_rate(void)` / `imu_get_vibrato_depth(void)`
Returns detected vibrato rate (Hz) and depth (cents). Zero when no
vibrato is detected.

### `int8_t imu_get_tilt_octave(void)`
Returns octave shift from sharp tilt: +1 (tilt up > 35°), -1 (tilt down
< -35°), 0 otherwise.

---

## Module: synth

### `void synth_init(void)`
Builds 8 wavetables (256 samples each) and initialises 16 voices.

### `void synth_note_on(int8_t note, uint8_t vel, const patch_t *patch)`
Triggers a voice with the given MIDI note, velocity, and patch settings.
Implements voice-stealing if all 16 voices are active.

### `void synth_note_off(int8_t note)`
Releases the voice playing `note` (begin release phase).

### `void synth_set_breath(float v01, const patch_t *patch)`
Sets the global breath amplitude (0..1) with per-patch curve applied.

### `void synth_set_bend_cents(int16_t cents)`
Sets pitch bend in cents (applies to all active voices).

### `void synth_set_modulation(uint8_t cc1)`
Sets modulation amount (0-127).

### `void synth_set_vibrato(float rate_hz, float depth_cents)`
Sets vibrato LFO rate and depth.

### `void synth_render_block(int16_t *stereo, int n_frames)`
Renders `n_frames` of stereo 16-bit audio into `stereo`. Called by
`synth_task` at 44.1 kHz.

### `void synth_task(void *arg)`
FreeRTOS task that continuously renders audio and writes to I2S DMA.

---

## Module: audio

### `void audio_init(void)`
Configures I2S (ESP32-S3 standard mode) for 44100 Hz, 16-bit, stereo.
Maps to GPIO35 (BCK), GPIO36 (WS), GPIO37 (DOUT) → PCM5102A DAC.

### `void audio_write_block(const int16_t *data, size_t bytes)`
Writes `bytes` of audio data to the I2S DMA buffer (blocks if full).

---

## Module: midi

### `void midi_init(void)`
Initialises BLE MIDI (NimBLE GATT service) and USB MIDI (TinyUSB class).

### `void midi_send_note_on/off(uint8_t ch, uint8_t note, uint8_t vel)`
Sends a MIDI note on/off message on both BLE and USB.

### `void midi_send_cc(uint8_t ch, uint8_t cc, uint8_t val)`
Sends a MIDI CC message on both BLE and USB.

### `void midi_send_pitch_bend(uint8_t ch, int16_t bend14)`
Sends a 14-bit pitch bend message (bend14 is unsigned 0..16383, 8192=center).

### `void midi_send_program_change(uint8_t ch, uint8_t prog)`
Sends a MIDI program change (patch selection).

### `void midi_display_task(void *arg)`
FreeRTOS task (50 Hz) that reads `g_state`, sends MIDI messages, and
refreshes the OLED display.

---

## Module: patch

### `void patch_load_all(void)`
Loads all 8 patches from NVS flash. If a patch is not stored, writes the
default.

### `void patch_save(int idx, const patch_t *p)`
Saves a patch to NVS at index `idx` (0-7).

### `patch_t *patch_get(int idx)`
Returns a pointer to patch at index `idx`.

### `void patch_next(void)` / `patch_prev(void)`
Cycles to the next/previous patch and updates `g_state.patch`.

### `const char *patch_name(int idx)`
Returns the 16-char name of patch `idx`.

---

## Module: display

### `void display_init(void)`
Initialises the SSD1306 OLED over I2C (GPIO8=SDA, GPIO9=SCL, 0x3C).

### `void display_update(const aero_state_t *st)`
Renders: patch name, octave, breath bar, note, battery %, charge status,
bend indicator. Uses a built-in 5×7 bitmap font.

---

## Module: power

### `void power_init(void)`
Configures the TP4056 charge-status GPIO and MAX17048 fuel gauge (I2C).

### `void power_task(void *arg)`
FreeRTOS task (1 Hz) that reads battery % and charge status, updates
`g_state.battery_pct` and `g_state.charging`.

---

## Global State

### `aero_state_t g_state`
Shared state structure, updated by `sensor_task` and consumed by
`synth_task` and `midi_display_task`:

| Field | Type | Description |
|-------|------|-------------|
| `current_note` | int8_t | Decoded MIDI note (-1 = none) |
| `breath_vel` | uint8_t | Breath velocity (0-127) |
| `breath_gate` | bool | Breath above note-on threshold |
| `bend_cents` | int16_t | Pitch bend in cents |
| `modulation` | uint8_t | Modulation CC1 (0-127) |
| `vibrato_rate` | float | Vibrato LFO rate (Hz) |
| `vibrato_depth` | float | Vibrato depth (cents) |
| `patch_idx` | int8_t | Current patch index (0-7) |
| `patch` | patch_t | Current patch settings |
| `battery_pct` | uint8_t | Battery percentage |
| `charging` | bool | USB charging active |
| `ble_connected` | bool | BLE MIDI connected |
| `usb_connected` | bool | USB MIDI connected |

---

## Patch Format (32 bytes)

| Offset | Field | Type | Range |
|--------|-------|------|-------|
| 0 | wavetable index | u8 | 0-7 |
| 1 | transpose | i8 | -24..+24 |
| 2 | breath curve exponent | u8 | 1-8 (÷4) |
| 3 | breath CC curve exponent | u8 | 1-8 |
| 4 | bore Q | u8 | 1-20 (÷10) |
| 5 | noise mix | u8 | 0-127 |
| 6 | bend range (semitones) | u8 | 0-12 |
| 7 | growl depth | u8 | 0-127 |
| 8 | tilt mod depth | u8 | 0-127 |
| 9 | vibrato rate | u8 | 0-20 (÷2) |
| 10 | vibrato depth (cents) | u8 | 0-100 |
| 11 | attack | u8 | 0-127 |
| 12 | decay | u8 | 0-127 |
| 13 | sustain | u8 | 0-127 |
| 14 | release | u8 | 0-127 |
| 15 | octave base | i8 | -3..+3 |
| 16-31 | name | char[16] | ASCII |