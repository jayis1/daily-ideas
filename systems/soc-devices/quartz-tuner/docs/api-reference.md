# Quartz Tuner — API Reference

## BLE GATT Service: QuartzTuner

**Service UUID**: `0xQT01` (custom)
**Characteristics**:

| Characteristic | UUID | Properties | Description |
|---------------|------|-----------|-------------|
| SweepData | `0xQT02` | Notify | Live sweep data (frequency + real + imaginary per point) |
| Parameters | `0xQT03` | Read | Motional parameters (fₛ, R₁, C₁, L₁, C₀, Q, ESR) |
| Classification | `0xQT04` | Read | Crystal type classification (label + confidence) |
| Turnover | `0xQT05` | Read | Temperature turnover data (T₀, Tc, coefficients) |
| Command | `0xQT06` | Write | Control commands (start sweep, calibrate, etc.) |
| Status | `0xQT07` | Notify | Device status (idle, sweeping, calibrating, error) |

## Command Interface (Write to Command characteristic)

| Byte | Value | Meaning |
|------|-------|---------|
| 0x01 | — | Start frequency sweep |
| 0x02 | — | Start temperature sweep |
| 0x03 | — | Start Allan deviation measurement |
| 0x10 | — | Start OSLT calibration (short) |
| 0x11 | — | Continue OSLT calibration (open) |
| 0x12 | — | Continue OSLT calibration (load) |
| 0x13 | — | Continue OSLT calibration (through) |
| 0x20 | freq_hi, freq_mid, freq_lo | Set center frequency (24-bit, Hz) |
| 0x21 | span_hi, span_lo | Set span (16-bit, kHz) |
| 0x30 | — | Reset device |

## SweepData Notification Format

Each notification contains 12 bytes:

| Offset | Size | Field | Format |
|--------|------|-------|--------|
| 0 | 4 | Frequency | uint32, Hz |
| 4 | 2 | Real part | int16, ×10⁻⁶ S |
| 6 | 2 | Imaginary part | int16, ×10⁻⁶ S |
| 8 | 2 | Magnitude | uint16, ×10⁻⁶ S |
| 10 | 2 | Phase | int16, ×0.01° |

## Parameters Read Format

32 bytes:

| Offset | Size | Field | Format |
|--------|------|-------|--------|
| 0 | 4 | fₛ | float, Hz |
| 4 | 4 | R₁ | float, Ω |
| 8 | 4 | C₁ | float, F |
| 12 | 4 | L₁ | float, H |
| 16 | 4 | C₀ | float, F |
| 20 | 4 | Q | float |
| 24 | 4 | ESR | float, Ω |
| 28 | 4 | Pullability | float, ppm/pF |

## USB-CDC Serial Protocol

The USB-CDC interface provides a text-based command protocol:

| Command | Response | Description |
|---------|----------|-------------|
| `SWEEP` | JSON sweep data | Run a frequency sweep |
| `MEASURE` | JSON parameters | Run sweep + extract parameters |
| `TEMP` | JSON turnover data | Run temperature sweep |
| `ALLAN` | JSON Allan data | Run Allan deviation measurement |
| `CAL SHORT` | `OK` | Start OSLT short calibration |
| `CAL OPEN` | `OK` | Open calibration |
| `CAL LOAD` | `OK` | Load calibration |
| `CAL THROUGH` | `OK` | Through calibration |
| `FREQ <Hz>` | `OK` | Set center frequency |
| `SPAN <Hz>` | `OK` | Set sweep span |
| `STATUS` | JSON status | Get device state |
| `LIST` | JSON file list | List saved measurements on SD |
| `GET <id>` | JSON measurement | Retrieve saved measurement |

## SD Card File Format

Each measurement is saved as `XTAL_NNNNNN.JSON`:

```json
{
  "id": 42,
  "f_center_hz": 10000000.0,
  "timestamp_ms": 87451234567,
  "f_s": 10000125.3,
  "R1": 22.3,
  "C1": 2.01e-14,
  "L1": 1.258e-2,
  "C0": 5.2e-12,
  "Q": 35500,
  "ESR": 23.1,
  "class": "AT-cut",
  "confidence": 0.97,
  "T0": 38.2,
  "Tc": -0.00004,
  "sweep_points": 512,
  "data": [[9999000, 1.234e-5, -2.345e-6], ...]
}
```