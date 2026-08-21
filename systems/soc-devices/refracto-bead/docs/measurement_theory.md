# Refracto Bead — Measurement Theory

## 1. Critical-Angle Refractometry

The Refracto Bead uses the **critical-angle method**, the same principle employed by benchtop Abbe refractometers (Atago, Bellingham+Stanley, Schmidt+Haensch).

### 1.1 Snell's Law and Total Internal Reflection

When light crosses the boundary between two media with different refractive indices, it refracts according to Snell's Law:

```
n₁ sin(θ₁) = n₂ sin(θ₂)
```

where n₁, θ₁ are the index and angle in the first medium (prism), and n₂, θ₂ in the second (sample).

When n₁ > n₂ (light going from high-index prism to low-index sample), there exists a **critical angle** θ_c beyond which total internal reflection (TIR) occurs:

```
sin(θ_c) = n₂ / n₁
```

For angles θ > θ_c, all light is reflected back into the prism (bright region).
For angles θ < θ_c, light partially transmits into the sample (dark region).

The sharp boundary between bright and dark directly encodes the sample's refractive index:

```
n_sample = n_prism × sin(θ_c)
```

### 1.2 The Abbe Refractometer Geometry

In an Abbe refractometer:
1. Light is introduced into the prism at all possible angles (diffuse illumination)
2. The light exits through the prism's second face
3. An optical system (lens + detector) measures the angular distribution of the exit light
4. The bright/dark boundary position gives θ_c

The Refracto Bead replaces the traditional telescope+eyepiece with a **256-pixel linear CCD (TSL1402R)** and a **plano-convex lens (f=12mm)**, converting angular position to pixel position:

```
p_edge = p₀ + (f / pixel_pitch) × tan(θ_exit)
```

With f = 12 mm and pixel_pitch = 63.5 µm:
- Angular resolution: ~1.5 pixels per degree
- 256 pixels → ~17° angular range → RI range ~1.30–1.70 (with SF11 prism, n = 1.785)

### 1.3 The SF11 Flint Glass Prism

The prism material is **SF11** (Schott), a high-index flint glass:
- n_D = 1.78472 at 589 nm
- Abbe number V_D = 25.76 (high dispersion)
- dn/dT = −6.4 × 10⁻⁵ /°C

**Why SF11?** A high prism index maximizes the RI measurement range (since sin(θ_c) = n_sample/n_prism, we need n_prism > n_sample for all samples). SF11's n = 1.785 comfortably exceeds the highest sample RI (~1.70 for heavy oils).

**Why high dispersion?** High prism dispersion (low V_D = 25.76) means the critical angle varies significantly with wavelength, giving good dispersion sensitivity.

### 1.4 Calibration

The pixel-to-RI mapping is calibrated with two reference liquids of known RI:

```
n(p) = a + b × p + c × p²
```

**2-point (linear)**:
- Water (n_D = 1.3330) → pixel position p₁
- RI standard oil (n_D = 1.5150) → pixel position p₂

```
b = (1.5150 - 1.3330) / (p₂ - p₁)
a = 1.3330 - b × p₁
c = 0
```

**3-point (quadratic)** for extended range:
- Add a third standard (n_D = 1.7000) to solve for c

### 1.5 Sub-Pixel Edge Detection

The bright/dark boundary is a step function convolved with the optical system's point-spread function. Detection:

1. **Smoothing**: 5-tap moving average (reduces pixel noise)
2. **Derivative**: 5-tap Lanczos central difference (4th-order accurate)
3. **Peak finding**: Locate the maximum negative derivative (steepest descent)
4. **Sub-pixel refinement**: Parabolic interpolation around the derivative peak

```
δ = 0.5 × (d[i-1] - d[i+1]) / (d[i-1] - 2×d[i] + d[i+1])
p_edge = i + δ
```

This gives **±0.1 pixel** edge resolution, corresponding to **±0.0003 RI** with the default calibration.

---

## 2. Dispersion and the Abbe Number

### 2.1 Multi-Wavelength Measurement

Refractive index varies with wavelength (dispersion), described by the **Sellmeier equation**:

```
n²(λ) = 1 + Σ Bᵢλ²/(λ² - Cᵢ)
```

By measuring at 4 wavelengths (470, 525, 589, 655 nm), we compute:
- **n_D** = n(589 nm) — the standard reference RI
- **n_F** = n(470 nm) — approximating the hydrogen F-line (486.1 nm)
- **n_C** = n(655 nm) — approximating the hydrogen C-line (656.3 nm)
- **Dispersion** = n_F − n_C
- **Abbe number** V_D = (n_D − 1) / (n_F − n_C)

### 2.2 Why Dispersion Matters

The Abbe number is a powerful discriminator. Two liquids with nearly identical n_D can have very different V_D:

| Compound | n_D | V_D |
|----------|------|-----|
| Ethanol | 1.3611 | 59.0 |
| Acetone | 1.3588 | 54.6 |

The RI difference is 0.0023 (just at the resolution limit), but the V_D difference is 4.4 units (easily measured). This enables reliable identification of compounds that n_D alone cannot distinguish.

### 2.3 Cauchy Fit (3-term)

For the 4 measured wavelengths, we fit the Cauchy equation:

```
n(λ) = A + B/λ² + C/λ⁴
```

This allows interpolation to any wavelength (e.g., the exact hydrogen F and C lines at 486.1 and 656.3 nm) and extrapolation for Sellmeier analysis.

---

## 3. Temperature Correction

### 3.1 Prism Temperature Effect

The prism's refractive index changes with temperature:

```
n_prism(T) = n_prism(20°C) + (T - 20) × (dn/dT)_prism
```

