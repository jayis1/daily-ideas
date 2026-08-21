# Aero Cast — Calibration Guide

## Overview

The Aero Cast requires two types of calibration:

1. **Zero-wind calibration** — determines per-path timing offsets caused by transducer delay, circuit propagation, and mechanical asymmetry. Required for accurate wind measurement.
2. **Path length verification** — confirms the physical distance between transducer pairs matches the calibrated value.

## Zero-Wind Calibration

### When to calibrate

- First use after assembly
- After firmware update
- After mechanical reassembly
- If readings seem consistently biased
- Monthly for research-grade accuracy

### Procedure

1. **Find still air**: Place the device indoors in a closed room, away from:
   - HVAC vents and fans
   - Open windows or doors
   - People walking by (wait 5 minutes after placing)
   - Heaters or air conditioners
2. **Level the device**: Place on a flat surface. The sensor head should be vertical (transducers pointing up/down as designed). Use the bubble level on the enclosure or check with a smartphone level app.
3. **Enter calibration mode**: Press the MODE button until the OLED shows "CAL MODE".
4. **Start calibration**: Hold the AVG button for 3 seconds. The display shows "CALIBRATING..." and the status LED flashes.
5. **Wait**: The device collects 100 samples (5 seconds at 20 Hz). Keep the device absolutely still.
6. **Complete**: The display shows "CAL DONE" and the offset values are stored in flash.
7. **Verify**: Return to Wind mode. In still air, speed should read <0.1 m/s and direction should be stable.

### What it measures

For each path *i*, the firmware computes:

```
offset[i] = average(v_path[i]) over 100 samples
```

Where `v_path[i] = (L/2) × (1/t_forward - 1/t_reverse)`.

In still air, the true wind component along each path is zero, so any non-zero `v_path` is due to timing asymmetry. The offset is subtracted from all future measurements.

### Serial log output

```
[cal] zero-wind: collecting 100 samples...
[cal] path 0 offset = 0.0342 m/s
[cal] path 1 offset = -0.0156 m/s
[cal] path 2 offset = 0.0089 m/s
[cal] zero-wind calibration complete
```

## Path Length Verification

The nominal path length is 89.4mm (sqrt(40² + 80²) for the default tripod geometry). Manufacturing tolerances may cause the actual path length to differ by ±2mm.

### Procedure

1. **Enter calibration mode** and perform zero-wind calibration first.
2. **Use the Python script** to read raw TOF values:

```bash
python3 scripts/aero_stream.py --raw --device /dev/ttyACM0
```

3. **Check forward TOF**: In still air at ~20°C, the forward TOF should be:
   - t = L / c = 0.0894 / 343 = 260.6 µs
   - Acceptable range: 255–265 µs
4. **If TOF is off**: The actual path length can be computed as:
   - L_actual = c × t_forward = 343 × t_forward_us × 1e-6
   - Update the path length via BLE command:
   ```
   device.set_path_length(0, L_actual * 1000)  # mm
   ```
5. **Repeat for all 3 paths**.

## Field Verification

### Wind tunnel comparison (if available)

1. Place the Aero Cast in a wind tunnel at known speeds (1, 5, 10, 20 m/s).
2. Compare the device's reading to the tunnel reference.
3. At each speed, the difference should be <0.2 m/s (calibrated) or <0.5 m/s (uncalibrated).

### Natural wind comparison

1. Place the Aero Cast next to a reference anemometer (e.g., a Davis Vantage Pro).
2. Log both for 30 minutes in natural wind.
3. Compare:
   - Mean speed should agree within ±0.3 m/s
   - Mean direction should agree within ±5°
   - Correlation of 1-second averages should be >0.95

### Sonic temperature check

1. Compare the sonic temperature with a reference thermometer in still air.
2. The difference should be <1°C after humidity correction.
3. If offset is consistent, add a temperature offset in the firmware:
   ```c
   #define T_SONIC_OFFSET  0.5f  // °C, adjust per unit
   ```

## Geometry Matrix

The geometry matrix transforms path-projected wind components into the orthogonal (u, v, w) wind vector. It is computed from the physical transducer mounting angles:

```
Path 0: from (R, 0, 0) to (0, 0, H) → direction = (-R, 0, H) / L
Path 1: from (R·cos120°, R·sin120°, 0) to (0, 0, H) → direction = (-R·cos120°, -R·sin120°, H) / L
Path 2: from (R·cos240°, R·sin240°, 0) to (0, 0, H) → direction = (-R·cos240°, -R·sin240°, H) / L
```

If you modify the physical geometry (different standoff heights, ring radius), update `FRAME_RADIUS_MM` and `FRAME_HEIGHT_MM` in `sdkconfig.h` and recompile.

## Recalibration Schedule

| Use Case | Recalibrate |
|----------|-------------|
| Casual/outdoor sports | Every 6 months |
| Precision agriculture | Monthly |
| Scientific research | Before each campaign |
| After firmware update | Always |
| After mechanical change | Always |

## Calibration Storage

Calibration data is stored in the last flash sector of the RP2040:

| Address | Content |
|--------|---------|
| 0x101FF000 | Magic word (0xAEC57A11) |
| 0x101FF004 | Path 0 length (float, mm) |
| 0x101FF008 | Path 1 length (float, mm) |
| 0x101FF00C | Path 2 length (float, mm) |
| 0x101FF010 | Path 0 offset (float, m/s) |
| 0x101FF014 | Path 1 offset (float, m/s) |
| 0x101FF018 | Path 2 offset (float, m/s) |
| 0x101FF01C | CRC-32 |

If the magic word is not found (e.g., after flash erase), defaults are used and the device operates in uncalibrated mode.