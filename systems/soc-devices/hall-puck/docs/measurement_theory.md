# Hall Puck — Measurement Theory

## 1. The Van der Pauw Method

The Van der Pauw method (Van der Pauw, 1958) measures the sheet resistance of a thin, uniformly thick sample of arbitrary shape using 4 contacts on the periphery. It is standardized as **ASTM F76**.

### Requirements
- The sample must be uniformly thick
- The sample must be simply connected (no holes)
- The 4 contacts must be on the periphery (boundary)
- The contacts should be "point contacts" (much smaller than sample dimensions)

### Procedure

**Step 1 — Resistance R_A:**
- Force current I between contacts 1 and 2
- Measure voltage V between contacts 3 and 4
- R_A = |V₃₄| / I

**Step 2 — Resistance R_B:**
- Force current I between contacts 2 and 3
- Measure voltage V between contacts 4 and 1
- R_B = |V₄₁| / I

**Current reversal:** For each measurement, the current is reversed and the average |V| is taken. This cancels thermoelectric EMFs at the contacts:
```
R = (V_{+I} - V_{-I}) / (2 × I)
```

### Van der Pauw Equation

The sheet resistance R_s satisfies:
```
exp(-π · R_A / R_s) + exp(-π · R_B / R_s) = 1
```

This transcendental equation is solved iteratively (Newton-Raphson) for R_s.

**Initial guess:** For the symmetric case R_A ≈ R_B ≈ R:
```
R_s = (π / ln(2)) · R ≈ 4.532 · R
```

**Newton-Raphson iteration:**
```
f(R_s) = exp(-π·R_A/R_s) + exp(-π·R_B/R_s) - 1
f'(R_s) = (π·R_A/R_s²)·exp(-π·R_A/R_s) + (π·R_B/R_s²)·exp(-π·R_B/R_s)
R_s ← R_s - f(R_s)/f'(R_s)
```

Converges in ~5–10 iterations for typical samples.

### Resistivity

```
ρ = R_s × d    (Ω·cm, where d = sample thickness in cm)
```

## 2. The Hall Effect

When a magnetic field B is applied perpendicular to a current-carrying conductor, a transverse voltage (Hall voltage) develops:

```
V_H = (R_H × I × B) / d
```

where:
- R_H = Hall coefficient (cm³/C)
- I = current (A)
- B = magnetic field (T)
- d = sample thickness (cm)

### Hall Measurement Configuration

Using the Van der Pauw geometry (same 4 contacts):

1. Force current I between contacts 1 and 3 (diagonal)
2. Measure voltage V between contacts 2 and 4 (other diagonal)
3. Apply magnetic field B perpendicular to sample

### Offset Cancellation (4-Point Method)

The Hall voltage is typically very small (µV range) and must be separated from contact offsets, thermoelectric EMFs, and amplifier offsets. The 4-point method uses both current reversal AND field reversal:

```
V_H = (V_{+I,+B} - V_{-I,+B} - V_{+I,-B} + V_{-I,-B}) / 4
```

This cancels:
- **Thermoelectric offsets** (reversed by current reversal)
- **Contact resistance asymmetries** (reversed by current reversal)
- **Ampler offsets** (reversed by current reversal)
- **Misalignment voltage** (reversed by field reversal, not current reversal)

### Hall Coefficient

```
R_H = V_H × d / (I × B)    (cm³/C)
```

Unit conversion: V_H [µV], d [mm], I [mA], B [T]:
```
R_H [cm³/C] = (V_H_µV × d_mm) / (I_mA × B_T × 10⁴)
```

### Carrier Concentration

```
n = 1 / (|R_H| × e)    (cm⁻³)
```

where e = 1.602 × 10⁻¹⁹ C (electron charge).

### Carrier Type

- **R_H > 0** → p-type (holes are majority carriers)
- **R_H < 0** → n-type (electrons are majority carriers)

### Carrier Mobility

```
μ = |R_H| / R_s    (cm²/V·s)
```

where R_s is the sheet resistance from the Van der Pauw measurement.

## 3. Magnetic Field Reversal

Hall Puck uses a permanent N52 neodymium magnet (Ø10mm × 5mm) that provides ~0.48 T at the sample surface. The magnet is mounted on a rotating arm driven by a 28BYJ-48 stepper motor (2048 steps/rev).

**Field reversal procedure:**
1. Measure Hall voltage with magnet in B+ orientation (V_{+I,+B}, V_{-I,+B})
2. Rotate magnet 180° (1024 steps) to B- orientation
3. Measure Hall voltage (V_{+I,-B}, V_{-I,-B})
4. Compute V_H using the 4-point formula

**Position verification:**
A DRV5053 Hall-effect switch monitors the magnet orientation. The DRV5053 output voltage indicates field direction:
- B+ → DRV5053 output > 2.5V (positive field)
- B- → DRV5053 output < 2.5V (negative field)

## 4. Error Sources & Mitigations

| Source | Effect | Mitigation |
|--------|--------|------------|
| Contact resistance | Voltage offset | Current reversal (4-point method) |
| Thermoelectric EMF | Voltage offset | Current reversal |
| Misalignment voltage | Dominates V_H | Field reversal (4-point method) |
| Non-uniform sample thickness | Systematic error | Verify sample flatness |
| Finite contact size | Geometric error | Use small contacts (pogo pins) |
| Sample not simply connected | Invalid method | No holes in sample |
| Temperature variation | Mobility/conc drift | Monitor temperature (DS18B20) |
| B-field inaccuracy | R_H error | Calibrate B with reference sample |
| Current source inaccuracy | R_s error | Calibrate current with precision resistor |
| ADC offset | Voltage offset | Auto-zero before measurement |
| INA333 offset drift | Low-level error | Chopper-stabilized (10µV max offset) |

## 5. Temperature-Dependent Measurement

An optional resistive heater (polyimide film, 10Ω) on the sample platform allows temperature sweeps from 25–80 °C. At each temperature setpoint:

1. Set heater PWM via TIM2
2. Wait for thermal equilibrium (±0.5°C, 10s stable, monitored by DS18B20)
3. Run full Van der Pauw + Hall measurement
4. Log R_s(T), R_H(T), μ(T), n(T)

### Arrhenius Analysis

Carrier mobility often follows:
```
μ(T) = μ₀ × T^(-n) × exp(-E_a / kT)
```

A plot of ln(μ × T^n) vs 1/T gives:
- **Slope** = -E_a / k → activation energy E_a
- **Intercept** = ln(μ₀) → prefactor

This reveals scattering mechanisms (acoustic phonon, ionized impurity, etc.).

## 6. References

- Van der Pauw, L.J. "A Method of Measuring Specific Resistivity and Hall Effect of Discs of Arbitrary Shape." Philips Research Reports, 13, 1–9 (1958).
- ASTM F76-08: Standard Test Methods for Measuring Resistivity and Hall Coefficient of Single-Crystal Semiconductors.
- Schroder, D.K. *Semiconductor Material and Device Characterization*, 3rd ed. Wiley, 2006. Chapter 8: Hall Effect.
- Pierret, R.F. *Semiconductor Device Fundamentals*. Addison-Wesley, 1996. Chapter 2: Carrier Transport.