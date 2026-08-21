# Thermo Trace — Pocket Differential Scanning Calorimeter

> A battery-powered, pocket-sized differential scanning calorimeter (DSC)
> that measures heat flow vs. temperature (RT–300 °C) using two
> power-compensated MEMS heater cells with PT1000 RTD feedback, computes
> glass transitions, melting points, crystallization peaks, and enthalpy
> (ΔH), matches against a 50-material DSC fingerprint library, and
> streams results over BLE — bringing $15k–$60k lab DSCs (TA Q2000,
> Mettler DSC 3, Netzsch 214) down to ~$75 and pocket size.

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         THERMO TRACE                                  │
 │          Pocket Differential Scanning Calorimeter                     │
 │                                                                       │
 │  ┌─────────────┐         ┌──────────────┐         ┌─────────────┐   │
 │  │ Sample pan  │         │ Reference pan │         │  Ambient    │   │
 │  │ (Al, 5 mg)  │         │ (Al, empty)   │         │  DS18B20    │   │
 │  └──────┬──────┘         └───────┬───────┘         └──────┬──────┘   │
 │         │                        │                       │           │
 │         ▼                        ▼                       │           │
 │  ┌─────────────┐         ┌──────────────┐                │           │
 │  │ Kapton      │         │ Kapton       │                │           │
 │  │ thin-film   │         │ thin-film    │                │           │
 │  │ heater 50Ω  │         │ heater 50Ω   │                │           │
 │  └──────┬──────┘         └───────┬──────┘                │           │
 │         │ PWM₁                    │ PWM₂                  │           │
 │         ▼                        ▼                       │           │
 │  ┌─────────────┐         ┌──────────────┐                │           │
 │  │ PT1000 RTD  │         │ PT1000 RTD   │                │           │
 │  │ (pan temp)  │         │ (pan temp)   │                │           │
 │  └──────┬──────┘         └───────┬──────┘                │           │
 │         │ 4-wire                   │ 4-wire               │           │
 │         ▼                        ▼                       ▼           │
 │  ┌──────────────────────────────────────────────────────────┐       │
 │  │              ADS122U04 24-bit ∆Σ ADC                      │       │
 │  │   CH0: sample RTD   CH1: ref RTD   CH2: I_sense  CH3: V   │       │
 │  └──────────────────────────┬───────────────────────────────┘       │
 │                             │ SPI                                    │
 │  ┌──────────────────────────▼───────────────────────────────┐       │
 │  │                    STM32G491RET6                           │       │
 │  │  170 MHz Cortex-M4F  ·  CORDIC  ·  FMAC                    │       │
 │  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐ │       │
 │  │  │ Dual PID │  │ Heat flow│  │  Peak     │  │ Library  │ │       │
 │  │  │ heater   │  │ ΔP =     │  │  detect + │  │ k-NN     │ │       │
 │  │  │ control  │  │ Ps - Pr  │  │  ΔH integ │  │ match 50 │ │       │
 │  │  └──────────┘  └──────────┘  └───────────┘  └──────────┘ │       │
 │  │  TIM1 PWM₁ → MOSFET₁   TIM8 PWM₂ → MOSFET₂               │       │
 │  └──────┬──────────┬──────────────┬──────────────┬──────────┘       │
 │         │ SPI      │ I2C          │ SPI          │ UART              │
 │         ▼          ▼              ▼              ▼                  │
 │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐           │
 │  │ SH1106   │ │ microSD  │ │ ESP32-C3 │ │ Safety       │           │
 │  │ OLED     │ │ logging  │ │ BLE/WiFi │ │ comparator   │           │
 │  │ 128×64   │ │ CSV      │ │ stream   │ │ TLV3201      │           │
 │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘           │
 │                                                                       │
 │  Power: 18650 LiPo + TP4056 + boost 5V                                │
 │  Safety: HW over-temp cutoff at 320°C + fuse + thermal fuse          │
 └──────────────────────────────────────────────────────────────────────┘
