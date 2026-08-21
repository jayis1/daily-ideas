# Ion Sprint — Pocket Capillary Electrophoresis with C4D

> A battery-powered, pocket-sized capillary electrophoresis (CE)
> instrument that separates and quantifies ionic species in solution
> using a 10–30 kV electrophoretic field through a 50 µm fused-silica
> capillary, detects them via contactless conductivity detection
> (C4D) with lock-in demodulation, identifies peaks against a 40-ion
> migration-time library, quantifies via internal-standard
> calibration, and streams the electropherogram over BLE — bringing
> $25k–$60k lab CE systems (Agilent 7100, Thermo Dionex) down to ~$72
> and pocket size.

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         ION SPRINT                                    │
 │       Pocket Capillary Electrophoresis + C4D                         │
 │                                                                       │
 │  ┌──────────┐  HV+   ┌───────────────┐  C4D    ┌─────────────┐       │
 │  │ Buffer    ├──────▶│ Fused silica  │────────▶│ C4D detector│       │
 │  │ vial (HV) │  30 kV│ capillary      │ cell    │ (ring pair) │       │
 │  │ Pt elec   │       │ 50µm ID ×25 cm │        │ AC excit +  │       │
 │  └──────────┘       └───────┬───────┘         │ lock-in     │       │
 │                             │                  └──────┬──────┘       │
 │                             ▼                         │              │
 │                      ┌──────────┐                     │              │
 │                      │ Sample   │                     │              │
 │                      │ vial(GND)│                     │              │
 │                      │ Pt elec  │                     │              │
 │                      └──────────┘                     │              │
 │                                                       ▼              │
 │  ┌──────────────────────────────────────────────────────────┐       │
 │  │              STM32G474RET6                                │       │
 │  │  170 MHz Cortex-M4F · CORDIC · FMAC · HRTIM              │       │
 │  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐  │       │
 │  │  │ HV PID   │ │ C4D      │ │ Peak      │ │ Library  │  │       │
 │  │  │ field    │ │ lock-in  │ │ detect +  │ │ 40-ion   │  │       │
 │  │  │ control  │ │ I/Q demod│ │ area integ │ │ k-NN     │  │       │
 │  │  └──────────┘ └──────────┘ └───────────┘ └──────────┘  │       │
 │  │  DAC1→HV setpoint  DAC2→C4D excit  ADC1→C4D sig          │       │
 │  └──────┬──────────┬──────────────┬──────────────┬─────────┘       │
 │         │ SPI      │ I2C          │ SPI          │ UART              │
 │         ▼          ▼              ▼              ▼                  │
 │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐           │
 │  │ SH1106   │ │ microSD  │ │ ESP32-C3 │ │ Safety       │           │
 │  │ OLED     │ │ logging  │ │ BLE/WiFi │ │ HV monitor   │           │
 │  │ 128×64   │ │ CSV      │ │ stream   │ │ TLV3201      │           │
 │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘           │
 │                                                                       │
 │  Power: 18650 LiPo + TP4056 + boost 5V                                │
 │  HV:   Cockcroft-Walton 5V→30kV (200µA max, current-limited)         │
 │  Safety: HW current cutoff at 250µA + bleeder + interlock            │
 └──────────────────────────────────────────────────────────────────────┘
