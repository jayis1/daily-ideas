# Normative Database — Bone Echo

The normative database holds mean and standard deviation of the
Stiffness Index (SI) for each demographic group, used to compute
T-scores and Z-scores.

## Structure

The database has 4 ethnicities × 2 sex × 7 age groups = 56 entries.

### Ethnicities

| Index | Name | Notes |
|-------|------|-------|
| 0 | Caucasian | Most validated reference population |
| 1 | Asian | Derived from published studies |
| 2 | African | Higher baseline BMD (validated) |
| 3 | Hispanic | Approximate; less validated |

### Sex

| Index | Name |
|-------|------|
| 0 | Male |
| 1 | Female |

### Age Groups

| Index | Age Range |
|-------|-----------|
| 0 | 20–29 (young-adult reference for T-score) |
| 1 | 30–39 |
| 2 | 40–49 |
| 3 | 50–59 |
| 4 | 60–69 |
| 5 | 70–79 |
| 6 | 80+ |

## Reference Values (Mean SI / SD)

### Caucasian Male

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 95 | 14 |
| 30–39 | 93 | 14 |
| 40–49 | 91 | 15 |
| 50–59 | 88 | 15 |
| 60–69 | 84 | 16 |
| 70–79 | 80 | 16 |
| 80+   | 75 | 17 |

### Caucasian Female

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 89 | 12 |
| 30–39 | 87 | 12 |
| 40–49 | 84 | 13 |
| 50–59 | 78 | 14 |
| 60–69 | 70 | 15 |
| 70–79 | 62 | 16 |
| 80+   | 55 | 17 |

### Asian Male

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 93 | 13 |
| 30–39 | 91 | 13 |
| 40–49 | 89 | 14 |
| 50–59 | 86 | 14 |
| 60–69 | 82 | 15 |
| 70–79 | 78 | 15 |
| 80+   | 73 | 16 |

### Asian Female

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 87 | 11 |
| 30–39 | 85 | 11 |
| 40–49 | 82 | 12 |
| 50–59 | 76 | 13 |
| 60–69 | 68 | 14 |
| 70–79 | 60 | 15 |
| 80+   | 53 | 16 |

### African Male

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 99 | 13 |
| 30–39 | 97 | 13 |
| 40–49 | 95 | 14 |
| 50–59 | 92 | 14 |
| 60–69 | 88 | 15 |
| 70–79 | 84 | 15 |
| 80+   | 79 | 16 |

### African Female

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 93 | 11 |
| 30–39 | 91 | 11 |
| 40–49 | 88 | 12 |
| 50–59 | 82 | 13 |
| 60–69 | 74 | 14 |
| 70–79 | 66 | 15 |
| 80+   | 59 | 16 |

### Hispanic Male

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 94 | 14 |
| 30–39 | 92 | 14 |
| 40–49 | 90 | 15 |
| 50–59 | 87 | 15 |
| 60–69 | 83 | 16 |
| 70–79 | 79 | 16 |
| 80+   | 74 | 17 |

### Hispanic Female

| Age | Mean SI | SD |
|-----|---------|-----|
| 20–29 | 88 | 12 |
| 30–39 | 86 | 12 |
| 40–49 | 83 | 13 |
| 50–59 | 77 | 14 |
| 60–69 | 69 | 15 |
| 70–79 | 61 | 16 |
| 80+   | 54 | 17 |

## T-score and Z-score Computation

```
T-score = (SI_patient − SI_youngAdultMean) / SI_youngAdultSD
Z-score = (SI_patient − SI_ageMatchedMean) / SI_ageMatchedSD
```

### Example

A 55-year-old Caucasian female with SI = 72:

- Young-adult (20–29) Caucasian female: mean = 89, SD = 12
  → T = (72 − 89) / 12 = −1.42 (osteopenia)
- Age-matched (50–59) Caucasian female: mean = 78, SD = 14
  → Z = (72 − 78) / 14 = −0.43 (slightly below age peers)

Classification: **Osteopenia** (T = −1.42, between −1.0 and −2.5).

## Data Sources

The values above are approximate, derived from published QUS
calcaneus studies (Langton 1996; GE Achilles InSight manual; NHANES
III QUS subset). In a clinical device, the database should be
validated against a local reference population.

## Caveats

- **Population specificity**: The Caucasian reference is the most
  validated. Other ethnicities have less published data.
- **Age groups**: The database uses 10-year bins; within-bin
  variation is not captured.
- **Device specificity**: SI values depend on the QUS device and
  transducer geometry. The values here are calibrated for the Bone
  Echo transducer pair (1 MHz, 13 mm, through-transmission). A
  different transducer pair requires re-calibration of the database.