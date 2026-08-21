# Halo Pin — Field Guide

## Quick Start

1. **Charge** via USB-C until the green LED stops pulsing (~3 h for a
   depleted 18650).
2. **Power on** — the OLED shows "HALO PIN v1.0 ready".
3. **Select mode** — rotate the encoder to choose:
   - `SAMPLE` — start particle counting
   - `CALIB` — PSL calibration (see `docs/calibration-guide.md`)
   - `ZERO` — HEPA zero-air test
   - `VIEW` — view last results
   - `BLE` — BLE pairing mode
4. **Start sampling** — press SELECT or the SCAN button.
5. The OLED shows a live histogram (16 bins) and PM2.5/PM10 values.
6. **Stop** — press MODE. Data is logged to SD card every 60 s.
7. **BLE streaming** — pair with the companion app
   (`scripts/halo_pin_app.py`) for live plotting and CSV logging.

## Interpreting Results

### PM2.5 (µg/m³) — WHO Air Quality Guidelines

| PM2.5 (µg/m³) | WHO AQI Category | Health Advisory |
|---------------|-----------------|-----------------|
| 0–12 | Good | None |
| 12–35 | Moderate | Unusually sensitive individuals should limit prolonged exertion |
| 35–55 | Unhealthy for Sensitive Groups | People with respiratory/heart conditions should limit outdoor activity |
| 55–150 | Unhealthy | Everyone should reduce prolonged exertion |
| 150–250 | Very Unhealthy | Avoid prolonged outdoor exertion |
| > 250 | Hazardous | Everyone should avoid outdoor activity |

### Particle Size Distribution

The 16-bin histogram shows the number of particles counted per bin
in the last 1-second interval. Key patterns:

- **Single peak at 0.3–0.5 µm** → combustion aerosol (vehicle exhaust,
  biomass burning). PM2.5 will be moderate but particle count very high.
- **Peak at 2–5 µm** → resuspended dust, industrial emissions.
- **Peak at 10–20 µm** → pollen, large dust. PM10 will be high but
  PM2.5 low.
- **Bimodal** (0.3–0.5 µm + 3–5 µm) → typical urban mixture.

## Deployment Tips

### Indoor Air Quality Monitoring
- Place at breathing height (1–1.5 m).
- Avoid direct airflow from HVAC vents (turbulence affects counting).
- Run for ≥ 10 minutes for a stable reading.

### Outdoor Air Quality
- Place in a shaded location (direct sun can heat the optical cell
  and increase electronic noise).
- Avoid rain (the inlet is not waterproof; use a rain shield).
- Temperature below 0°C may reduce blower efficiency; keep warm.

### Industrial / Workplace
- For dust monitoring (silica, wood, construction), set density to
  2.65 g/cm³ (`DENS:2.65`).
- Position at the worker's breathing zone.
- Run continuously; check PM2.5/PM10 against OSHA PEL limits.

### Cleanroom Certification
- Set density to the material being tested.
- Use the ZERO test to verify the baseline first.
- The 0.3 µm lower cutoff is suitable for ISO Class 1–5 cleanrooms.

## Limitations

- **0.3 µm lower limit**: Particles smaller than 0.3 µm produce
  scattering signals below the detection threshold. For ultrafine
  particle (< 100 nm) monitoring, use a condensation particle counter
  (CPC) instead.
- **40 µm upper limit**: Particles larger than 40 µm may not be
  aspirated efficiently into the inlet nozzle.
- **Coincidence loss**: At concentrations > 1000 #/cm³, two particles
  may cross the beam simultaneously and be counted as one larger
  particle. The firmware detects this (abnormally wide pulses) but
  does not correct for it. For high-concentration environments,
  dilute the sample with HEPA-filtered air.
- **Humidity effect**: At RH > 80%, hygroscopic particles absorb
  water and grow, increasing their scattering cross-section. The
  firmware supports κ-Köhler hygroscopic growth correction
  (`HYGR:1`), but the κ parameter (default 0.3) is a rough average.
  For accurate mass at high RH, use a dryer or apply species-specific
  κ values.
- **Flow rate**: The 1.0 L/min flow rate is calibrated for the
  included flow restrictor. Changes in restrictor geometry (e.g.,
  dust accumulation) shift the flow calibration. Check monthly
  with a reference flow meter.
- **Not a reference-grade instrument**: The Halo Pin is designed for
  screening and personal exposure assessment. For regulatory
  compliance, use a FRM/FEM-certified monitor (e.g., Met One BAM-1020).