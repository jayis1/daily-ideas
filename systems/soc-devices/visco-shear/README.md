# Visco Shear — Pocket Rotational Rheometer & Viscometer

> **Bringing $5k–$30k benchtop rheometers (Anton Paar MCR, TA Discovery HR, Brookfield DV3T, Malvern Kinexus) down to ~$67 and pocket size.**

Visco Shear is a pocket-sized instrument that measures the **dynamic viscosity (η)**, **yield stress (σ_y)**, **storage/loss moduli (G′/G″)**, and **thixotropy** of liquids, pastes, gels, inks, foods, slurries, and biological fluids using a **controlled-rate rotational rheometry** method.

A precision NEMA8 stepper motor drives an interchangeable rotating spindle (bob) immersed in a ~2 mL sample cup. A novel **magnetically-coupled torsion spring + Hall-effect angular-displacement sensor** converts the viscous drag torque into a digital reading with ~0.05 µN·m resolution — no expensive air bearings or torque transducers required. By sweeping the rotation rate from 0.01 to 100 rpm, Visco Shear builds a full flow curve (shear stress vs. shear rate), fits it to standard rheological models (Newtonian, Power-Law, Bingham, Herschel–Bulkley, Casson), and computes viscoelastic parameters via oscillatory mode (small-angle sinusoidal oscillation with I/Q demodulation for G′/G″).

---

## Why rotational rheometry?

Rheology — the study of how materials flow and deform — governs product quality across nearly every industry:

- **Food & beverage** — sauce mouthfeel, yogurt gel strength, chocolate yield stress, dough consistency, beverage texture
- **Pharmaceuticals** — syrup viscosity, gel rheology, biotherapeutic protein aggregation, topical cream spreadability
- **Paints, inks & coatings** — leveling, sag resistance, brushability, pigment suspension
- **Cosmetics** — lotion texture, shampoo flow, mascara thixotropy
- **Petroleum** — drilling mud yield stress, crude oil viscosity, pipeline transport modeling
- **Adhesives & sealants** — green strength, cure monitoring, application rheology
- **Ceramics & slurries** — slip castability, particle suspension, binder rheology
- **Biomedical** — blood plasma viscosity, synovial fluid, mucus, saliva diagnostics
- **3D printing** — resin viscosity, bioink printability, filament melt flow
- **Battery & energy** — electrode slurry coating rheology, electrolyte viscosity
- **Education** — undergraduate rheology labs, material science teaching

Rotational rheometry is the **gold-standard method** for non-Newtonian fluids — it maps the full flow curve across a wide shear-rate range and distinguishes shear-thinning, shear-thickening, yield-stress, and thixotropic behavior that simple capillary or falling-ball viscometers cannot.

---

## Highlights

| Feature | Detail |
|---|---|
| Viscosity range | 0.5–200,000 mPa·s (6 decades via 4 spindles + 2 cups) |
| Viscosity accuracy | ±3% typical (after calibration), ±5% worst-case |
| Viscosity resolution | 0.01 mPa·s (low-viscosity range) |
| Shear rate range | 0.001–1000 s⁻¹ (spindle + cup geometry dependent) |
| Torque range | 0.05 µN·m – 50 mN·m (spring + Hall sensor) |
| Torque resolution | 0.05 µN·m (14-bit ADC + oversampling) |
| Rotation speed | 0.01–100 rpm (microstepping, 0.01 rpm resolution) |
| Oscillatory mode | 0.01–10 Hz, 0.001–10 rad amplitude (G′/G″ measurement) |
| Temperature | −10 to +80 °C (Peltier-controlled cup, ±0.1 °C) |
| Sample volume | 0.5–2.0 mL (geometry dependent) |
| Rheological models | Newtonian, Power-Law (Ostwald), Bingham, Herschel–Bulkley, Casson, Cross, Carreau |
| Oscillatory analysis | G′, G″, tan δ, complex viscosity |η*|, phase angle δ |
| Thixotropy | Hysteresis loop area, structural breakdown/recovery time |
| Spindle geometries | 4 interchangeable: coaxial cylinder, cone-plate, vane, T-bar |
| Display | 1.3" OLED (SH1106, 128×64) — live flow curve + model fit |
| Logging | MicroSD (FAT32) CSV + binary; BLE + Wi-Fi live streaming |
| Power | 18650 (3.7V, 3500 mAh) → 3.3V buck-boost; ~12 h battery or USB-C |
| Size | ~Ø32 × 165 mm (pen-sized) with spindle |
| BOM cost | ~$67 (see `hardware/BOM.csv`) |

