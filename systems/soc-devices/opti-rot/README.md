# Opti Rot

**A pocket-sized digital polarimeter that measures the optical rotation of chiral liquids — sugar concentration, honey adulteration, essential-oil authentication, pharmaceutical enantiomeric excess, amino-acid identification, and reaction monitoring — using multi-wavelength polarized light (405/520/589 nm), a microstepping analyzer on a stepper motor, Malus's-law curve fitting, Drude optical-rotatory-dispersion analysis, a 50-compound specific-rotation library, temperature compensation, and BLE/Wi-Fi streaming — bringing $3k–$15k lab polarimeters down to ~$58 and coffee-mug size.**

---

## What It Does

The Opti Rot is a **pocket digital polarimeter** — an analytical instrument that measures the angle through which a chiral substance rotates the plane of linearly polarized light. Many molecules are "handed" (chiral): sugar, amino acids, many pharmaceuticals, and essential oils all rotate polarized light in a characteristic, measurable way. The amount and direction of rotation depends on the molecule, its concentration, the path length, the wavelength, and the temperature. By measuring rotation at multiple wavelengths and fitting the Drude optical-rotatory-dispersion equation, the device can both quantify concentration and fingerprint the identity of a chiral compound.

### Why a pocket polarimeter matters

| Application | How Opti Rot Helps |
|---|---|
| **Sugar content (°Z)** | International Sugar Scale — measure sucrose concentration in sugar juice, syrups, and molasses at harvest and in refining. 1°Z ≈ 0.26 g sucrose / 100 mL |
| **Honey adulteration** | Pure honey has characteristic optical rotation (e.g., clover +Lev, honeydew −). Detect corn-syrup/glucose adulteration — a $1B+ global fraud problem |
| **Essential oil authentication** | Many essential oils (citrus, peppermint, eucalyptus) have well-documented specific rotations. Detect synthetic/diluted oils |
| **Pharmaceutical chiral purity** | Measure enantiomeric excess (ee) of chiral drug substances. Most drugs are chiral; the wrong enantiomer can be toxic (thalidomide). On-line reaction monitoring |
| **Amino acid identification** | All proteinogenic amino acids except glycine are chiral (L-form in biology). Identify and quantify by specific rotation |
| **Starch / polysaccharide** | Starch rotates light; measure gelatinization and hydrolysis progress in food processing |
| **Citrus juice quality** | Brix-acid ratio is critical; polarimetry gives sugar content independent of acidity |
| **Fermentation monitoring** | Track the conversion of chiral substrates (sugars) to products (alcohols, acids) in real time |
| **Olive oil detection** | Detect admixture with cheaper non-chiral oils by optical rotation change |
| **Tea/coffee optical activity** | Polyphenol content affects rotation; quality screening |
| **Tartaric acid (wine)** | Measure tartaric/cream of tartar content in winemaking |
| **Camphor / menthol** | Natural vs. synthetic chiral compounds — different rotations |

### How it works

1. **Light source** — A narrowband LED (default 589 nm, the sodium D-line, which is the standard polarimetry wavelength) is collimated into a parallel beam. Two additional LEDs at 405 nm and 520 nm enable multi-wavelength Drude analysis.

2. **Polarizer** — The collimated beam passes through a linear polarizing film, producing linearly polarized light at a known angle.

3. **Sample** — The polarized light passes through a borosilicate sample tube (100 mm path length, the standard polarimetry tube) containing the liquid under test. Chiral molecules in the liquid rotate the plane of polarization by an angle α proportional to concentration c, path length l, and the specific rotation [α] of the compound: **α = [α] × l × c**.

4. **Analyzer** — A second polarizing film (the "analyzer") is mounted on a stepper motor. The motor rotates the analyzer through 180° while a photodiode measures the transmitted intensity at each angle. According to **Malus's law**, I = I₀ cos²(θ), the intensity is minimum when the analyzer is crossed (perpendicular) to the rotated polarization. By curve-fitting the measured I(θ) around the minimum, the exact null angle is determined with sub-step precision.

