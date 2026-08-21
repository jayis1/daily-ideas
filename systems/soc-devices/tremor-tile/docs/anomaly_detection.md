# Tremor Tile — Anomaly Detection Algorithm

## Overview

The Tremor Tile uses a **statistical baseline learning + multi-feature deviation detection** approach to identify structural vibration anomalies. This is not a machine learning model — it's a lightweight, deterministic algorithm that runs entirely on the RP2040's dual ARM Cortex-M0+ cores.

## Baseline Learning

### Phase 1: Calibration (24 hours default)

During the first 24 hours of operation (or after a baseline reset), the device learns the **normal vibration signature** of its mounting location.

For each spectral feature, the baseline stores:
- **Mean** (μ) — average value
- **Standard deviation** (σ) — variation range
- **Min/Max** — observed extremes

Features tracked:

| Feature | Description | Unit |
|---------|-------------|------|
| Peak frequencies (×5) | Dominant frequencies | Hz |
| Peak amplitudes (×5) | Magnitude at each peak | g/√Hz |
| Band energies (×5) | Integrated PSD in each band | g²·Hz |
| RMS vibration | Overall root-mean-square | g |
| Crest factor | Peak-to-RMS ratio | dimensionless |
| Kurtosis | 4th moment normalized | dimensionless |

### Phase 2: Monitoring

After the baseline is established, each new FFT window is evaluated against the baseline statistics.

## Anomaly Detection Rules

An anomaly is flagged when **any** of these conditions is met:

### Rule 1: New Spectral Peak

A peak appears in the spectrum that was not present in the baseline:
- **New peak**: frequency more than 5 Hz from any baseline peak
- **Threshold**: amplitude > 6σ above the baseline noise floor
- **Severity**: `min(10, peak_sigma / 2)`

**Interpretation**: A new vibration frequency means something changed — a new resonant mode, a bearing defect, a loose bolt, etc.

### Rule 2: Peak Frequency Shift

An existing baseline peak has shifted frequency:
- **Threshold**: shift > 20% of baseline peak frequency
- **Severity**: `min(10, shift_fraction * 20)`

**Interpretation**: Frequency shifts indicate changes in structural stiffness or mass distribution — cracks, delamination, or foundation settlement.

### Rule 3: Band Energy Exceedance

The energy in a frequency band exceeds the baseline:
- **Threshold**: band energy > 5σ above baseline mean
- **Severity**: `min(10, band_sigma / 2)`

**Interpretation**: Increased energy in a specific band can indicate bearing wear, imbalance, or resonance excitation.

### Rule 4: RMS Increase

Overall vibration RMS exceeds baseline:
- **Threshold**: RMS > 4σ above baseline mean
- **Severity**: `min(10, rms_sigma / 2)`

**Interpretation**: General increase in vibration level — multiple simultaneous problems or overall degradation.

### Rule 5: Kurtosis Increase

The kurtosis of the vibration signal exceeds baseline:
- **Threshold**: kurtosis > 3σ above baseline mean
- **Severity**: `min(10, kurt_sigma / 2)`

**Interpretation**: High kurtosis indicates **impulsive** events — impacts, bearing defects (ball/pass frequency), or gear mesh issues.

## Alert Generation

When an anomaly is detected:

1. An `alert_t` structure is created with:
   - `type`: Which rule triggered (NEW_PEAK, PEAK_SHIFT, etc.)
   - `severity`: 1-10 scale
   - `affected_bands`: Bitmask of which frequency bands are affected
   - `timestamp`: Unix time from DS3231 RTC

2. The alert is queued for LoRa transmission
   - **Normal alerts**: Sent at SF7 (normal power, fast)
   - **High-severity alerts** (severity ≥ 8): Sent at SF12 (max range, slower)

3. The buzzer sounds an alert pattern
4. The status LED changes to red
5. The alert is logged to flash memory

## Threshold Adjustment

| Setting | Default | Range | Use Case |
|---------|---------|-------|----------|
| Anomaly threshold (σ) | 5.0 | 1.0 – 20.0 | Higher = fewer false alarms, lower = more sensitive |
| Peak shift (%) | 20% | 5% – 50% | Smaller = detect smaller shifts, more alerts |
| New peak (σ) | 6.0 | 3.0 – 15.0 | Higher = require stronger new peaks |
| Kurtosis (σ) | 3.0 | 1.0 – 10.0 | Lower = detect more impulsive events |

### Recommended Thresholds by Application

| Application | σ Threshold | Notes |
|-------------|-------------|-------|
| Bridge monitoring | 7.0 | Low false alarm rate, detect major changes |
| Industrial machinery | 5.0 | Balanced, detect bearing wear early |
| Building seismic | 3.0 | Sensitive, catch micro-seismic events |
| Wind turbine | 4.0 | Moderate sensitivity, handle variable loads |
| Heritage structure | 6.0 | Conservative, avoid false alarms on old buildings |

## Baseline Reset

The baseline should be reset when:
1. **Moving the device** to a new location (baseline is location-specific)
2. **Major structural changes** (renovation, retrofit, repair)
3. **Seasonal recalibration** (every 6-12 months recommended)
4. **After a confirmed anomaly** that changes the normal signature

To reset: send `CMD_RESET_BASELINE` (0x04) over USB, or send a LoRa downlink command.

## Performance Characteristics

| Metric | Value |
|--------|-------|
| FFT computation time | ~8ms (1024-point, RP2040 @ 133MHz) |
| Feature extraction time | ~2ms |
| Anomaly evaluation time | ~0.5ms |
| Total per-window latency | ~11ms |
| Maximum throughput | ~90 windows/second |
| Typical throughput | ~0.78 windows/second (50% overlap at 400Hz) |
| RAM usage (baseline) | ~2KB |
| Flash usage (baseline) | ~1KB |
| Flash usage (code) | ~60KB |

## Limitations

1. **Not a neural network** — the algorithm uses statistical thresholds, not learned patterns. It can't detect subtle, multi-feature correlations that an ML model could.

2. **Baseline-dependent** — anomalies are only detected relative to the learned baseline. If the baseline was learned during abnormal conditions, the device won't detect the actual anomaly.

3. **Single-axis analysis** — the default configuration analyzes the Z-axis (vertical). X and Y axes can be selected via USB command, but simultaneous 3-axis analysis is not supported in the current firmware.

4. **No frequency-domain correlation** — the algorithm doesn't correlate changes across multiple frequency bands simultaneously. Each band is evaluated independently.

5. **Fixed learning period** — the baseline doesn't adapt to gradual, slow changes (drift). A periodic manual reset is recommended.