```

## What It Does

Ion Sprint is a complete capillary electrophoresis instrument that fits
in a pocket. On a button press, the device:

1. **Primes the capillary** — a micro-peristaltic pump flushes the
   fused-silica capillary (50 µm ID, 25 cm total, 20 cm to detector)
   with background electrolyte (BGE) from a reservoir vial. The
   capillary inlet is then lowered into the sample vial.

2. **Injects the sample** — electrokinetic injection: the HV field is
   applied at reduced voltage (5 kV) for 1–5 seconds, driving a
   plug of ionic sample into the capillary inlet. Alternatively, a
   gravity/hydrodynamic injection lifts the inlet vial 10 cm above
   the outlet for 5–30 seconds (motorized vial lift, NEMA8 stepper).

3. **Separates the ions** — the full separation voltage (10–30 kV) is
   applied across the capillary. Cations migrate toward the cathode
   (outlet, ground), anions toward the anode (inlet, HV) — though
   in normal-polarity CE with EOF, all ions are swept toward the
   outlet by electroosmotic flow (EOF); cations arrive first, then
   neutrals (unresolved), then anions. Each ion's migration time is
   determined by its electrophoretic mobility μ_ep, which depends
   on charge-to-size ratio and the BGE pH.

4. **Detects via C4D** — at the detection window (20 cm from inlet),
   two cylindrical copper electrodes (2 mm wide, 1 mm gap) wrapped
   around the capillary form a capacitive coupler. A 100 kHz AC
   excitation (±3.3 V from DAC2) is applied to the driver electrode;
   the pickup electrode feeds a differential amplifier. When an ion
   zone with different conductivity than the BGE passes between the
   electrodes, the measured admittance changes. The STM32 lock-in
   demodulates the AC signal at the excitation frequency, extracting
   the amplitude change — this is the electropherogram signal.

5. **Detects peaks** — the firmware runs a running-baseline
   algorithm (asymmetric least squares) followed by derivative-based
   peak detection: a peak is flagged when the first derivative
   crosses zero with the second derivative negative and the
   amplitude exceeding 3× the baseline noise (σ). Each peak's
   migration time, height, and area (trapezoidal integration) are
   recorded.

6. **Identifies ions** — the migration time of each peak is compared
   against a 40-ion library (Na⁺, K⁺, NH₄⁺, Ca²⁺, Mg²⁺, Li⁺, Cl⁻,
   NO₃⁻, SO₄²⁻, F⁻, formate, acetate, oxalate, citrate, lactate,
   etc.) measured under standard BGE conditions (20 mM MES/His,
   pH 6.1, 25 °C). A k-NN classifier (k=3) over a 2D feature space
   (normalized migration time, peak shape skewness) identifies the
   most likely ion. Temperature correction (DS18B20) compensates
   for mobility drift.

7. **Quantifies** — peak area is converted to concentration via an
   internal-standard calibration (e.g., Ba²⁺ or benzoate added at
   a known concentration to the sample). The device stores
   per-ion response factors in flash. Results are shown in mM
   and mg/L.

8. **Reports** — displays the live electropherogram, peak table
   (ion, t_m, area, concentration) on the OLED; logs every run to
   microSD (CSV with timestamp, BGE, voltage, temperature, raw
   electropherogram binary); and streams the electropherogram +
   results over BLE to a phone/PC app.

## Why It's Interesting

Capillary electrophoresis is one of the most powerful separation
techniques in analytical chemistry, capable of resolving dozens of
ionic species from a few nanoliters of sample in under 10 minutes
with zeptomole-level detection limits. It is the workhorse of:

- **Clinical chemistry** — serum/urine ion panels (Na, K, Cl, bicarbonate),
  amino acid analysis, therapeutic drug monitoring, hemoglobin variants.
- **Environmental monitoring** — drinking water anions (EPA Method 6505),
  wastewater, rainwater, soil extracts.
- **Food & beverage** — organic acids in wine/juice, preservative
  quantification, amino acid profiling, authenticity testing.
- **Pharmaceutical QC** — drug purity, chiral separations, counter-ion
  assay, impurity profiling.
- **Forensics** — explosive residue ions, inorganic poisons, drug screening.
- **Biotechnology** — fermentation broth monitoring (organic acids,
  amino acids, sugars), protein charge variants.
- **Education** — every chemistry department teaches CE theory;
  hands-on access is limited to $30k+ instruments.

Commercial CE instruments (Agilent 7100, Thermo Scientific Dionex
ICS series, Beckman P/ACE) cost $25,000–$60,000, weigh 15–30 kg, and
require mains power, compressed gas (for vial lifting), and a
dedicated lab bench. This puts CE out of reach for:

- Field-deployable water quality labs (rural utilities, disaster
  response, military).
- Point-of-care clinical settings in low-resource countries.
- Small wineries, breweries, and food producers.
- Undergraduate teaching labs (one instrument per 200 students).
- Citizen-science environmental monitoring.

Ion Sprint brings CE to ~$72 and 150 × 80 × 40 mm, making it:

- **Field-deployable** — battery-powered (18650, 8+ hours / 40+ runs),
  no compressed gas, no mains power.
- **Low-cost** — contactless conductivity detection (C4D) avoids the
  UV lamp, monochromator, and optics of UV-absorbance CE; the
  detector is two copper rings and a differential amplifier.
- **Universal detection** — C4D detects ALL ions (unlike UV which
  requires chromophores), making it ideal for inorganic anions/cations,
  amino acids, and sugars that are UV-transparent.
- **Open** — full schematics, firmware, ion library, and BGE
  recipes are open; users can add new ions or methods.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| SoC | STM32G474RET6 (ARM Cortex-M4F, 170 MHz, FPU, CORDIC, FMAC, HRTIM) |
| BLE / Wi-Fi bridge | ESP32-C3-MINI-1 (BLE 5, Wi-Fi 4) |
| Capillary | Fused silica, 50 µm ID, 365 µm OD, 25 cm total, 20 cm to detector |
| Separation voltage | 10–30 kV (programmable), current-limited to 200 µA |
| HV supply | Cockcroft-Walton multiplier, 5 V → 30 kV, 200 µA max |
| Injection | Electrokinetic (5 kV, 1–5 s) or hydrodynamic (10 cm, 5–30 s) |
| Detection | Contactless conductivity (C4D), 100 kHz excitation, lock-in |
| C4D electrodes | Copper tube electrodes, 2 mm wide, 1 mm gap, around capillary |
| C4D sensitivity | ~10 µS/cm conductivity change (sub-µM detection for most ions) |
| ADC sample rate | 1 kHz electropherogram (after lock-in low-pass) |
| Electropherogram window | 0–600 s (10 min max run) |
| Ion library | 40 ions (cations, anions, organic acids, amino acids) |
| Classification | k-NN (k=3) over normalized migration time + peak skewness |
| Quantification | Internal-standard method, per-ion response factor |
| BGE temperature | 15–40 °C (ambient), DS18B20 compensation |
| Display | 1.3" OLED 128×64 I2C (SH1106) — live electropherogram + peak table |
| Logging | microSD (FAT32, CSV + raw binary electropherogram) |
| Wireless | BLE 5 (ESP32-C3 bridge) — electropherogram + results streaming |
| Power | 18650 Li-ion (3.7 V, 2600 mAh) — ~8 h / ~40 runs |
| Form factor | 150 × 80 × 40 mm |
| Weight | ~220 g (with battery) |
| BOM cost | ~$72 |

## Block Diagram

```
                       ┌────────────────────────────────────────────┐
                       │           STM32G474RET6 (U1)                │
                       │  ┌──────────────────────────────────────┐ │
                       │  │ Cortex-M4F 170 MHz · CORDIC · FMAC   │ │
                       │  │ HRTIM · 5× 12-bit ADC · 4× DAC       │ │
                       │  └──────────────────────────────────────┘ │
                       │                                            │
                       │  DAC1 ──▶ HV setpoint (Cockcroft-Walton)   │
                       │  DAC2 ──▶ C4D excitation (100 kHz AC)      │
                       │  ADC1 ─◀ C4D signal (after preamp + filter)│
                       │  ADC2 ─◀ HV current monitor (sense R)      │
                       │  ADC3 ─◀ HV voltage monitor (divider)       │
                       │  CORDIC ▶ Lock-in I/Q demod (CMSIS-DSP FFT)│
                       │  I2C1 ──▶ SH1106 OLED + DS18B20             │
                       │  SPI1 ──▶ microSD                           │
                       │  SPI2 ──▶ W25Q128 (electropherogram buffer)  │
                       │  USART─▶ ESP32-C3 (BLE bridge)               │
                       │  TIM2  ─▶ NEMA8 stepper (vial lift)         │
                       │  TIM3  ─▶ Peristaltic pump (capillary flush)│
                       └────────────────────────────────────────────┘
                          │      │      │      │       │       │
                     ┌────┘  ┌───┘  ┌───┘  ┌───┘  ┌────┘  ┌────┘
                     ▼       ▼     ▼       ▼     ▼       ▼
              ┌──────────┐┌────┐┌─────┐┌────┐┌─────┐┌──────┐
              │HV CW     ││C4D ││ HV  ││HV  ││OLED ││ESP32-│
              │mult 30kV ││det ││ I   ││ V  ││128  ││C3 BLE│
              │+ bleeder ││ring││mon  ││mon ││×64  ││bridge│
              └────┬─────┘└─┬──┘└─────┘└────┘└─────┘└──────┘
                   │        │
                   ▼        ▼
              ┌──────────┐  ┌────────────┐
              │ Capillary│  │ Driver elec│
              │ inlet    │  │ + pickup   │
              │ (HV+ vial)│  │ elec (C4D)│
              └──────────┘  └────────────┘
                   │              │
                   └──────────────┘
                     Capillary:
                     50µm ID × 25cm
                     fused silica

  HV path:  DAC1 → CW multiplier → 30 kV → capillary inlet (Pt electrode)
            → BGE-filled capillary → outlet vial (GND, Pt electrode)
            Current monitor: sense resistor → ADC2 (10 µA resolution)
            Voltage monitor: 10000:1 divider → ADC3 (1 V/kV)

  C4D path: DAC2 (100 kHz AC) → driver electrode (Cu ring) → capillary
            wall (dielectric) → pickup electrode (Cu ring) → preamp
            → BPF (90–110 kHz) → ADC1 (1 kHz after I/Q demod)
            → electropherogram

  Injection: NEMA8 stepper lifts inlet vial 10 cm (hydrodynamic)
             OR 5 kV for 2 s (electrokinetic)