5. **Optical rotation computation** — The difference between the null angle measured with the empty tube (reference, θ₀) and with the sample (θ₁) gives the optical rotation: **α = θ₁ − θ₀**.

6. **Concentration calculation** — If the compound is known (from the built-in library), the concentration is computed as: **c = α / ([α] × l)**, with temperature correction applied to [α] using the d[α]/dT coefficient.

7. **Multi-wavelength Drude analysis** — Measuring α at 3 wavelengths (405, 520, 589 nm) and fitting the Drude equation **[α](λ) = K / (λ² − λ₀²)** allows estimation of the absorption wavelength λ₀ near an electronic transition, providing additional compound fingerprinting.

### Operating modes

| Mode | Description |
|------|-------------|
| **Measure** | Insert sample tube → auto-zero (if needed) → rotate analyzer → fit Malus curve → display rotation + concentration |
| **Identify** | Multi-wavelength measurement → Drude fit → match against 50-compound library → display best match + confidence |
| **Monitor** | Continuous measurement at 10 s intervals — track reaction progress or fermentation |
| **Library** | Browse 50-compound specific-rotation library; add custom entries via BLE |
| **Calibrate** | Zero with empty tube; verify with sucrose standard (26 g / 100 mL = +34.6° for 100 mm) |
| **Config** | Set path length, default wavelength, temperature units, BLE/Wi-Fi on/off |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              OPTI ROT                                         │
│                                                                               │
│  ┌─────────────────┐  I2C (400 kHz)  ┌──────────────────────────────────────┐  │
│  │  SSD1306 OLED   │◄─────────────►│                                      │  │
│  │  128×64         │               │         STM32G491RET6                 │  │
│  └─────────────────┘               │   (Cortex-M4F @ 170 MHz + CORDIC)     │  │
│                                     │                                      │  │
│  ┌─────────────────┐  I2C          │  ┌────────────────────────────────┐  │  │
│  │  DS18B20         │◄─────────────►│  │  Malus-law curve fitting       │  │  │
│  │  (sample temp)   │  (1-Wire)     │  │  Drude ORD analysis             │  │  │
│  └─────────────────┘               │  │  Concentration calculation      │  │  │
│                                     │  │  Temperature compensation        │  │  │
│  ┌─────────────────┐  SPI           │  │  Library k-NN matching          │  │  │
│  │  microSD Card    │◄─────────────►│  └──────────┬─────────────────────┘  │  │
│  │  (log+library)   │               │             │ UART @ 1 Mbps           │  │
│  └─────────────────┘               │             ▼                         │  │
│                                     │  ┌──────────────────────────────┐     │  │
│  ┌─────────────────┐  GPIO          │  │  ESP32-C3 (companion)        │     │  │
│  │  3× Buttons      │◄─────────────►│  │  BLE 5.0 + Wi-Fi bridge      │     │  │
│  │  MEAS/MODE/CAL   │               │  └──────────────────────────────┘     │  │
│  └─────────────────┘               └───────────┬────────────────────────────┘  │
│                                     │                                           │
│  ┌─────────────────┐  GPIO                       │ PWM (timers)                │
│  │  RGB LED         │◄─────────────┐              │                             │
│  │  (status)        │              │              ▼                             │
│  └─────────────────┘              │  ┌──────────────────────────────────────┐   │
│                                     │  │  28BYJ-48 Stepper Motor              │   │
│  ┌─────────────────┐  GPIO          │  │  (ULN2003 driver, 4096 steps/rev)   │   │
│  │  USB-C (charge   │◄──────────┐   │  │  rotates analyzer polarizer          │   │
│  │  + UART debug)   │           │   │  └──────────────┬───────────────────┘   │
│  └─────────────────┘           │   │                  │                        │
│                                 │   │                  ▼                        │
│  Power: 18650 → TP4056 ─────────┘   │  ╔══════════════════════════════════════╗ │
│  → AP2112-3.3V (digital)            │  ║        OPTICAL BENCH (see below)     ║ │
│  → LP5907-3.3V (analog, photodiode) │  ╚══════════════════════════════════════╝ │
│  → ADP7118-5.0V (stepper)           │                                         │
│                                     │  ┌──────────────────────────────────┐    │
│                                     │  │  3× LEDs: 405nm / 520nm / 589nm   │    │
│                                     │  │  (selected via DAC intensity ctrl) │    │
│                                     └─►│  + TSL257 photodiode (ADC input)   │    │
│                                        └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                      OPTICAL BENCH (top view)                            │
  │                                                                         │
  │   405nm LED ─┐                                                          │
  │   520nm LED ─┼─► Collimator Lens ─► Polarizer ─► [Sample Tube 100mm]     │
  │   589nm LED ─┘     (aspheric)        (film)       (borosilicate)         │
  │                                                                   │      │
  │                                                         Analyzer ─► Photodiode
  │                                                         (film on     (TSL257)
  │                                                          stepper)        │
  │                                                                   │      │
  │                                                         28BYJ-48    └──────►
  │                                                         stepper
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## Hardware Design

