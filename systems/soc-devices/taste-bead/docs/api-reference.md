# Taste Bead — API Reference

## Communication Interfaces

### 1. BLE (ESP32-S3 native)

The ESP32-S3 exposes a BLE GATT server with these characteristics:

| UUID (short) | Name | Direction | Description |
|------|------|-----------|-------------|
| `0xF001` | Result | Notify → Phone | Classification result packets |
| `0xF002` | Spectrum | Notify → Phone | Raw impedance spectra (chunked) |
| `0xF003` | Command | Phone → Write | Configuration and trigger commands |
| `0xF004` | Library | Read + Notify → Phone | Library entries (list/manage) |
| `0xF005` | Status | Notify → Phone | Status messages and errors |

**Service UUID**: `0xF00D`

### 2. BLE Command Protocol

Write to characteristic `0xF003` with the following format:

```
[opcode:1] [data:N]
```

| Opcode | Name | Data | Description |
|--------|------|------|-------------|
| `0x01` | IDENTIFY | (none) | Trigger an identification sweep |
| `0x02` | LEARN | label[32] | Capture a new reference with the given label |
| `0x03` | DELETE | index[1] | Delete library entry at index |
| `0x04` | LIST_LIBRARY | (none) | Send all library entries via `0xF004` notify |
| `0x05` | CALIBRATE | step[1] | Run calibration step: 0=open, 1=short, 2=KCl |
| `0x06` | MONITOR_START | (none) | Start continuous monitoring (10s interval) |
| `0x07` | MONITOR_STOP | (none) | Stop continuous monitoring |
| `0x08` | SET_MODE | mode[1] | Set UI mode (0-6) |
| `0x09` | GET_STATUS | (none) | Request current status |

### 3. Result Packet Format (0xF001 → Notify)

```
[type:1=0x01] [label:32] [confidence:4 float] [distance:4 float] [timestamp:8 int64]
```
Total: 50 bytes per result notification.

### 4. Spectrum Packet Format (0xF002 → Notify)

Each measurement produces 100 spectrum points (5 electrodes × 20 freqs).
Each point is sent as a separate notification:

```
[type:1=0x02] [seq:1] [electrode:1] [freq_index:1] [z_mag:4 float] [z_phase:4 float]
```
Total: 12 bytes per spectrum point notification. 100 notifications per sweep.

### 5. Wi-Fi (optional)

When connected to Wi-Fi (configured via BLE), the ESP32-S3 can serve data via:

- **TCP socket** on port 8000: raw CSV stream (same format as SD card log)
- **HTTP** on port 80: JSON status endpoint at `/status`, POST `/learn` to add references
- **WebSocket** on port 8080: real-time measurement results

### 6. USB Serial (debug)

USB-CDC serial at 115200 baud provides debug log output.

## Data Formats

### SD Card CSV Format

```
timestamp_us,label,confidence,liquid_temp_c,f0,f1,...,f47,
Z_mag_e0_f0,Z_phase_e0_f0,Z_mag_e0_f1,Z_phase_e0_f1,...,
Z_mag_e4_f19,Z_phase_e4_f19
```

Each measurement row contains:
- 4 header fields (timestamp, label, confidence, liquid_temp)
- 48 feature values
- 200 impedance values (5 electrodes × 20 freqs × mag+phase)

Total: 252 columns per row.

### Feature Vector (48 features)

| Index | Feature | Description |
|-------|---------|-------------|
| 0-6 | Electrode 0 (Au) | log10(R_s), log10(R_ct), log10(C_dl), log10(σ_w), log10(f_peak), log10(Z_100Hz), z_ratio |
| 7-13 | Electrode 1 (Pt) | Same 7 features |
| 14-20 | Electrode 2 (Ag/AgCl) | Same 7 features |
| 21-27 | Electrode 3 (GC) | Same 7 features |
| 28-34 | Electrode 4 (Cu) | Same 7 features |
| 35-43 | Cross-electrode ratios | Au/Cu, Pt/GC, Ag/Au at 3 key frequencies |
| 44-47 | Phase differences | Phase diff between adjacent electrodes at 100 Hz |