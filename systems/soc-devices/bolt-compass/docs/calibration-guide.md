# Bolt Compass — Calibration Guide

The Bolt Compass has three calibration steps: **loop balance**, **bearing
alignment**, and **distance model fit**. All are done once, at first
deployment, and stored in NVS.

## 1. Loop balance

The two VLF loops must have **identical gain** for the `atan2` bearing
to be accurate. A gain mismatch `δ` introduces a bearing error of
`~δ/2` radians at the cardinal points.

### Procedure

1. Feed a **known 10 kHz sine** (from a signal generator or the
   `scripts/sferic_gen.py --plot` output played through a small coil)
   into both loops simultaneously from a single transmit coil placed
   ~1 m away, oriented to couple equally into both.
2. Read the peak amplitudes `peak_ns` and `peak_ew` from the BLE/Wi-Fi
   debug endpoint (`/events.json?raw=1`).
3. They should match within 5 %. If not, adjust the **software gain
   trim** (stored in NVS key `loop_gain_ns` / `loop_gain_ew`):
   ```
   loop_gain_ew = peak_ns / peak_ew
   ```
4. Re-verify.

## 2. Bearing alignment

The N-S loop must be aligned to true north.

### Procedure

1. Using a compass (correct for local magnetic declination), orient the
   N-S loop plane to true north.
2. Wait for a stroke with a known location (from lightningmaps.org).
3. Compare the device's bearing to the true bearing (computed from the
   device's GPS position and the stroke's lat/lon).
4. If there is a constant offset, store it in NVS key `bearing_offset_deg`.
5. Repeat for 5–10 strokes; the offset should converge.

## 3. Distance model fit

The distance estimation depends on `ref_field_uv` — the peak E-field
that a "standard" CG stroke produces at 100 km. This varies with local
ground conductivity, ionosphere conditions, and the loop effective
height.

### Procedure

1. Record 50+ strokes during an active storm (via `--replay` or live
   BLE), noting the device's estimated distance for each.
2. Download the same strokes from the **Blitzortung** public feed
   (`lightningmaps.org` → JSON export) to get ground-truth distances.
3. Run the calibration script:
   ```bash
   python3 scripts/storm_view.py --replay SFERIC_20260626.csv \
       --calibrate --blitzortung
   ```
4. The script fits `ref_field_uv` to minimize the RMS distance error
   across all paired strokes.
5. Store the result in NVS key `ref_field_uv` (default: 1000 µV/m).

### Day vs. night

The Earth-ionosphere waveguide attenuation changes dramatically across
the day/night terminator. The firmware auto-selects day/night from the
GPS hour. For best accuracy, calibrate separately for day and night
storms and store both values (NVS keys `ref_field_uv_day`,
`ref_field_uv_night`).

### Ground conductivity

Select the ground-conductivity region matching your deployment site:

| Region | σ_g | Setting |
|--------|-----|---------|
| Ocean / seawater | 4 S/m | `GROUND_OCEAN` |
| Wet soil / coastal | 30 mS/m | `GROUND_WET` |
| Continental average | 10 mS/m | `GROUND_AVG` (default) |
| Dry soil / desert | 3 mS/m | `GROUND_DRY` |
| Ice shield / glacier | 1 mS/m | `GROUND_ICE` |

Set via the Wi-Fi config page or NVS key `ground_type`.

## 4. Verification

After calibration, over a full storm (50+ strokes):

| Metric | Target |
|--------|--------|
| Bearing RMS error | < 5° |
| Distance RMS error | < 20 % (30–200 km) |
| CG/IC classification accuracy | > 90 % |
| False alarm rate | < 1 / min (quiet conditions) |
| Detection efficiency (vs Blitzortung) | > 80 % within 100 km |