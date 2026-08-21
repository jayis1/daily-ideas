# Aero Cast — API Reference

## Communication Interfaces

### 1. BLE (via ESP32-C3)

The ESP32-C3 exposes a BLE GATT server with these characteristics:

| UUID | Name | Direction | Description |
|------|------|-----------|-------------|
| `0000aero-0000-1000-8000-00805f9b34fb` | Wind Data | Notify → Phone | 20 Hz wind data packets |
| `0000aer1-0000-1000-8000-00805f9b34fb` | Command | Phone → Write | Configuration commands |
| `0000aer2-0000-1000-8000-00805f9b34fb` | Status | Notify → Phone | Status messages, turbulence stats |
| `0000aer3-0000-1000-8000-00805f9b34fb` | Raw TOF | Notify → Phone | Raw time-of-flight data (calibration) |

### 2. UART Binary Protocol (RP2040 ↔ ESP32-C3)

The RP2040 communicates with the ESP32-C3 over UART at 1 Mbps using a binary packet protocol:

```
[0xAA] [type:1] [len_lo:1] [len_hi:1] [payload:N] [crc8:1]
```

| Type | Name | Direction | Payload |
|------|------|-----------|---------|
| 0x01 | Wind Data | RP2040→ESP | 40 bytes (see below) |
| 0x02 | Status | RP2040→ESP | Variable string |
| 0x03 | Command | ESP→RP2040 | 1 byte cmd + args |
| 0x04 | Ack | RP2040→ESP | Echo of command |
| 0x05 | Raw TOF | RP2040→ESP | 28 bytes (3 paths × 2 × float + timestamp) |

### 3. Wi-Fi (via ESP32-C3)

When connected to Wi-Fi, the ESP32-C3 can serve data via:
- **TCP socket** on port 8000: raw CSV stream at 20 Hz
- **HTTP** on port 80: JSON status endpoint at `/status`
- **WebSocket** on port 8080: real-time wind data

### 4. USB Serial (RP2040 debug)

USB CDC serial at 115200 baud provides debug output and can accept text commands.

---

## Wind Data Packet (0x01)

40-byte payload:

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | timestamp | uint32 | Microsecond timestamp (low 32 bits) |
| 4 | 4 | speed | float | Horizontal wind speed (m/s) |
| 8 | 4 | direction | float | Wind direction (degrees, meteorological: FROM) |
| 12 | 4 | u | float | East-west component (m/s) |
| 16 | 4 | v | float | North-south component (m/s) |
| 20 | 4 | w | float | Vertical component (m/s) |
| 24 | 4 | t_sonic | float | Sonic temperature (K) |
| 28 | 4 | bme_temp | float | BME280 temperature (°C) |
| 32 | 4 | bme_press | float | BME280 pressure (Pa) |
| 36 | 4 | bme_rh | float | BME280 relative humidity (%) |

All float values are IEEE 754 single-precision, little-endian.

---

## Turbulence Stats Packet (0x02)

48-byte payload:

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | u_mean | float | Mean u (m/s) |
| 4 | 4 | v_mean | float | Mean v (m/s) |
| 8 | 4 | w_mean | float | Mean w (m/s) |
| 12 | 4 | sigma_u | float | Std dev of u (m/s) |
| 16 | 4 | sigma_v | float | Std dev of v (m/s) |
| 20 | 4 | sigma_w | float | Std dev of w (m/s) |
| 24 | 4 | u_w_cov | float | ⟨u'w'⟩ covariance (m²/s²) |
| 28 | 4 | v_w_cov | float | ⟨v'w'⟩ covariance (m²/s²) |
| 32 | 4 | tke | float | Turbulent kinetic energy (m²/s²) |
| 36 | 4 | u_star | float | Friction velocity (m/s) |
| 40 | 4 | turb_intensity | float | Turbulence intensity (σ_u/ū) |
| 44 | 4 | elapsed_s | uint32 | Averaging window elapsed (seconds) |

---

## Raw TOF Packet (0x05)

28-byte payload (for calibration and debugging):

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | path0_fwd_us | float | Path 0 forward TOF (µs) |
| 4 | 4 | path0_rev_us | float | Path 0 reverse TOF (µs) |
| 8 | 4 | path1_fwd_us | float | Path 1 forward TOF (µs) |
| 12 | 4 | path1_rev_us | float | Path 1 reverse TOF (µs) |
| 16 | 4 | path2_fwd_us | float | Path 2 forward TOF (µs) |
| 20 | 4 | path2_rev_us | float | Path 2 reverse TOF (µs) |
| 24 | 4 | timestamp | uint32 | Microsecond timestamp |