```

## What It Does

Thermo Trace is a complete power-compensated differential scanning
calorimeter that fits in a pocket. On a button press, the device:

1. **Loads a sample** — the user places 1–10 mg of material into a
   standard aluminum DSC pan (crimped or open) on the sample cell, and
   an empty matched pan on the reference cell. The cells are tiny
   Kapton thin-film heaters with PT1000 RTDs bonded underneath.
2. **Ramps the temperature** — a dual PID control loop drives both
   heater cells along a programmed temperature profile (e.g., 25 °C →
   300 °C at 5 °C/min, with optional isothermal holds). Each PID loop
   independently maintains its cell at the setpoint using PWM-driven
   MOSFETs at ~10 kHz, with PT1000 RTD feedback measured by a 24-bit
   ADS122U04 delta-sigma ADC at 100 Hz.
3. **Measures heat flow** — in power-compensation DSC, the heat flow
   into the sample is the electrical power delivered to maintain it at
   the setpoint: `Φ = P_sample − P_reference`. Each heater's power is
   `P = V² · duty / R_heater`, computed from the measured supply
   voltage (ADC CH3) and the sense-resistor current (ADC CH2). When the
   sample melts (endothermic), extra power is needed → positive peak.
   When it crystallizes or oxidizes (exothermic), less power is needed
   → negative peak.
4. **Detects transitions** — a derivative-based peak detector finds
   endothermic and exothermic events. For each peak: onset temperature
   (extrapolated), peak temperature, and enthalpy `ΔH = ∫ ΔP dt / m`
   (J/g, normalized by sample mass entered by the user). Glass
   transitions (Tg) are detected as step changes in heat flow
   (inflection point with half-height / half-ΔCp method).
5. **Identifies materials** — the extracted features (Tg, Tm, ΔH_m,
   Tc, ΔH_c, onset/peak temperatures) are compared against a
   50-material DSC fingerprint library (PE, PP, PS, PET, PA6, PA66,
   PEEK, PC, PMMA, PVC, PLA, wax, paraffin, indium, tin, bismuth,
   stearic acid, ibuprofen, acetaminophen, aspirin, chocolate, butter,
   coconut oil, etc.) using k-NN (k=3) in feature space. The top-3
   matches with confidence scores are displayed.
6. **Reports** — the OLED shows a live heat-flow vs. temperature curve
   with peak markers, current temperature, and ramp rate. Data is
   logged to microSD (heat flow + temperature at 1 Hz, full scan CSV)
   and streamed over BLE to a phone/PC app for real-time plotting and
   analysis.

## Why It Matters

Differential scanning calorimetry is the gold standard for thermal
analysis in materials science, pharmaceuticals, polymers, food
science, and forensics. It can identify polymers by their melting
point and glass transition, detect polymorphism in drugs, verify
purity, study curing of resins, characterize fats and waxes in food,
and screen for counterfeit materials. But benchtop DSCs cost
$15,000–$60,000 and require lab infrastructure, liquid nitrogen
cooling, and trained operators. Thermo Trace brings this capability
to:

- **Field polymer identification** — recycling sorting, counterfeit
  detection, quality control at receiving docks
- **Pharma point-of-care** — verify drug polymorphism / melting point
  in low-resource pharmacies, detect counterfeit medications
- **Food science** — characterize fat melting profiles, detect
  adulteration in oils/honey/wax
- **Education** — affordable DSC for university teaching labs
- **Forensics** — rapid material screening at crime scenes

## Specifications

| Parameter | Value |
|-----------|-------|
| SoC | STM32G491RET6 (170 MHz Cortex-M4F, CORDIC, FMAC) |
| Wireless | ESP32-C3-MINI-1 (BLE 5.0 + WiFi) |
| Temperature range | RT – 300 °C (RT – 250 °C recommended) |
| Ramp rate | 0.1 – 20 °C/min (programmable) |
| Temperature resolution | 0.01 °C (24-bit ADC + PT1000) |
| Heat flow resolution | 2 µW (24-bit power measurement) |
| Heat flow accuracy | ±5 µW (after indium calibration) |
| Sample mass | 1 – 10 mg (user-entered) |
| Pan type | Standard aluminum DSC pans (TA Instruments Tzero or equivalent) |
| Enthalpy accuracy | ±3% (after calibration with indium standard) |
| Library | 50 materials, k-NN (k=3) matching |
| Display | SH1106 OLED 128×64 (heat-flow curve, status) |
| Logging | microSD, CSV (temp, heat flow, time @ 1 Hz) |
| Wireless range | BLE ~10 m line-of-sight |
| Battery | 18650 LiPo 3400 mAh, ~15 scans per charge |
| Charge time | ~4 h (TP4056 USB-C) |
| Size | 110 × 70 × 30 mm (pocket-sized) |
| Weight | ~150 g (with battery) |
| Cost (BOM) | ~$75 |

## Block Diagram

```
                    ┌─────────────────────────────────────────┐
                    │           STM32G491RET6                  │
                    │         (170 MHz Cortex-M4F)             │
                    │                                          │
   PT1000 sample ──▶│  ADS122U04  │  PID₁ → TIM1 PWM₁ → FET₁  │──▶ Heater₁
   PT1000 ref    ──▶│  (SPI,      │  PID₂ → TIM8 PWM₂ → FET₂  │──▶ Heater₂
   I_sense       ──▶│   24-bit)   │                           │
   V_supply      ──▶│             │  Heat flow = P₁ - P₂       │
                    │             │  Peak detect → ΔH           │
                    │             │  Library k-NN match         │
                    └──┬────┬──────┬────┬──────┬───────────────┘
                       │SPI │I2C   │SPI │UART  │GPIO
                       ▼    ▼      ▼    ▼      ▼
                    ┌─────┐┌────┐┌────┐┌─────┐┌──────┐
                    │OLED ││ SD ││ESP ││Safe ││Buttons│
                    │SH110││card││C3  ││ty   ││×3    │
                    │6    ││    ││BLE ││cmp  ││      │
                    └─────┘└────┘└────┘└─────┘└──────┘
                    
   DS18B20 ──▶ OneWire ──▶ STM32 (ambient temp, cold junction)

   Power: 18650 → TP4056 → BQ25883 → 5V boost → 3.3V LDO → rails
   Safety: TLV3201 comparator, pan temp > 320°C → heater FET gate LOW (HW)
           + 250°C thermal fuse (one-shot, non-resettable) in series
