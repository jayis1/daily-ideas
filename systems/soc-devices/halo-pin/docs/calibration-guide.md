# Halo Pin — Calibration Guide

## Overview

The Halo Pin requires two calibrations:

1. **PSL Sphere Calibration** — maps photodiode pulse height to
   particle size using NIST-traceable polystyrene latex (PSL) spheres
   of known diameters.
2. **Zero-Air Test** — verifies the baseline noise floor using
   filtered (HEPA) air, ensuring no false counts.

## PSL Sphere Calibration

### Materials

- PSL sphere standards (NIST-traceable), e.g.:
  - 0.5 µm (Thermo Fisher 4009A)
  - 1.0 µm (Thermo Fisher 4010A)
  - 2.0 µm (Thermo Fisher 4202A)
  - 5.0 µm (Thermo Fisher 4250A)
- Nebulizer / atomizer (for generating PSL aerosol)
- HEPA-filtered air supply (for dilution)

### Procedure

1. Connect the Halo Pin to the companion app (`scripts/psl_calibrate.py`).
2. Run the script: `python3 psl_calibrate.py --device MAC --sizes 0.5,1.0,2.0,5.0`
3. The script sends `CALIB` to enter calibration mode.
4. For each PSL size:
   a. Nebulize the PSL suspension into the inlet.
   b. The device samples for 60 s, collecting pulse heights.
   c. The script records the median peak height.
5. The script performs log-log linear regression:
   `peak_mV = A * d^B`
6. The fitted A and B parameters are used to compute the 16 bin
   boundaries (in mV) from the bin-edge diameters (in µm).
7. The new boundaries are sent to the device via `BINS:` command.
8. The device stores the calibration in flash (NVS).

### Expected Results

| PSL Size (µm) | Expected Peak (mV) | Notes |
|---------------|-------------------|-------|
| 0.5 | ~30–50 | Near Rayleigh regime |
| 1.0 | ~80–120 | Transition regime |
| 2.0 | ~200–300 | Geometric regime |
| 5.0 | ~800–1200 | Geometric regime |

The power-law exponent B should be approximately 2.0–2.5 (Mie theory
predicts V ∝ d² for the geometric scattering regime). Significant
deviation from B ≈ 2 may indicate:
- Misaligned optics (check optical cell)
- Laser power drift (check monitor PD)
- Photodiode saturation at large sizes (reduce laser power)

### Recalibration Frequency

- **Every 6 months** in normal use.
- **After any optical cell disassembly** or laser diode replacement.
- **When changing to a different lot of PSL standards** (lot-to-lot
  variation can be ±5%).

## Zero-Air Test

### Purpose

Verify that the device reports zero counts when sampling perfectly
clean (HEPA-filtered) air. Any counts indicate:
- Optical cell contamination (dust on the photodiode window)
- Electronic noise (ground loop, ADC noise)
- Light leakage into the optical cell

### Procedure

1. Attach a HEPA filter (included) to the inlet.
2. Press MODE → select "ZERO" → press SELECT.
3. The device runs for 60 s with HEPA-filtered air.
4. The total count should be < 10 particles in 60 s at 1 L/min
   (i.e., < 10/60 L = 0.17 #/L).
5. If counts are higher:
   a. Clean the optical cell with compressed air.
   b. Check the photodiode window for dust.
   c. Verify the cell cover is seated (reed switch).
   d. Check for stray light (operate in a shaded area).

### Acceptance Criteria

| Metric | Pass | Fail |
|--------|------|------|
| Zero counts (60 s) | < 10 | ≥ 10 |
| Baseline noise σ | < 10 mV | ≥ 10 mV |
| Flow stability | ±5% of target | > 5% deviation |

## Flow Rate Verification

The SDP810 differential pressure sensor provides flow feedback, but
its calibration depends on the flow restrictor geometry. To verify:

1. Connect a reference flow meter (e.g., Sensirion SFM3200) at the
   exhaust.
2. Run the device. The reported flow (F: in BLE status) should
   match the reference within ±5%.
3. If not, adjust `FLOW_CALIB_K` in `airflow.c` and reflash.

## Density Configuration

The default particle density is 1.65 g/cm³ (typical atmospheric
aerosol). For specific applications:

| Aerosol Type | Density (g/cm³) | Command |
|-------------|-----------------|---------|
| Atmospheric | 1.65 | `DENS:1.65` (default) |
| Dust (mineral) | 2.65 | `DENS:2.65` |
| Sea salt | 2.20 | `DENS:2.20` |
| Soot/BC | 1.80 | `DENS:1.80` |
| PSL spheres | 1.05 | `DENS:1.05` |
| Pollen | 0.90 | `DENS:0.90` |