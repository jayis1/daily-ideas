# Iono Pin — Measurement Theory

## Ion mobility spectrometry (IMS) — physical basis

Ion mobility spectrometry separates ions by how fast they drift through a gas under an electric field. The drift velocity depends on the ion's collision cross-section, mass, and charge, so different compounds produce different drift times — a chemical fingerprint.

### 1. Ionization

In positive-ion mode (air drift gas), a radioactive Ni-63 beta source (or corona discharge) ionizes the carrier gas. The primary reactant ion is the **proton hydrate** cluster:

    H⁺(H₂O)ₙ   (n ≈ 3 at room humidity)

This appears as the **Reactant Ion Peak (RIP)** at K₀ ≈ 2.70 cm²/V·s and serves as an internal reference.

Analyte molecules M with higher proton affinity than water steal the proton:

    M + H⁺(H₂O)ₙ → MH⁺(H₂O)ₙ₋ₘ + m H₂O

forming **product ions**. Some analytes also form dimers (M₂H⁺) or adducts (M·NH₄⁺), giving multiple peaks per compound.

### 2. Drift

A Bradbury-Nielsen shutter grid admits a thin (~200 µs) slab of ions into the drift region. Ions drift under a uniform field E = V/L:

    v_d = K · E

where **K** is the ion mobility. Heavier/bulkier ions collide more and drift slower. The drift time:

    t_d = L / v_d = L² / (K · V)

### 3. Reduced mobility K₀

Mobility K depends on gas number density (pressure and temperature). To make the library portable, we compute the **reduced mobility** K₀:

    K₀ = K · (P₀/P) · (T/T₀) = (L² / (V · t_d)) · (P/760 torr) · (273 K / T)

where P₀ = 760 torr, T₀ = 273 K. K₀ is an intrinsic property of the ion (independent of instrument), so libraries built on K₀ transfer between instruments. Iono Pin reads P and T from the BME280 (ambient) and DS18B20 (drift tube wall), then computes K₀ in [`firmware/main/ims.c`](../firmware/main/ims.c).

### 4. Detection

Ions hit a **Faraday plate** — a metal electrode connected to an electrometer-grade transimpedance amplifier (ADA4530-1, 10 fA bias current, 1×10¹¹ Ω feedback). The current (pA–nA) becomes a voltage sampled at 40 ksps by the STM32 ADC1. The arrival-time distribution is the **mobility spectrum**.

### 5. Resolving power

The resolving power:

    R_p = t_d / w_h

where w_h is the FWHM of a peak. For Iono Pin: t_d ≈ 3.5 ms, w_h ≈ 100 µs → R_p ≈ 35. This is modest (commercial units reach 50–100) but sufficient to separate the major classes (RIP, explosives at K₀ 1.3–1.9, drugs at 1.5–2.0, CWAs at 1.3–1.9).

### 6. Sensitivity

Sensitivity is set by ionization efficiency, Faraday plate area, and TIA noise. With Ni-63 at 37 kBq, typical limits are ~10 ppb for TNT-like compounds (mass-limited). The corona alternative gives ~25 ppb at 1/3 the cost and no radioactivity.

## Classification

### Peak detection

1. **Baseline**: median of the first 10 samples (pre-arrival region) — robust to drift.
2. **Threshold**: 15% of the dynamic range above baseline.
3. **Derivative**: 2-sample slope; rising edge > 20 counts/sample triggers a peak start; falling edge < -20 closes it.
4. **Peak position**: the maximum sample within the peak window — converted to drift time t_d = 0.5 ms + index × 25 µs.

### k-NN classification

For each detected peak, find the K=5 nearest library entries by absolute K₀ distance. Confidence = 1 − (mean distance / 0.10), weighted by peak amplitude. The best-scoring peak across the spectrum wins. This is simple but effective: K₀ libraries are well-separated for the major classes (explosives 1.3–1.9, drugs 1.5–2.0, CWAs 1.3–1.9, VOCs 1.6–2.3) with overlap handled by the amplitude weighting.

## Limitations and extensions

- **Humidity**: the RIP position shifts with humidity; the firmware recomputes K₀ from the live RIP, partly compensating.
- **Dimerization**: high concentrations form M₂H⁺ dimers at lower K₀; the library includes both monomer and dimer K₀ where relevant (the classifier picks the best match).
- **Selectivity**: IMS alone cannot resolve all isobaric compounds (e.g., some drugs and CWAs overlap). For definitive ID, couple to a pre-separation column (GC-IMS, as in Plume Sniffer) or add a second drift tube (DMS/FAIMS differential mobility). These are natural extensions.
- **Memory effects**: adsorptive compounds (explosives) can linger; the 2 s purge between samples mitigates this.

## References

- Eiceman, Karpas & Hill, *Ion Mobility Spectrometry*, 3rd ed., CRC Press, 2014.
- IUPAC, "Ion Mobility Spectrometry," Pure Appl. Chem. 85(8), 2013.
- Siems et al., "Measuring the Resolving Power of Ion Mobility Spectrometers," Anal. Chem. 66, 1994.