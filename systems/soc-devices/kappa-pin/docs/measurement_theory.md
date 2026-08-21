# Kappa Pin — Measurement Theory

## 1. The Transient Line-Source Method

The transient line-source (needle probe) method is based on the analytical solution for an infinitely long line heat source in an infinite homogeneous medium. It is standardized as:

- **ASTM D5334** — Standard Test Method for Determination of Thermal Conductivity of Soil and Soft Rock by Thermal Needle Probe Procedure
- **ASTM D7896** — Standard Test Method for Thermal Conductivity of Engine Coolants and Related Fluids by Transient Hot Wire Liquid Method
- **IEEE 442** — Guide for Soil Thermal Resistivity Measurements

## 2. Governing Equation

For a line source of power per unit length **Q** (W/m) switched on at t=0, the temperature rise at radius r is (Carslaw & Jaeger, *Conduction of Heat in Solids*, 1959):

```
ΔT(r, t) = (Q / 4πλ) · E₁(r² / 4αt)
```

where E₁ is the exponential integral. For **r²/(4αt) << 1** (i.e., probe radius is small relative to thermal penetration depth), E₁(x) ≈ -γ - ln(x) + O(x), giving:

```
ΔT(t) ≈ (Q / 4πλ) · [-γ - ln(r²/4αt)]
       = (Q / 4πλ) · [ln(t) + ln(4α/r²) - γ]
```

where:
- λ = thermal conductivity (W·m⁻¹·K⁻¹)
- α = thermal diffusivity (m²·s⁻¹)
- γ = Euler-Mascheroni constant (0.5772...)
- r = probe radius (m)

## 3. Extracting Thermal Conductivity (λ)

In the linear regime (typically 10–50% into the heat pulse, once r²/(4αt) << 1 and before boundary effects), ΔT is linear in ln(t):

```
ΔT(t) = m · ln(t) + c
```

The slope **m = Q/(4πλ)** gives:

```
λ = Q / (4π · m)
```

This is the primary measurement. The slope m is found by linear regression of ΔT vs ln(t) over an optimal window selected to maximize R².

## 4. Extracting Thermal Diffusivity (α)

From the full model:

```
ΔT(t) = (Q / 4πλ) · [ln(t) + ln(4α/r²) - γ]
```

The intercept c = (Q/4πλ) · [ln(4α/r²) - γ] contains α:

```
ln(4α/r²) = γ + 4πλ·c/Q
α = (r²/4) · exp(γ + 4πλ·c/Q)
```

However, the intercept-based method is sensitive to early-time transients. Kappa Pin uses a **Levenberg-Marquardt nonlinear fit** of both λ and α to the full model over the regression window, providing more robust diffusivity estimation.

## 5. Derived Quantities

### Volumetric Heat Capacity
```
ρcₚ = λ / α
```
Units: J·m⁻³·K⁻¹

This is the amount of heat required to raise the temperature of a unit volume by 1 K. For water: ρcₚ ≈ 4.18 × 10⁶ J·m⁻³·K⁻¹.

### Thermal Effusivity
```
e = √(λ · ρcₚ) = √(λ²/α)
```
Units: J·m⁻²·K⁻¹·s⁻⁰·⁵

Effusivity measures how readily a material absorbs heat when touched. It's the property that determines the "feel" of a material (metal feels cold because it has high effusivity, drawing heat from skin quickly).

## 6. Constant Power Control

The accuracy of λ depends critically on knowing Q precisely. Kappa Pin maintains constant power via a PI control loop:

1. **Measure** V_heater and I_heater at each sample (120 Hz)
2. **Compute** Q = V × I / L_active (power per unit length)
3. **Adjust** digital potentiometer wiper to correct Q toward target
4. **Record** actual Q per sample for post-hoc computation

This per-sample Q measurement means that even if the PI loop isn't perfect, the actual Q is known to ±1%, giving λ accuracy of ±1% from power uncertainty alone.

## 7. Error Analysis

### Systematic Errors

