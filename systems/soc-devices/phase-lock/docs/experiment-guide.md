# Phase Lock — Experiment Guide

This guide describes five classic experiments you can perform with
the Phase Lock pocket lock-in amplifier. Each includes the wiring,
parameters, and expected results.

## 1. Chopped Photodiode Signal Recovery

**Goal:** Measure a tiny light signal buried in 100× ambient light.

### Wiring
```
   Ref Out BNC ──▶ LED driver ( transistor + 220Ω + LED )
                      ↓ modulated light at f₀ = 1 kHz
                  Photodiode (reverse-biased 9 V)
                      ↓ photocurrent
                  TIA (OPA2356, Rf = 1 MΩ, Cf = 10 pF)
                      ↓ voltage (1 V/µA)
                  Signal In BNC
```

### Setup
1. Set f₀ = 1 kHz (the LED modulates at this rate).
2. Set TC = 100 ms, slope = 12 dB/oct.
3. Set gain = AUTO.
4. Press RUN.
5. Block the LED: R should drop to the noise floor (~few nV).
6. Unblock: R rises to the photocurrent magnitude.
7. The DC ambient light (which would swamp a DC measurement) is
   rejected by the lock-in; only the AC component at 1 kHz survives.

### Expected
- With a 1 µW LED at 30 cm and a BPW34 photodiode, the photocurrent
  is ~50 nA → R ≈ 50 mV at the TIA output (1 V/µA gain).
- The lock-in recovers this even with 100× ambient (5 µW DC sunlight),
  because the DC is filtered out by the IIR LPF.

---

## 2. Hall-Effect Measurement

**Goal:** Measure the Hall voltage of a semiconductor sample.

### Wiring
```
   Ref Out BNC ──▶ Voltage-to-current converter ( 100Ω + op-amp )
                      ↓ AC current at f₀ = 113 Hz
                  Hall bar sample ( in cryostat or on bench )
                      ↓ Hall voltage ( differential, µV )
                  Instrumentation amp ( INA128, gain = 1000× )
                      ↓ single-ended
                  Signal In BNC
   Aux In BNC  ◀── B-field Hall sensor ( for B-field tagging )
```

### Setup
1. Set f₀ = 113 Hz (away from 60/120 Hz mains harmonics).
2. Set amplitude = 1 V → ~10 mA AC current.
3. Set TC = 300 ms, slope = 24 dB/oct.
4. Set gain = 128× (or AUTO).
5. Sweep the magnet (or sweep f₀ if you want the Hall response vs.
   frequency).
6. Read R = Hall voltage; Θ should be ~0° (resistive) or ~90° (if
   there's a capacitive component).

### Expected
- For a 10 mA current and a Hall coefficient R_H = 0.01 cm³/C,
  the Hall voltage at B = 0.1 T is V_H = R_H × I × B / d ≈ 10 µV.
- The lock-in reads R ≈ 10 µV with a noise floor of ~4 nV/√Hz →
  SNR > 1000 in a 1 Hz ENBW.

---

## 3. Electrochemical Impedance Spectroscopy (EIS)

**Goal:** Measure the impedance spectrum of an electrochemical cell
(battery, corrosion coupon, or electrochemistry electrode).

### Wiring
```
   Ref Out BNC ──▶ Potentiostat ( or simple op-amp + reference electrode )
                      ↓ AC voltage ( 10 mV ) at swept f₀
                  Electrochemical cell ( working / counter / ref )
                      ↓ AC current
                  TIA ( Rf = 1 kΩ )
                      ↓ voltage
                  Signal In BNC
```

### Setup
1. Set amplitude = 10 mV (small-signal, to stay in the linear regime).
2. Set TC = 100 ms, slope = 12 dB/oct.
3. Set gain = AUTO.
4. Start a SWEEP: 1 Hz–100 kHz, 50 points, log-spaced.
5. The device sweeps f₀, records R/Θ at each frequency.
6. Fit the resulting Bode plot to a Randles equivalent circuit
   (R_s + (R_ct ∥ C_dl) + W) using the Python script
   `scripts/eis_fit.py`.

### Expected
- A typical battery shows R_s ≈ 10 mΩ at high frequency, R_ct ≈ 50 mΩ
  in the mid-band, and a -45° Warburg tail at low frequency.
- The lock-in gives you |Z| and Θ directly; fit with `eis_fit.py`.

---

## 4. LVDT Position Readout

**Goal:** Measure the displacement of a Linear Variable Differential
Transformer (LVDT) core.

### Wiring
```
   Ref Out BNC ──▶ LVDT primary ( 5 kHz, 1 V )
                  LVDT secondary ( differential )
                      ↓
                  Differential amp ( INA128, gain = 100× )
                      ↓
                  Signal In BNC
```

### Setup
1. Set f₀ = 5 kHz (typical LVDT carrier).
2. Set TC = 10 ms, slope = 12 dB/oct.
3. Set gain = AUTO.
4. Press RUN.
5. Move the LVDT core; R is proportional to |displacement|, and
   Θ flips 180° when the core crosses the null.

### Expected
- For an LVDT with sensitivity 100 mV/V/mm, at 1 V excitation,
  R ≈ 100 mV per mm of displacement.
- The null (zero displacement) gives R ≈ 0, with Θ flipping by 180°
  as you cross it — this gives you the sign of the displacement.

---

## 5. Dielectric Spectroscopy of a Ferroelectric

**Goal:** Measure the dielectric constant ε(f) of a ferroelectric
capacitor (e.g., a PZT or BaTiO₃ sample) as a function of frequency
and temperature.

### Wiring
```
   Ref Out BNC ──▶ Sample capacitor ( 100 mV, swept f₀ )
                      ↓ AC current
                  TIA ( Rf = 10 kΩ, Cf = 10 pF )
                      ↓ voltage
                  Signal In BNC
   Aux In BNC  ◀── Thermistor ( for sample temperature )
```

### Setup
1. Set amplitude = 100 mV (small-signal).
2. Set TC = 100 ms, slope = 12 dB/oct.
3. Set gain = AUTO.
4. Start a SWEEP: 100 Hz–100 kHz, 50 points, log.
5. The dielectric constant is:
   ε' = |Z|⁻¹ × d / (ω × ε₀ × A), where d is thickness, A is area.
   ε'' = ε' × tan(δ), where δ = 90° − Θ.
6. Monitor the aux-input thermistor to track the Curie transition.

### Expected
- A PZT capacitor (1 mm thick, 5 mm dia, ε_r ≈ 1300) shows
  |Z| ≈ 1/(ω × C) with C ≈ 90 pF → |Z| ≈ 1.8 MΩ at 1 kHz.
- The lock-in reads this directly; the phase Θ tells you the loss
  tangent (tan δ = cot Θ).
- Near the Curie temperature (~350 °C for PZT), ε' peaks and Θ shifts.