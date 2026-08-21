# Dent Scope — Measurement Theory

## Instrumented Indentation Overview

Instrumented indentation (also called depth-sensing indentation or instrumented hardness testing) measures the mechanical properties of materials by pressing a hard tip into a surface while continuously recording the applied force and the resulting penetration depth. Unlike traditional hardness tests (which only measure the residual indent size after unloading), instrumented indentation captures the full elastic-plastic response, enabling extraction of both hardness and elastic modulus.

The technique is standardized in:
- **ISO 14577** (Instrumented indentation testing)
- **ASTM E2546** (Standard test method for instrumented indentation)

## Load–Displacement (P–h) Curve

A typical test cycle has three phases:

1. **Loading**: Force increases at a controlled rate. The indenter penetrates the sample, causing both elastic and plastic deformation.
2. **Hold**: Force is held constant at peak load. The depth may increase due to creep (time-dependent deformation).
3. **Unloading**: Force decreases at the same rate. The depth decreases elastically but does not return to zero (plastic deformation is permanent).

```
 P (mN)
  │        ╱╲         ← peak load P_max
  │       ╱  ╲___      ← creep hold (constant P, depth increases)
  │      ╱       ╲    ← elastic unloading (slope = stiffness S)
  │     ╱         ╲
  │    ╱            ╲  ← loading (plastic + elastic)
  │   ╱              ╲
  │__╱________________╲___
  │         h_f           ← residual depth (plastic)
  └──────────────────────── h (µm)
         h_max
```

## Oliver–Pharr Method

The Oliver–Pharr method (W.C. Oliver & G.M. Pharr, *J. Mater. Res.* 1992, 2004) is the standard procedure for extracting hardness and modulus from P–h curves.

### Step 1: Contact Stiffness (S)

The unloading curve is fitted to a power law:

```
P = α (h − h_f)^m
```

where `h_f` is the final residual depth, `α` is a fitting coefficient, and `m` is the power exponent (typically 1.2–1.8 for most materials).

The contact stiffness `S = dP/dh` is evaluated at the peak load:

```
S = α · m · (h_max − h_f)^(m−1)
```

We fit the upper 30–60% of the unloading curve using Levenberg–Marquardt iteration.

### Step 2: Contact Depth (h_c)

The contact depth accounts for the sink-in (or pile-up) around the indenter:

```
h_c = h_max − ε · P_max / S
```

where `ε` depends on indenter geometry:
- `ε = 0.75` for Vickers (136° pyramid) and Berkovich (65.27° pyramid)
- `ε = 1.0` for spherical (ball) indenters

### Step 3: Contact Area A(h_c)

The projected contact area depends on the indenter geometry:

| Indenter | Area Function |
|---|---|
| Vickers (136°) | `A = 24.5 · h_c²` (µm²) |
| Berkovich (65.27°) | `A = 24.5 · h_c²` (µm²) |
| Ball (diameter D) | `A = π · D · h_c` (µm²) |

For a real (non-ideal) tip, the area function is a calibrated polynomial:
```
A = C₀ · h_c² + C₁ · h_c + C₂ · h_c^(1/2) + ...
```

### Step 4: Hardness (H)

```
H = P_max / A(h_c)    [Pa]
```

Converting to Vickers hardness (HV):
```
HV = H / 9.807    [kgf/mm²]
```

Converting to Brinell (HB):
```
HB = H / 9.807    [kgf/mm²]
```

### Step 5: Reduced Modulus (E_r)

```
E_r = S / (2 · β · √(A / π))
```

where `β` is a correction factor:
- `β = 1.012` for Vickers
- `β = 1.034` for Berkovich

### Step 6: Young's Modulus (E)

The reduced modulus accounts for both sample and indenter elastic deformation:

```
1/E_r = (1 − ν²)/E + (1 − ν_i²)/E_i
```

