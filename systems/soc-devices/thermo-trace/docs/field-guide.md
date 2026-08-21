# Field Guide — Thermo Trace Pocket DSC

## Quick Start

1. Charge the device via USB-C (green LED flashes while charging,
   solid when charged)
2. Load 1-10 mg of sample into an aluminum DSC pan
3. Place the sample pan on the sample cell (left), empty pan on the
   reference cell (right)
4. Close the DSC cell lid
5. Press button A → set mass (mg) using B/C buttons → press A
6. Set ramp rate (°C/min) → press A to start
7. Wait for the scan to complete (~55 min for 5°C/min to 300°C)
8. View the match result on the OLED
9. Connect via BLE to the app for detailed analysis

## Common Applications

### Polymer Identification

Place 2-5 mg of plastic sample in the pan. The DSC curve will show:
- Glass transition (Tg) — step change in heat flow
- Melting peak (Tm) — sharp endothermic peak
- Crystallization peak (Tc) — exothermic peak during cooling

The library contains 20 common polymers (PE, PP, PS, PET, PA, PC, etc.)
for automatic identification.

**Tip:** For recycling sorting, a 100°C/min ramp (if supported) can
identify polymers in under 3 minutes.

### Pharmaceutical Analysis

- **Melting point verification**: Verify drug identity by Tm
- **Polymorphism detection**: Different crystal forms have different Tm
  (e.g., sulfathiazole form I = 172°C, form II = 202°C)
- **Purity assessment**: Impure samples have broadened, depressed peaks

### Food Science

- **Fat melting profile**: Characterize cocoa butter, butter, oils
- **Adulteration detection**: Different fats have distinct DSC curves
- **Honey authentication**: Pure honey has characteristic glass transition

### Wax Analysis

- **Melting point**: Identify wax type (paraffin 58°C, beeswax 64°C,
  carnauba 82°C)
- **Blends**: Multiple peaks indicate wax blends

## Safety Precautions

⚠️ **The DSC cell reaches up to 300°C — do not touch during or
immediately after a scan!**

- Always wait for cooldown (T < 50°C) before opening the cell lid
- Never load flammable or explosive samples
- Never exceed 300°C (the device has safety cutoffs, but don't rely
  on them alone)
- Use only aluminum DSC pans (not plastic or glass)
- Ventilate the area — some samples may release vapors when heated
- Do not leave the device unattended during a scan

## Interpreting DSC Curves

```
  Heat flow (mW)
       │
   +10 ┤        ╱╲              Endothermic (melting)
    +5 ┤       ╱  ╲             ↑ (sample absorbs heat)
     0 ┤──────╱────╲──────────────────────────────
    -5 ┤     ╱      ╲       ╲╱
   -10 ┤    ╱        ╲     ╱╲ Exothermic (crystallization)
       │                     ↓ (sample releases heat)
       └─────────────────────────────────────── Temperature (°C)
              Tg    Tm        Tc
            (step) (peak↑)  (peak↓)
```

### Key Features

| Feature | Appearance | Meaning |
|---------|-----------|---------|
| Glass transition (Tg) | Step change (↓) | Polymer becomes rubbery |
| Melting (Tm) | Sharp peak (↑) | Crystal → liquid |
| Crystallization (Tc) | Sharp peak (↓) | Liquid → crystal (cooling) |
| Curing (exotherm) | Broad peak (↓) | Resin crosslinking |
| Decomposition | Irregular | Sample breaking down |

## Material Library Quick Reference

### Polymers (Tg / Tm)
- HDPE: — / 135°C
- PP: -10 / 165°C
- PET: 80 / 255°C
- PA6: 50 / 220°C
- PC: 145 / —
- PLA: 60 / 170°C

### Metals (Tm / ΔH)
- Indium: 156.6°C / 28.7 J/g
- Tin: 231.9°C / 60.2 J/g
- Bismuth: 271.4°C / 53.3 J/g

### Waxes (Tm)
- Paraffin: 58°C
- Beeswax: 64°C
- Carnauba: 82°C

### Pharmaceuticals (Tm)
- Ibuprofen: 75°C
- Acetaminophen: 169°C
- Aspirin: 135°C
- Caffeine: 235°C

## Tips for Good Results

1. **Use small samples** — 1-5 mg is ideal. Too much sample causes
   thermal lag and broadened peaks.
2. **Crimp the pan** — good thermal contact is essential. Use a DSC
   pan crimper tool.
3. **Match the pans** — use the same type of pan for sample and
   reference (same mass, same material).
4. **Use moderate ramp rates** — 5°C/min gives the best resolution.
   Faster rates (10-20°C/min) sacrifice resolution for speed.
5. **Let it equilibrate** — after loading, wait 30 seconds for thermal
   stabilization before starting a scan.
6. **Clean the cell** — between samples, wipe the cell with isopropyl
   alcohol on a cotton swab.
7. **Avoid humidity** — water evaporation creates a broad endothermic
   peak that obscures other transitions.

## Battery Life

- Full charge: ~4 hours via USB-C
- Scans per charge: ~15 (at 5°C/min to 300°C)
- Battery indicator on OLED: "BAT: XX%"
- Charge when below 20% to avoid deep discharge