# Clinical Guide — Bone Echo

This guide covers the clinical use of the Bone Echo pocket QUS bone
densitometer: phantom calibration, patient positioning,
interpretation of SOS/BUA/SI/T-score, WHO classification, and the
limitations of QUS vs. DEXA.

## Background

Quantitative ultrasound (QUS) of the calcaneus (heel bone) is a
validated, radiation-free method for assessing bone quality and
fracture risk. QUS measures two quantities:

- **Speed of Sound (SOS)** — the velocity of ultrasound through
  bone (m/s). SOS reflects bone elasticity and cortical density.
  Typical calcaneus SOS: 1450–1950 m/s (higher = denser/healthier).
- **Broadband Ultrasound Attenuation (BUA)** — the slope of
  frequency-dependent attenuation (dB/MHz) through the trabecular
  bone. BUA reflects trabecular architecture and density.
  Typical calcaneus BUA: 20–80 dB/MHz (higher = denser).

The **Stiffness Index (SI)** combines SOS and BUA:

```
SI = 0.67 × BUA + 0.28 × SOS − 420
```

SI correlates with bone mineral density (BMD) and independently
predicts fracture risk. Meta-analyses of >40,000 patients show QUS
of the calcaneus predicts hip fracture as well as central DEXA
(Marshall et al., 2000; Hans et al., 2000).

## Phantom Calibration

**Before each session**, calibrate with the included 25 mm acrylic
phantom:

1. Place the phantom between the transducers (reed switch detects
   it automatically).
2. Press SCAN (or send `PHANTOM` over BLE).
3. The device measures:
   - SOS (should be ~2700 m/s for acrylic PMMA)
   - Reference FFT `|H_ref(f)|` (cancels transducer + coupling)
   - Probe delay (transducer + cable latency)
4. If SOS is outside 2650–2750 m/s, repeat. If still off, check
   transducer seating and gel coupling.

The phantom calibration is stored in NVS and persists across power
cycles. Recalibrate once per day or if the ambient temperature
changes by >5 °C.

## Patient Positioning

1. **Apply gel** — ultrasonic coupling gel on both transducer faces.
   Air is a strong ultrasound reflector; even a thin air layer
   blocks the signal entirely.
2. **Position the heel** — the calcaneus (the large heel bone) sits
   between the two transducers. The spring-loaded fixture applies
   gentle, consistent pressure (10 N). The calcaneus should be
   centered on the transducer active area (13 mm diameter).
3. **Hold still** — movement during the 32 ms scan window creates
   artifacts. The patient should relax the foot and not move.
4. **Enter demographics** — ID, age, sex, ethnicity. The normative
   database is population-specific; entering the correct ethnicity
   improves T-score accuracy.

## Interpreting Results

### Speed of Sound (SOS)

| SOS (m/s) | Interpretation |
|-----------|---------------|
| <1500 | Very low — severe bone loss |
| 1500–1600 | Low — osteoporosis range |
| 1600–1700 | Moderate — osteopenia range |
| 1700–1800 | Normal |
| >1800 | High — healthy cortical bone |

### Broadband Ultrasound Attenuation (BUA)

| BUA (dB/MHz) | Interpretation |
|--------------|---------------|
| <30 | Very low — poor trabecular architecture |
| 30–50 | Low — osteopenia range |
| 50–65 | Moderate — borderline |
| 65–75 | Normal |
| >75 | High — healthy trabecular density |

### Stiffness Index (SI)

| SI | Interpretation |
|----|---------------|
| <60 | High fracture risk |
| 60–75 | Moderate fracture risk |
| 75–90 | Low-moderate fracture risk |
| >90 | Low fracture risk |

### T-score (WHO Classification)

| T-score | Classification | Recommendation |
|---------|---------------|----------------|
| ≥ −1.0 | Normal | Repeat screening in 2 years |
| −2.5 to −1.0 | Osteopenia | DEXA confirmation recommended |
| ≤ −2.5 | Osteoporosis | Physician consult; DEXA confirmation |
| ≤ −2.5 + fracture | Severe osteoporosis | Urgent physician consult |

The T-score compares the patient's SI to the young-adult (20–29)
reference mean for their sex and ethnicity.

### Z-score

The Z-score compares to age-matched peers. A Z-score < −2.0
suggests the bone loss is more than expected for age, warranting
investigation for secondary causes (hyperparathyroidism, multiple
myeloma, etc.).

## Limitations vs. DEXA

| Aspect | QUS (Bone Echo) | DEXA |
|--------|----------------|------|
| Radiation | None | Ionizing (low dose) |
| Site | Calcaneus (heel) | Spine, hip, forearm |
| What it measures | Bone quality (architecture + density) | Areal BMD (g/cm²) |
| Accuracy | T-score ±0.3 SD | T-score ±0.1 SD |
| Precision | CV 1–3% | CV 1% |
| Cost | ~$78 device | $40k–$80k scanner |
| Portability | Pocket | Clinic-installed |
| Screening | Yes (validated) | Gold standard |

**Key limitation**: QUS is a *screening* tool, not a diagnostic
replacement for DEXA. The ISCD official position (2019) states:

> "QUS of the calcaneus may be used for fracture risk assessment
> in women >55 years. It should not be used for diagnosis or for
> monitoring treatment response."

A positive QUS screen (osteopenia or osteoporosis) should be
confirmed by central DEXA before initiating pharmacological
treatment.

## Three-Scan Average

ISCD recommends the average of 3 measurements for clinical use.
Bone Echo supports a "3-scan average" mode:

1. Enable 3-scan average in the menu (UI_3SCAN).
2. Press SCAN three times (reposition the heel between scans).
3. The device reports the mean SOS, BUA, SI, T-score.

This reduces measurement variability (CV from ~2% to ~1.2%).

## Normative Database Notes

The included normative database (54 entries: 4 ethnicities × 2 sex
× 7 age groups) is derived from published QUS calcaneus studies.
In a clinical device, these should be from a validated reference
population (e.g., NHANES III, GE Achilles InSight database).

**Important**: The Caucasian reference values are the most
validated. For other ethnicities, the values are approximate and
may over- or under-estimate fracture risk. If the patient's
ethnicity is "Other," the device falls back to Caucasian with a
warning.

## Safety

- **No ionizing radiation** — QUS is safe for all patients,
  including pregnant women and children. No shielding, no
  radiation safety officer required.
- **200 V HV** — the transmitter pulser operates at 200 V, but
  only for a 5 µs burst (duty cycle <0.1%). The transducer is
  isolated from the patient by the coupling gel and transducer
  face. The fixture prevents touching the transducer with HV armed.
- **Contraindications** — none for QUS. Open wounds on the heel
  should be covered with a sterile film before scanning.

## References

1. Langton CM, Palmer SB, Porter RW (1984). "Measurement of
   broadband ultrasonic attenuation in cancellous bone."
   *Eng Med* 13(2):89-91.
2. Marshall D, Johnell O, Wedel H (2000). "Meta-analysis of how
   well measures of bone mineral density predict osteoporotic
   fracture." *BMJ* 312:1254-1259.
3. Hans D et al. (2000). "Does moving the ultrasound measurement
   site to the radius improve the clinical utility of QUS?" *Osteo
   Int* 11:10-17.
4. ISCD (2019). "Official Positions — Adult." International Society
   for Clinical Densitometry.
5. WHO (1994). "Assessment of fracture risk and its application to
   screening for postmenopausal osteoporosis." WHO Tech Rep Ser 843.