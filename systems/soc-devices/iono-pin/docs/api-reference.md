# Iono Pin — API Reference

## Firmware modules (STM32G474)

### `ims.c` — drift-time DSP
| Function | Description |
|---|---|
| `void ims_init(void)` | Initialize the DSP accumulator. |
| `void ims_reset_avg(void)` | Clear the rolling average (call before each sample). |
| `void ims_accumulate(const int16_t *raw)` | Add one 140-sample sweep to the average. |
| `bool ims_result_ready(void)` | True once ≥ 8 sweeps are accumulated. |
| `void ims_compute(float p_kpa, float t_drift, float t_amb, ims_result_t *out)` | Detect peaks, compute K₀, fill the result struct. |
| `uint8_t ims_detect_peaks(...)` | Low-level peak detection on a raw spectrum. |
| `static inline float ims_k0(...)` | Reduced-mobility formula (header). |

### `library.c` — 45-compound K₀ library + k-NN
| Function | Description |
|---|---|
| `void library_classify(const ims_peak_t *peaks, uint8_t n, classify_result_t *out)` | k-NN (k=5) classification over detected peaks. |

`g_library[LIB_SIZE]` holds the 45 compounds. `classify_result_t` contains `name`, `cls` (CLASS_EXPLOSIVE/DRUG/CWA/TIC/VOC/REFERENCE/NONE), `k0`, `confidence` (0..1).

### `hv_supply.c` — EMCO F50CT 5 kV control
| Function | Description |
|---|---|
| `void hv_enable(bool on)` | Enable/disable the HV supply (interlocked). |
| `void hv_set_drift_v(float v)` | Servo to a target drift voltage (0–5000 V). |
| `float hv_read_drift_v(void)` | Read back actual drift voltage via the monitor divider. |
| `void hv_emergency_shutdown(void)` | Immediate HV off. |
| `bool hv_fault(void)` | True if TLV3201 over-current fault latched. |

### `shutter.c` — Bradbury-Nielsen shutter
| Function | Description |
|---|---|
| `void shutter_set_rep_rate_hz(uint32_t hz)` | Set repetition rate (5–60 Hz). |
| `void shutter_arm(bool on)` | Start/stop periodic shutter pulsing. |
| `void shutter_trigger_pulse(void)` | Manual single 200 µs pulse (calibration). |

### `electrometer.c` — ADA4530-1 TIA + ADC1 40 ksps
| Function | Description |
|---|---|
| `void electromer_capture(int16_t *out, uint16_t n)` | Blocking capture of one sweep. |
| `bool electrometer_sweep_ready(void)` | Non-blocking check (DMA complete). |
| `void electrometer_get(int16_t *out, uint16_t n)` | Retrieve the latest DMA buffer. |

### `bme280.c` / `ds18b20.c` / `pump.c` / `display.c` / `sd_log.c` / `ble_bridge.c` / `safety.c` / `buttons.c`
See the header files in [`firmware/main/`](../firmware/main/) for signatures.

## BLE GATT interface (ESP32-C3 bridge)

| UUID | Type | Description |
|---|---|---|
| `0x18A0` | Service | Iono Pin IMS service |
| `0x2BE0` | Characteristic (Notify) | Live spectrum + verdict frames |

### Frame format (UART + BLE)
```
[0xAA][0x55][type][len_hi][len_lo][payload...][crc16_lo][crc16_hi]
```
- `type 0x01` — spectrum + verdict: `[P f32][T_drift f32][T_amb f32][n_peaks u8][K0 f32 × n][amp i16 × n][name_len u8][name][class u8][conf f32][spec_hi u8 × 140]`
- `type 0x02` — status: ASCII text
- `type 0x03` — fault: ASCII text

## Wi-Fi HTTP endpoints

| Endpoint | Method | Returns |
|---|---|---|
| `/status` | GET | JSON: `{"name":"iono-pin","status":"OK","vbat":3.9}` |
| `/log.csv` | GET | Current session CSV (download) |
| `/ota` | POST | Firmware OTA (multipart) |

## Python helper scripts

| Script | Purpose |
|---|---|
| [`scripts/live_stream.py`](../scripts/live_stream.py) | Connect over BLE, plot live mobility spectrum + verdict. |
| [`scripts/analyze_log.py`](../scripts/analyze_log.py) | Parse a session CSV, plot spectra, export K₀ reports. |
| [`scripts/calibrate.py`](../scripts/calibrate.py) | Collect a blank (RIP) calibration, adjust the library K₀ offset. |