---

## Commands (Phone → Device)

Commands are sent via the Command characteristic (write) or UART type 0x03:

| Cmd | Name | Args | Description |
|-----|------|------|-------------|
| 0x01 | Set Mode | [mode:1] | Set operating mode (0=Wind, 1=Gust, 2=Flux, 3=Profile, 4=Calib, 5=Stream) |
| 0x02 | Start Calibration | none | Begin zero-wind calibration |
| 0x03 | Set Sample Rate | [rate_hz:1] | Set measurement rate (1–20 Hz) |
| 0x04 | Set Averaging | [window_s:4] | Set averaging window in seconds |
| 0x05 | Set Threshold | [dac:2] | Set comparator threshold (0–4095) |
| 0x06 | Reset Gust | none | Reset gust peak tracker |
| 0x07 | Get Battery | none | Request battery voltage (replied via status) |
| 0x08 | Start SD Log | [filename:16] | Start logging to SD with filename |
| 0x09 | Stop SD Log | none | Stop SD logging and close file |
| 0x0A | Set Path Length | [path:1] [length_mm:4] | Override calibrated path length |
| 0x0B | Save Calibration | none | Save current calibration to flash |
| 0x0C | Reset Device | none | Soft reset RP2040 |

---

## SD Card Log Format

CSV files are written to the SD card with this format:

### Wind data log (main CSV)

```csv
timestamp_us,speed,direction,u,v,w,t_sonic,bme_temp,bme_press,bme_rh,path0_fwd,path0_rev,path1_fwd,path1_rev,path2_fwd,path2_rev
1234567,3.45,270.0,3.41,0.12,0.03,295.15,22.3,101325.0,45.2,291.2,291.8,290.9,292.1,291.5,292.0
...
```

### Turbulence log (appended rows)

```csv
TURB,timestamp,u_mean,v_mean,w_mean,sigma_u,sigma_v,sigma_w,u_w_cov,v_w_cov,tke,u_star,elapsed_s
TURB,1234567,1.23,0.45,0.02,0.34,0.28,0.12,-0.05,0.01,0.21,0.22,60
...
```

---

## Wi-Fi Endpoints

### GET /status

Returns JSON with current status:

```json
{
  "device": "aero-cast",
  "version": "1.0",
  "mode": "wind",
  "sample_rate_hz": 20,
  "averaging_s": 1,
  "battery_v": 3.72,
  "charging": false,
  "sd_logging": true,
  "sd_file": "aero_1234.csv",
  "sd_records": 12345,
  "ble_connected": true,
  "uptime_s": 3600,
  "wind": {
    "speed": 3.45,
    "direction": 270.0,
    "u": 3.41,
    "v": 0.12,
    "w": 0.03
  },
  "atmospheric": {
    "temperature": 22.3,
    "pressure": 1013.25,
    "humidity": 45.2,
    "sonic_temp": 22.1
  }
}
```

### TCP port 8000

Raw CSV stream (same format as SD log), one line per sample at 20 Hz.

### WebSocket port 8080

JSON messages at 20 Hz:

```json
{
  "t": 1234567,
  "spd": 3.45,
  "dir": 270.0,
  "u": 3.41,
  "v": 0.12,
  "w": 0.03,
  "ts": 295.15
}
```

---

## Python API

```python
from aero_stream import AeroCast

# Connect via BLE
device = AeroCast.connect_ble("aero-cast")

# Or connect via Wi-Fi TCP
device = AeroCast.connect_tcp("192.168.1.100", 8000)

# Read 20 Hz wind data
for sample in device.stream():
    print(f"Speed: {sample.speed:.2f} m/s, Dir: {sample.direction:.0f}°, W: {sample.w:.2f}")

# Read turbulence stats (emitted every averaging window)
for stats in device.turbulence_stream():
    print(f"TKE: {stats.tke:.3f}, u*: {stats.u_star:.3f}")

# Send commands
device.set_mode("flux")
device.set_sample_rate(10)
device.set_averaging(300)  # 5 minutes
device.start_calibration()
device.reset_gust()
```

See [scripts/aero_stream.py](../scripts/aero_stream.py) for the full implementation.