Solving for E:
```
E = (1 − ν²) / (1/E_r − (1 − ν_i²)/E_i)
```

where:
- `E_i = 1141 GPa` (diamond indenter)
- `ν_i = 0.07` (diamond Poisson's ratio)
- `ν` = Poisson's ratio of the sample (user-configurable, default 0.30 for steel)

## Additional Measurements

### Martens Hardness (HM)

```
HM = P_max / (26.43 · h_max²)    [MPa]  (Vickers)
```

This includes both elastic and plastic deformation (unlike H which is based on contact area).

### Work of Indentation

- **Total work**: `W_total = ∫₀^{h_max} P dh` (area under loading curve)
- **Elastic work**: `W_elastic = ∫_{h_f}^{h_max} P dh` (area under unloading curve)
- **Plastic work**: `W_plastic = W_total − W_elastic`
- **Elastic work ratio**: `η = W_elastic / W_total`

`η` is a useful discriminator: ceramics have high η (0.3–0.6), metals low η (0.02–0.08), polymers very high (0.6–0.9).

### Creep

During the hold at peak load, depth increases with time:
```
C(t) = (h(t) − h(t_hold_start)) / P_max    [µm/mN]
```

The creep rate `dh/dt` during hold indicates time-dependent deformation behavior.

### Strain-Rate Sensitivity

From tests at different loading rates `dP/dt`:
```
m = d(ln H) / d(ln ε̇)
```

where `ε̇ ∝ (dh/dt)/h` is the strain rate. High `m` indicates superplastic behavior.

## Material Identification

Dent Scope stores a 30-material library with {HV, E_GPa, η} values from literature. The on-device k-NN (k=3) classifier matches measured results against the library in normalized log-scale {H, E, η} space:

| Category | Materials |
|---|---|
| Aluminum alloys | 6061-T6, 2024-T3, pure (annealed) |
| Copper | annealed, cold-worked |
| Brass/Bronze | 360 brass, bronze |
| Carbon steel | 1018, 1045, 4140 |
| Stainless steel | 304, 316 |
| Cast iron | gray, ductile |
| Titanium | Grade 2, Grade 5 (6Al-4V) |
| Other metals | Mg AZ31, Zn |
| Ceramics | Alumina 96%, Zirconia Y-TZP, soda-lime glass, SiC, Si₃N₄ |
| Polymers | PMMA, HDPE, PC, Nylon 66, PTFE |
| Composites | CFRP, GFRP |
| Coatings | TiN |

## Temperature Correction

Elastic modulus is temperature-dependent:
```
E(T) = E₀ · (1 − α_T · (T − T₀))
```

where `α_T` is the temperature coefficient (~0.0005/°C for steel). Dent Scope records sample temperature via DS18B20 for optional correction.

## Frame Compliance

A common error source in instrumented indentation is frame compliance — the test frame deforms under load, adding an apparent depth that is not from the sample. Dent Scope eliminates this by measuring depth relative to the **reference ring** (which sits on the sample surface) via the capacitive parallel-plate sensor. The reference ring is the zero-depth reference, so frame compliance in the stepper, leadscrew, and enclosure does not affect the depth reading.

## References

1. W.C. Oliver and G.M. Pharr, "An improved technique for determining hardness and elastic modulus using load and displacement sensing indentation experiments," *J. Mater. Res.* 7(6), 1564–1583 (1992).
2. W.C. Oliver and G.M. Pharr, "Measurement of hardness and elastic modulus by instrumented indentation: Advances in understanding and refinements to methodology," *J. Mater. Res.* 19(1), 3–20 (2004).
3. ISO 14577-1:2015, "Metallic materials — Instrumented indentation test for hardness and materials parameters."
4. ASTM E2546-07, "Standard test methods for instrumented indentation testing."
5. M.F. Doerner and W.D. Nix, "A method for interpreting the data from depth-sensing indentation instruments," *J. Mater. Res.* 1(4), 601–609 (1986).