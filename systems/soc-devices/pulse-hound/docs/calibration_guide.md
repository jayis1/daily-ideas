# Pulse Hound — AD8318 RSSI Calibration Guide

## Why Calibration Is Needed

The AD8318's output voltage-to-power transfer function varies slightly between individual chips and over temperature. While the datasheet provides typical values (slope = −19 mV/dB, intercept = 1.80 V at 25 °C), calibrating against a known signal source improves accuracy from ±3 dB (uncalibrated) to ±1 dB.

## Equipment Required

- **Calibrated signal generator** (e.g., HackRF, ADALM-Pluto, or any signal generator with known output power)
- **50 Ω SMA terminator** (for noise-floor measurement)
- **Attenuator** (20–30 dB, if your signal generator output is > +5 dBm — the AD8318 max input)
- USB-C cable for connecting to the Pulse Hound
- Computer with Python 3 + `pyserial` installed

## Procedure

### Step 1: Noise-Floor Baseline

1. Disconnect the antenna; attach the 50 Ω SMA terminator
2. Power on the Pulse Hound, connect via USB-C
3. Run the calibration script:

```bash
python3 scripts/calibration.py --port /dev/ttyACM0 --noise-floor
```

The script reads RSSI for 10 seconds (no signal) and records the average as the noise-floor reference. Typical value: −75 to −80 dBm.

### Step 2: Known-Signal Calibration

1. Connect your signal generator to the SMA connector (through an attenuator if needed)
2. Set the generator: frequency = 2400 MHz (2.4 GHz, the AD8318's most accurate band), power = −30 dBm, CW (no modulation)
3. Run:

```bash
python3 scripts/calibration.py --port /dev/ttyACM0 --calibrate --freq 2400 --power -30
```

The script reads the AD8318 VOUT, computes the actual slope and intercept, and stores them in NVS:

```
[Calibration] Signal: 2400 MHz @ -30 dBm
[Calibration] VOUT measured: 2.372 V
[Calibration] TEMP: 24.8 °C
[Calibration] Computed slope: -19.2 mV/dB (was -19.0)
[Calibration] Computed intercept: 1.796 V (was 1.80)
[Calibration] Storing to NVS... OK
```

### Step 3: Multi-Point Calibration (Optional, for Higher Accuracy)

For the best accuracy, calibrate at multiple power levels:

```bash
python3 scripts/calibration.py --port /dev/ttyACM0 --multipoint \
  --points "-60,-50,-40,-30,-20,-10"
```

The script sweeps the signal generator through each power level, records VOUT, and performs a linear regression to find the best-fit slope and intercept.

```
[Calibration] Multi-point fit:
  -60 dBm → 2.94 V
  -50 dBm → 2.75 V
  -40 dBm → 2.56 V
  -30 dBm → 2.37 V
  -20 dBm → 2.18 V
  -10 dBm → 1.99 V
[Calibration] Linear fit: slope=-19.1 mV/dB, intercept=1.795 V
[Calibration] R² = 0.9998 (excellent)
[Calibration] Storing to NVS... OK
```

### Step 4: Temperature Compensation Verification

Place the Pulse Hound in a temperature-controlled environment (or just let it warm up to steady state):

```bash
python3 scripts/calibration.py --port /dev/ttyACM0 --temp-sweep
```

The script reads RSSI at a fixed signal level while varying the temperature (or just monitoring over time as the device warms up). It computes the temperature coefficient and stores it.

### Step 5: Verification

1. Set the signal generator to a different power level (e.g., −25 dBm)
2. Read the Pulse Hound display — it should show −25 dBm ± 1 dB
3. Repeat at a few frequencies (900 MHz, 2400 MHz, 5500 MHz) — the AD8318 is relatively flat across frequency, but there may be ±1–2 dB variation

## Typical AD8318 Parameters

| Parameter | Typical | Range |
|-----------|---------|-------|
| Slope | −19 mV/dB | −18 to −20 mV/dB |
| Intercept (25 °C) | 1.80 V | 1.75–1.85 V |
| Temp coefficient | −2.2 mV/°C | −1.8 to −2.6 mV/°C |
| Noise floor | −78 dBm | −75 to −82 dBm |
| Linearity error | ±1 dB | ±0.5 to ±2 dB |

## Storage

Calibration values are stored in ESP32 NVS (non-volatile storage):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cal_slope` | float | −19.0 | mV per dB |
| `cal_intercept` | float | 1.80 | V at 0 dBm extrapolation |
| `cal_temp_coeff` | float | −2.2 | mV per °C |
| `cal_noise_floor` | float | −78.0 | dBm, no-signal baseline |

## When to Recalibrate

- After replacing the AD8318
- After a firmware update that changes the ADC configuration
- Annually (the AD8318 is stable, but the reference resistors can drift)
- If RSSI readings seem consistently off by > 2 dB

## Safety

⚠️ **Never apply more than +10 dBm (10 mW) to the AD8318 input.** Higher power can damage the detector. If testing near a transmitter, always use an attenuator.