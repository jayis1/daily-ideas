# Ping Caliper — Probe & Coupling Guide

The Ping Caliper works with any piezoelectric ultrasonic transducer in the 1–10 MHz range with a coaxial (BNC or LEMO) connector. This guide helps you pick the right probe for your application and couple it correctly.

---

## 1. Probe Types

| Type | Frequency | Use | Notes |
|------|-----------|-----|-------|
| Contact (straight) | 2–10 MHz | General thickness; flaw detection on flat or gently curved surfaces | Most common; requires couplant |
| Delay-line | 5–20 MHz | Thin parts (<3 mm); high-resolution near-surface flaw detection | Built-in delay line isolates the initial pulse from near-surface echoes |
| Angle beam | 1–5 MHz | Weld inspection; detecting cracks not parallel to the surface | Uses a refracting wedge to introduce shear waves at an angle |
| Immersion | 5–20 MHz | Lab/precision; small parts in a water tank | Highest resolution; requires immersion tank |
| Dual-element (pitch-catch) | 2–5 MHz | Rough/corrosion surfaces; castings | Separate TX and RX crystals; good for pitted surfaces |
| Fingertip (miniature) | 10–20 MHz | Tiny parts; fillets; complex geometry | Small footprint; high frequency |

### Choosing a frequency

- **Lower frequency (1–2 MHz)**: deeper penetration (thick castings, coarse-grain materials) but lower resolution.
- **Mid (3–5 MHz)**: general-purpose; good balance of penetration and resolution.
- **Higher (5–10 MHz)**: fine-grained materials, thin parts, near-surface flaws, high resolution.

### Element diameter

- **6 mm**: general purpose; good for pipes ≥25 mm OD.
- **10 mm**: larger flat surfaces; deeper penetration.
- **3 mm**: small-radius curves; fillets; small parts.

---

## 2. Coupling

Ultrasonic energy does not transmit through an air gap. You **must** use a coupling medium (couplant) between the probe face and the test surface.

### Couplants

- **General purpose**: ultrasonic gel (water-based, propylene-glycol). Sold in squeeze tubes or packets. Works on steel, aluminum, most metals.
- **High temperature** (up to 200 °C): silicone-based couplant. For hot pipes in service.
- **Low temperature**: methanol or glycerol-based (won't freeze).
- **Rough surfaces**: a thicker couplant or grease helps fill pits.
- **Immersion**: water (with a wetting agent).

### Coupling technique

1. Clean the surface (wire brush if rusty; wipe with solvent if greasy).
2. Apply a thin, even drop of couplant to the probe face or the surface.
3. Press the probe down firmly and evenly — you want a thin couplant film, not a pool.
4. Rock the probe slightly to squeeze out air bubbles.
5. Hold steady while measuring. The A-scan should show a clean back-wall echo.

### Checking coupling

The Ping Caliper has a **coupling test** (probe-present detect on PC2). If the probe is not coupled, the device refuses to fire and shows "Couple probe." When properly coupled, the A-scan shows a strong surface echo.

---

## 3. Reference Blocks

For calibration, you need a **reference block** of the same material as your test piece, with a known, accurate thickness.

### IIW (International Institute of Welding) block

The standard IIW V1 block is a 25 mm thick steel block with a 100 mm radius and precision-drilled holes. Use it for:
- Zero calibration (couple to the 25 mm flat face)
- Velocity calibration (measure the known 25 mm)
- Beam angle verification (for angle-beam probes)

### Step blocks

A 4-step steel step block (e.g., 4/6/8/10 mm) is handy for quick linearity checks. Measure each step and verify the reading matches.

### Custom reference

For a specific material, machine a small coupon of the exact alloy to a known thickness (measured with calipers to ±0.01 mm) and use it as your velocity + zero reference.

---

## 4. Common Measurement Scenarios

### 4.1. Pipe wall thickness

- Use a **contact probe** (5 MHz, 6 mm) with a curved-face shoe for small-diameter pipes, or a flat probe for ≥100 mm pipes.
- Apply couplant along the pipe axis.
- Scan around the circumference, especially at the 6 o'clock position (bottom, where corrosion accumulates).
- Use **echo-to-echo mode** if the pipe is painted — this ignores the coating.

### 4.2. Pressure vessel

- Use a **dual-element probe** (4 MHz) for rough/pitted corrosion surfaces.
- Survey in a grid pattern; log each point.
- Compare readings to the nominal design thickness; flag any reading below 70 % nominal.

### 4.3. Weld inspection

- Use an **angle-beam probe** (45°/60°/70°, 2–5 MHz).
- Calibrate on the IIW block.
- Scan across the weld with a zig-zag ("creep" or "half-skip" technique).
- Place the **flaw gate** in the weld volume; any echo in the gate above threshold is a potential flaw (porosity, slag, lack of fusion, crack).

### 4.4. Coated structures (echo-to-echo)

- Use a **contact probe** (5 MHz) and **echo-to-echo mode**.
- Couple to the painted surface. The A-scan shows the coating echo (B0) and the metal back-wall echoes (B1, B2, ...).
- The device measures B2 − B1 and computes the **metal** thickness, ignoring the coating.

### 4.5. Castings

- Use a **low-frequency probe** (1–2 MHz) due to the coarse grain structure (high attenuation at high frequencies).
- Expect more scatter/noise in the A-scan.
- Use the **flaw gate** to find shrinkage cavities and inclusions.

---

## 5. Velocity by Material

The longitudinal wave velocity varies by alloy. The Ping Caliper has a built-in database (see `firmware/materials.c`). If your alloy isn't listed:

1. Machine a coupon of the exact material to a known thickness.
2. Run **velocity calibration** (Calibrate menu → Velocity, enter the known thickness).
3. The device solves for v and stores it.

Common velocities (m/s):

| Material | Velocity |
|----------|---------|
| Mild steel | 5920 |
| Stainless 304 | 5660 |
| Aluminum 6061 | 6320 |
| Copper | 4760 |
| Titanium grade 5 | 6100 |
| Cast iron (grey) | 4600 |
| Glass | 5640 |
| Acrylic | 2730 |

---

## 6. Care of Probes

- **Clean** the probe face with isopropyl alcohol after each use. Couplant residue is corrosive over time.
- **Store** probes in their case; protect the face from scratches.
- **Inspect** the wear plate periodically; a worn face reduces coupling and changes the zero offset.
- **Never drop** a probe — the piezo crystal is brittle.
- **Cable** — avoid kinking the coax; the connector is the most common failure point.

---

*MIT License — SoC Device Inventions.*