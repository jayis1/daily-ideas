# Flux Ring — Calibration Guide

## Overview

The Flux Ring uses the MMC5983MA AMR magnetometer, which requires calibration to compensate for:

1. **Hard-iron distortion** — permanent magnetic fields from nearby ferrous components (USB-C shell, motor core, PCB traces). This appears as a constant offset on all readings.
2. **Soft-iron distortion** — ferrous materials near the sensor that distort the Earth's field. This appears as stretching/compression of the measured sphere into an ellipsoid.
3. **Sensor offset** — internal AMR bridge offset. The MMC5983MA's on-chip SET/RESET function handles most of this automatically.

## Automatic Calibration (On-Device)

On first boot, the Flux Ring enters calibration mode:

1. The OLED displays "CALIBRATE rotate..."
2. Rotate the ring in a **figure-8 pattern** for 10 seconds
3. Try to cover all orientations (flip it, rotate it, tilt it)
4. The OLED shows "CAL OK!" when done
5. Calibration parameters are stored in flash

### Figure-8 Technique

The figure-8 rotation pattern ensures the sensor visits all points on the magnetic sphere. Here's how to do it:

1. Hold your hand with the ring flat (palm down)
2. Rotate your wrist in a circle (like stirring a pot)
3. Flip your hand over (palm up)
4. Rotate in a circle again
5. Tilt your hand left, right, forward, back
6. Repeat for 10 seconds

The goal is to expose the sensor to all possible orientations relative to the ambient magnetic field.

## Calibration via Python Script

For more control, use the `calibrate.py` script:

```bash
python3 scripts/calibrate.py --mac AA:BB:CC:DD:EE:FF --duration 15
```

This collects raw samples and computes:
- Hard-iron offset (midpoint of min/max per axis)
- Soft-iron scale (normalizes axis ranges)

The output includes a `calibration_params.txt` file with the computed values.

## Manual Calibration

If you need to manually set calibration values:

1. Read the current calibration from the device
2. Place the ring in 6 known orientations (±X, ±Y, ±Z aligned with Earth's field)
3. Record the reading for each orientation
4. Compute offset: `offset_x = (max_x + min_x) / 2`
5. Compute scale: `scale_x = avg_delta / (max_x - min_x)`

## SET/RESET Operation

The MMC5983MA's SET/RESET function:

- **SET**: Applies a strong magnetic pulse that aligns all magnetic domains in the sensor in one direction
- **RESET**: Applies a reverse pulse that flips all domains

By taking readings after both SET and RESET, the offset cancels out:

```
B_actual = (B_after_SET + B_after_RESET) / 2
```

The firmware performs SET/RESET every 10 seconds automatically. This eliminates most drift without user intervention.

## When to Recalibrate

Recalibrate if:

- The compass heading seems off by more than 10°
- You've attached the ring to a metal watch band or case
- The ring has been dropped or mechanically shocked
- You're using the ring in a significantly different geographic location (different Earth field angle)
- Readings seem "stuck" or don't respond to magnet proximity

## Calibration Quality Check

After calibration, verify by:

1. In compass mode, slowly rotate the ring 360°
2. The heading should sweep smoothly from 0° to 360°
3. Plot X vs Y — it should form a circle centered at (0,0)
4. Any significant offset or elliptical distortion indicates poor calibration

## Advanced: Ellipsoid Fitting

For the best possible calibration (especially with soft-iron distortion), use the ellipsoid fitting method:

1. Collect 500+ samples in various orientations
2. Fit an ellipsoid to the 3D point cloud
3. Decompose into rotation matrix + scale matrix
4. Apply inverse transform to all readings

This is implemented in `scripts/calibrate.py` as an optional `--advanced` flag.

```bash
python3 scripts/calibrate.py --mac AA:BB:CC:DD:EE:FF --advanced
```

## Calibration Persistence

Calibration parameters are stored in the nRF52840's flash memory (NVS partition). They persist across:

- Power cycles
- Firmware updates (unless you erase flash)
- Battery replacement

To force a recalibration, double-tap + hold for 5 seconds, or send the BLE command via the Mode characteristic.

---

*See also: [API Reference](api_reference.md) | [Assembly Guide](assembly_guide.md)*