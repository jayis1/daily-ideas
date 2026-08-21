# Sap Watch — Calibration Guide

## Overview

The Sap Watch requires two calibration steps for accurate sap-flow measurement:

1. **Zero-flow calibration** — corrects for imperfect probe installation and natural thermal gradients. Run at predawn when transpiration is zero.
2. **Wound factor determination** — corrects for the disruption of xylem flow around the drilled probe holes. Species-dependent, set once.

## 1. Zero-Flow Calibration

### When to run
- **Automatically**: The firmware attempts zero-flow calibration every night at 04:00 local time (configurable via `ZERO_CAL_PREDAWN_HOUR`). It collects predawn measurements over multiple nights and averages them.
- **Manually**: Send a downlink command (port 3, command 3) or use the serial provisioning menu (option 4).

### Principle
At zero sap flow (predawn, when stomata are closed and there is no transpiration), the heat pulse should spread symmetrically — the upstream and downstream thermistors should see identical temperature rises. Any difference is due to:
- Asymmetric probe spacing (installation error)
- Natural thermal gradients in the trunk (sun heating one side)
- Thermistor mismatch

The firmware measures the heat-pulse velocity at zero flow and stores it as an offset (`zero_flow_offset`), subtracted from all subsequent readings.

### Procedure (manual)
1. Wait until 2–4 hours before dawn (e.g., 02:00–04:00 in summer)
2. Ensure the tree has not been watered or rained on in the last 12 hours
3. Send the zero-cal command via downlink: `03 03 0000` (port 3, command 3, value ignored)
4. The firmware will collect measurements over the next hour and compute the offset
5. Check the next uplink: `probe_health` bit 4 should be 1 (zero_cal_valid)
6. Repeat weekly (firmware auto-invalidates after 7 days if not refreshed)

### Validation
- The zero-flow offset should be small: |V_h| < 0.005 cm/s
- If the offset is large (>0.02 cm/s), the probe may be poorly installed — check needle spacing and depth
- Negative offsets (V_h < 0) suggest reverse thermal gradient (heat rising from soil) — normal at night

## 2. Wound Factor Determination

### Background
When you drill holes for the probe needles, the xylem around each hole is damaged (crushed vessels, filled with air). This "wound zone" (typically 0.5–1.0 mm radius) slows heat conduction, causing the measured heat-pulse velocity to underestimate the true sap flux. The wound correction factor (`F_wound`) compensates for this.

The wound factor depends on:
- **Probe diameter**: 1.2 mm needles create ~0.8 mm wound zones
- **Species**: softwoods (pine, spruce) have larger wound zones than hardwoods (oak, maple)
- **Wood moisture content**: drier wood heals less, larger wound effect

### Default values by species

| Species group | Wound factor | Notes |
|---------------|-------------|-------|
| Oak (Quercus) | 1.35 | Default; moderate wound effect |
| Maple (Acer) | 1.30 | Similar to oak |
| Pine (Pinus) | 1.55 | Softwood, larger wound zone |
| Spruce (Picea) | 1.60 | Similar to pine |
| Eucalyptus | 1.25 | Hard, dense wood, small wound |
| Apple / cherry | 1.35 | Typical fruit tree |
| Vine (Vitis) | 1.20 | Very small diameter, minimal wound |
| Citrus | 1.30 | Moderate |
| Birch (Betula) | 1.40 | Diffuse-porous, moderate wound |
| Douglas fir | 1.50 | Softwood |

### Setting the wound factor
Send a downlink: `03 04 0087` (port 3, command 4, value 135 → 1.35)

Or via serial menu (option 3): enter 1.35.

### Empirical determination (advanced)
For research-grade accuracy, you can measure the wound factor empirically:
1. Cut a stem section with the probe installed
2. Measure actual sap flow gravimetrically (weigh water uptake)
3. Compare to the Sap Watch's reading (with wound_factor = 1.0)
4. `wound_factor = actual_flow / measured_flow`
5. Set via downlink

This is typically only done for published research. For operational use, the species default is sufficient (±10% accuracy).

## 3. Sapwood Area Measurement

The Sap Watch converts sap-flux velocity (cm/h) to whole-tree water use (L/h) using the sapwood area. This must be measured once per tree and set via downlink.

### Method 1: Increment core (most accurate)
1. Use a Pressler increment borer (5 mm) to core the tree at breast height
2. Identify the sapwood (lighter color, active xylem) vs. heartwood (darker, inactive)
3. Measure sapwood depth (mm) from the bark to the sapwood/heartwood boundary
4. `A_sapwood = π × (R_outer² - R_heartwood²)` where R is the radius (cm)
5. For a 30 cm DBH oak with 20 mm sapwood: R = 15 cm, R_h = 13 cm
   `A = π × (15² - 13²) = π × 56 ≈ 180 cm²`

### Method 2: Species-specific allometry (faster)
Use published allometric equations. For many species:
```
A_sapwood = a × DBH^b
```
where `a` and `b` are species-specific coefficients. Example (from literature):
- Oak: A = 0.53 × DBH^1.65 (DBH in cm, A in cm²)
- Pine: A = 0.91 × DBH^1.48
- Maple: A = 0.42 × DBH^1.73

### Setting sapwood area
Send a downlink: `03 02 00B4` (port 3, command 2, value 180 → 180 cm²)

## 4. Sapwood Thermal Properties (Advanced)

The default thermal properties (k_xylem, ρ_sapwood, c_sapwood) are suitable for most trees. For highest accuracy in research applications, these can be measured from an increment core:

- **k_xylem**: measured with a thermal needle probe (thermal diffusivity meter)
- **ρ_sapwood**: measure fresh weight and volume of the core, divide
- **c_sapwood**: estimated from moisture content: c = (1200 + 4186 × MC) / (1 + MC) where MC is moisture fraction

For operational use (irrigation scheduling, stress monitoring), the defaults are adequate.

## 5. Quality Control Checks

### Good measurement (trust)
- ΔT_up and ΔT_dn both 0.1–3.0 °C (clear heat-pulse signal)
- V_sap in range 0–60 cm/h (typical for most trees)
- Zero-flow calibration valid (probe_health bit 4 = 1)
- No fault flags

### Suspicious measurement (investigate)
- ΔT < 0.05 °C: weak signal — check heater function, battery voltage
- ΔT > 5 °C: heater over-powered or probe poorly coupled — check insertion
- V_sap > 80 cm/h: unusually high — possible thermal gradient from sun exposure
- V_sap negative: reverse flow at night (root pressure) — normal in some species

### Bad measurement (discard)
- V_sap = NaN: ADC read failure or thermistor disconnected — check probe
- probe_health = 0x00: all sensors failed — check power, connections
- heater_fault flag set: overcurrent or thermal fuse blown — replace probe