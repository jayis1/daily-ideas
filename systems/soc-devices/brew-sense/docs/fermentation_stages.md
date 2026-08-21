# Fermentation Stages — Reference Guide

## Overview

The Brew Sense classifies fermentation into 6 stages based on specific gravity (SG), CO₂ evolution rate, temperature trend, and pH. This guide explains each stage and what it means for your brew.

## Stage Classification

### LAG (Stage 0)

**What's happening**: Yeast cells are adapting to the wort environment. They're taking up oxygen, building sterols for cell walls, and reproducing. No visible activity yet.

**Sensor signature**:
- SG: >1.060 (high, near original gravity)
- CO₂: <400 ppm above ambient (flat or slowly rising)
- Temperature: Stable at pitching temperature
- Activity index: 0-15

**Duration**: 6-24 hours (varies with yeast health, pitching rate, temperature)

**Action**: Wait. Do not add more yeast. Ensure temperature is in the recommended range.

---

### ACTIVE (Stage 1)

**What's happening**: Yeast is actively fermenting sugars. Krausen (foam) is forming. CO₂ production is ramping up. This is the most vigorous phase.

**Sensor signature**:
- SG: Dropping rapidly (>0.002 per hour)
- CO₂: 500-2000 ppm above ambient, rising
- Temperature: May rise 1-3°F from fermentation heat
- Activity index: 40-80

**Duration**: 2-5 days (varies with OG, yeast strain, temperature)

**Action**: Monitor temperature closely. Use the Brew Sense alerts to catch temperature excursions. Consider temperature control if fermenting lagers or sensitive styles.

---

### PEAK (Stage 2)

**What's happening**: Fermentation is at maximum vigor. Krausen is at its highest. CO₂ production is peaking. SG is in the 1.020-1.040 range for most beers.

**Sensor signature**:
- SG: 1.020-1.040 (plateau area)
- CO₂: Maximum (1000-3000 ppm above ambient)
- Temperature: Peak fermentation temperature
- Activity index: 90-100

**Duration**: 1-3 days

**Action**: For ales, maintain temperature. For lagers, begin ramping down. This is when off-flavors are most likely to form if temperature is too high.

---

### SLOWING (Stage 3)

**What's happening**: Most easily fermentable sugars have been consumed. Fermentation is decelerating. Krausen is falling. CO₂ production is decreasing.

**Sensor signature**:
- SG: Dropping slowly (<0.001 per hour)
- CO₂: Declining (200-500 ppm above ambient)
- Temperature: Returning to ambient
- Activity index: 20-50

**Duration**: 2-7 days

**Action**: For many beers, this is a good time to start a diacetyl rest (raise temperature 2-3°F for 2 days). For lagers, continue lowering temperature.

---

### FINISHED (Stage 4)

**What's happening**: Fermentation is complete. SG has stabilized. CO₂ is near zero. Yeast is settling out (flocculating). The beer is ready for packaging.

**Sensor signature**:
- SG: Stable at final gravity (<1.015 for most beers)
- CO₂: <100 ppm above ambient
- Temperature: At ambient
- Activity index: 0-10

**Duration**: Indefinite (beer stays at FG)

**Action**: 
- Verify FG matches your target (typically 1/4 to 1/3 of OG)
- Check for desired attenuation
- Package (bottle or keg)
- The Brew Sense will alert you with a "HAPPY" tone!

**Typical FG ranges**:
| Style | FG Range | Apparent Attenuation |
|-------|----------|---------------------|
| Light Lager | 1.004-1.010 | 85-90% |
| Pale Ale | 1.008-1.014 | 75-80% |
| IPA | 1.008-1.014 | 75-82% |
| Stout | 1.010-1.018 | 70-78% |
| Belgian | 1.006-1.012 | 80-90% |
| Barleywine | 1.016-1.030 | 65-75% |

---

### STUCK (Stage 5)

**What's happening**: Fermentation has stopped prematurely. SG is higher than expected and hasn't changed in >48 hours. This can ruin a batch if not addressed.

**Sensor signature**:
- SG: Stable above expected FG (>1.020 for most beers)
- CO₂: Near zero
- Temperature: At ambient
- Activity index: 0-5 (for >48 hours)
- Trend: 0 (stable) for >48 hours

**Common causes**:
1. Temperature too low (yeast went dormant)
2. Temperature too high (yeast stressed, off-flavors)
3. Nutrient deficiency (nitrogen, minerals)
4. Yeast health issues (old yeast, low pitch rate)
5. High OG wort (yeast can't handle the alcohol)

**Action**:
1. Check temperature — warm to 68-72°F if too cold
2. Gently rouse yeast by swirling the fermenter
3. Add yeast nutrient (Fermaid O, Fermaid K)
4. Repitch with fresh yeast if SG is >1.030
5. The Brew Sense will alert you with a "SIREN" tone

---

## Activity Index Explained

The activity index (0-100) is a composite metric:

```
Activity = (Gravity Rate Score × 0.4) + (CO₂ Level Score × 0.3) + (CO₂ Rate Score × 0.3)
```

| Component | Calculation | Max Score |
|-----------|------------|-----------|
| Gravity Rate | \|dSG/dt\| × 2000 | 40 points |
| CO₂ Level | CO₂_ppm / 33 | 30 points |
| CO₂ Rate | dCO₂/dt / 3.3 | 30 points |

**Typical activity profiles**:

```
Activity
100 |         ╱╲
 80 |       ╱    ╲
 60 |     ╱        ╲
 40 |   ╱            ╲
 20 | ╱                ╲
  0 |╱                    ╲
    |LAG|ACTIVE|PEAK|SLOW|FIN|
    └─────────────────────────→ Time (days)
     0   1  2  3  4  5  6  7
```

## pH Monitoring

pH is especially important for:
- **Kombucha**: Target pH 2.5-3.5 (finished)
- **Sourdough**: Target pH 3.5-4.5 (active)
- **Kimchi**: Target pH 3.5-4.0 (fermented)
- **Beer**: pH 4.0-4.5 (finished beer)
- **Safety**: pH < 4.6 required for food safety

The Brew Sense will alert you if pH goes outside the expected range for your selected mode.