---

## SoC Architecture

```
                ┌──────────────────────────────────────┐
                │   RP2040                              │
                │   dual-core Cortex-M0+ 133 MHz        │
  ┌─────────────│   264 KB SRAM + 2 MB QSPI flash       │
  │  PIO stepper │   Core 0: motor control + torque    │
  │  microstep   │   Core 1: rheology DSP + model fit  │──────────────┐
  │  drive       │   • stepper ramp generator (PIO)    │   ESP32-C3   │
  │              │   • Hall ADC sampling at 2 kHz      │   Wi-Fi/BLE  │
  └─────────────┤   • torque → viscosity computation  │   relay +    │
                │   • oscillatory I/Q demodulation     │   CSV web    │
                │   • model fitting (Levenberg-Marq.)  │   download   │
                └──────────┬───────────────────────────┘──────────────┘
                           │ SPI / I²C / GPIO / PWM / PIO
            ┌──────────────┼───────────────────────────────┐
            ▼              ▼                               ▼
  ┌────────────────┐ ┌───────────────┐          ┌──────────────────┐
  │ ADS1115        │ │ TMC2209       │          │ SH1106 OLED      │
  │ 16-bit ADC     │ │ stepper drv   │          │ 128×64 I2C       │
  │ I2C @ 2 kHz    │ │ 1/256 µstep   │          └──────────────────┘
  │ Hall torque    │ │ NEMA8 motor   │
  │ + Peltier temp │ └───────────────┘
  └────────────────┘
```

- **RP2040** — Dual-core ARM Cortex-M0+ at 133 MHz with 264 KB SRAM and external 2 MB QSPI flash. Core 0 runs the stepper ramp generator (via PIO for jitter-free microstep pulses), Hall-sensor ADC sampling, and Peltier PID. Core 1 runs the rheology DSP: torque-to-viscosity conversion, oscillatory I/Q demodulation, flow-curve model fitting (Levenberg-Marquardt), and thixotropy analysis.
- **ESP32-C3** — Companion MCU providing BLE 5.0 + Wi-Fi 2.4 GHz for live streaming, remote control, and CSV/web download. Communicates with the RP2040 via UART at 1 Mbaud.
- **ADS1115** — 16-bit delta-sigma ADC (TI) with I²C interface and programmable gain (PGA 2/3 = ±0.256 V to ±6.144 V). Samples the DRV5053 Hall sensor output at up to 860 SPS (boosted to ~2 kHz via continuous-conversion + software interpolation). Also reads the Peltier NTC thermistor.
- **TMC2209** — Trinamic stepper driver with 1/256 microstepping (StealthChop2) for ultra-smooth rotation at sub-rpm speeds. Drives the NEMA8 bipolar stepper that rotates the spindle via a magnetic coupling through the cup wall.
- **DRV5053** — Texas Instruments linear Hall-effect sensor (±50 mT range, 25 mV/mT sensitivity, analog output). Measures the angular deflection of the torsion-spring-coupled spindle housing — the deflection is proportional to viscous drag torque.

---

## Block Diagram

