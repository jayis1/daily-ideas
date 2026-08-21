# Field Guide — Ion Sprint

## Quick Start

### 1. Prepare BGE
- Mix 20 mM MES / 20 mM L-Histidine, pH 6.1
- Filter through 0.45 µm syringe filter
- Fill BGE reservoir vial (5 mL) and both inlet/outlet vials (1.5 mL)

### 2. Prepare Sample
- Filter sample through 0.22 µm syringe filter
- Add internal standard (e.g., 1 mM BaCl₂) for quantification
- Fill sample vial (1.5 mL microcentrifuge tube)

### 3. Install Capillary
- Insert capillary inlet into sample/inlet vial position
- Insert capillary outlet into outlet vial position
- Ensure C4D electrodes are aligned with detection window

### 4. Run
1. Power on (18650 charged, or USB-C connected)
2. Select BGE recipe (Menu → BGE → 1: MES/His)
3. Set HV voltage (Menu → HV → 20 kV)
4. Set injection mode (Menu → Inj → EK or HD)
5. Press START button
6. Device flushes capillary (30 s), injects sample, separates (3–10 min)
7. View electropherogram on OLED
8. Results: ion table with concentrations
9. Data saved to SD card + streamed over BLE

## BGE Recipes

### Recipe 0: Universal Anion/Cation (MES/His pH 6.1)
- 20 mM MES, 20 mM L-Histidine
- pH 6.1 (adjust with NaOH or HCl)
- Detects: both cations and anions in one run
- EOF moderate; cations first, then neutrals, then anions

### Recipe 1: Reversed-EOF Anions (MES/His + CTAB)
- 20 mM MES, 20 mM His, 0.5 mM CTAB (cetyltrimethylammonium bromide)
- pH 6.1
- CTAB reverses EOF; anions migrate first (fastest)
- Best for: inorganic anions in water (F, Cl, NO₂, NO₃, SO₄)

### Recipe 2: Cation Analysis (His/MES pH 4.5)
- 20 mM L-Histidine, 20 mM MES
- pH 4.5 (adjust with HCl)
- Low EOF; cations well separated
- Best for: serum/urine Na, K, Ca, Mg, Li

### Recipe 3: Organic Acids (MES/His pH 5.7)
- 20 mM MES, 20 mM His
- pH 5.7
- Best for: wine/juice (tartaric, malic, lactic, citric, acetic)

### Recipe 4: Amino Acids (Phosphate pH 2.5)
- 50 mM sodium phosphate
- pH 2.5 (adjust with phosphoric acid)
- Amino acids are cationic at low pH
- Best for: protein hydrolysates, fermentation broth

### Recipe 5: Sugars (NaOH pH 12.1)
- 20 mM NaOH
- pH 12.1
- Sugars are anionic at high pH (pKa ~12)
- Best for: carbohydrate analysis (glucose, fructose, sucrose)

### Recipe 6: Transition Metals (MES/His + EDTA)
- 20 mM MES, 20 mM His, 5 mM EDTA
- pH 6.1
- EDTA complexes metals for separation
- Best for: environmental water, industrial process monitoring

### Recipe 7: Organic Acids Anionic (Borate pH 9.3)
- 30 mM sodium borate
- pH 9.3
- Organic acids anionic at high pH
- Best for: pharmaceutical QC, counter-ion assay

## Common Applications

### Drinking Water Anion Analysis (EPA 6505)
1. BGE: Recipe 0 (MES/His pH 6.1)
2. Sample: tap water, filtered 0.22 µm
3. Internal standard: 1 mM BaCl₂
4. HV: 20 kV, injection: EK 5 kV / 2 s
5. Run time: 5 min
6. Detects: F⁻ (<1 ppm), Cl⁻, NO₃⁻, SO₄²⁻, PO₄³⁻

### Wine Organic Acids
1. BGE: Recipe 3 (MES/His pH 5.7)
2. Sample: wine diluted 100× in BGE
3. Internal standard: 1 mM benzoate
4. HV: 25 kV, injection: HD 10 cm / 10 s
5. Run time: 6 min
6. Detects: tartaric, malic, lactic, citric, acetic, succinic

### Serum Electrolytes
1. BGE: Recipe 2 (His/MES pH 4.5)
2. Sample: serum diluted 10× in deionized water
3. Internal standard: 1 mM CsCl
4. HV: 20 kV, injection: EK 5 kV / 3 s
5. Run time: 4 min
6. Detects: Na⁺, K⁺, Ca²⁺, Mg²⁺, Li⁺ (if on lithium therapy)

## Troubleshooting

### No peaks detected
- **Capillary blocked**: flush with 0.1 M NaOH (10 min), then BGE
- **Injection too small**: increase EK duration or HD lift time
- **C4D not working**: check electrode connections, verify AC excitation
- **BGE depleted**: replace with fresh BGE

### Peaks too broad
- **Sample too concentrated**: dilute 10–100×
- **Injection too large**: reduce EK duration or HD time
- **Capillary too long**: use 20 cm instead of 25 cm
- **HV too low**: increase to 25–30 kV

### Baseline drift
- **Temperature change**: run in temperature-controlled environment
- **Capillary conditioning**: flush with 0.1 M NaOH, then BGE, 5 min each
- **BGE contamination**: replace BGE and reservoir

### Poor resolution
- **BGE pH wrong**: check pH with meter, adjust
- **Ion co-migration**: try different BGE recipe
- **Capillary old**: replace if >100 runs or >1 month

### HV won't turn on
- **Lid interlock open**: close lid
- **Battery low**: charge battery
- **HW current limit tripped**: check for short circuit in capillary
- **Bleeder still active**: wait 1 s after turning off

## Maintenance

### Daily
- Flush capillary with BGE (5 min) after last run
- Empty and rinse vials

### Weekly
- Flush capillary with 0.1 M NaOH (10 min) → water (5 min) → BGE (5 min)
- Inspect C4D electrodes for corrosion
- Check BGE reservoir for contamination

### Monthly
- Replace BGE stock (discard >1 month old)
- Check capillary for damage (kinks, breaks)
- Calibrate migration times with standard solution
- Verify HV voltage monitor with external HV probe

### Capillary Replacement
- Capillary lifetime: ~200 runs or ~1 month (whichever first)
- Symptoms: loss of resolution, increased current, broad peaks
- Replace with: 50 µm ID, 365 µm OD, 25 cm, with detection window at 20 cm