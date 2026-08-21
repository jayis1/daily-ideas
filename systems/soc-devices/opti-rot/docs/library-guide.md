# Opti Rot — Compound Library Guide

The Opti Rot ships with a built-in library of 40 common chiral compounds. This guide explains how to use, expand, and calibrate the library for your specific application.

## Built-in Library

The following compounds are pre-loaded in firmware flash (see `library.c`):

| # | Compound | [α]_D (589nm, 20°C) | Temp Coeff | Notes |
|---|----------|---------------------|------------|-------|
| 1 | Sucrose | +66.5 | -0.01 | Sugar standard, most common |
| 2 | D-Glucose | +52.7 | -0.02 | Blood sugar, brewing |
| 3 | D-Fructose | -92.4 | -0.02 | Fruit sugar, honey |
| 4 | D-Galactose | +80.2 | -0.02 | Milk sugar component |
| 5 | D-Mannose | +14.5 | -0.02 | |
| 6 | Lactose | +52.6 | -0.01 | Milk sugar |
| 7 | Maltose | +137.0 | -0.01 | Malt sugar, starch hydrolysis |
| 8 | D-Xylose | +18.8 | -0.02 | Wood sugar |
| 9 | L-Arabinose | +104.5 | -0.02 | Plant sugar |
| 10 | Raffinose | +101.0 | -0.01 | Legumes |
| 11 | D-Sorbitol | -2.0 | -0.01 | Sugar alcohol |
| 12 | D-Mannitol | -23.0 | -0.01 | Sugar alcohol |
| 13 | L-(+)-Tartaric acid | +12.0 | -0.003 | Wine, cream of tartar |
| 14 | D-(−)-Tartaric acid | -12.0 | -0.003 | Enantiomer |
| 15 | L-(−)-Malic acid | -2.3 | -0.003 | Apples |
| 16 | Citric acid | 0.0 | 0.0 | Achiral (reference blank) |
| 17 | L-(+)-Lactic acid | +3.3 | -0.005 | Fermentation product |
| 18 | L-Aspartic acid | +25.0 | -0.005 | Amino acid |
| 19 | L-Glutamic acid | +31.8 | -0.005 | Amino acid (MSG precursor) |
| 20 | L-Alanine | +2.7 | -0.005 | Amino acid |
| 21 | L-Valine | +28.3 | -0.005 | Amino acid |
| 22 | L-Leucine | +15.1 | -0.005 | Amino acid |
| 23 | L-Phenylalanine | -34.0 | -0.005 | Amino acid (aromatic) |
| 24 | L-Tyrosine | -7.4 | -0.005 | Amino acid |
| 25 | L-Tryptophan | -31.5 | -0.005 | Amino acid |
| 26 | L-Proline | -85.0 | -0.005 | Amino acid (cyclic) |
| 27 | L-Histidine | -39.0 | -0.005 | Amino acid |
| 28 | L-Serine | +14.9 | -0.005 | Amino acid |
| 29 | L-Threonine | -28.5 | -0.005 | Amino acid |
| 30 | Glycine | 0.0 | 0.0 | Achiral (reference blank) |
| 31 | D-(+)-Camphor | +44.0 | -0.005 | Essential oil |
| 32 | L-(−)-Camphor | -44.0 | -0.005 | Enantiomer |
| 33 | L-(−)-Menthol | -49.0 | -0.005 | Mint constituent |
| 34 | D-(+)-Menthol | +49.0 | -0.005 | Enantiomer |
| 35 | D-(+)-Limonene | +125.0 | -0.005 | Citrus oil constituent |
| 36 | L-(−)-Limonene | -125.0 | -0.005 | Pine/turpentine |
| 37 | R-(−)-Carvone | -61.0 | -0.005 | Spearmint oil |
| 38 | S-(+)-Carvone | +61.0 | -0.005 | Caraway seed oil |
| 39 | R-Thalidomide | +63.0 | -0.003 | Pharmaceutical (teratogen) |
| 40 | L-Ascorbic acid | +20.5 | -0.005 | Vitamin C |

## How Matching Works

When you run the **Identify** mode (3-wavelength measurement), the device:

1. Measures optical rotation at 405, 520, and 589 nm
2. Fits the Drude equation [α](λ) = K/(λ²-λ₀²) to get K and λ₀
3. Constructs a 5-dimensional feature vector: [α₅₈₉, α₄₀₅, α₅₂₀, K, λ₀]
4. Normalizes each dimension to approximately [-1, 1] scale
5. Computes Euclidean distance to every library entry
6. Uses k-NN (k=3) — the 3 nearest entries vote
7. Confidence = 100 × (1 - d_best/d_third)

## Adding Custom Compounds

### Via BLE (Python script)

```bash
python3 scripts/opti_rot.py --ble --add "My Compound" 42.5 -0.02
```

### Via Wi-Fi API

```bash
curl -X POST http://192.168.4.1/api/library/add \
  -H "Content-Type: application/json" \
  -d '{"name":"My Compound","alpha":42.5,"tc":-0.02,"K":0,"lambda0":200}'
```

### Via UART

Send a `CMD_LIBRARY_ADD` (0x87) frame with the compound parameters.

Custom entries are stored in SD card (`/opti_rot/library.bin`) and persist across power cycles. Up to 10 custom entries can be added.

## Calibrating a New Compound

To add a new compound to the library with accurate parameters:

1. **Prepare a standard solution**: Weigh a known mass of the pure compound (e.g., 10.000 g) and dissolve in distilled water, diluting to exactly 100 mL at 20°C. This gives c = 10.000 g/100mL.

2. **Auto-zero**: With an empty tube (or water-filled), press CAL to zero.

3. **Measure at 589 nm**: Insert the sample, press MEAS. Record the rotation α₅₈₉.

4. **Calculate specific rotation**: [α]_D = α / (l × c) where l = 1 dm (100mm tube), c = concentration in g/mL. Example: if α = 4.25° and c = 0.1 g/mL (10g/100mL), then [α]_D = 4.25 / (1 × 0.1) = 42.5°.

5. **Measure at 405 and 520 nm**: Run Identify mode to get α₄₀₅ and α₅₂₀.

6. **Fit Drude parameters**: Use the Drude equation fit (the device does this automatically in Identify mode). Record K and λ₀.

7. **Determine temperature coefficient**: Measure at several temperatures (e.g., 10°C, 20°C, 30°C) and fit [α](T) = [α]₂₀ × (1 + k × (T-20)). The slope gives k.

8. **Add to library**: Use any method above to store the compound with all parameters.

## Quality Notes

- Literature values for [α]_D vary by source and purity. Always verify with a standard.
- Specific rotation depends on solvent (values above are for water unless noted).
- Drude parameters are approximate; precise ORD characterization requires more wavelengths.
- Temperature coefficients are approximate; measure at your operating temperature range.
- For pharmaceutical applications, always validate against a certified reference standard.