```
 ┌──────────┐    ┌─────────────┐    ┌───────────────────────────┐    ┌──────────────┐
 │ 18650    │───►│ TPS63020    │───►│ RP2040                    │───►│ SH1106 OLED  │
 │ 3500mAh  │    │ buck-boost  │    │  main SoC (Core 0 + 1)    │    │ 1.3" 128×64  │
 │ 3.7V     │    │ 3.3V/2A     │    │                           │    └──────────────┘
 └──────────┘    └─────────────┘    └──────────┬────────────────┘
       │                                      │ SPI / I2C / PIO
       │                            ┌─────────┴──────────────┐
       │                            ▼                        ▼
       │                   ┌──────────────┐        ┌──────────────────┐
       │                   │ ADS1115      │        │ TMC2209          │
       │                   │ 16-bit ADC   │        │ stepper driver   │
       │                   │ I2C          │        │ 1/256 microstep  │
       │                   └──────┬───────┘        └────────┬─────────┘
       │                          │ analog                    │ A/B
       │                          ▼                           ▼
       │                   ┌──────────────┐        ┌──────────────────┐
       │                   │ DRV5053      │        │ NEMA8 stepper    │
       │                   │ Hall sensor  │        │ 20mm 0.28A       │
       │                   │ (torque arm) │        └────────┬─────────┘
       │                   └──────────────┘                 │ magnetic
       │                                                     │ coupling
       │                                    ┌────────────────┘
       │                                    ▼
       │              ┌──────────────────────────────────────────┐
       │              │  SAMPLE CHAMBER                           │
       │              │  ┌──────────────────────────────────────┐ │
       │              │  │ Torsion spring (beryllium copper)    │ │
       │              │  │   ↕ angular deflection → torque      │ │
       │              │  │ Spindle (bob): CC / CP / vane / T-bar│ │
       │              │  │ Sample cup (0.5–2 mL)                │ │
       │              │  │ Peltier TEC1-12706 temp control      │ │
       │              │  │ NTC 10kΩ thermistor feedback         │ │
       │              │  └──────────────────────────────────────┘ │
       │              └──────────────────────────────────────────┘
       │
       ├─► USB-C 5V charge
       │
       │    ┌────────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────────┐
       └───►│ MicroSD    │    │ Tactile    │    │ DRV8833      │    │ Peltier      │
            │ FAT32 log  │    │ buttons×3  │    │ H-bridge     │────│ TEC1-12706   │
            │ SPI        │    │ GPIO       │    │ (Peltier)    │    │ heat/cool    │
            └────────────┘    └────────────┘    └──────────────┘    └──────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ ESP32-C3         │
                          │ BLE 5.0 + Wi-Fi  │
                          │ UART ← RP2040    │
                          └──────────────────┘
```

---

## Pin Assignments (RP2040)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| GPIO0 | STEP | Output | TMC2209 step pulses (PIO-driven) |
| GPIO1 | DIR | Output | TMC2209 rotation direction |
| GPIO2 | TMC_EN | Output | TMC2209 enable (active low) |
| GPIO3 | TMC_UART | I/O | TMC2209 UART config (optional) |
| GPIO4 | I2C_SCL | Output | ADS1115 + OLED (shared I²C bus) |
| GPIO5 | I2C_SDA | I/O | ADS1115 + OLED (shared I²C bus) |
| GPIO6 | HALL_VREF | Output (ADC) | DRV5053 zero-torque reference ADC channel |
| GPIO7 | PELTIER_PWM | Output (PWM) | DRV8833 A-IN1 (Peltier heating/cooling) |
| GPIO8 | PELTIER_DIR | Output | DRV8833 A-IN2 (Peltier polarity) |
| GPIO9 | PELTIER_EN | Output | DRV8833 EN (Peltier on/off) |
| GPIO10 | SD_CS | Output | MicroSD SPI chip select |
| GPIO11 | SPI_SCK | Output | Shared SPI (SD card) |
| GPIO12 | SPI_MISO | Input | Shared SPI (SD card) |
| GPIO13 | SPI_MOSI | Output | Shared SPI (SD card) |
| GPIO14 | BUTTON_START | Input | Start measurement (active low) |
| GPIO15 | BUTTON_MODE | Input | Cycle geometry/model (active low) |
| GPIO16 | BUTTON_MENU | Input | Menu/select (active low) |
| GPIO17 | BUZZER | Output (PWM) | Audible feedback |
| GPIO18 | UART_TX | Output | RP2040 → ESP32-C3 UART (1 Mbaud) |
| GPIO19 | UART_RX | Input | ESP32-C3 → RP2040 UART (1 Mbaud) |
| GPIO20 | STATUS_LED | Output | White status LED |
| GPIO21 | SPINDLE_DETECT | Input (ADC) | Spindle ID resistor (ADC divider) |
| GPIO22 | FAULT_TMC | Input | TMC2209 diagnostic (open/short) |
| GPIO23 | LED_B | Output | Onboard RP2040 LED (debug) |
| GPIO24 | LED_G | Output | Onboard RP2040 LED (debug) |
| GPIO25 | LED_R | Output | Onboard RP2040 LED (debug) |
| GPIO26 | ADC_HALL | Input (ADC0) | DRV5053 torque signal (primary) |
| GPIO27 | ADC_NTC | Input (ADC1) | Peltier NTC thermistor |
| GPIO28 | ADC_VBAT | Input (ADC2) | Battery voltage monitor |
| GPIO29 | ADC_TEMP | Input (ADC3) | RP2040 internal temperature (diode) |

