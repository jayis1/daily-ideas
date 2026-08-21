# Volt Scribe — API Reference

## Serial/BLE Protocol

Volt Scribe communicates via UART (115200, 8N1) to the ESP32-C3, which relays over BLE. The same command set works over USB CDC serial.

### Command Format

All commands are ASCII, newline-terminated:
```
<command> [arguments]\r\n
```

Responses are also ASCII:
```
<response>\r\n
```

### Commands

#### `mode <technique>`

Select the electrochemical technique.

| Technique | Description |
|-----------|-------------|
| `cv` | Cyclic Voltammetry |
| `dpv` | Differential Pulse Voltammetry |
| `swv` | Square-Wave Voltammetry |
| `eis` | Electrochemical Impedance Spectroscopy |
| `amperometric` | Amperometric i-t |
| `galvanostatic` | Galvanostatic (constant current) |

Example:
```
VS> mode cv
Mode set to cv
```

#### `set <parameter> <value>`

Set an experiment parameter.

| Parameter | Technique | Unit | Default | Range |
|-----------|-----------|------|---------|-------|
| `potential_start` | CV | V | -0.2 | ±2.048 |
| `potential_vertex` | CV | V | 0.8 | ±2.048 |
| `potential_end` | CV | V | -0.2 | ±2.048 |
| `scan_rate` | CV | V/s | 0.05 | 0.001–100 |
| `cycles` | CV | count | 3 | 1–100 |
| `dpv_start` | DPV | V | 0.0 | ±2.048 |
| `dpv_end` | DPV | V | 0.6 | ±2.048 |
| `dpv_step` | DPV | V | 0.004 | 0.001–0.1 |
| `dpv_pulse_amp` | DPV | V | 0.050 | 0.001–0.5 |
| `dpv_pulse_width` | DPV | s | 0.050 | 0.01–1.0 |
| `dpv_scan_rate` | DPV | V/s | 0.010 | 0.001–10 |
| `swv_start` | SWV | V | 0.0 | ±2.048 |
| `swv_end` | SWV | V | 0.6 | ±2.048 |
| `swv_step` | SWV | V | 0.004 | 0.001–0.1 |
| `swv_amplitude` | SWV | V | 0.025 | 0.001–0.5 |
| `swv_frequency` | SWV | Hz | 25 | 1–1000 |
| `eis_dc_bias` | EIS | V | 0.0 | ±2.048 |
| `eis_ac_amplitude` | EIS | V rms | 0.010 | 0.001–0.100 |
| `eis_freq_start` | EIS | Hz | 1 | 1–100000 |
| `eis_freq_end` | EIS | Hz | 100000 | 1–100000 |
| `eis_ppd` | EIS | count | 10 | 3–50 |
| `potential` | Amperometric | V | 0.45 | ±2.048 |
| `duration` | Amperometric | s | 60 | 0.1–3600 |
| `sample_rate` | Amperometric | Hz | 10 | 0.1–1000 |
| `ir_compensation` | All | Ω | 0 | 0–10000 |

#### `run`

Start the experiment with current settings. Data streams to SD card and BLE.

#### `stop`

Abort the running experiment.

#### `auto`

Auto-range the TIA. The device applies a small test voltage and selects the most sensitive range that doesn't saturate.

#### `status`

Display current settings and TIA range.

#### `help`

Show available commands.

## BLE Streaming Protocol

Binary protocol over UART to ESP32-C3, relayed via BLE UART service.

### Frame Format

```
[0xAA] [0x55] [type] [len] [data...] [crc8]
```

| Field | Size | Description |
|-------|------|-------------|
| Header | 2 | 0xAA 0xAA55 |
| Type | 1 | Packet type identifier |
| Length | 1 | Data payload length |
| Data | len | Payload bytes |
| CRC8 | 1 | CRC-8 of data field |

### Packet Types

| Type | Name | Data | Description |
|------|------|------|-------------|
| 0x01 | Data Point | float E (4) + float I (4) | Single (E, I) measurement |
| 0x02 | EIS Point | float Z_real (4) + float Z_imag (4) + float freq (4) | Impedance at frequency |
| 0x03 | Status | uint8 mode_state (1) | Device status change |
| 0x04 | Peak Report | float E (4) + float I (4) + uint8 type (1) | Detected peak |
| 0x05 | Randles Fit | float R_s (4) + float R_ct (4) + float C_dl (4) + float alpha (4) | Circuit fit result |
| 0x06 | Experiment Start | uint8 technique (1) + uint32 n_points (4) | Beginning of experiment |
| 0x07 | Experiment End | uint8 status (1) | Experiment complete |

### CRC-8 Algorithm

Polynomial: 0x07 (CRC-8-CCITT)

```python
def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc
```

## SD Card File Format

All files are CSV with a `.csv` extension, stored on a FAT32 microSD card.

### CV File Format: `cv_NNNNNN.csv`

```
E_V,I_A,segment,cycle
# Peak 1: E=0.312V, i=4.70uA (anodic)
# Peak 2: E=0.248V, i=-4.20uA (cathodic)
# ΔE_p = 64 mV (quasi-reversible)
-0.200000,-0.000001
-0.199000,-0.000001
...
0.800000,0.000005
...
```

### EIS File Format: `eis_NNNNNN.csv`

```
freq_Hz,Z_real_Ohm,Z_imag_Ohm,|Z|_Ohm,phase_deg
# R_s=127, R_ct=2340, C_dl=18.70uF, alpha=0.91, sigma_w=0.0
1.0,2470.00,-1560.00,2920.00,-32.3
1.3,2350.00,-1480.00,2780.00,-32.1
...
100000.0,127.00,-5.20,127.10,-2.3
```

### DPV File Format: `dpv_NNNNNN.csv`

```
E_V,dI_A,i_base_A,i_pulse_A
0.000000,0.000001,0.000001,0.000002
0.004000,0.000002,0.000001,0.000003
...
```

### Amperometric File Format: `it_NNNNNN.csv`

```
time_s,I_A,E_V
0.0000,0.000001,0.450000
0.1000,0.000002,0.450000
...
```

## Calibration Constants

Stored in STM32G4 flash (option bytes area):

| Constant | Offset | Size | Description |
|----------|--------|------|-------------|
| DAC_OFFSET | 0x00 | 4 | DAC zero-offset correction (float) |
| DAC_GAIN | 0x04 | 4 | DAC gain correction factor (float) |
| ADC_OFFSET | 0x08 | 4 | ADC zero-offset correction (float) |
| ADC_GAIN | 0x0C | 4 | ADC gain correction factor (float) |
| TIA_CAL[7] | 0x10 | 28 | Per-range calibration factors (7×float) |
| VREF_ACTUAL | 0x2C | 4 | Actual REF3030 voltage (float) |

## Companion App Protocol

The ESP32-C3 runs a BLE UART service (Nordic UART Protocol compatible) with:
- **Service UUID**: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- **TX Characteristic**: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (notifications)
- **RX Characteristic**: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (write)

The companion app (iOS/Android) receives binary frames and renders:
- Real-time voltammograms (CV, DPV, SWV)
- Nyquist and Bode plots (EIS)
- i-t curves (amperometric)
- Peak detection overlays
- Randles circuit fit results