```

## Pin Assignments (STM32G474RET6 — LQFP64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0  | ADC1_IN1 (C4D signal after preamp+BPF)  | Analog in  | 0–3.3 V, 1 kHz effective |
| PA1  | DAC1_OUT1 (HV setpoint 0–3.3V → 0–30 kV) | Analog out | 12-bit, drives CW multiplier V_ctrl |
| PA2  | DAC1_OUT2 (C4D excitation, 100 kHz AC)  | Analog out | 12-bit, ±1.65 V centered |
| PA3  | ADC1_IN4 (HV current monitor)           | Analog in  | Sense R: 1 µA → 1 mV, ×100 amp |
| PA4  | ADC1_IN17 (battery V divider)           | Analog in  | 2:1 divider on Vbat |
| PA5  | ADC2_IN13 (HV voltage monitor)          | Analog in  | 10000:1 divider, 1 V/kV |
| PA6  | ADC1_IN3 (C4D amplitude ref)           | Analog in  | DC reference for lock-in |
| PA7  | GPIO (HV enable / arm)                  | Output     | Active-high, gates CW oscillator |
| PA8  | TIM1_CH1 (NEMA8 stepper PWM)            | PWM out    | Vial lift stepper, 200 steps |
| PA9  | USART1_TX (ESP32-C3 bridge)            | UART out   | 921600 baud |
| PA10 | USART1_RX (ESP32-C3 bridge)            | UART in    | 921600 baud |
| PA11 | I2C1_SDA (OLED + DS18B20 1-Wire bridge) | I2C        | 400 kHz |
| PA12 | I2C1_SCL (OLED + DS18B20 1-Wire bridge) | I2C        | 400 kHz |
| PA13 | SPI1_SCK (microSD)                     | SPI out    | 25 MHz max |
| PA14 | SPI1_MISO (microSD)                    | SPI in     | SD card data |
| PA15 | SPI1_MOSI (microSD)                    | SPI out    | SD card data |
| PB0  | GPIO (mode button)                    | Input(pu)  | Long-press = menu |
| PB1  | GPIO (start/stop button)              | Input(pu)  | Start run / abort |
| PB2  | GPIO (injection button)               | Input(pu)  | Trigger injection |
| PB3  | SPI2_SCK (W25Q128 flash)               | SPI out    | 50 MHz |
| PB4  | SPI2_MISO (W25Q128 flash)              | SPI in     | Flash data |
| PB5  | SPI2_MOSI (W25Q128 flash)              | SPI out    | Flash data |
| PB6  | GPIO (HV discharge / bleeder)          | Output     | Active-low, bleeder FET |
| PB7  | GPIO (safety interlock)               | Input(pu)  | Lid closed = safe |
| PB8  | TIM4_CH1 (peristaltic pump PWM)        | PWM out    | Capillary flush pump |
| PB9  | GPIO (pump direction)                 | Output    | Forward/reverse |
| PB10 | GPIO (C4D shield / guard)             | Output    | Driven shield for C4D |
| PB11 | GPIO (status LED 1: HV armed)         | Output     | Red LED |
| PB12 | GPIO (status LED 2: running)          | Output     | Green LED |
| PB13 | ADC3_IN5 (C4D temp / ambient)         | Analog in  | Optional temp at C4D cell |
| PB14 | GPIO (WS2812B status)                 | Output     | RGB status LED |
| PC0  | GPIO (NEMA8 dir)                      | Output     | Stepper direction |
| PC1  | GPIO (NEMA8 enable)                   | Output     | Active-low enable |
| PC2  | GPIO (interlock HV cutoff)            | Output     | Drives TLV3201 safety gate |
| PC3  | GPIO (TLV3201 fault read)             | Input      | HW current-limit trip |
| PC4  | GPIO (SD card detect)                 | Input(pu)  | SD card inserted |
| PC5  | GPIO (vial lift home switch)         | Input(pu)  | Limit switch for vial lift |
| PC6  | GPIO (1-Wire DS18B20, optional)       | Bidir      | BGE temperature |
| PC10 | GPIO (vial position sensor)          | Input(pu)  | Optical: vial present |
| PC11 | GPIO (outlet vial sensor)            | Input(pu)  | Optical: outlet vial present |
| PC12 | GPIO (BGE reservoir sensor)          | Input(pu)  | Optical: BGE present |
| PC13 | GPIO (BOOT0 / debug)                  | Input      | Debug probe |
| PC14 | GPIO (reserved / expansion)           | —          | Expansion |
| PC15 | GPIO (reserved / expansion)           | —          | Expansion |

## Schematic Overview

The schematic (in `schematic/ion_sprint.kicad_sch`) is organized into
these sections:

### 1. Power
- USB-C 5 V → TP4056 charger → 18650 cell → MCP1640B boost (3.7→5 V)
- AP2112-3.3 (digital 3.3 V), LP5907-3.3 (analog 3.3 V), REF3030 (3.0 V reference)
- Ferrite beads (BLM18PG121) isolate analog/digital ground planes

### 2. HV Supply (Cockcroft-Walton)
- A 5-stage Cockcroft-Walton voltage multiplier converts 5 V to 30 kV
- Driven by a 50 kHz oscillator (MC34063A boost → 100 V AC, then CW ladder)
- DAC1 sets the control voltage (0–3.3 V → 0–30 kV output)
- HV current monitor: 100 Ω sense resistor in return path → AD8629 amp (×100) → ADC2
- HV voltage monitor: 10000:1 divider (100 MΩ / 10 kΩ) → ADC3
- HV bleeder: 1 GΩ resistor discharges the 30 kV node to GND when PB6 goes low
- Safety: TLV3201 comparator trips at 250 µA, cuts off HV oscillator gate via PC2

### 3. C4D Detector
- **Driver electrode**: copper tube (2 mm wide) around capillary, driven by
  DAC2 at 100 kHz AC (±1.65 V centered on 1.65 V)
- **Pickup electrode**: copper tube (2 mm wide), 1 mm gap from driver
- **Preamp**: OPA656 (low-noise JFET, 500 MHz GBW) in transimpedance config
- **Band-pass filter**: 4th-order Bessel, 90–110 kHz (passes 100 kHz carrier)
- **Lock-in demodulation**: firmware I/Q demodulation at 100 kHz (CORDIC),
  low-pass filter (τ=10 ms), output = electropherogram amplitude
- **Guard shield**: PB10 drives a shield ring between electrodes to reduce
  parasitic capacitance coupling

### 4. Capillary & Vial System
- Fused silica capillary: 50 µm ID, 365 µm OD, 25 cm total length
- Polyimide coating removed at detection window (2 mm) for C4D electrodes
- Inlet vial: 1.5 mL microcentrifuge tube with Pt wire electrode (HV+)
- Outlet vial: 1.5 mL microcentrifuge tube with Pt wire electrode (GND)
- BGE reservoir: 5 mL vial feeding the peristaltic flush pump
- NEMA8 stepper (TIM2) lifts the inlet vial for hydrodynamic injection
- Peristaltic pump (TIM4, geared DC motor) flushes capillary between runs

### 5. Sensors
- DS18B20: BGE/carrier temperature (1-Wire on PC6)
- TLV3201: HW current-limit comparator (250 µA trip, PC3 fault read)
- Optical sensors (PC10/PC11/PC12): vial presence detection

### 6. Memory / Logging
- microSD (SPI1, FAT32): CSV run log + raw electropherogram binary
- W25Q128 (SPI2, 16 MB): electropherogram ring buffer for BLE streaming

### 7. Display
- SH1106 1.3" 128×64 OLED (I2C1, 0x3D): live electropherogram + peak table

### 8. BLE Bridge
- ESP32-C3-MINI-1 (USART1, 921600 baud): BLE 5 + Wi-Fi 4 streaming

### 9. UI
- EC11 rotary encoder + 3 tactile buttons (Mode, Start/Stop, Inject)
- 2 status LEDs (HV armed red, running green) + WS2812B RGB

## Power Architecture

```
USB-C 5V ──▶ TP4056 ──▶ 18650 (3.7V 2600mAh)
                              │
                              ▼
                        MCP1640B boost (3.7→5V, 500mA)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              AP2112-3.3   LP5907-3.3  CW HV stage
              (digital)    (analog)   (5V→30kV, 200µA)
                    │         │
                    ▼         ▼
              STM32G474   OPA656, AD8629
              ESP32-C3    REF3030
              SH1106 OLED
              SD, W25Q128