### ESP32-C3 Pin Assignments

| Pin | Function | Notes |
|-----|----------|-------|
| GPIO2 | UART_RX | From RP2040 GPIO18 (TX) |
| GPIO3 | UART_TX | To RP2040 GPIO19 (RX) |
| GPIO5 | BLE/Wi-Fi status LED | Blue LED |
| GPIO8 | USB_D- | USB-C data (firmware flashing) |
| GPIO9 | USB_D+ | USB-C data |

---

## Torque Sensor Design

The key innovation in Visco Shear is a **low-cost, high-resolution torque sensor** that replaces the expensive air-bearing torque transducers found in lab rheometers:

### Magnetic-Coupled Torsion Spring + Hall Sensor

```
      ┌─────────────────────────────────────┐
      │         NEMA8 STEPPER MOTOR          │
      │              (fixed)                 │
      └──────────────┬──────────────────────┘
                     │ shaft + rotor magnet (N42 disc)
                     ▼
      ═══════════════════════════════════════  ← cup wall (non-magnetic, 0.5mm PEEK)
                     │
         ┌───────────┴───────────┐
         │   stator magnet +     │     ← magnetic coupling transmits torque
         │   torsion spring       │       through the sealed cup wall
         │   (beryllium copper)   │
         │   ↕ angular deflection │
         │   proportional to τ    │
         └───────────┬───────────┘
                     │
                     ▼
              ┌──────────────┐
              │  SPINDLE     │     ← rotates in sample fluid
              │  (bob)       │
              │  CC / CP /   │
              │  vane / T-bar│
              └──────────────┘
                     │
      ┌──────────────┴──────────────┐
      │  DRV5053 Hall sensor        │     ← measures angular deflection
      │  (mounted on fixed frame,   │       of torsion arm relative to
      │   sensing magnet on arm)    │       motor shaft
      └─────────────────────────────┘
```

### Principle of Operation

1. **Magnetic coupling** — A N42 NdFeB disc magnet on the motor shaft couples magnetically through a 0.5 mm PEEK cup wall to a matching magnet on the torsion-spring assembly. This transmits torque without a physical shaft penetration — eliminating seals, bearings in the fluid, and contamination.

2. **Torsion spring** — A precision beryllium copper torsion spring (spring constant k_τ ≈ 0.5 mN·m/rad for the standard spindle) converts the viscous drag torque into an angular deflection θ = τ / k_τ.

3. **Hall sensor readout** — A small bias magnet on the torsion arm moves past a DRV5053 linear Hall sensor. The sensor output voltage is linearly proportional to the arm's angular position: V_Hall = V_0 + S_H · θ, where S_H ≈ 25 mV/mT and the magnet geometry gives ~100 mT/rad angular sensitivity. The ADS1115 16-bit ADC with PGA gain 2/3 (±6.144 V, 187.5 µV LSB) resolves ~0.01° angular deflection → ~5 µN·m torque.

4. **Differential measurement** — A second DRV5053 on the motor shaft (zero-torque reference) is subtracted to cancel temperature drift and common-mode magnetic fields. The differential signal is the pure torque reading.

5. **Auto-zero** — Before each measurement, the motor is stopped and the zero-torque Hall reading is recorded. This eliminates static offset errors from mounting tolerance and remanent magnetization.

### Torque → Viscosity

For a **coaxial cylinder** geometry (inner bob radius R_i, outer cup radius R_o, immersed length L):

```
τ = 4π · η · Ω · R_i² · R_o² · L / (R_o² - R_i²)
```

where Ω is the angular velocity (rad/s) and τ is the measured torque. Solving for viscosity:

```
η = τ · (R_o² - R_i²) / (4π · Ω · R_i² · R_o² · L)
```

The shear rate at the bob surface is:

```
γ̇ = Ω · 2·R_o² / (R_o² - R_i²)
```

For **cone-plate** geometry (cone angle α, radius R):

```
τ = (2/3) · π · η · Ω · R³ / α
γ̇ = Ω / α
```

---

## Spindle Geometries

