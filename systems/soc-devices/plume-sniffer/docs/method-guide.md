# Plume Sniffer — Method Guide

## Choosing a Method

| Scenario | Method | Why |
|----------|--------|-----|
| General unknown sample | M_ETHOS | Broad coverage C5–C16 |
| Quick yes/no screening | M_FAST | 4-min run, covers C5–C10 |
| Very volatile solvents (ether, pentane, freon) | M_ISOTH | No ramp, isothermal 80°C |
| Semivolatiles (naphthalene, limonene, nonanal) | M_HIGH | Higher start temp, ramps to 180°C |

## Sample Volume

| Volume | Time @ 30 mL/min | Sensitivity | Use case |
|--------|-------------------|-------------|----------|
| 50 mL | 100 s | ~50 ppm | High-conc (headspace of pure solvent) |
| 100 mL | 200 s | ~25 ppm | General screening |
| 250 mL | 500 s | ~10 ppm | Field air monitoring |
| 500 mL | 1000 s | ~5 ppm | Trace analysis (BTEX, breath VOCs) |

Larger volumes improve sensitivity but lengthen the sampling phase. The
practical limit is ~500 mL (17 min sample time); beyond that, breakthrough
on Tenax TA becomes significant.

## Ramp Rate

- **Slower ramp (5 °C/min)** — better peak separation, longer run.
  Use for complex mixtures (food aroma, fuel headspace).
- **Faster ramp (20 °C/min)** — co-elution of late peaks, but faster
  screening. Use for quick yes/no detection of target compounds.
- **Isothermal** — best for simple mixtures of known volatility range.
  No temperature drift artifacts; baseline is very flat.

## Carrier Gas

The default carrier is **filtered ambient air** (through an inline
activated-carbon scrubber). This is free and portable but has lower TCD
sensitivity than helium or nitrogen (air's thermal conductivity is
mid-range, so the contrast with analyte vapors is smaller).

For **2–5× better sensitivity**, connect a small disposable N₂ cartridge
(18 g, whipped-cream charger) to the carrier inlet port instead of the
carbon filter. The firmware works identically — only the baseline signal
level changes. Run a blank to re-establish the baseline after switching
carriers.

## Compound Library Customization

The 40-compound library is embedded in `firmware/library.c`. To add or
modify entries:

1. Edit the `s_library[]` array in `library.c`.
2. Add `{ "Name", RI, CAS_compact, response_factor }`.
3. Rebuild and flash.

For field customization without recompiling, a future version will support
NVS-stored library extensions via BLE. For now, the flash library is
authoritative.

### Retention Index (RI) Values

RI values in the library are for a **5% OV-101** (non-polar, dimethyl-
silicone) column, equivalent to DB-1, HP-1, OV-1, SPB-1. If you use a
different stationary phase (e.g., PEG/wax for polar compounds), the RI
values will differ significantly and you must build a new library.

### Response Factors

TCD response factors are relative to propane = 1.0. They depend on the
thermal conductivity difference between the analyte and the carrier gas.
For air carrier, approximate factors:

| Compound class | Response factor range |
|----------------|----------------------|
| Alkanes | 0.7–1.0 |
| Aromatics | 0.7–0.85 |
| Alcohols | 0.35–0.55 |
| Ketones/Aldehydes | 0.45–0.60 |
| Chlorinated | 0.7–0.85 |
| Amines | 0.4–0.7 |

## Calibration

### n-Alkane Calibration (Required)

Run an n-alkane mix (C5–C16) and record retention times. Upload via
`scripts/alkane_cal.py`. This anchors the Kovats RI scale. Re-calibrate:
- After column replacement
- Monthly (column aging shifts retention)
- After any method change (different ramp = different RI scale)

### Concentration Calibration (Optional)

For accurate ppm values, calibrate against a known standard:

1. Prepare a standard at a known concentration (e.g., 100 ppm toluene
   in N₂, from a certified gas standard or a permeation tube).
2. Run the standard and note the peak area.
3. Adjust `CALIBRATION_K` in `firmware/identify.c` until the reported
   concentration matches the standard.

The default `K = 0.01` is a rough estimate; real values typically range
0.005–0.03 depending on TCD cell geometry and carrier gas.

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No peaks | Leak in flow path | Re-tighten ferrules, soap-test |
| Broad, tailing peaks | Column overloaded or dirty | Reduce sample volume, bake out column at 180°C for 30 min |
| Baseline drift | Carrier flow unstable; column bleed | Check pump voltage; condition column at max temp for 1 h |
| Negative peaks | Analyte has higher thermal conductivity than carrier (e.g., H₂ in N₂) | Normal for H₂/He; invert polarity in firmware if needed |
| Retention time shift | Column aging or temp drift | Re-calibrate n-alkane anchors |
| Ghost peaks | Tenax degradation or carryover | Bake preconcentrator at 250°C for 10 min between runs |