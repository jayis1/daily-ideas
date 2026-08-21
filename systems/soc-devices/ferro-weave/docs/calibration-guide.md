# Calibration Guide — Ferro Weave

Ferro Weave needs two calibrations: a **current-sense gain** calibration
(sets the H axis) and an **integrator scale** calibration (sets the B
axis). Both are stored in flash and applied in `adc_to_engineering()`.

## 1. Current-sense calibration (H axis)

The H field is `H = N1 · I / l_e`, and `I` is derived from the voltage
across the 0.1 Ω sense resistor after a gain stage:

```
I = (V_adc − V_mid) / (Rsense · gain)
```

### Procedure

1. **Disconnect the specimen.** Connect a known precision resistor
   (e.g. 10 Ω 0.1%) across the primary posts.
2. Drive a **DC** sweep (`WAVE DC`, `IPEAK 0.5`) and measure the actual
   current with a bench DMM in series.
3. Read the `I` value reported by the firmware (over BLE/Wi-Fi status
   or the debug UART).
4. Compute the correction factor:
   `gain_corr = I_dmm / I_reported`
5. Enter it via the Wi-Fi portal or the command:
   `ICAL <gain_corr>`
6. Repeat at ±0.5 A, ±1.0 A, ±2.0 A; the gain should be linear. If it
   isn't, the sense resistor or the op-amp gain stage is off — check
   soldering.

Expected: `gain ≈ 20.0` (the nominal front-end gain). Stored in flash
key `i_gain`.

## 2. Integrator scale calibration (B axis)

The integrator converts `V_sec = −N2·A·dB/dt` to a voltage
`V_int = −1/(R·C) · ∫ V_sec dt`, so:

```
B = V_int · (R·C) / (N2 · A)
```

The `(R·C)/(N2·A)` scale factor (`b_kint` in firmware) must be
calibrated against a **known flux**.

### Procedure (mutual-inductor method)

1. Wind a **calibration toroid** with known N1 = N2 = 100 and a
   precisely measured cross-section `A` (use `wind_calc.py`).
2. Drive a **sinusoidal** sweep at a low amplitude where the material
   is **linear** (well below saturation), e.g. I_peak = 0.1 A.
3. Measure the peak secondary voltage `V_sec_peak` with an oscilloscope
   and the peak integrator output `V_int_peak` reported by the firmware.
4. The expected B_peak for a linear material is:
   `B_peak = V_sec_peak / (N2 · A · 2π · f)`
5. Compute:
   `b_kint = B_peak / V_int_peak`
6. Enter it: `BCAL <b_kint>`

Stored in flash key `b_kint`.

### Alternative (known-material method)

If you have a material with a published B_sat (e.g. 3E25 ferrite,
B_sat = 0.47 T at 25 °C), drive it to saturation and adjust `b_kint`
until the reported B_sat matches the datasheet. Less precise but good
enough for relative measurements.

## 3. Integrator drift / offset

The OPA2188 chopper op-amp has < 0.05 µV/°C offset, so drift is
dominated by the integrator cap leakage. The 100 nF C0G cap specified
in the BOM has > 10 GΩ insulation resistance → drift < 1 mV/s, which is
negligible over a single 100 ms sweep. The firmware resets the
integrator at the start of every half-cycle anyway.

If you see the loop **shifting** along the B axis between sweeps, the
integrator reset switch (TS5A3166) may be leaky — check its soldering
and the reset pulse timing (should be 10 µs, driven from INTG_RESET).

## 4. Air-flux correction

The air-flux correction subtracts `μ₀·H·(A₂−A_core)/A₂` from B. Make
sure `A2` (the secondary winding total enclosed area, including
clearance) and `A_core` (the specimen cross-section) are entered
correctly — `wind_calc.py` computes both. For a close-fitting winding
`A2 ≈ A_core` and the correction is near zero; for a loosely-wound
secondary it can be several %.

## 5. Verification

After calibration, sweep a 3E25 toroid and compare:

| Quantity | Datasheet (3E25 @ 10 Hz, 25 °C) | Typical measured |
|----------|----------------------------------|------------------|
| B_sat    | 0.47 T                           | 0.45–0.47 T |
| H_c      | 12 A/m                           | 10–14 A/m |
| μ_dc     | 8000 (initial)                   | 7000–9000 |
| P_v @ 0.1T/10Hz | ~5 mW/kg | 4–6 mW/kg |

If μ_dc is way off, the air-flux correction or N1/l_e is wrong. If
B_sat is right but H_c is off, the current-sense gain is wrong. If B_sat
is wrong but H_c is right, the integrator scale is wrong.