Four interchangeable spindles connect via a quick-change magnetic coupling:

### 1. Coaxial Cylinder (CC-13) — general purpose
- **Bob**: Ø13 mm × 20 mm, stainless 316L
- **Cup**: Ø14.5 mm × 25 mm (gap = 0.75 mm)
- **Volume**: 2.0 mL
- **Shear rate range**: 0.1–1000 s⁻¹ (at 0.1–100 rpm)
- **Viscosity range**: 1–10,000 mPa·s
- **Standard**: ISO 3219, DIN 53019

### 2. Cone-Plate (CP-25) — high shear, small volume
- **Cone**: Ø25 mm, 1° cone angle, truncated tip (50 µm gap)
- **Plate**: flat stainless, Peltier-controlled
- **Volume**: 0.05 mL
- **Shear rate range**: 1–10,000 s⁻¹
- **Viscosity range**: 0.5–5,000 mPa·s
- **Standard**: ISO 3219 cone-plate

### 3. Vane (VN-16) — yield stress, pastes, gels
- **Vane**: 4-blade, Ø16 mm × 16 mm, 316L
- **Cup**: Ø22 mm × 30 mm
- **Volume**: 3.0 mL
- **Use**: Direct yield stress measurement (no wall slip), pastes, slurries
- **Method**: Vane method (Barnes & Nguyen, 2001)

### 4. T-Bar (TB-3) — very high viscosity
- **Bar**: Ø3 mm cross-bar on shaft
- **Use**: Rotating in a beaker of arbitrary size
- **Viscosity range**: 1,000–200,000 mPa·s
- **Standard**: Brookfield-type T-bar with helipath

### Spindle ID
Each spindle has an ID resistor in the magnetic coupling (0Ω = CC, 10kΩ = CP, 22kΩ = vane, 47kΩ = T-bar), read via GPIO21 ADC divider. Firmware auto-selects geometry constants and shear-rate computation.

---

## Measurement Theory

### Controlled-Rate (CR) Mode — Flow Curve

The stepper motor rotates at a programmed series of angular velocities Ω_i. At each speed, the steady-state torque τ_i is recorded. The flow curve (τ vs. γ̇) is constructed and fit to rheological models:

**Newtonian**: τ = η · γ̇ (constant viscosity, linear)

**Power-Law (Ostwald–de Waele)**: τ = K · γ̇^n
- n < 1: shear-thinning (pseudoplastic)
- n > 1: shear-thickening (dilatant)
- n = 1: Newtonian (K = η)

**Bingham plastic**: τ = τ_B + η_p · γ̇ (yield stress + linear)

**Herschel–Bulkley**: τ = τ_HB + K · γ̇^n (general yield + power-law)

**Casson**: √τ = √τ_C + √(η_C · γ̇) (paints, inks, chocolate)

**Cross**: η = η_∞ + (η_0 − η_∞) / (1 + (λ·γ̇)^m) (full shear-thinning curve)

**Carreau**: η = η_∞ + (η_0 − η_∞) / (1 + (λ·γ̇)^2)^(n/2) (polymer solutions)

Fitting is via **Levenberg–Marquardt** nonlinear least-squares (running on RP2040 Core 1). The best-fit model (lowest AIC) is reported.

### Controlled-Stress (CS) Mode — Yield Stress

The torque is ramped linearly from 0 to a programmed maximum while monitoring angular velocity. The yield stress σ_y is detected as the torque at which rotation begins (first non-zero Ω). Methods:

- **Stress ramp** — linear torque ramp, detect onset of flow
- **Stress sweep** — stepwise torque, log-spaced; detect Ω > threshold
- **Vane method** — peak torque at startup = yield stress (σ_y = τ_peak / (2πR³H · geometry_factor))

### Oscillatory Mode — Viscoelasticity (G′/G″)

The spindle oscillates sinusoidally at angular displacement γ(t) = γ_0 · sin(ω·t). The torque response τ(t) = γ_0 · [G′ · sin(ω·t) + G″ · cos(ω·t)] is decomposed by **synchronous I/Q demodulation**:

```
I = (2/T) ∫₀^T τ(t) · sin(ω·t) dt   →  G′ = I / γ_0
Q = (2/T) ∫₀^T τ(t) · cos(ω·t) dt   →  G″ = Q / γ_0
tan δ = G″ / G′
|η*| = √(G′² + G″²) / ω
```