### SoC Selection

| Component | Part | Why |
|-----------|------|-----|
| Main MCU | **STM32G491RET6** | 170 MHz Cortex-M4F with FPU, CORDIC coprocessor (trigonometric for Malus's law fitting), FMAC (filter math accelerator), 3× 12-bit DACs (LED intensity control), 5× 12-bit ADCs (4 Msps for photodiode), 128 KB flash, 32 KB SRAM. $4.50 |
| Companion MCU | **ESP32-C3-MINI-1** | RISC-V @ 160 MHz, BLE 5.0 + Wi-Fi. Handles all wireless connectivity; communicates with STM32 via UART. $2.20 |
| Display | **SSD1306 OLED** 128×64 | I2C, low power, sunlight-readable. Shows rotation angle, concentration, Drude plot. $2.00 |
| Temperature sensor | **DS18B20** | 1-Wire digital temperature, ±0.5°C accuracy. Mounted in sample chamber for temperature compensation. $1.50 |
| Light sensor | **TSL257** | Light-to-voltage converter (photodiode + TIA in one package), 540 nm peak response, linear output. $3.50 |
| LEDs | 405 nm / 520 nm / 589 nm narrowband | 589 nm = sodium D-line (standard polarimetry wavelength); 405 nm + 520 nm for Drude ORD analysis. $2.50 total |
| Stepper motor | **28BYJ-48** | 5V unipolar, 64:1 gearbox → 4096 steps/rev (half-step), 0.088°/step. Rotates analyzer polarizer. $3.00 |
| Motor driver | **ULN2003** | Darlington array, drives 28BYJ-48. $0.50 |
| SD card slot | Standard microSD | SPI, FAT32 — library storage + measurement logging. $0.30 |
| Charger | **TP4056** | Li-ion charge controller, USB-C input. $0.30 |
| LDO (digital) | **AP2112-3.3** | 600 mA, 3.3V for MCU + peripherals. $0.20 |
| LDO (analog) | **LP5907MFX-3.3** | 250 mA, ultra-low-noise (6.5 µV RMS) for TSL257 photodiode supply. $0.80 |
| LDO (stepper) | **ADP7118ARDZ-5.0** | 200 mA, 5.0V low-noise for stepper motor + LEDs. $1.50 |
| Optics | Polarizing film × 2, collimator lens, sample tube | Linear polarizing sheets (Edmund Optics); 25mm aspheric collimator lens; borosilicate sample tube (100mm path, 10mm OD). $12.00 |
| Battery | 18650 Li-ion, 2600 mAh | $3.00 |
| Enclosure | 3D-printed PLA + optical assembly | $2.00 |

### Optical Bench Design

The optical bench is a horizontal light path ~180 mm long, mounted in a 3D-printed enclosure:

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │  LED assembly        Collimator    Polarizer    Sample tube     │
    │  ┌─────────┐         ┌────────┐   ┌──────┐    ┌──────────────┐  │
    │  │405nm    │         │Aspheric│   │Linear│    │ 100mm borosil │  │
    │  │520nm   ─┼────────►│ Lens   ├──►│Polar ├──►│  10mm OD tube  │  │
    │  │589nm    │  25mm   │  f=20mm│   │ film │    │  (removable)  │  │
    │  └─────────┘         └────────┘   └──────┘    └──────┬───────┘  │
    │                                                     │           │
    │                                                     ▼           │
    │                                              ┌──────────┐       │
    │                                              │ Analyzer │       │
    │                                              │ (polar   │       │
    │                                              │  film on │       │
    │                                              │  stepper)│       │
    │                                              └────┬─────┘       │
    │                                                   │             │
    │                                                   ▼             │
    │                                              ┌──────────┐       │
    │                                              │ TSL257   │       │
    │                                              │Photodiode│       │
    │                                              └──────────┘       │
    └─────────────────────────────────────────────────────────────────┘

    LED assembly (detail):
    ┌───────────────────┐
    │ 589nm LED   ────┐ │  ← mounted at 15° to beam axis
    │ 520nm LED   ──┐ │ │  ← 20° offset
    │ 405nm LED   ─┼─┼─┘  ← 25° offset
    │              ▼ ▼    (converging onto collimator via mirror/prism)
    └───────────────────┘
```

### Pin Assignments (STM32G491RET6)

| Pin | Function | Description |
|-----|----------|-------------|
| PA0 | DAC1 OUT | 589nm LED intensity control (PWM via DAC) |
| PA1 | DAC2 OUT | 520nm LED intensity control |
| PA4 | DAC3 OUT | 405nm LED intensity control |
| PA2 | ADC1 IN2 | TSL257 photodiode analog input |
| PA3 | ADC2 IN3 | Battery voltage divider (1/3) |
| PA5 | GPIO OUT | ULN2003 IN1 (stepper coil A) |
| PA6 | GPIO OUT | ULN2003 IN2 (stepper coil B) |
| PA7 | GPIO OUT | ULN2003 IN3 (stepper coil C) |
| PA8 | GPIO OUT | ULN2003 IN4 (stepper coil D) |
| PB0 | I2C1 SCL | SSD1306 OLED |
| PB1 | I2C1 SDA | SSD1306 OLED |
| PB2 | GPIO OUT | RGB LED Red |
| PB3 | GPIO OUT | RGB LED Green |
| PB4 | GPIO OUT | RGB LED Blue |
| PB5 | GPIO IN | Button MEAS (measure trigger) |
| PB6 | GPIO IN | Button MODE (mode cycle) |
| PB7 | GPIO IN | Button CAL (calibrate/zero) |
| PB8 | SPI2 CS | microSD card chip select |
| PB9 | GPIO IN | SD card detect |
| PB10 | SPI2 SCK | microSD SPI clock |
| PB11 | SPI2 MISO | microSD SPI MISO |
| PB12 | SPI2 MOSI | microSD SPI MOSI |
| PB13 | UART2 TX | → ESP32-C3 UART RX (1 Mbps) |
| PB14 | UART2 RX | ← ESP32-C3 UART TX (1 Mbps) |
| PB15 | GPIO OUT | ESP32-C3 enable/reset |
| PC0 | GPIO OUT | DS18B20 1-Wire data line |
| PC4 | GPIO IN | TP4056 charge status |
| PC10 | UART4 TX | USB-C debug UART (optional) |
| PC11 | UART4 RX | USB-C debug UART (optional) |

### Pin Assignments (ESP32-C3-MINI-1)

| Pin | Function | Description |
|-----|----------|-------------|
| GPIO0 | UART0 TX | → STM32 UART2 RX (1 Mbps) |
| GPIO1 | UART0 RX | ← STM32 UART2 TX (1 Mbps) |
| GPIO2 | GPIO IN | STM32 enable/reset (from PB15) |
| GPIO8 | GPIO OUT | BLE status LED (optional) |
| GPIO9 | GPIO IN | Boot button (config) |

### Power Architecture

```
                    ┌──────────────┐
    USB-C 5V ──────►│  TP4056      │───────┬──────────────────────────────────┐
                    │  Charger     │       │                                  │
                    │  CHRG status─┼──► GPIO (STM32 PC4)                    │
                    └──────────────┘  ┌────┴────┐                             │
                                      │ 18650   │                             │
                                      │ 3.7V    │                             │
                                      │ 2600mAh │                             │
                                      └────┬────┘                             │
                                           │                                  │
                    ┌──────────────────────┼──────────────────────────────┐  │
                    │                      │                              │  │
                    ▼                      ▼                              ▼  │
            ┌──────────────┐      ┌──────────────┐              ┌──────────────┐
            │ AP2112-3.3    │      │ LP5907-3.3   │              │ ADP7118-5.0  │
            │ (digital)    │      │ (analog)     │              │ (stepper/LED)│
            │ 600mA LDO    │      │ 250mA LDO    │              │ 200mA LDO    │
            └──────┬───────┘      └──────┬───────┘              └──────┬───────┘
                   │                     │                             │
                   ▼                     ▼                             ▼
              3.3V DIGITAL           3.3V ANALOG                    5.0V POWER
              STM32G491               TSL257 photodiode              28BYJ-48 motor
              SSD1306 OLED            (ultra-low-noise)              3× LEDs
              ESP32-C3                                               ULN2003
              DS18B20
              SD card
              RGB LED
              Buttons

              Current budget:
              STM32G491:   ~35 mA (active DSP)
              ESP32-C3:    ~20 mA (BLE), ~80 mA (Wi-Fi TX)
              TSL257:      ~0.8 mA
              589nm LED:   ~20 mA (during measurement)
              Stepper:     ~250 mA (during rotation), 0 mA (idle, de-energized)
              OLED:        ~12 mA
              SD card:     ~30 mA (write), ~0.1 mA (idle)
              DS18B20:     ~1.5 mA (conversion), ~0.001 mA (idle)
              ─────────────────────
              Total:       ~120 mA idle (measurement ready)
                           ~400 mA during stepper rotation
                           ~140 mA during analysis (stepper off)
              Battery life: ~6 hours continuous measuring
                           ~20 hours intermittent use
                           ~80 hours standby (BLE only)
```

---

## Firmware

The firmware is written in C using the STM32 HAL library (STM32CubeMX G4 framework). The ESP32-C3 companion runs ESP-IDF.

### Dual-processor architecture

**STM32G491RET6 (main):**
- Malus's law curve fitting (CORDIC-assisted trigonometric computation)
- Drude ORD multi-wavelength analysis
- Stepper motor control (half-step sequence, 4096 steps/rev)
- Photodiode ADC sampling at 1 kHz (oversampled for noise reduction)
- DS18B20 temperature reading
- SD card logging + library storage
- OLED display + button UI
- Specific rotation library (50 compounds in flash)
- Concentration calculation with temperature compensation

**ESP32-C3 (companion):**
- BLE 5.0 GATT server (measurement results, library access, commands)
- Wi-Fi softAP (web dashboard, data download)
- UART bridge to STM32 (binary protocol, 1 Mbps)

### Source files

```
firmware/
├── CMakeLists.txt          # STM32 build (arm-none-eabi-gcc)
├── sdkconfig.h             # Build configuration
├── main.c                  # Entry point, system init, main loop
├── stepper.h               # 28BYJ-48 stepper motor driver
├── stepper.c               # Half-step sequence, microstepping, angle positioning
├── photodiode.h            # TSL257 ADC sampling + oversampling
├── photodiode.c
├── polarimeter.h           # Core polarimetry measurement engine
├── polarimeter.c           # Malus curve fitting, auto-zero, rotation computation
├── drude.h                 # Drude ORD multi-wavelength analysis
├── drude.c                 # Nonlinear least-squares fit of [α](λ) = K/(λ²-λ₀²)
├── temperature.h           # DS18B20 1-Wire driver
├── temperature.c
├── library.h               # Specific rotation compound library
├── library.c               # 50-compound table, k-NN matching, custom entries
├── display.h               # SSD1306 OLED driver
├── display.c               # Text, graphs, Drude plot rendering
├── sd_log.h                # SD card CSV logging
├── sd_log.c
├── ble_bridge.h            # UART protocol to ESP32-C3
├── ble_bridge.c            # Binary frame protocol, command dispatch
├── ui.h                    # Button handling, mode state machine
├── ui.c
└── led.h                   # RGB status LED
    led.c
```

### Key Algorithms

**Malus's law curve fitting:**
```c
// Malus's law: I(θ) = I₀ × cos²(θ + α) = (I₀/2) × (1 + cos(2θ + 2α))
// The analyzer rotates through ~180° while sampling the photodiode at each step.
// We sample N points around the expected minimum, then fit:
//   I(θ) = A + B × cos(2θ + φ)
// The minimum occurs at θ_min = (φ + π) / 2 (mod π)
// Using CORDIC for fast cos computation on STM32G4:

// 1. Sample photodiode at 64 angles spanning ±90° around estimated null
for (int i = 0; i < 64; i++) {
    stepper_move_to(estimate_null - 90 + i * 180/63);
    angles[i] = stepper_get_angle();
    intensity[i] = photodiode_oversample(100);  // 100 samples averaged
}

// 2. Fit I = A + B*cos(2θ + φ) using linear least squares on cos(2θ), sin(2θ)
//    I = A + B*cos(φ)*cos(2θ) - B*sin(φ)*sin(2θ)
//    → solve for A, P=B*cos(φ), Q=-B*sin(φ)
//    → φ = atan2(-Q, P), B = sqrt(P² + Q²)
//    → θ_min = (π - φ) / 2 (mod π)

// 3. Optical rotation = θ_min(sample) - θ_min(reference)
double rotation = theta_min_sample - theta_min_reference;
```

**Drude ORD fitting:**
```c
// Drude equation: [α](λ) = K / (λ² - λ₀²)
// Measure rotation at 3 wavelengths (405, 520, 589 nm)
// Linearize: 1/[α] = (λ² - λ₀²)/K = λ²/K - λ₀²/K
// Plot 1/[α] vs λ² → linear: slope = 1/K, intercept = -λ₀²/K
// → K = 1/slope, λ₀ = sqrt(-intercept/slope) = sqrt(-intercept * K)

// With 3 wavelength points, exact fit:
// Solve: [α]ᵢ × (λᵢ² - λ₀²) = K  for i = 1,2,3
// → [α]₁(λ₁² - λ₀²) = [α]₂(λ₂² - λ₀²) = [α]₃(λ₃² - λ₀²) = K
// → λ₀² = ([α]₁λ₁² - [α]₂λ₂²) / ([α]₁ - [α]₂)
// → K = [α]₁ × (λ₁² - λ₀²)
double lambda0_sq = (alpha[0]*lambda[0]*lambda[0] - alpha[1]*lambda[1]*lambda[1])
                  / (alpha[0] - alpha[1]);
double lambda0 = sqrt(lambda0_sq);
double K = alpha[0] * (lambda[0]*lambda[0] - lambda0_sq);
```

**Temperature compensation:**
```c
// Specific rotation is temperature-dependent: [α]_T = [α]_20 × (1 + k × (T - 20))
// where k is the temperature coefficient (typically -0.01 to -0.05 /°C for sugars)
// Correct measured rotation to 20°C:
double alpha_20 = alpha_measured / (1.0 + temp_coeff * (temperature - 20.0));
```

**Concentration from optical rotation:**
```c
// α = [α] × l × c  →  c = α / ([α] × l)
// where:
//   α = measured rotation (degrees)
//   [α] = specific rotation at 20°C, 589nm (degrees·mL/(g·dm))
//   l = path length in dm (100mm = 1 dm)
//   c = concentration in g/mL
double concentration = alpha_corrected / (specific_rotation * path_length_dm);
// Convert to g/100mL (common units):
double g_per_100mL = concentration * 100.0;
```

---

## Bill of Materials

See [hardware/BOM.csv](hardware/BOM.csv) for the full bill of materials.

**Total estimated cost: ~$58** (excluding PCB, enclosure, 18650 battery, and shipping)

---

## Schematic

See the [schematic/](schematic/) directory for KiCad project files.

---

## Documentation

- [Assembly Guide](docs/assembly-guide.md) — PCB assembly, optical bench construction, calibration
- [API Reference](docs/api-reference.md) — BLE GATT protocol, Wi-Fi endpoints, UART binary protocol
- [Compound Library Guide](docs/library-guide.md) — Building the specific-rotation library, adding compounds
- [Python Helper](scripts/opti_rot.py) — BLE data receiver, library management, Drude plot viewer

---

## Python Companion

The `scripts/opti_rot.py` script connects to the Opti Rot over BLE, receives measurement results, manages the compound library, and provides a real-time Drude ORD plot viewer:

```bash
python3 opti_rot.py --ble --measure          # trigger a measurement and display result
python3 opti_rot.py --ble --identify          # multi-wavelength identification
python3 opti_rot.py --ble --drude             # real-time Drude ORD plot
python3 opti_rot.py --ble --monitor --output fermentation.csv  # track reaction over time
python3 opti_rot.py --ble --library           # browse/manage compound library
python3 opti_rot.py --ble --add "Fructose" +91.5 -0.02        # add custom compound
```

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Wavelengths | 589 nm (primary), 405 nm + 520 nm (ORD) |
| Path length | 100 mm (1 dm) standard polarimetry tube |
| Rotation range | ±180° (full range) |
| Rotation resolution | 0.088°/step (stepper), ~0.005° (curve-fit) |
| Measurement accuracy | ±0.02° (calibrated, 589nm) |
| Concentration accuracy | ±0.1 g/100mL (compound-dependent) |
| Temperature range | 5 – 60 °C |
| Temperature accuracy | ±0.5 °C (DS18B20) |
| Compound library | 50 reference compounds (flash), expandable via BLE |
| Drude analysis | K and λ₀ from 3-wavelength fit |
| Measurement time | ~15 s (single wavelength), ~45 s (3-wavelength) |
| Interface | BLE 5.0 (via ESP32-C3), Wi-Fi softAP, microSD, USB-C |
| Battery | 18650 Li-ion, 2600 mAh |
| Battery life | ~6 hours continuous, ~80 hours standby |
| Charging | USB-C, ~4 hours full charge |
| Dimensions | 160 × 65 × 35 mm (body) |
| Weight | ~180 g (with battery) |
| Cost (BOM) | ~$58 |

---

## Comparison to Commercial Polarimeters

| Feature | Opti Rot | Rudolph Autopol IV | Schmidt+Haensch Polartronic |
|----------|----------|--------------------|-----------------------------|
| Price | ~$58 | ~$15,000 | ~$8,000 |
| Size | 160×65×35 mm | 510×230×330 mm | 400×200×350 mm |
| Wavelengths | 3 (405/520/589 nm) | 1–4 (filter-based) | 1 (589 nm) |
| Resolution | 0.005° (curve-fit) | 0.001° | 0.01° |
| Accuracy | ±0.02° | ±0.002° | ±0.01° |
| Multi-wavelength ORD | ✓ (Drude fit) | ✗ (separate filters) | ✗ |
| On-device compound library | 50 compounds | ✗ | ✗ |
| BLE/Wi-Fi | ✓ | ✗ | ✗ (USB only) |
| Battery | 18650, 6 hours | Mains only | Mains only |
| Temperature compensation | ✓ (DS18B20) | ✓ (Peltier) | ✗ |

The Opti Rot trades a small amount of absolute precision (0.02° vs. 0.002°) for 250× lower cost, pocket size, multi-wavelength capability, and battery operation — making polarimetry accessible for field use, education, and small labs.

---

## License

MIT — build it, sell it, improve it.

---

*Invented as part of the [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) collection.*