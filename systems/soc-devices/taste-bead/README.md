# Taste Bead

**A pocket-sized electronic tongue that identifies liquids — water quality, milk freshness, honey adulteration, beverage authentication, and counterfeit detection — by sweeping multi-frequency electrochemical impedance spectroscopy (EIS) across a 5-metal electrode array and classifying the resulting impedance fingerprints with on-device k-NN/decision-tree machine learning. Built around an ESP32-S3 with an AD5941 analog front-end, dual-core measurement + classification pipeline, OLED display, SD card library storage, and BLE/Wi-Fi reporting — bringing $15k+ lab electronic tongues down to ~$72 and pocket size.**

---

## What It Does

The Taste Bead is a **pocket electronic tongue** — a liquid identification instrument that works like a human tongue but with far greater precision and consistency. It immerses an array of five dissimilar metal electrodes into a liquid sample, applies a multi-frequency AC voltage sweep, and measures the complex impedance response at each frequency for each electrode. The resulting 5-electrode × 20-frequency = 100-point "impedance fingerprint" is unique to each liquid's chemical composition. The device compares this fingerprint against a stored library using on-device machine learning and reports the identified liquid, confidence level, and quality metrics.

### Why a pocket electronic tongue matters

| Application | How Taste Bead Helps |
|---|---|
| **Water quality** | Identify contaminated/turbid water, distinguish tap vs. bottled vs. distilled, detect heavy metals |
| **Milk freshness** | Detect spoilage before smell/visual changes — impedance shifts as bacteria convert lactose to lactic acid |
| **Honey adulteration** | Detect glucose/fructose syrup adulteration — a $6B global fraud problem |
| **Olive oil authentication** | Distinguish extra-virgin from adulterated/refined oils |
| **Beverage authentication** | Identify counterfeit whiskey, wine, and spirits — a $3B counterfeit market |
| **Coffee quality** | Distinguish roast levels, detect staleness in brewed coffee |
| **Urine analysis** | Point-of-care screening for UTI, diabetes indicators (glucose, ketones) |
| **Soap/surfactant** | Verify detergent concentration in industrial cleaning |
| **Wine varietal** | Preliminary varietal/origin screening for importers |
| **Environmental** | Detect pollutants in surface water, identify unknown liquid spills |
| **Pharmaceutical** | Verify drug solution concentration and identity |

### How it works

1. **Electrode array** — Five dissimilar metal electrodes are mounted on a dunkable probe tip:
   - **Gold (Au)** — inert, responds to redox-active species
   - **Platinum (Pt)** — catalytic, sensitive to organic compounds
   - **Silver/Silver Chloride (Ag/AgCl)** — reference + chloride response
   - **Glassy Carbon (GC)** — wide potential window, responds to aromatic compounds
   - **Copper (Cu)** — catalyzes sugar/alcohol oxidation, responds to organic acids

   Each electrode contacts the liquid and contributes a unique impedance signature based on the liquid's ionic content, molecular species, and electrochemical reactivity at that metal's surface.

2. **Multi-frequency EIS sweep** — The AD5941 analog front-end applies a sine-wave voltage excitation at 20 logarithmically-spaced frequencies from 1 Hz to 100 kHz (1, 4, 10, 40, 100, 400, 1k, 4k, 10k, 40k, 100k Hz per decade, plus intermediate points) and measures the complex impedance (magnitude |Z| and phase θ) at each frequency for each electrode. This produces a Nyquist-like spectrum that encodes the liquid's:
   - **Solution resistance (R_s)** — related to ionic conductivity
   - **Double-layer capacitance (C_dl)** — electrode-liquid interface
   - **Charge-transfer resistance (R_ct)** — electrochemical reactivity
   - **Diffusion impedance (Warburg, Z_w)** — mass transport of ions

3. **Feature extraction** — From the 100-point raw impedance matrix, the ESP32-S3 extracts:
   - Per-electrode: R_s, R_ct, C_dl, Warburg coefficient σ, peak frequency
   - Cross-electrode ratios (e.g., Z_Au/Z_Cu at 100 Hz)
   - Principal component projections (pre-computed PCA loadings stored in flash)
   - Total 48 features per measurement

4. **On-device classification** — The feature vector is classified using a combination of:
   - **k-Nearest Neighbors (k=5)** against a flash-stored library of up to 50 reference liquids
   - **Decision tree** for fast rule-based pre-filtering (e.g., "if R_s > 10 kΩ → distilled/demineralized")
   - **Confidence scoring** — the k-NN vote agreement percentage is reported as confidence
   - The library is user-expandable: the "Learn" mode captures a new reference fingerprint and stores it in flash

