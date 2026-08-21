# Calibration Guide — Thermo Trace Pocket DSC

Calibration is essential for accurate temperature and enthalpy
measurements. Thermo Trace supports two-point calibration using
reference standards.

## Why Calibrate?

The raw temperature reading from the PT1000 RTD has small errors from:
- RTD tolerance (class A: ±0.15°C at 0°C, ±0.35°C at 100°C)
- Lead wire resistance (mitigated by 4-wire measurement)
- ADS122U04 offset and gain errors
- Thermal gradients between heater and RTD

The raw heat flow reading has errors from:
- Heater resistance tolerance (±10%)
- Supply voltage measurement error
- PID duty cycle quantization
- Thermal asymmetry between sample and reference cells

Calibration corrects these systematic errors.

## Reference Standards

| Standard | Tm (°C) | ΔHf (J/g) | Purpose |
|----------|---------|-----------|---------|
| Indium | 156.6 | 28.71 | Primary calibration |
| Tin | 231.9 | 60.22 | High-temperature verification |
| Gallium | 29.8 | 80.1 | Low-temperature verification (optional) |
| Water (ice) | 0.0 | 334 | Sub-ambient verification (optional) |

## One-Point Calibration (Indium)

### Procedure

1. **Prepare the indium sample**
   - Weigh 3-5 mg of indium metal (99.999% purity)
   - Place in an aluminum DSC pan
   - Crimp the pan with a standard DSC crimper

2. **Load the sample**
   - Open the DSC cell lid
   - Place the indium pan on the sample cell (heater 1)
   - Place an empty aluminum pan on the reference cell (heater 2)
   - Close the lid

3. **Run the calibration scan**
   - Press button A to start
   - Set mass: 5 mg (use buttons B/C to adjust)
   - Set ramp: 5 °C/min
   - Press A to begin the scan
   - Wait for the scan to complete (~55 min)

4. **Analyze the results**
   - The indium melting peak should appear near 156.6°C
   - Run the calibration script:
     ```bash
     python scripts/calibrate.py --indium
     ```
   - The script connects via BLE, retrieves the scan data, detects
     the indium peak, and computes correction coefficients:
     - `T_corrected = a × T_measured + b`
     - `Φ_corrected = c × Φ_measured + d`

5. **Apply the correction**
   - The script sends the coefficients to the device via BLE
   - The device stores them in flash (NVS)
   - Future scans use the corrected values

### Expected Results

- Measured Tm should be within ±2°C of 156.6°C before calibration
- After calibration, Tm should be within ±0.5°C
- Measured ΔHf should be within ±10% of 28.71 J/g before calibration
- After calibration, ΔHf should be within ±3%

## Two-Point Calibration (Indium + Tin)

For improved accuracy across the full temperature range:

1. Run the indium calibration as above
2. Repeat with a tin sample (3-5 mg, Tm = 231.9°C, ΔHf = 60.22 J/g)
3. Run:
   ```bash
   python scripts/calibrate.py --indium --tin
   ```
4. The script fits a linear correction across both points:
   - Temperature: linear fit through both Tm points
   - Heat flow: linear fit through both ΔHf points

### Expected Results (Two-Point)

- Tm accuracy: ±0.3°C across the full range (RT to 300°C)
- ΔHf accuracy: ±2% across the full range

## Verification

After calibration, verify with a known sample:

1. **Paraffin wax** (Tm = 58°C, ΔHf = 210 J/g)
   - Run a scan from RT to 100°C at 5°C/min
   - Verify the melting peak is at 58 ± 1°C

2. **Polyethylene (LDPE)** (Tm = 110°C, ΔHf = 110 J/g)
   - Run a scan from RT to 150°C at 5°C/min
   - Verify the melting peak is at 110 ± 2°C

3. **Aspirin** (Tm = 135°C, ΔHf = 150 J/g)
   - Run a scan from RT to 180°C at 5°C/min
   - Verify the melting peak is at 135 ± 2°C

## Recalibration

- Recalibrate every 6 months, or after replacing the DSC cell
- Recalibrate if the device is dropped or exposed to mechanical shock
- The calibration coefficients are stored in flash and persist across
  power cycles

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|---------|
| No indium peak detected | Sample not loaded | Check pan placement, ensure sample is on heater 1 |
| Tm off by >5°C | RTD wiring issue | Check 4-wire connections, verify IDAC current |
| ΔHf off by >20% | Heater resistance wrong | Measure actual R_heater, update `HEATER_R_OHM` in config |
| Baseline drift | Thermal asymmetry | Ensure both cells have identical empty pans |
| Noisy heat flow | PID instability | Tune PID gains, reduce ramp rate |
| Peak split | Sample decomposition | Check pan is sealed (crimped) |