| Source | Magnitude | Mitigation |
|--------|-----------|------------|
| Finite probe length (L/d < ∞) | 1–5% | Use L/d > 30; apply Blackwell correction |
| Probe thermal resistance | 1–3% | Thermal grease fill; small diameter |
| Axial heat flow along probe | 0.5–2% | Blackwell (1956) correction term |
| Contact resistance (soil) | 2–10% | Pre-drill guide hole; thermal grease |
| Natural convection (liquids) | 5–50% if ΔT > 5K | Keep ΔT < 2K; short pulse; horizontal wire |
| Power measurement error | 0.5–1% | Per-sample V×I measurement |
| Temperature measurement error | 0.1–0.5% | 4-wire RTD, 24-bit ADC, 1mA IDAC |

### Random Errors

| Source | Magnitude | Mitigation |
|--------|-----------|------------|
| Temperature noise | ±0.001°C | 24-bit ADC, averaging |
| Thermal noise in environment | ±0.01–0.1°C | Equilibrium check before measurement |
| Regression fit uncertainty | ±0.5–2% | Optimal window selection, R² > 0.9998 |

### Total Uncertainty Budget

| Component | Contribution to λ |
|-----------|-------------------|
| Power (Q) | ±1% |
| Slope (m) | ±2% (regression) |
| Contact resistance | ±2% (soil), ±0.5% (liquid) |
| Probe corrections | ±1% |
| **Total (RSS)** | **±3% typical, ±5% worst-case** |

## 8. Blackwell Axial Correction

For finite-length probes, heat flows axially along the probe sheath, causing the measured λ to be slightly high. Blackwell (1956) derived a correction:

```
λ_true = λ_measured · (1 - (2λ_probe / Q) · G(t, α, r, L))
```

where G is a geometric factor. For the NP-100 probe (stainless steel, λ_probe ≈ 16 W/m·K), the correction is typically < 1% at t > 10s and is applied automatically by the firmware.

## 9. Probe Design Considerations

### Length-to-Diameter Ratio (L/d)
- **L/d > 30**: Radial heat flow assumption valid, errors < 2%
- **L/d > 50**: Errors < 1% (recommended for precision)
- NP-100: L=80mm, d=1.2mm → L/d = 67 ✓

### Probe Radius
- Must satisfy r²/(4αt) << 1 for the linear regime
- For soil (α ≈ 0.5 mm²/s): r²/(4αt) < 0.01 requires t > r²/(0.04α) = 0.0006²/(0.04×5e-7) = 18s
- Hence the 30s pulse for soil measurements

### Heater-Sensor Geometry
- RTD should be co-located with heater (midpoint)
- Radial offset causes phase lag → systematic error
- NP-100: RTD at 50mm, heater spans 10–90mm → co-located ✓

## 10. Standards Compliance

| Standard | Scope | Kappa Pin Compliance |
|----------|-------|---------------------|
| ASTM D5334 | Soil thermal conductivity | ✓ (needle probe method) |
| ASTM D7896 | Liquid thermal conductivity | ✓ (hot-wire method) |
| IEEE 442 | Soil thermal resistivity | ✓ |
| ISO 22007-2 | Plastics — hot-wire method | ✓ (with HW-60 probe) |

## References

1. Carslaw, H.S. and Jaeger, J.C., *Conduction of Heat in Solids*, 2nd ed., Oxford, 1959.
2. Blackwell, J.H., "The transient-flow method for measuring thermal conductivity," *Can. J. Phys.*, 34, 1956.
3. ASTM D5334-14, *Standard Test Method for Determination of Thermal Conductivity of Soil and Soft Rock by Thermal Needle Probe Procedure*.
4. ASTM D7896-14, *Standard Test Method for Thermal Conductivity of Engine Coolants and Related Fluids by Transient Hot Wire Liquid Method*.
5. Vos, B.J., "Measurement of thermal conductivity of soils by the non-steady state method," *Comm. No. 19025*, Wageningen, 1955.
6. Decagon Devices, *KD2 Pro Thermal Properties Analyzer Operator's Manual*, 2016.