- G′ > G″: gel/solid-like behavior
- G″ > G′: liquid-like behavior
- Crossover (G′ = G″): gel point / sol-gel transition

Oscillation is generated by the PIO stepper driver as a sinusoidal step-rate pattern at 0.01–10 Hz, 0.001–10 rad amplitude.

### Thixotropy

**Hysteresis loop** — ramp shear rate up then down; the loop area is the thixotropic energy (energy per unit volume dissipated in structural breakdown).

**Step-shear recovery** — apply high shear (break structure), then step to low shear and monitor viscosity recovery vs. time. Fit to exponential recovery model:

```
η(t) = η_∞ + (η_0 − η_∞) · (1 − exp(−t/τ_r))
```

---

## Temperature Control

A **TEC1-12706 Peltier module** (40 mm × 40 mm) is bonded to the sample cup base, providing:

- **Heating**: RT to +80 °C (Peltier hot side)
- **Cooling**: RT to −10 °C (Peltier cold side, with heat sink + fan)
- **Control**: PID loop at 1 Hz, NTC 10kΩ thermistor feedback, ±0.1 °C stability
- **Driver**: DRV8833 H-bridge for bidirectional current (heat/cool), PWM at 20 kHz

Temperature-dependent viscosity sweeps are automated: the user sets a temperature profile (e.g., 25→60→25 °C at 1 °C/min) and Visco Shear measures viscosity at each setpoint, producing an Arrhenius plot:

```
ln(η) = ln(A) + E_a / (R · T)
```

where E_a is the activation energy and T is absolute temperature.

---

## Measurement Sequence

1. **Idle**: monitor sample temperature, display spindle type and current temperature
2. **Equilibration**: wait for target temperature (if set), stability ±0.1 °C for 5 s
3. **Auto-zero**: stop motor, record Hall sensor zero-torque baseline (64-sample average)
4. **Flow curve** (CR mode):
   - Ramp through N shear rates (log-spaced, e.g., 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000 s⁻¹)
   - At each rate: accelerate to target Ω, wait for steady state (torque drift < 1% over 3 s), average 64 torque samples
   - Record (Ω_i, τ_i, γ̇_i, η_i)
5. **Model fitting**: fit all 7 models, select best by AIC, report parameters
6. **Oscillatory** (if selected):
   - Apply sinusoidal oscillation at 5 frequencies (log-spaced, 0.1–10 Hz)
   - I/Q demodulate torque → G′, G″, tan δ, |η*|
7. **Thixotropy** (if selected):
   - Up-ramp + down-ramp, compute hysteresis loop area
   - Step-shear recovery test
8. **Display + log**: show flow curve + model fit on OLED; write CSV to SD; BLE notify

---

## Firmware

The firmware is built with the **Pico SDK** (C) and runs on the RP2040. The ESP32-C3 companion runs ESP-IDF.

### Source layout (RP2040)

```
firmware/
├── CMakeLists.txt          # Pico SDK project (RP2040)
├── sdkconfig               # Build defaults
├── main.c                  # Main application + state machine
├── stepper.c / .h          # PIO-driven microstep ramp generator
├── torque.c / .h           # ADS1115 + DRV5053 torque acquisition
├── rheology.c / .h         # Viscosity, G′/G″, model fitting (LM)
├── temperature.c / .h      # Peltier PID + NTC readout
├── spindle.c / .h          # Spindle ID + geometry constants
├── oled_display.c / .h     # SH1106 OLED UI
├── sd_logger.c / .h        # MicroSD CSV + binary logging
├── ble_uart.c / .h         # UART bridge to ESP32-C3
├── database.c / .h         # Reference fluid library
└── buttons.c / .h          # Debounced button input
```

### Source layout (ESP32-C3)

```
firmware/esp32c3/
├── CMakeLists.txt          # ESP-IDF project
├── main/
│   ├── main.c              # UART relay + BLE/Wi-Fi
│   ├── ble_stream.c / .h   # BLE GATT streaming
│   └── wifi_web.c / .h     # Wi-Fi AP web UI + CSV download
```

### State machine

