# Echo Mote — API Reference

## Serial Console (USB-C, 115200 baud, 8N1)

### Measurement Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `measure rt60` | — | Start RT60 measurement (8 s) |
| `measure freq` | — | Start frequency response measurement (8 s) |
| `measure modes` | — | Start room mode scan (25 s) |
| `measure clarity` | — | Start clarity C50/C80 measurement (8 s) |
| `measure noise` | — | Start background NC measurement (30 s) |

### Calibration Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `cal spm <dB>` | dB: measured SPL at 1m from speaker | Calibrate speaker output level |
| `cal mic` | — | Start microphone sensitivity matching calibration |

### Wi-Fi Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `wifi start <ssid> <pass>` | SSID, password | Connect to Wi-Fi and start HTTP server |
| `wifi stop` | — | Disconnect Wi-Fi and stop server |

### System Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `status` | — | Show device status, battery, mode |
| `results` | — | Print last measurement results |
| `sleep` | — | Enter deep sleep (press POWER to wake) |
| `ble start` | — | Start BLE advertising |
| `ble stop` | — | Stop BLE advertising |

---

## BLE GATT Service (0xFFB0)

### Service: EchoMote (0xFFB0)

| Characteristic | UUID | Properties | Type | Description |
|---------------|------|-----------|------|-------------|
| Measurement Command | 0xFFB1 | Write | uint8 | 1=RT60, 2=FREQ, 3=MODES, 4=CLARITY, 5=NOISE |
| RT60 Results | 0xFFB2 | Read/Notify | 24 bytes | 6× float32 T60 values (125–4k Hz octaves) |
| Freq Response | 0xFFB3 | Read | 240 bytes | 60× float32, 1/3-octave magnitude |
| Room Modes | 0xFFB4 | Read/Notify | 32 bytes | 8× {freq_u16, decay_u16, type_u8} |
| Clarity | 0xFFB5 | Read/Notify | 28 bytes | 6× C50 int8 + 6× C80 int8 (dB) |
| NC Curve | 0xFFB6 | Read | 32 bytes | 16× uint8 dB SPL per 1/3-octave |
| Device Status | 0xFFB7 | Read/Notify | uint8 | 0=idle, 1=measuring, 2=streaming, 3=error |
| Battery Level | 0xFFB8 | Read | uint8 | Battery percentage (0–100) |

### BLE Advertising Packet (31 bytes)

| Field | Bytes | Value |
|-------|-------|-------|
| Flags | 3 | 0x02, 0x01, 0x06 |
| Complete 16-bit UUID | 4 | 0x03, 0x03, 0xB0, 0xFF |
| Manufacturer-specific | 5 | 0x04, 0xFF, 0x00, status, battery% |

### Room Modes Data Format (0xFFB4)

Each mode is 4 bytes:

| Byte | Field | Scale |
|------|-------|-------|
| 0–1 | Frequency | uint16, 1 Hz resolution |
| 2 | Decay time | (uint16 >> 4) × 0.01 s |
| 3 | Type + decay | (lower nibble: type) + (upper nibble: decay MSB) |

Type values: 0 = axial, 1 = tangential, 2 = oblique

---

## Wi-Fi HTTP REST API

### GET /api/status

Returns device status as JSON:

```json
{
  "device": "EchoMote",
  "status": "idle",
  "mode": 0,
  "has_results": true
}
```

### POST /api/measure

Trigger a measurement:

```json
{
  "mode": "rt60"
}
```

Valid modes: `rt60`, `freq`, `modes`, `clarity`, `noise`

Response:
```json
{
  "status": "measuring"
}
```

### GET /api/results

Returns last measurement results as JSON:

```json
{
  "mode": 0,
  "speed_of_sound": 344.5,
  "temperature": 23.1,
  "humidity": 45.0,
  "rt60": [0.82, 0.71, 0.63, 0.58, 0.49, 0.38],
  "c50": [2.1, 3.5, 4.2, 5.1, 6.8, 8.2],
  "c80": [5.3, 6.1, 7.0, 8.4, 9.5, 10.1],
  "room_modes": [
    {"freq": 42.5, "decay": 1.2, "type": 0},
    {"freq": 68.0, "decay": 0.8, "type": 1}
  ],
  "nc_rating": 30.0
}
```

### GET /api/impulse_resp

Returns the raw impulse response as binary data:

- Format: 4 s × 48000 Hz × 2 channels × 16-bit = 768,000 bytes
- Layout: interleaved L/R samples (int16 little-endian)

### GET /api/waterfall

Returns frequency response data at 1/24-octave resolution:

```json
{
  "frequencies": [20.0, 21.2, 22.5, ...],
  "magnitudes": [-45.2, -44.8, -43.1, ...]
}
```

---

## Acoustic Parameter Definitions

### RT60 (Reverberation Time)

The time for sound to decay by 60 dB after the excitation signal stops. Measured using Schroeder backward integration from the impulse response.

- **T20**: Decay from -5 dB to -25 dB, extrapolated to -60 dB
- **T30**: Decay from -5 dB to -35 dB, extrapolated to -60 dB
- **T60**: The full 60 dB decay (usually extrapolated from T20/T30)

### C50 (Early-to-Late Energy Ratio, 50 ms)

```
C50 = 10 × log10(E(0-50ms) / E(50ms-∞))  [dB]
```

- C50 > 0 dB: Good speech intelligibility
- C50 < -5 dB: Poor speech intelligibility

### C80 (Clarity, 80 ms)

```
C80 = 10 × log10(E(0-80ms) / E(80ms-∞))  [dB]
```

- C80 > 0 dB: Good music clarity
- Used primarily for concert hall assessment

### D50 (Definition)

```
D50 = E(0-50ms) / E(total)   [ratio, 0-1]
```

- D50 > 0.5: Good speech intelligibility

### NC Rating (Noise Criteria)

The NC rating is the lowest NC contour (NC-15 to NC-65) that the measured background noise spectrum does not exceed at any octave band.

Typical targets:
- Recording studio: NC-15 to NC-20
- Conference room: NC-25 to NC-30
- Open office: NC-35 to NC-40

### IACC (Inter-Aural Cross-Correlation)

Cross-correlation between left and right microphone impulse responses. Higher IACC indicates a more lateral sound field.

---

*Echo Mote API Reference — SoC Device Inventions*