```

Power budget:
- STM32G474 @ 170 MHz: ~45 mA
- ESP32-C3 (BLE): ~25 mA
- OLED: ~20 mA
- SD card (write): ~30 mA (peak)
- OPA656 + AD8629: ~8 mA
- CW HV stage (30 kV × 100 µA = 3 W → 600 mA from 5V at 50% eff): ~600 mA during run
- Total during run: ~730 mA → 2600 mAh / 730 mA ≈ 3.5 h continuous
- Typical run: 5 min separation + 2 min flush → ~40 runs per charge

## HV Safety

The 30 kV HV rail is the highest-voltage node in any device in this
collection. Safety measures:

- **Current-limited supply**: the Cockcroft-Walton stage is inherently
  current-limited by the driving oscillator's output impedance;
  max output is 200 µA at 30 kV (6 W).
- **Hardware current cutoff**: a TLV3201 comparator monitors the HV
  return current (100 Ω sense resistor × 100 amp = 10 mV/µA).
  If current exceeds 250 µA (2.5 V trip), the comparator pulls PC2
  low, gating off the CW oscillator within 1 µs.
- **Active bleeder**: PB6 (active-low) controls a FET that connects
  a 1 GΩ resistor from the 30 kV node to GND. When PB6 goes low,
  the HV node discharges: τ = 1G × 100pF (cap parasitic) = 100 ms
  → 30 kV → 0 V in <1 s (10τ). The firmware drives PB6 low at run
  completion or fault.
- **Interlock**: PB7 (pulled high) reads the vial-lid interlock
  switch. If the lid is open (PB7 low), the firmware refuses to
  arm HV and displays a warning.
- **Voltage monitor**: ADC3 reads the 10000:1 divider, verifying
  the HV is at the setpoint. If the measured voltage deviates
  by more than ±2 kV from the setpoint, the firmware aborts.
- **Soft-start**: the HV setpoint (DAC1) ramps from 0 to target
  over 5 seconds to avoid capillary overheating from sudden EOF.

## Grounding

- **AGND / DGND split**: analog ground (OPA656, AD8629, REF3030,
  C4D electrodes, HV return) ties to AGND; digital ground (STM32,
  ESP32-C3, OLED, SD, W25Q128) ties to DGND. They meet at a single
  star point under the STM32.
- **HV return**: the CW multiplier return is a separate net that
  ties to AGND at the star point only, to keep HV switching currents
  out of the C4D signal ground.
- **C4D shield**: the guard shield (PB10) is driven at the same
  potential as the driver electrode to minimize parasitic capacitance
  to ground, which would shunt the AC signal.

## Firmware Architecture

The firmware is organized into modular C files:

| Module | File | Function |
|--------|------|----------|
| System | `main.c` | Top-level state machine + main loop |
| Config | `stm32g474_conf.h` | Clock, peripheral, parameter defines |
| HV supply | `hv_supply.c/h` | CW multiplier control, ramp, monitor |
| C4D detector | `c4d.c/h` | AC excitation, ADC capture, lock-in demod |
| Injection | `injection.c/h` | Electrokinetic / hydrodynamic injection |
| Electropherogram | `eph.c/h` | Baseline correction, peak detection, area |
| Library | `library.c/h` | 40-ion migration-time library, k-NN ID |
| Quantification | `quant.c/h` | Internal-standard calibration, mM/mg-L |
| Temperature | `temperature.c/h` | DS18B20 read, mobility correction |
| Pump | `pump.c/h` | Peristaltic flush pump control |
| Vial lift | `vial_lift.c/h` | NEMA8 stepper for hydrodynamic injection |
| Safety | `safety.c/h` | HW current limit, interlock, bleeder |
| Display | `display.c/h` | OLED: live electropherogram + peak table |
| SD logging | `sd_log.c/h` | CSV + raw binary electropherogram |
| BLE bridge | `ble_bridge.c/h` | UART protocol to ESP32-C3 |
| Battery | `battery.c/h` | 18650 voltage monitor |
| UI | `ui.c/h` | Encoder + buttons + menu |

### State Machine

```
IDLE → MENU → (set BGE, voltage, injection mode, ions)
  → PRIME (flush capillary with BGE, 30 s)
  → INJECT (electrokinetic or hydrodynamic, 2 s)
  → SEPARATE (apply HV, acquire electropherogram, detect peaks)
  → IDENTIFY (k-NN library match, quantify)
  → REPORT (OLED display, SD log, BLE stream)
  → FLUSH (clean capillary, 30 s)
  → IDLE