```
  ┌──────┐  button    ┌──────────┐  temp OK   ┌──────────┐  sweep
  │ IDLE │──────────►│  EQUIB   │───────────►│ FLOW     │ done
  │      │           │ (temp)   │            │ (CR mode)│
  │      │◄──────────│          │   timeout  └────┬─────┘
  │      │  cancel   └──────────┘                 │
  │      │                                         ▼
  │      │          ┌──────────┐   done     ┌──────────┐
  │      │◄─────────│  RESULT  │◄──────────│ OSCILL   │
  │      │  button   │ (display)│           │ (G'/G'') │
  └──────┘           │  + log   │           └────┬─────┘
                     └──────────┘                │
                                  ┌──────────────┘
                                  ▼
                          ┌──────────┐
                          │ THIXO    │ (optional)
                          │ (hyster) │
                          └────┬─────┘
                               │
                               ▼
                          ┌──────────┐
                          │  RESULT  │
                          └──────────┘
```

### Building (RP2040)

```bash
# Requires Pico SDK v1.5+ with PICO_SDK_PATH set
cd firmware
mkdir build && cd build
cmake ..
make -j4
# Flash via USB:
openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg \
  -c "adapter speed 5000; program glyph_press.elf verify reset exit"
# Or: picotool load visco-shear.uf2
```

### Building (ESP32-C3)

```bash
cd firmware/esp32c3
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB1 flash
```

---

## BLE Interface

| UUID | Type | Description |
|------|------|-------------|
| 0xA101 | Service | Visco Shear Service |
| 0xA102 | Notify | Torque data stream (6 bytes: ts_u16 + torque_s16 + omega_s16) |
| 0xA103 | Read/Notify | Measurement result (η + model params + G′/G″) |
| 0xA104 | Write | Command (start/stop/set geometry/set temp) |
| 0xA105 | Read | Device info (firmware version, spindle type, calibration date) |

---

## SD Card Log Format

Each measurement produces a CSV file `VS_YYYYMMDD_HHMMSS.csv`:

```csv
# Visco Shear measurement log
# Date: 2026-07-31T10:15:30Z
# Spindle: CC-13 (coaxial cylinder)
# Sample: honey_test
# Temperature: 25.0 C
# Mode: flow_curve
# Best model: Herschel-Bulkley (tau_HB=2.34 Pa, K=0.89 Pa.s^n, n=0.62)
# Columns: step, omega_rpm, shear_rate_1_s, torque_uNm, viscosity_mPa_s
1,0.100,0.067,45.2,674.3
2,0.300,0.201,89.7,446.2
3,1.000,0.670,156.3,233.3
...
9,100.0,67.0,892.1,133.2
# END
```

Oscillatory results append:

```csv
# Oscillatory: freq_Hz, G_prime_Pa, G_double_prime_Pa, tan_delta, eta_complex_Pa_s
0.100,12.5,3.2,0.256,128.3
0.316,11.8,4.1,0.347,123.1
1.000,10.2,6.8,0.667,122.5
3.162,7.5,9.2,1.227,117.8
10.00,3.1,11.5,3.710,118.2
# G' < G'' crossover at: 2.1 Hz (liquid-like above)
# END
```

---

## Reference Fluid Library

The firmware includes a 30-entry flash library of reference fluids for calibration verification and teaching:

| Fluid | η (mPa·s) @ 25°C | Type | Notes |
|-------|------------------|------|-------|
| Water | 0.890 | Newtonian | Primary standard |
| Glycerin (99%) | 1412 | Newtonian | High-viscosity standard |
| Sucrose 20% | 1.94 | Newtonian | |
| Sucrose 60% | 56.5 | Newtonian | |
| Mineral oil (light) | 25 | Newtonian | |
| Mineral oil (heavy) | 200 | Newtonian | |
| Silicone oil 100 cSt | 96 | Newtonian | NIST-traceable |
| Silicone oil 1000 cSt | 970 | Newtonian | NIST-traceable |
| Honey (raw) | ~10,000 | Shear-thinning | Variable |
| Ketchup | ~50,000 | Herschel–Bulkley | Yield stress ~15 Pa |
| Mayonnaise | ~20,000 | Bingham | Yield stress ~85 Pa |
| Yogurt (set) | ~8,000 | Herschel–Bulkley | |
| Toothpaste | ~100,000 | Bingham | Yield ~200 Pa |
| Paint (latex) | ~500 | Shear-thinning | |
| Blood (plasma) | 1.2 | Newtonian | |
| Blood (whole) | 4.5 | Shear-thinning | Casson model |
| Motor oil 5W-30 | 60 | Newtonian | |
| Motor oil 20W-50 | 200 | Newtonian | |
| Drilling mud ( Bentonite) | ~15,000 | Herschel–Bulkley | |
| Corn syrup | 1,380 | Newtonian | |
| Molasses | 3,000 | Newtonian | |
| Chocolate (melted) | ~2,500 | Casson | Yield ~20 Pa |
| Peanut butter | ~250,000 | Bingham | |
| Shampoo | ~3,000 | Shear-thinning | |
| Nail polish | ~800 | Thixotropic | |
| Resin (epoxy uncured) | 12,000 | Newtonian | |
| Sodium alginate 2% | ~300 | Shear-thinning | |
| Xanthan gum 0.5% | ~800 | Shear-thinning | Strong power-law |
| Polyacrylamide 1% | ~5,000 | Shear-thinning | |
| Custard (cornstarch 40%) | ~10,000 | Shear-thickening | n > 1 |