```

## Pin Assignments (STM32G491RET6, LQFP64)

| Pin | Function | Notes |
|-----|----------|-------|
| PA0 | ADC1_IN1 | Heater 1 current sense (via op-amp, optional fast path) |
| PA1 | ADC1_IN2 | Heater 2 current sense (via op-amp, optional fast path) |
| PA2 | USART2_TX | → ESP32-C3 UART RX (BLE bridge) |
| PA3 | USART2_RX | ← ESP32-C3 UART TX |
| PA4 | DAC1_OUT1 | (unused, reserved for analog ref) |
| PA5 | SPI1_SCK | → ADS122U04 SCLK |
| PA6 | SPI1_MISO | ← ADS122U04 DOUT/DRDY |
| PA7 | SPI1_MOSI | → ADS122U04 DIN |
| PA8 | TIM1_CH1 | PWM₁ → MOSFET₁ gate (heater 1, 10 kHz) |
| PA9 | TIM1_CH2 | PWM₂ → MOSFET₂ gate (heater 2, 10 kHz) |
| PA10 | GPIO_OUT | ADS122U04 CS (chip select) |
| PA11 | GPIO_OUT | ADS122U04 START |
| PA12 | GPIO_IN | ADS122U04 DRDY (data ready interrupt) |
| PB0 | GPIO_OUT | OLED DC (data/command) |
| PB1 | GPIO_OUT | OLED RESET |
| PB2 | SPI2_SCK | microSD SCLK (SPI mode) |
| PB3 | SPI2_MISO | microSD MISO |
| PB4 | SPI2_MOSI | microSD MOSI |
| PB5 | GPIO_OUT | microSD CS |
| PB6 | I2C1_SCL | OLED SH1106 SCL |
| PB7 | I2C1_SDA | OLED SH1106 SDA |
| PB8 | GPIO_IN | Safety comparator output (over-temp interrupt) |
| PB9 | GPIO_OUT | Heater enable (global, active LOW = cutoff) |
| PB10 | GPIO_IN | Button A (START/STOP) |
| PB11 | GPIO_IN | Button B (UP/NEXT) |
| PB12 | GPIO_IN | Button C (DOWN/SELECT) |
| PB13 | GPIO_OUT | Status LED (red, heating) |
| PB14 | GPIO_OUT | Status LED (green, ready) |
| PB15 | GPIO_OUT | ESP32-C3 BOOT/EN (power control) |
| PC0 | ADC2_IN1 | Battery voltage (via divider, 1/2) |
| PC1 | GPIO_IN | DS18B20 OneWire data |
| PC6 | TIM3_CH1 | (reserved, buzzer PWM) |
| PC13 | GPIO_OUT | TP4056 charge status LED |
| PC14 | GPIO_IN | TP4056 CHRG status |
| PC15 | GPIO_IN | TP4056 STDBY status |
| VDD | Power | 3.3V |
| VSS | Ground | GND |
| VDDA | Analog power | 3.3V (ferrite bead isolated) |
| VREF+ | ADC reference | 3.3V (LM4040 reference optional) |

## Power Architecture

```
 USB-C 5V ──┬──▶ TP4056 ──▶ 18650 LiPo (3.7V, 3400 mAh)
            │    (charge)     │
            │                 ├──▶ BQ25883 /boost → 5.0V rail (heaters)
            │                 │         │
            │                 │         └──▶ MOSFET₁/₂ → heaters (50Ω each)
            │                 │              (max 5V/50Ω = 0.5W per heater)
            │                 │
            │                 └──▶ AP2112 LDO → 3.3V rail (MCU, ADC, OLED, ESP32-C3)
            │
            └──▶ (USB power path while charging)