```

### C4D Lock-In Detection

The C4D signal is a 100 kHz AC carrier whose amplitude changes as
ion zones pass through the detection cell. The lock-in algorithm:

1. **ADC1** samples the preamp output at 200 kHz (4× oversampling)
2. **I/Q demodulation**: multiply by cos(2π·100k·t) and sin(2π·100k·t)
   (CORDIC-generated sine table), accumulate over 100 samples (0.5 ms)
3. **Low-pass filter**: IIR 2nd-order, τ=10 ms → rejects 100 kHz carrier
4. **Amplitude**: R = √(I² + Q²) → electropherogram data point at 100 Hz
5. **Baseline**: asymmetric least squares (ALS) baseline, λ=10⁵, p=0.001
6. **Peak detection**: derivative zero-cross + 2nd-derivative negative +
   amplitude > 3σ_noise

## BOM

See `hardware/BOM.csv` for the full bill of materials. Key cost drivers:

| Part | Cost | Note |
|------|------|------|
| STM32G474RET6 | $6.40 | SoC |
| ESP32-C3-MINI-1 | $2.70 | BLE/WiFi bridge |
| OPA656 (C4D preamp) | $5.20 | Low-noise JFET op-amp |
| AD8629 (HV current monitor) | $2.40 | Zero-drift op-amp |
| TLV3201 (safety comparator) | $0.80 | HW current limit |
| CW HV stage (diodes + caps) | $4.50 | 5-stage Cockcroft-Walton |
| Fused silica capillary (25 cm) | $3.50 | 50 µm ID, polyimide coated |
| NEMA8 stepper | $4.00 | Vial lift for hydrodynamic injection |
| Peristaltic pump | $3.50 | Capillary flush |
| SH1106 OLED | $2.80 | 128×64 display |
| W25Q128 flash | $1.10 | Electropherogram buffer |
| PCB (4-layer, 80×50 mm) | $4.00 | JLCPCB |
| **Total** | **~$72** | |

## Applications

### Drinking Water Anion Analysis (EPA Method 6505)
BGE: 20 mM MES/His, pH 6.1. Detects F⁻, Cl⁻, NO₂⁻, NO₃⁻, PO₄³⁻, SO₄²⁻
in <5 minutes at sub-ppm levels. Field-deployable for rural utilities,
disaster response, and military water-quality testing.

### Clinical: Serum/Urinary Ion Panel
BGE: 20 mM MES/His, pH 6.1 with Ba²⁺ internal standard. Measures Na⁺,
K⁺, Ca²⁺, Mg²⁺, Cl⁻ in 8 minutes from 10 µL of serum or urine.

### Food: Wine Organic Acids
BGE: 20 mM MES/His, pH 5.7. Separates tartaric, malic, lactic, citric,
acetic, succinic acids in 6 minutes. Authenticates wine varietals and
detects adulteration.

### Pharma: Drug Counter-Ion Assay
BGE: 20 mM MES/His, pH 6.1. Quantifies Cl⁻, SO₄²⁻, maleate, fumarate
counter-ions in drug substances.

### Education: Undergraduate Analytical Chemistry Lab
Each student pair can have a CE instrument for $72 instead of sharing
a $30k Agilent 7100. Pre-loaded BGE recipes and ion library make it
suitable for lab courses in separation science.

## BGE Recipes

The device stores 8 BGE recipes in flash (selectable via menu):

| # | BGE | pH | Ions detected | Application |
|---|-----|-----|---------------|-------------|
| 1 | 20 mM MES/His | 6.1 | Anions + cations (universal) | Water quality |
| 2 | 20 mM MES/His + 0.5 mM CTAB | 6.1 | Anions (reversed EOF) | Inorganic anions |
| 3 | 20 mM His/MES | 4.5 | Cations (Na-K-Ca-Mg-Li) | Serum electrolytes |
| 4 | 20 mM MES/His | 5.7 | Organic acids (wine/juice) | Food analysis |
| 5 | 50 mM phosphate | 2.5 | Amino acids (cationic) | Protein hydrolysates |
| 6 | 20 mM NaOH | 12.1 | Sugars (as anions) | Carbohydrate analysis |
| 7 | 20 mM MES/His + 5 mM EDTA | 6.1 | Transition metals | Environmental |
| 8 | 30 mM borate | 9.3 | Organic acids (anionic) | Pharmaceutical QC |

## Assembly

See `docs/assembly-guide.md` for detailed assembly instructions.

Key notes:
- The C4D electrode assembly is the most delicate part: the two copper
  tube electrodes (2 mm wide, 1 mm apart) must be precisely positioned
  over the capillary detection window (polyimide removed). A 3D-printed
  jig aligns them.
- The HV section requires careful creepage/clearance: 30 kV needs
  ≥10 mm creepage on the PCB (slot + conformal coating).
- The capillary is fragile; route it in a protected channel in the
  3D-printed enclosure.

## Comparison to Commercial CE Systems

| Feature | Ion Sprint | Agilent 7100 | Thermo Dionex ICS-6000 |
|---------|-----------|-------------|------------------------|
| Cost | ~$72 | ~$30,000 | ~$50,000 |
| Weight | 220 g | 15 kg | 30 kg |
| Power | Battery (8 h) | Mains 100 W | Mains 200 W |
| Detection | C4D (universal) | UV-Vis + Fluorescence | Conductivity (suppressed) |
| Separation voltage | 10–30 kV | up to 30 kV | up to 30 kV (IC) |
| Capillary | 50 µm, 25 cm | 50–100 µm, up to 1 m | 4 mm column (IC) |
| Injection | Electrokinetic + hydrodynamic | Pressure (compressed gas) | Loop injection |
| Sample | nL (manual) | nL (auto-sampler) | µL (auto-sampler) |
| Ion library | 40 ions (on-device) | — (software) | — (software) |
| Run time | 3–10 min | 1–60 min | 10–60 min |
| Sensitivity | ~1 µM (C4D) | ~1 nM (UV) | ~1 ppb (suppressed) |
| Field-deployable | Yes | No | No |

Ion Sprint trades sensitivity (C4D is ~1000× less sensitive than
UV-absorbance for chromophores) for universality (C4D detects ALL ions,
including UV-transparent inorganics) and portability (battery, no
gas, pocket size).

## License

MIT — build it, sell it, improve it.

---

*Invented as part of [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions).*