---

## Calibration

### Single-point calibration (silicone oil)
Silicone oil (100 cSt, NIST-traceable, η = 96 mPa·s at 25 °C):

1. Install CC-13 spindle, add 2.0 mL silicone oil
2. Set temperature to 25 °C, wait for equilibrium
3. Run measurement at 10 rpm → obtain η_measured
4. Calibration factor: **CF = 96 / η_measured**
5. Store CF in flash; applied to all future measurements

### Two-point calibration (water + glycerin)
- Water: η = 0.890 mPa·s (low-viscosity point)
- Glycerin: η = 1412 mPa·s (high-viscosity point)
- Fit correction: η_corrected = a · η_measured + b
- Extends accuracy across full range

### Torque sensor zero
- Run before each session: stop motor, record Hall baseline
- Compensates for temperature drift and mounting offset

### Spindle calibration
- Each spindle's effective spring constant k_τ is factory-calibrated by hanging known weights
- Stored in flash per spindle ID

Run `scripts/calibrate.py` for guided calibration over BLE.

---

## Assembly Guide

See `docs/assembly_guide.md` for step-by-step build instructions, including:

- PCB fabrication (4-layer, 30 × 80 mm)
- Mechanical assembly (motor mount, torsion spring, Hall sensor alignment, Peltier cup)
- Spindle fabrication (CC, CP, vane, T-bar)
- Firmware flashing (RP2040 + ESP32-C3)
- Calibration procedure
- 3D-printed enclosure

---

## Comparison to Commercial Instruments

| Feature | Visco Shear | Anton Paar MCR 302 | TA Discovery HR-30 | Brookfield DV3T |
|---------|-------------|---------------------|---------------------|------------------|
| Type | Rotational (CR/CS/osc) | Rotational (CR/CS/osc) | Rotational (CR/CS/osc) | Rotational (CR only) |
| η range (mPa·s) | 0.5–200,000 | 10⁻³–10¹² | 10⁻³–10¹² | 15–10⁷ |
| Torque range | 0.05 µN·m–50 mN·m | 0.5 nN·m–200 mN·m | 1 nN·m–200 mN·m | 0.1 µN·m–67 mN·m |
| Shear rate (s⁻¹) | 0.001–1000 | 10⁻⁶–10⁴ | 10⁻⁶–10⁴ | 0.01–100 |
| Oscillatory | Yes (G′/G″) | Yes | Yes | No |
| Temperature | −10 to +80 °C | −180 to +1000 °C | −80 to +600 °C | −10 to +100 °C |
| Models | 7 built-in | Software | Software | Limited |
| Wireless | BLE + Wi-Fi | USB | USB | USB |
| Size | Ø32×165 mm | Benchtop | Benchtop | Handheld |
| Battery | 12h (18650) | N/A (AC) | N/A (AC) | N/A (AC) |
| Price | ~$67 | ~$45,000 | ~$38,000 | ~$3,500 |

Visco Shear trades the extreme low-torque (nN·m) and wide-temperature ranges of $40k lab rheometers for portability, battery operation, wireless connectivity, and 500× lower cost — sufficient for field quality control, food/pharma production floor testing, education, and R&D screening where mPa·s-level viscosity and ±3% accuracy are acceptable.

---

## License

MIT — build it, sell it, improve it.