5. **Output and reporting** — Results shown on OLED (identified liquid, confidence %, quality score), logged to SD card with full 100-point spectra, streamed over BLE/Wi-Fi to a phone app or Python script.

### Operating modes

| Mode | Description |
|------|-------------|
| **Identify** | Dip probe → sweep → classify → display result + confidence |
| **Library** | Browse stored reference fingerprints, delete entries |
| **Learn** | Capture new reference fingerprint (name it via BLE/phone) |
| **Raw** | Stream raw 100-point impedance matrix over BLE (for PC analysis) |
| **Monitor** | Continuous sweep at 10 s intervals — track changes over time (e.g., milk spoiling) |
| **Calibrate** | Open/short/standard calibration using 0.01 M KCl reference solution |

---

## Block Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              TASTE BEAD                                     │
│                                                                             │
│  ┌─────────────────┐  I2C (400 kHz)  ┌──────────────────────────────────┐  │
│  │  SSD1306 OLED    │◄─────────────►│                                    │  │
│  │  128×64          │               │         ESP32-S3                   │  │
│  └─────────────────┘               │   (Dual-core Xtensa LX7 @ 240 MHz)  │  │
│                                     │                                    │  │
│  ┌─────────────────┐  I2C          │  ┌──────────────────────────────┐  │  │
│  │  BME280          │◄─────────────►│  │  Core 0: EIS sweep engine  │  │  │
│  │  T/RH (ambient)  │               │  │  AD5941 control + DSP       │  │  │
│  └─────────────────┘               │  └──────────┬───────────────────┘  │  │
│                                     │             │ feature vector       │  │
│  ┌─────────────────┐  SPI           │  ┌──────────▼───────────────────┐  │  │
│  │  microSD Card    │◄─────────────►│  │  Core 1: k-NN classifier    │  │  │
│  │  (library+log)   │               │  │  + UI + BLE + SD logging     │  │  │
│  └─────────────────┘               │  └──────────────────────────────┘  │  │
│                                     └───────────┬────────────────────────┘  │
│  ┌─────────────────┐  GPIO                       │ SPI (4-wire)            │
│  │  3× Buttons      │◄──────────┐                 │                         │
│  │  ID/LIB/MODE     │           │                 ▼                         │
│  └─────────────────┘           │  ┌──────────────────────────┐             │
│                                 │  │    AD5941 AFE             │             │
│  ┌─────────────────┐  GPIO       │  │  (Impedance + AMR + HRT)   │             │
│  │  RGB LED         │◄──────────┤  │  16-bit DAC + PGA + DFT   │             │
│  │  (status)        │           │  └──────────┬──────────────┘             │
│  └─────────────────┘           │             │                             │
│                                 │             │ Analog Mux                  │
│  ┌─────────────────┐  UART      │             ▼                             │
│  │  USB-C (charge  │◄──────────┤  ┌──────────────────────────┐             │
│  │  + debug)       │           │  │  ADG715 8:1 Analog Switch  │             │
│  └─────────────────┘           │  │  (selects working electrode)│            │
│                                 │  └──────────┬──────────────┘             │
│  ┌─────────────────────────────────────────────┘            │               │
│  │  Power: 18650 Li-ion → TP4056 → AP2112 3.3V              │               │
│  │  + ADP7118-3.3V (analog rails) + LP5907-1.8V (AD5941)     │               │
│  └──────────────────────────────────────────────────────────┘               │
│                                               │                              │
│                                  ┌────────────▼─────────────────┐            │
│                                  │   Electrode Probe (dunkable) │            │
│                                  │   ┌──┬──┬──┬──┬──┐            │            │
│                                  │   │Au│Pt│Ag│GC│Cu│  5 metals  │            │
│                                  │   └──┴──┴──┴──┴──┘            │            │
│                                  │   (common Pt counter electrode)           │
│                                  └──────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Hardware Design

### SoC Selection

