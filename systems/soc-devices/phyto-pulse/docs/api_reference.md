# API Reference — Phyto Pulse

## BLE GATT Service

### Service UUID: `0x180C`

| Characteristic | UUID | Properties | Description |
|---------------|------|------------|-------------|
| Waveform | `0xFF01` | Notify | Live voltage samples (6 bytes: 4B timestamp + 2B mV×100) |
| Event | `0xFF02` | Notify | Spike event notifications (JSON) |
| Status | `0xFF03` | Read, Notify | Device status (JSON) |
| Command | `0xFF04` | Write | Commands to device (JSON) |

### Waveform Packet Format (0xFF01)

```
Byte 0-3: timestamp_ms (uint32, little-endian)
Byte 4-5: voltage (int16, little-endian, mV × 100, so 0x0064 = 1.00 mV)
```

### Event JSON (0xFF02)

```json
{
  "t": "e",
  "ts": 1234600,
  "c": "AP",
  "a": 45.2,
  "d": 23,
  "conf": 0.91
}
```

| Field | Type | Description |
|-------|------|-------------|
| t | string | "e" (event) |
| ts | uint32 | Timestamp (ms since session start) |
| c | string | Class: "AP", "VP", or "ART" |
| a | float | Amplitude (mV) |
| d | float | Duration (ms) |
| conf | float | CNN confidence (0-1) |

### Status JSON (0xFF03)

```json
{
  "t": "stat",
  "bat": 3.72,
  "g": 101,
  "st": "REC"
}
```

### Commands (0xFF04)

Write JSON to the Command characteristic:

| Command | JSON | Description |
|---------|------|-------------|
| Start recording | `{"cmd":"start"}` | Begin acquisition |
| Stop recording | `{"cmd":"stop"}` | Stop and save |
| Trigger stimulus | `{"cmd":"stim"}` | Fire stimulus probe |
| Set gain | `{"cmd":"gain","g":101}` | Set INA333 gain (2/11/101/1001) |
| Set sensitivity | `{"cmd":"sens","k":5.0}` | Set detection threshold k |
| Start experiment | `{"cmd":"exp","id":0}` | Start guided experiment |
| Set mode | `{"cmd":"mode","m":"wave"}` | Set display mode |

---

## Wi-Fi WebSocket API

### Connection

1. Connect to Wi-Fi AP: `PhytoPulse-XXXX` (open network)
2. Open WebSocket: `ws://192.168.4.1/ws`

### Messages (server → client)

**Live sample (60 Hz):**
```json
{"type":"sample","t":1234567,"v":0.0234,"gain":11}
```

**Event:**
```json
{"type":"event","t":1234600,"class":"AP","amp":45.2,"dur":23,"conf":0.91}
```

**Slow-wave update (every 60 s):**
```json
{"type":"swp","t":1234623,"mean":12.3,"pp":8.1}
```

**Status:**
```json
{"type":"stat","bat":3.72,"gain":101,"state":"REC"}
```

### Messages (client → server)

```json
{"cmd":"start"}
{"cmd":"stop"}
{"cmd":"stim"}
{"cmd":"gain","g":101}
{"cmd":"exp","id":0}
```

---

## SD Card File Formats

### Raw Data: `RAW_xxxx.BIN`

Binary file with 16-byte header followed by sample records:

**Header (16 bytes):**
| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Magic: "PHYT" |
| 4 | 2 | Version (1) |
| 6 | 2 | Sample rate (1000 Hz) |
| 8 | 2 | INA gain × 100 |
| 10 | 1 | PGA setting |
| 11 | 1 | Reserved |
| 12 | 4 | Start timestamp (HAL tick) |

**Sample record (6 bytes each, 1000/s):**
| Offset | Size | Field |
|--------|------|-------|
| 0 | 2 | Voltage (int16, mV × 100) |
| 2 | 4 | Timestamp (uint32, ms) |

File size: ~11 MB/hour.

### Events: `EVENTS_xxxx.CSV`

CSV with header row:
```csv
timestamp_ms,sample_idx,amp_mV,duration_ms,area_mVms,rise_ms,decay_tau_ms,asymmetry,class,confidence
1234600,12346,45.2,23.0,520.5,8.5,15.2,0.358,AP,0.91
1235800,13580,-12.3,3200.0,-8500.0,120.0,2100.0,0.054,VP,0.88
```

Slow-wave results appear as comment lines:
```
# SWP,1234623,12.3,8.1,0.5
```

---

## Python Helper Scripts

### `scripts/read_results.py`
Reads SD card session files (RAW + CSV) and plots the waveform + events.

### `scripts/train_cnn.py`
Trains the int8 1D-CNN spike classifier on labeled event data and exports weights as a C header file.

### `scripts/live_stream.py`
Connects to the Wi-Fi WebSocket and plots live waveform + events in real time.

### `scripts/calibrate.py`
Calibration helper for electrode offset and noise floor measurement.