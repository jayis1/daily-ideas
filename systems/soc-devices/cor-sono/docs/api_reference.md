# Cor Sono — API Reference

## BLE GATT Interface

### Service: Cor Sono (UUID 0x9201)

| Characteristic | UUID | Type | Description |
|---------------|------|------|-------------|
| Audio Stream | 0x9202 | Notify | 20 ms audio frames (80 samples × 2 ch × int16 = 320 bytes) |
| Classification Result | 0x9203 | Notify | `{class_id_u8, confidence_u8, hr_u16_le}` (4 bytes) |
| Command | 0x9204 | Write | `{cmd_u8, [param_u8]}` |
| Device Info | 0x9205 | Read | `{fw_version_str, mode_u8, battery_u8}` |

### Commands (0x9204)

| Cmd | Param | Action |
|-----|-------|--------|
| 0x01 | — | Start/stop recording (toggle) |
| 0x02 | — | Cycle mode (heart → lung → mixed → heart) |
| 0x03 | volume (0–30) | Set speaker volume in dB |
| 0x04 | mode (0–2) | Set mode directly |
| 0x05 | — | Get current status (responds on 0x9203) |

---

## Wi-Fi HTTP API

### Endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/` | HTML dashboard (live waveform + results) |
| GET | `/rec` | Toggle recording |
| GET | `/mode` | Cycle mode |
| GET | `/wav` | Download latest WAV recording |
| GET | `/csv` | Download latest CSV classification log |
| WS | `/ws` | WebSocket: JSON `{hr, cls, conf}` updates every 1 s |

### WebSocket JSON format
```json
{
  "hr": 72,
  "cls": "Normal",
  "conf": 92
}
```

---

## Classification Classes

| ID | Name | Description |
|----|------|-------------|
| 0 | Normal | Clean S1/S2, no murmur |
| 1 | S3 gallop | Protodiastolic gallop (volume overload, CHF) |
| 2 | S4 gallop | Presystolic gallop (stiff ventricle, HTN) |
| 3 | Systolic murmur | Between S1–S2 (AS, MR, VSD) |
| 4 | Diastolic murmur | Between S2–S1 (AR, MS) |
| 5 | Crackles | Discontinuous lung sounds (pneumonia, CHF, fibrosis) |
| 6 | Wheeze | Continuous musical lung sounds (asthma, COPD) |
| 7 | Pleural rub | Pleural friction rub (pleuritis) |

### Confidence threshold
- Results are only reported when confidence ≥ 60%
- Below threshold: "indeterminate" (no class reported)
- Adjustable via BLE command 0x03 (param = threshold)

---

## SD Card File Formats

### WAV file (`CS_YYYYMMDD_HHMMSS.wav`)
- Format: PCM, 16-bit, stereo
- Sample rate: 4000 Hz
- Channel 0: contact microphone (body sounds, post-ANC)
- Channel 1: ambient microphone (reference, pre-ANC)

### CSV file (`CS_YYYYMMDD_HHMMSS.csv`)
```csv
# Cor Sono classification log
# Date: 2026-08-03T10:15:30Z
# Mode: heart
# Columns: t_s, class_id, class_name, confidence
0.50,0,Normal,92
1.00,0,Normal,89
1.50,3,Systolic_murmur,71
...
# Summary: HR=72, final_class=Normal
# END
```

---

## Measurement Modes

| Mode | Bandwidth | CNN classes | Use case |
|------|-----------|-------------|----------|
| HEART (0) | 20–1000 Hz | Normal, S3, S4, Sys murmur, Dia murmur, Rub | Cardiac exam |
| LUNG (1) | 100–2000 Hz | Normal, Crackles, Wheeze, Rub | Pulmonary exam |
| MIXED (2) | 20–2000 Hz | All 8 classes | General screening |

---

## Firmware Architecture

### Dual-core task distribution
- **Core 0**: `audio_task` — I²S MEMS + ADC piezo acquisition at 4 kHz, writes to ring buffer
- **Core 1**: `pcg_task` — ANC, bandpass, envelope, HR computation, CNN inference, OLED, BLE, SD

### Memory layout
- **Flash**: 8 MB (3 MB app + 64 KB model + 4 KB NVS)
- **PSRAM**: 2 MB (CNN weights + audio ring buffers)
- **SRAM**: 512 KB (TFLite arena + stack)

### Key data flows
```
audio_task → ring_buffer → pcg_task
                            ├→ ANC (LMS filter)
                            ├→ Bandpass (biquad)
                            ├→ Envelope (Hilbert)
                            ├→ Autocorrelation → HR
                            ├→ Mel-spectrogram → CNN → class
                            ├→ OLED display
                            ├→ SD logger (WAV + CSV)
                            └→ BLE + Wi-Fi stream
```