| Component | Part | Why |
|-----------|------|-----|
| Main MCU | **ESP32-S3-WROOM-1** | Dual-core Xtensa LX7 @ 240 MHz, 512 KB SRAM, 8 MB flash. Core 0 runs real-time EIS sweep; Core 1 runs classification + UI + BLE. $3.00 |
| Analog front-end | **AD5941** (ADI) | High-precision impedance + amperometry AFE with 16-bit DAC, 16-bit ADC, TIA, DFT engine. Purpose-built for electrochemical impedance spectroscopy. $12.00 |
| Analog mux | **ADG715** | 8:1 CMOS analog switch, low on-resistance (2.5 Ω), selects which working electrode is active. $2.50 |
| Atmospheric sensor | **BME280** | Temperature + humidity for ambient compensation (liquid temperature affects impedance). I2C. $2.50 |
| Display | **SSD1306 OLED** 128×64 | I2C, low power, sunlight-readable. $2.00 |
| SD card slot | Standard microSD | SPI, FAT32 — library storage + measurement logging. $0.30 |
| Charger | **TP4056** | Li-ion charge controller, USB-C input. $0.30 |
| LDO (digital) | **AP2112-3.3** | 600 mA, 3.3V for MCU + peripherals. $0.20 |
| LDO (analog) | **ADP7118ARDZ-3.3** | Ultra-low-noise (3.5 µV RMS) 3.3V for AD5941 analog rails. $1.50 |
| LDO (AD5941 core) | **LP5907MFX-1.8** | 250 mA, 1.8V for AD5941 digital core (required by datasheet). $0.80 |
| Electrode probe | Custom 5-metal probe | Gold, platinum, Ag/AgCl, glassy carbon, copper wire electrodes in PEEK housing. $8.00 |

### Electrode Probe Design

The probe is a dunkable wand (~120 mm long, 8 mm diameter) with 5 metal electrodes exposed at the tip:

```
         ┌─────────────────────┐
         │   PEEK body          │
         │   (8mm dia)          │
         │                      │
         │  ┌─┐┌─┐┌─┐┌─┐┌─┐  │
         │  │A││P││A││G││C│  │  ← 5 working electrodes
         │  │u││t││g││C││u│  │     (Ø 1mm, 5mm spacing)
         │  └─┘└─┘└─┘└─┘└─┘  │
         │                      │
         │  Common Pt counter   │  ← Platinum ring (counting electrode)
         │  electrode (ring)     │
         │                      │
         │  Ag/AgCl reference   │  ← Reference electrode (for potential control)
         └─────────────────────┘
```

**Electrode materials and their sensing roles:**

| # | Metal | Diameter | Role | Sensitive to |
|---|-------|----------|------|-------------|
| 1 | Gold (Au) | 1.0 mm | Working electrode 1 | Redox-active species, proteins, heavy metals |
| 2 | Platinum (Pt) | 1.0 mm | Working electrode 2 | Organics, catalysis, dissolved oxygen |
| 3 | Ag/AgCl | 1.0 mm | Working electrode 3 | Chloride, halides, pH shift |
| 4 | Glassy Carbon (GC) | 1.0 mm | Working electrode 4 | Aromatics, broad potential window |
| 5 | Copper (Cu) | 1.0 mm | Working electrode 5 | Sugars, alcohols, organic acids |
| — | Platinum (ring) | 3.0 mm | Counter electrode | Current return path |
| — | Ag/AgCl | 1.0 mm | Reference electrode | Stable potential reference |

The ADG715 mux connects one working electrode at a time to the AD5941's working electrode (WE) input. The counter electrode (Pt ring) and reference electrode (Ag/AgCl) are always connected. A full measurement cycle sweeps all 5 electrodes × 20 frequencies = 100 impedance points in ~12 seconds.

### Pin Assignments (ESP32-S3)

| GPIO | Function | Description |
|------|----------|-------------|
| GPIO0 | I2C SDA | BME280 + SSD1306 OLED |
| GPIO1 | I2C SCL | BME280 + SSD1306 OLED |
| GPIO2 | SPI CS (AD5941) | AD5941 chip select |
| GPIO3 | SPI SCK | AD5941 SPI clock (16 MHz) |
| GPIO4 | SPI MISO | AD5941 SPI MISO |
| GPIO5 | SPI MOSI | AD5941 SPI MOSI |
| GPIO6 | AD5941 IRQ | AD5941 interrupt (measurement complete) |
| GPIO7 | AD5941 RESET | AD5941 hardware reset |
| GPIO8 | MUX EN | ADG715 enable |
| GPIO9 | MUX S0 | ADG715 address bit 0 |
| GPIO10 | MUX S1 | ADG715 address bit 1 |
| GPIO11 | MUX S2 | ADG715 address bit 2 |
| GPIO12 | SD CS | microSD card chip select |
| GPIO13 | SPI2 SCK | microSD SPI clock |
| GPIO14 | SPI2 MOSI | microSD SPI MOSI |
| GPIO15 | SPI2 MISO | microSD SPI MISO |
| GPIO16 | Button ID | Identify / trigger button |
| GPIO17 | Button MODE | Mode cycle button |
| GPIO18 | Button LIB | Library / learn button |
| GPIO19 | LED R | RGB LED red channel |
| GPIO20 | LED G | RGB LED green channel |
| GPIO21 | LED B | RGB LED blue channel |
| GPIO38 | ADC BATT | Battery voltage divider (1/2) |
| GPIO39 | CHRG | TP4056 charge status |
| GPIO40 | USB D- | USB-C data (native USB) |
| GPIO41 | USB D+ | USB-C data (native USB) |
| GPIO42 | Card Detect | microSD card detect switch |