For SF11: (dn/dT)_prism = −6.4 × 10⁻⁵ /°C

This shifts the critical angle and must be corrected:

```
θ_c(T) = arcsin(n_sample / n_prism(T))
```

### 3.2 Sample Temperature Effect

The sample's refractive index also changes with temperature:

```
n_sample(T) = n_sample(20°C) + (T - 20) × (dn/dT)_sample
```

Typical values:
- Water: (dn/dT) = −0.8 × 10⁻⁴ /°C
- Aqueous solutions: −1.0 to −2.0 × 10⁻⁴ /°C
- Oils: −3.5 to −4.0 × 10⁻⁴ /°C
- Solvents: −4.0 to −5.5 × 10⁻⁴ /°C

The Refracto Bead measures the prism temperature (DS18B20, ±0.1°C) and applies the appropriate correction based on the matched compound class.

### 3.3 Peltier Temperature Control (Optional)

For highest accuracy, the TEC1-04030 peltier element holds the prism at a stable 20.0°C ± 0.1°C using a PID controller:

```
duty_cycle = Kp × e + Ki × ∫e dt + Kd × de/dt
```

where e = 20.0 - T_prism. This eliminates temperature correction uncertainty entirely.

---

## 4. Derived Quantities

### 4.1 Brix (Sugar Content)

The **ICUMSA** (International Commission for Uniform Methods of Sugar Analysis) defines the relationship between refractive index and Brix (sucrose % by mass):

```
Brix = c₀ + c₁(n - 1.3330) + c₂(n - 1.3330)² + c₃(n - 1.3330)³
```

Approximate coefficients for 0–95 °Bx at 20°C:
- c₁ = 290, c₂ = 1200, c₃ = 3500

Valid for sucrose solutions; other sugars (glucose, fructose) have slightly different RI-Brix relationships.

### 4.2 Specific Gravity (Urine/Serum)

Clinical urine specific gravity is linearly related to RI:

```
SG = 1.000 + (n_D - 1.3330) × 2.6
```

Range: 1.000–1.070 (normal urine: 1.003–1.030; dehydration: >1.030)

### 4.3 Ethanol Concentration (%ABV)

For binary ethanol-water mixtures at 20°C:

| %ABV | n_D |
|------|------|
| 0 | 1.3330 |
| 10 | 1.3396 |
| 20 | 1.3469 |
| 40 | 1.3550 |
| 60 | 1.3616 |
| 80 | 1.3648 |
| 100 | 1.3611 |

Note: The relationship is **non-monotonic** (n_D peaks around 80% ABV). The Refracto Bead uses a lookup table for accurate ABV. For fermented beverages (wine, beer), dissolved sugars also raise RI — distillation or separate sugar correction is needed for accurate ABV.

### 4.4 Coolant Freeze Point

Ethylene glycol (EG) concentration from RI:

```
%EG = (n_D - 1.3330) / (1.3820 - 1.3330) × 50
```

Freeze point (0–50% EG):

```
FP = -0.74 × %EG  (°C)
```

| %EG | n_D | Freeze Point |
|-----|------|-------------|
| 0% | 1.3330 | 0°C |
| 25% | 1.3575 | -18°C |
| 50% | 1.3820 | -37°C |

---

## 5. Compound Identification (k-NN)

### 5.1 Feature Space

Each compound in the 60-entry library has two features:
- **n_D** (primary, measured to ±0.0003)
- **V_D** (secondary, measured to ±2.0)

### 5.2 Distance Metric

Weighted Euclidean distance:

```
d = sqrt(3 × (n_D_meas - n_D_lib)² + 0.01 × (V_D_meas - V_D_lib)²)
```

The n_D weight (3×) reflects its higher measurement precision. V_D is scaled down by 0.01 because its absolute range (~20–90) is much larger than n_D (~1.3–1.7).

### 5.3 k-NN Classification (k=3)

1. Compute distance to all 60 library entries
2. Select the 3 nearest neighbors
3. The nearest neighbor's name is the identification
4. Confidence = 1 − (d_nearest / threshold), threshold = 0.5

If confidence < 0.15, the result is marked "Unknown" (but the nearest match name is still shown for reference).

### 5.4 Limitations

- Binary mixtures: The RI of a mixture is approximately the volume-weighted average, so k-NN may identify the dominant component
- Temperature-sensitive compounds: If the prism temperature is far from 20°C and the dn/dT correction is imperfect, the n_D may be slightly off
- Very similar compounds: Ethanol vs. methanol have n_D = 1.3611 vs. 1.3284 — easily distinguished. But 40% sucrose (1.3997) vs. 20% NaCl (1.3686) are well-separated in (n_D, V_D) space despite being in similar RI ranges.

---

## 6. Accuracy Specifications

| Parameter | Specification | Conditions |
|-----------|--------------|------------|
| n_D range | 1.3000–1.7000 | SF11 prism, 256-pixel CCD |
| n_D accuracy | ±0.0003 | After 2-point calibration, 20°C |
| n_D resolution | ±0.0001 | Sub-pixel edge detection |
| V_D accuracy | ±2.0 | 4-wavelength measurement |
| Brix range | 0–95 °Bx | ICUMSA polynomial |
| Brix accuracy | ±0.1 °Bx | At 20°C, sucrose solutions |
| SG range | 1.000–1.070 | Clinical urine |
| SG accuracy | ±0.002 | At 20°C |
| Temperature | ±0.1°C | DS18B20 on prism |
| Measurement time | 3–4 s | 4-wavelength sweep |
| Battery life | 2,000+ measurements | 800 mAh LiPo |

---

*Refracto Bead Measurement Theory — SoC Device Inventions*