```

- **Heater power:** 5V boost rail, 0.5W per heater (max), enough for
  10 °C/min ramp on a ~0.5 g aluminum pan assembly
- **Logic power:** 3.3V LDO from battery, ~150 mA max (MCU + OLED +
  ESP32-C3 + ADS122U04)
- **Battery life:** ~15 full scans (25–300°C at 5°C/min, ~55 min each
  + cooldown) per charge
- **Charge time:** ~4 h via USB-C

## Safety Architecture

DSC heaters can be a fire hazard if control is lost. Thermo Trace has
**three independent safety layers**:

1. **Software watchdog** — STM32 PID loop must refresh the heater PWM
   every 100 ms. If the loop stalls (hard fault, crash), a hardware
   watchdog (IWDG) resets the MCU, cutting PWM.
2. **Hardware over-temperature comparator** — a TLV3201 high-speed
   comparator monitors the pan temperature (via a dedicated thermistor
   or the RTD signal). If pan temp exceeds 320 °C, the comparator
   drives the heater-enable GPIO LOW, physically cutting MOSFET gate
   drive. This operates independently of the MCU.
3. **One-shot thermal fuse** — a 250 °C non-resettable thermal fuse
   (e.g., Cantherm MF-RG250) is wired in series with the 5V heater
   rail. If all else fails, the fuse blows permanently at 250 °C,
   permanently disabling the heaters. The device must be serviced.

Additionally:
- **Heater current limiting** — 0.5Ω series resistor + polyfuse per
  heater channel
- **Reverse polarity protection** — on battery input
- **Thermal isolation** — heater cells are mounted on a ceramic spacer
  with air gap, thermally isolated from the PCB and battery

## DSC Cell Design

The heart of the instrument is the dual DSC cell:

```
        ┌───────────────────────────────────┐
        │           DSC CELL ASSEMBLY        │
        │                                    │
        │   ┌─────────┐     ┌─────────┐     │
        │   │ Al pan  │     │ Al pan  │     │
        │   │(sample) │     │ (empty) │     │
        │   └────┬────┘     └────┬────┘     │
        │        │                │          │
        │   ┌────┴────┐     ┌────┴────┐     │
        │   │Kapton   │     │Kapton   │     │
        │   │heater   │     │heater   │     │
        │   │50Ω 5×5mm│     │50Ω 5×5mm│     │
        │   └────┬────┘     └────┬────┘     │
        │        │                │          │
        │   ┌────┴────┐     ┌────┴────┐     │
        │   │PT1000   │     │PT1000   │     │
        │   │RTD      │     │RTD      │     │
        │   └────┬────┘     └────┬────┘     │
        │        │                │          │
        │   ═════════════════════════════     │
        │   Ceramic spacer (Al₂O₃, 1mm)      │
        │   ═════════════════════════════     │
        │   Air gap (2mm)                     │
        │   ═════════════════════════════     │
        │   PCB (FR4, standard)               │
        └───────────────────────────────────┘