### Power Architecture

```
                    ┌──────────────┐
    USB-C 5V ──────►│  TP4056      │───────┬──────────────────────────────┐
                    │  Charger     │       │                              │
                    │              │  ┌────┴────┐                         │
                    │  CHRG status─┼──│ 18650   │                         │
                    │  to GPIO39   │  │ 3.7V    │                         │
                    └──────────────┘  │ 2600mAh │                         │
                                      └────┬────┘                         │
                                           │                              │
                    ┌──────────────────────┼──────────────────────────────┤
                    │                      │                              │
                    ▼                      ▼                              ▼
            ┌──────────────┐      ┌──────────────┐              ┌──────────────┐
            │ AP2112-3.3   │      │ ADP7118-3.3  │              │ LP5907-1.8   │
            │ (digital)   │      │ (analog AFE) │              │ (AD5941 core)│
            │ 600mA LDO   │      │ low-noise    │              │ 250mA LDO    │
            └──────┬───────┘      └──────┬───────┘              └──────┬───────┘
                   │                     │                             │
                   ▼                     ▼                             ▼
              3.3V DIGITAL           3.3V ANALOG                    1.8V DIGITAL
              ESP32-S3               AD5941 analog rails            AD5941 core
              BME280                 ADG715 mux
              SSD1306
              SD card
              RGB LED
              Buttons

              Current budget:
              ESP32-S3:    ~80 mA (dual-core active)
              AD5941:      ~8 mA (sweep active), ~0.1 mA (idle)
              ADG715:      ~0.001 mA
              BME280:      ~0.3 mA
              OLED:        ~12 mA
              SD card:     ~30 mA (write), ~1 mA (idle)
              ─────────────────────
              Total:       ~130 mA typical during sweep
                           ~25 mA idle (BLE only)
              Battery life: ~20 hours active, ~100 hours idle
```

---

## Firmware

The firmware is written in C using the ESP-IDF framework (v5.1+). It uses both ESP32-S3 cores:

- **Core 0 (PRO_CPU)**: EIS sweep engine — AD5941 control, frequency sweep, impedance DSP, feature extraction
- **Core 1 (APP_CPU)**: Machine learning classifier (k-NN + decision tree), UI (OLED + buttons), SD card logging, BLE/Wi-Fi

### Source files

```
firmware/
├── CMakeLists.txt
├── sdkconfig.h          # Build configuration
├── main.c               # Entry point, dual-core launch, NVS init
├── ad5941.h              # AD5941 AFE driver (SPI)
├── ad5941.c              # EIS sweep, impedance measurement, calibration
├── mux.h                 # ADG715 electrode multiplexer driver
├── mux.c
├── eis.h                 # EIS measurement API
├── eis.c                 # Multi-electrode EIS sweep orchestration
├── features.h            # Feature extraction from impedance spectra
├── features.c            # R_s/R_ct/C_dl extraction, PCA projection
├── classifier.h          # k-NN + decision tree classifier
├── classifier.c          # k-NN inference, library management, confidence
├── library.h             # Reference library (NVS flash storage)
├── library.c             # Store/load/delete reference fingerprints
├── display.h             # SSD1306 OLED driver
├── display.c
├── sd_log.h              # SD card CSV logging
├── sd_log.c
├── ble.h                 # BLE GATT server
├── ble.c
├── bme280.h               # BME280 driver (I2C)
├── bme280.c
├── ui.h                  # Button handling, mode state machine
├── ui.c
└── calibrate.h           # Open/short/KCl standard calibration
    calibrate.c
```

See the [firmware directory](firmware/) for complete source code.

### Key Algorithms