```

- **Aluminum pans:** standard 5 mm DSC pans (TA Instruments 900793.901
  or equivalent), crimped or open
- **Kapton thin-film heaters:** 5×5 mm, 50Ω, polyimide substrate,
  rated to 300 °C (Minco HK5357 or similar, or custom etched foil)
- **PT1000 RTDs:** 2× PT1000 class A (±0.15 °C at 0 °C), 4-wire
  connection, bonded to the heater underside with thermally conductive
  epoxy
- **Ceramic spacer:** 1 mm alumina (Al₂O₃) plate, thermally isolates
  heaters from PCB
- **Enclosure:** the cell assembly is enclosed in a small aluminum
  shield (EMI + thermal radiation shield) with a removable lid for
  sample loading

## Measurement Principle

### Power-Compensation DSC

In power-compensation DSC, both the sample and reference cells are
maintained at the same programmed temperature `T(t)` by independent
heaters. The **heat flow** is the difference in electrical power
required:

```
Φ(t) = P_sample(t) − P_reference(t)   [mW]
```

where each heater's power is:

```
P = (V_supply² / R_heater) × duty_fraction   [W]
```

- `V_supply` is measured by the ADS122U04 (CH3, via voltage divider)
- `duty_fraction` is the PID controller's output (0.0–1.0)
- `R_heater` is the known heater resistance (50Ω, temperature-corrected)

### Transition Detection

- **Melting / crystallization peaks:** derivative-based peak detection
  on `Φ(t)`. Onset temperature = intersection of the pre-peak baseline
  with the steepest tangent. Peak temperature = extremum. Enthalpy:
  `ΔH = ∫(Φ − baseline) dt / m_sample` [J/g]
- **Glass transition (Tg):** step change in heat flow. Detected by
  finding the inflection point (zero of 2nd derivative). Tg =
  half-height temperature. ΔCp = step amplitude / (ramp_rate × m_sample)

### Calibration

Two-point calibration using reference standards:
1. **Indium** (Tm = 156.6 °C, ΔHf = 28.71 J/g) — calibrates
   temperature scale and heat flow
2. **Tin** (Tm = 231.9 °C, ΔHf = 60.22 J/g) — verifies linearity at
   higher temperature

The calibration script (`scripts/calibrate.py`) fits a linear
correction: `T_corrected = a · T_measured + b` and `Φ_corrected = c ·
Φ_measured + d`.

## Material Library (50 entries)

The on-device library stores DSC fingerprints for 50 common materials:

| # | Material | Tg (°C) | Tm (°C) | ΔH (J/g) | Category |
|---|----------|---------|---------|----------|----------|
| 1 | LDPE | −125 | 110 | 110 | Polymer |
| 2 | HDPE | −120 | 135 | 210 | Polymer |
| 3 | PP (isotactic) | −10 | 165 | 100 | Polymer |
| 4 | PS (atactic) | 100 | — | — | Polymer |
| 5 | PET | 80 | 255 | 140 | Polymer |
| 6 | PA6 (nylon 6) | 50 | 220 | 190 | Polymer |
| 7 | PA66 (nylon 66) | 60 | 265 | 250 | Polymer |
| 8 | PEEK | 145 | 343 | 130 | Polymer |
| 9 | PC (polycarbonate) | 145 | — | — | Polymer |
| 10 | PMMA | 105 | — | — | Polymer |
| 11 | PVC (rigid) | 80 | — | — | Polymer |
| 12 | PLA | 60 | 170 | 93 | Polymer |
| 13 | ABS | 105 | — | — | Polymer |
| 14 | SAN | 115 | — | — | Polymer |
| 15 | POM (acetal) | −60 | 175 | 230 | Polymer |
| 16 | PTFE | 115 | 327 | 80 | Polymer |
| 17 | PVDF | −35 | 177 | 105 | Polymer |
| 18 | EVA (12% VA) | −25 | 92 | 120 | Polymer |
| 19 | TPU | −40 | 180 | 50 | Polymer |
| 20 | Rubber (NR) | −70 | 30 | 20 | Polymer |
| 21 | Paraffin wax | — | 58 | 210 | Wax |
| 22 | Beeswax | — | 64 | 170 | Wax |
| 23 | Carnauba wax | — | 82 | 190 | Wax |
| 24 | Microcrystalline wax | — | 72 | 150 | Wax |
| 25 | Stearic acid | — | 69 | 200 | Fatty acid |
| 26 | Palmitic acid | — | 63 | 220 | Fatty acid |
| 27 | Indium | — | 156.6 | 28.7 | Metal |
| 28 | Tin | — | 231.9 | 60.2 | Metal |
| 29 | Bismuth | — | 271.4 | 53.3 | Metal |
| 30 | Lead | — | 327.5 | 23.0 | Metal |
| 31 | Gallium | — | 29.8 | 80.1 | Metal |
| 32 | Ibuprofen | — | 75 | 120 | Pharma |
| 33 | Acetaminophen | — | 169 | 180 | Pharma |
| 34 | Aspirin | — | 135 | 150 | Pharma |
| 35 | Caffeine | — | 235 | 110 | Pharma |
| 36 | Sulfathiazole (F1) | — | 172 | 95 | Pharma |
| 37 | Sulfathiazole (F2) | — | 202 | 85 | Pharma |
| 38 | Cocoa butter | — | 34 | 110 | Food |
| 39 | Chocolate (dark) | 28 | 34 | 50 | Food |
| 40 | Butter | — | 38 | 80 | Food |
| 41 | Coconut oil | — | 24 | 100 | Food |
| 42 | Palm oil | — | 36 | 90 | Food |
| 43 | Honey (pure) | −50 | 180 | 60 | Food |
| 44 | Sucrose | 62 | 186 (decomp) | — | Food |
| 45 | Gelatin | 210 | — | — | Food |
| 46 | Epoxy (uncured) | — | 150 (cure exo) | 350 | Resin |
| 47 | Epoxy (cured) | 130 | — | — | Resin |
| 48 | Polyester resin | 70 | 150 (cure exo) | 200 | Resin |
| 49 | Sulfur (α) | — | 115 | 60 | Chemical |
| 50 | Water (ice) | — | 0 | 334 | Reference |

## Firmware

The firmware is written in C and built with CMake + arm-none-eabi-gcc.
It runs on bare metal (no RTOS for determinism in the PID loop).

### Modules

| File | Function |
|------|----------|
| `main.c` | State machine, orchestrates scan, button handling |
| `heater.c` | Dual PID control, PWM output, power computation |
| `rtd.c` | PT1000 RTD reading via ADS122U04, Callendar-Van Dusen |
| `ads122.c` | ADS122U04 SPI driver, 24-bit ADC, 4-channel mux |
| `dsc.c` | Heat flow computation, baseline correction, peak detection |
| `ramp.c` | Temperature program (segmented ramps + holds) |
| `library.c` | 50-material DSC fingerprint library + k-NN matching |
| `display.c` | SH1106 OLED driver, heat-flow curve, status display |
| `sd_log.c` | microSD SPI driver, CSV logging |
| `ble_bridge.c` | UART protocol to ESP32-C3 for BLE/WiFi streaming |
| `safety.c` | Over-temp watchdog, comparator monitoring, thermal fuse |
| `battery.c` | LiPo voltage monitoring, charge status |
| `ui.c` | Button debouncing, menu navigation, mass entry |
| `startup_stm32g491xx.s` | Cortex-M4 startup code |
| `stm32g491_conf.h` | Register definitions, pin map |
| `stm32g491_lqfp64.ld` | Linker script |

### State Machine

```
  ┌──────┐  button A  ┌──────────┐  button A  ┌──────────┐
  │ IDLE │───────────▶│ SET_MASS │───────────▶│ SET_RAMP │
  └──────┘            └──────────┘            └──────────┘
       ▲                                          │ button A
       │                                          ▼
       │          ┌──────────┐           ┌──────────────┐
       │  done    │ COOLDOWN │◀──────────│  HEATING     │
       └──────────│ <50°C    │  T<50°C   │  (PID + DSC) │
                  └──────────┘           └──────────────┘
                                                │ button A
                                                ▼ (abort)
                                         ┌──────────────┐
                                         │   ABORT      │
                                         │  (heaters    │
                                         │   off)       │
                                         └──────┬───────┘
                                                │
                                          (any) │
                                                ▼
                                             ┌──────┐
                                             │ IDLE │
                                             └──────┘
```

## Python Companion App

`scripts/thermo_trace_app.py` — a BLE client that:
- Connects to Thermo Trace via BLE
- Receives live heat-flow + temperature data at 1 Hz
- Plots the DSC curve in real time (matplotlib)
- Performs peak detection, Tg analysis, and library matching on PC
- Exports data as CSV / JSON
- Supports calibration with indium/tin standards

`scripts/calibrate.py` — runs the calibration procedure:
- Prompts user to load indium standard, set mass, run scan
- Detects indium melting peak, compares to known values (156.6 °C, 28.71 J/g)
- Computes correction coefficients, sends to device via BLE
- Optionally repeats with tin standard for two-point calibration

## Assembly Guide

See [docs/assembly-guide.md](docs/assembly-guide.md) for step-by-step
assembly instructions.

## API Reference

See [docs/api-reference.md](docs/api-reference.md) for the BLE protocol,
firmware API, and data formats.

## Calibration Guide

See [docs/calibration-guide.md](docs/calibration-guide.md) for the
two-point calibration procedure using indium and tin standards.

## License

MIT — build it, sell it, improve it.