**Multi-electrode EIS sweep:**
```c
// For each working electrode e (0..4):
//   1. Mux select electrode e
//   2. For each frequency f (1 Hz..100 kHz, 20 points):
//      a. AD5941: program sine excitation at frequency f
//      b. AD5941: measure response via DFT engine
//      c. Read |Z| (magnitude) and θ (phase)
//   3. Store impedance spectrum for electrode e
for (int e = 0; e < NUM_ELECTRODES; e++) {
    mux_select(e);
    for (int f = 0; f < NUM_FREQS; f++) {
        ad5941_measure_z(frequencies[f], &z_mag[e][f], &z_phase[e][f]);
    }
}
```

**Equivalent circuit fitting (Randles model per electrode):**
```c
// From the Nyquist plot (Z_imag vs Z_real):
// - High-frequency intercept → R_s (solution resistance)
// - Semi-circle diameter → R_ct (charge-transfer resistance)
// - Semi-circle peak frequency → C_dl = 1 / (2π f_peak × R_ct)
// - Low-frequency 45° line → Warburg coefficient σ
// Simple extraction from impedance values:
R_s[e] = z_mag[e][0];              // highest frequency ≈ R_s
R_ct[e] = z_mag[e][idx_peak] - R_s[e]; // semi-circle diameter
C_dl[e] = 1.0 / (2 * M_PI * freqs[idx_peak] * R_ct[e]);
```

**k-NN classification:**
```c
// Feature vector: 48 features (5 electrodes × R_s, R_ct, C_dl, σ, peak_f
//                            + 23 cross-electrode ratios + PCA projections)
// Compute Euclidean distance to each library entry:
for (int i = 0; i < lib_size; i++) {
    dist[i] = euclidean_distance(features, library[i].features, 48);
}
// Find k=5 nearest, vote on identity:
qsort(dist_indices, lib_size, ...);  // sort by distance
for (int j = 0; j < 5; j++) {
    votes[library[dist_indices[j]].label]++;
}
// Winner = most-voted label; confidence = max_votes / 5 * 100%
```

---

## Bill of Materials

See [hardware/BOM.csv](hardware/BOM.csv) for the full bill of materials.

**Total estimated cost: ~$72** (excluding PCB, enclosure, 18650 battery, and shipping)

---

## Schematic

See the [schematic/](schematic/) directory for KiCad project files.

---

## Documentation

- [Assembly Guide](docs/assembly-guide.md) — PCB assembly, electrode probe construction, calibration
- [API Reference](docs/api-reference.md) — BLE GATT protocol, Wi-Fi endpoints, data formats
- [Library Guide](docs/library-guide.md) — Building the reference library, adding new liquids, calibration protocol
- [Python Helper](scripts/taste_bead.py) — BLE data receiver, library management, visualization

---

## Python Companion

The `scripts/taste_bead.py` script connects to the Taste Bead over BLE, receives impedance spectra and classification results, manages the reference library, and provides a real-time Nyquist plot viewer:

```bash
python3 taste_bead.py --ble --identify          # identify a dipped sample
python3 taste_bead.py --ble --learn "Tap Water"  # add a new reference
python3 taste_bead.py --ble --nyquist            # real-time Nyquist plots
python3 taste_bead.py --ble --monitor --output milk_spoilage.csv  # track changes over time
```

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Frequency range | 1 Hz – 100 kHz (20 log-spaced points) |
| Impedance range | 1 Ω – 10 MΩ |
| Impedance accuracy | ±1% (calibrated), ±3% (uncalibrated) |
| Electrodes | 5 working (Au, Pt, Ag/AgCl, GC, Cu) + Pt counter + Ag/AgCl reference |
| Feature vector | 48 features per measurement |
| Library capacity | 50 reference liquids (NVS flash) |
| Classification | k-NN (k=5) + decision tree pre-filter |
| Classification time | < 200 ms (after sweep) |
| Full measurement cycle | ~12 s (5 electrodes × 20 frequencies) |
| Interface | BLE 5.0, Wi-Fi (softAP), microSD, USB-C |
| Battery | 18650 Li-ion, 2600 mAh |
| Battery life | ~20 hours active, ~100 hours idle |
| Charging | USB-C, ~4 hours full charge |
| Operating temperature | 5 – 45 °C (liquid-dependent) |
| Dimensions | 110 × 55 × 25 mm (body), 120 × 8 mm (probe) |
| Weight | ~120 g (with battery) |
| Cost (BOM) | ~$72 |

---

## License

MIT — build it, sell it, improve it.

---

*Invented as part of the [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) collection.*