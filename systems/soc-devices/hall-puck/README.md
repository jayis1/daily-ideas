# Hall Puck — Pocket Hall Effect & Van der Pauw Semiconductor Characterization System

> **Bringing $10k–$50k benchtop Hall measurement systems (Lakeshore 8600, Ecopia HMS-3000, MMR H-50, Nanometrics HL5500PC) down to ~$44 and puck size.**

Hall Puck is a pocket-sized instrument that measures the fundamental electronic transport properties of semiconductor materials:

- **Sheet resistance / resistivity** (Van der Pauw method, ASTM F76)
- **Hall coefficient** (Hall effect with magnetic field reversal)
- **Carrier concentration** (n or p, in cm⁻³)
- **Carrier type** (n-type or p-type, from sign of Hall coefficient)
- **Carrier mobility** (in cm²/V·s)
- **Temperature-dependent measurement** (optional resistive heater, 25–80 °C)

Place a small semiconductor sample (5–20 mm square, any thickness up to 1 mm) on the spring-loaded 4-point sample holder. Hall Puck automatically runs the full Van der Pauw + Hall measurement sequence: it permutes current/voltage contacts via a solid-state switch matrix, reverses current to cancel thermoelectric offsets, rotates a neodymium magnet 180° to reverse the magnetic field, and computes all transport parameters on-device using CORDIC-accelerated math.

```
Carrier type:     n-type
Carrier conc:     1.23e16 cm⁻³
Resistivity:      0.452 Ω·cm
Mobility:         1120 cm²/V·s
Hall coeff:       -508 cm³/C
Temperature:      24.3 °C
B-field:          0.48 T
```

---

## Why Hall measurement?

The Hall effect and Van der Pauw measurements are the gold-standard methods for characterizing semiconductor electronic transport properties. They are essential for:

- **Semiconductor R&D** — doping concentration verification, mobility optimization, compensation ratio
- **Solar cell development** — absorber layer mobility/resistivity, TCO sheet resistance, junction quality
- **Thermoelectric materials** — power factor S²σ optimization requires accurate σ (conductivity) and carrier concentration
- **2D materials** — graphene, MoS₂, hBN transport characterization (Hall bar / Van der Pauw geometry)
- **Transparent conducting oxides** — ITO, AZO, FTO sheet resistance and carrier density for display/touch panel QA
- **Education** — solid-state physics laboratory experiments (Hall effect is a core undergraduate physics topic)
- **DIY / maker semiconductor projects** — homemade solar cells, thermoelectric generators, doped silicon characterization
- **Counterfeit detection** — verify carrier concentration and mobility match datasheet specifications

The Van der Pauw method is standardized as **ASTM F76** ("Standard Test Methods for Measuring Resistivity and Hall Coefficient of Single-Crystal Semiconductors").

---

## Highlights

| Feature | Detail |
|---|---|
| Measurement method | Van der Pauw (4-point) + Hall effect with field reversal |
| Sheet resistance range | 1 mΩ/□ – 100 kΩ/□ |
| Resistivity range | 10⁻⁶ – 10⁴ Ω·cm (sample-thickness dependent) |
| Hall coefficient range | ±10⁻³ – ±10⁵ cm³/C |
| Carrier concentration range | 10¹³ – 10²¹ cm⁻³ |
| Mobility range | 0.1 – 10⁵ cm²/V·s |
| Carrier type | n-type / p-type (automatic from Hall sign) |
| Current range | 1 µA – 10 mA (programmable, 2 ranges, auto-ranging) |
| Voltage resolution | ~0.5 µV (INA333 × ADS122U04 24-bit) |
| Magnetic field | 0.48 T (N52 neodymium, reversible via 180° stepper rotation) |
| Field reversal | 28BYJ-48 stepper + Hall switch position feedback |
| Contact switching | 2× ADG714 8-channel SPST SPI switch matrix (16 switches) |
| Temperature range | 25–80 °C (optional onboard resistive heater for T-dependent measurement) |
| Temperature sensor | DS18B20 (±0.5 °C, 1-wire) |
| Standard | ASTM F76 (Van der Pauw + Hall) |
| Measurement modes | Single-shot, temperature sweep, continuous monitoring, QA pass/fail |
| Display | 1.3" OLED (SSD1306, 128×64, SPI) — live results + Hall/voltage readings |
| Logging | MicroSD (FAT32) CSV; BLE + Wi-Fi live streaming via ESP32-C3 companion |
| Power | 18650 (3.7V, 3500 mAh) → 3.3V LDO; ~30 h battery or USB-C |
| Size | Ø72 × 28 mm (puck-shaped) |
| BOM cost | ~$44 (see `hardware/BOM.csv`) |

---

## SoC Architecture

```
                ┌──────────────────────────┐       UART       ┌──────────────────┐
                │   STM32G474RET6           │◄────────────────►│  ESP32-C3        │
                │   Cortex-M4 @ 170 MHz     │                  │  BLE 5.0 + WiFi  │
                │   512KB Flash, 96KB SRAM   │                  │  phone app link  │
                │   CORDIC + FMAC math      │                  │  CSV export      │
                │   • Van der Pauw engine   │                  └──────────────────┘
                │   • Hall coefficient calc │
                │   • Switch matrix control │
                │   • Current source PID    │
                │   • Magnet stepper control│
                │   • OLED + SD + flash     │
                └─────────────┬─────────────┘
                              │ SPI × 2 / DAC / GPIO / 1-wire / UART
           ┌──────────────────┼──────────────────────────────┐
           ▼                  ▼                ▼              ▼
  ┌────────────────┐  ┌───────────────┐  ┌──────────┐  ┌──────────┐
  │ ADS122U04      │  │ 2× ADG714     │  │ DAC1_OUT │  │ SSD1306  │
  │ 24-bit ADC     │  │ 16× SPST      │  │ → I src  │  │ OLED SPI │
  │ SPI (INA333)   │  │ switch matrix │  │ OPA2188  │  └──────────┘
  │ → µV voltage   │  │ 4-sample conn │  │ Howland  │
  └────────────────┘  └───────────────┘  └──────────┘
           │                  │                │
           ▼                  ▼                ▼
  ┌───────────────────────────────────────────────────────┐
  │              SAMPLE HOLDER (4 pogo pins)               │
  │   ┌─────────────────────────────────────────────────┐  │
  │   │  Contact 1 ●         ● Contact 2                │  │
  │   │              SAMPLE                              │  │
  │   │  Contact 4 ●         ● Contact 3                │  │
  │   └─────────────────────────────────────────────────┘  │
  │                     ▲ B-field (N52 magnet below)      │
  └───────────────────────────────────────────────────────┘
                                     │
                              ┌──────┴──────┐
                              │ 28BYJ-48    │  N52 magnet on
                              │ stepper     │  rotating arm
                              │ + ULN2003   │  (180° reversal)
                              └─────────────┘
```

- **STM32G474RET6** — Main SoC. Cortex-M4 at 170 MHz with hardware FPU, CORDIC (coordinate rotation), and FMAC (filter math accelerator). Runs the full measurement state machine: ADS122U04 SPI acquisition, current source control via internal DAC, ADG714 switch matrix permutation, stepper motor control for magnet reversal, Van der Pauw iterative solver, Hall coefficient computation, OLED UI, SD logging, and UART link to ESP32-C3. The CORDIC accelerator handles exp/log/sqrt for the Van der Pauw function and Arrhenius fitting.
- **ESP32-C3** — Companion SoC for BLE 5.0 + Wi-Fi connectivity. Receives measurement data and commands via UART from the STM32, streams live readings to a phone app via BLE GATT, and serves a Wi-Fi web UI for CSV download and remote control.
- **ADS122U04** — 24-bit delta-sigma ADC (TI). Configured for differential voltage measurement with PGA gain 1–128. Reads the INA333 instrumentation amplifier output. Provides ~0.5 µV resolution at the sample terminals.
- **INA333** — Chopper-stabilized instrumentation amplifier (TI). 10 µV max offset, 0.05 µV/°C drift. Programmable gain 1×–1000× via external resistor + analog switch. Measures the microvolt-level Hall voltage and Van der Pauw voltage drops.
- **2× ADG714** — 8-channel SPST analog switches (ADI), SPI-controlled. Form a 4×4 crosspoint switch matrix connecting the 4 sample contacts to I-force+, I-force-, V-sense+, V-sense- buses. Enables fully programmable Van der Pauw and Hall contact permutations.
- **OPA2188** — Zero-drift dual op-amp (TI). Implements a precision Howland current pump for the programmable current source (1 µA – 10 mA, 2 ranges).
- **28BYJ-48** — Stepper motor (via ULN2003 driver) that rotates the N52 neodymium magnet 180° for magnetic field reversal. Hall switch (DRV5053) provides position feedback.

---

## Block Diagram

```
 ┌──────────┐    ┌─────────────┐    ┌───────────────────────┐    ┌──────────────┐
 │ 18650    │───►│ TP4056      │───►│ STM32G474RET6         │───►│ SSD1306 OLED │
 │ 3500mAh  │    │ charger +   │    │  main SoC (170 MHz)   │    │ 1.3" 128×64  │
 │ 3.7V     │    │ 3.3V LDO    │    │  CORDIC + FMAC        │    └──────────────┘
 └──────────┘    └─────────────┘    └──────────┬────────────┘
       │                                      │ SPI1
       │                            ┌─────────┴──────────┐
       │                            ▼                    ▼
       │                   ┌──────────────┐    ┌──────────────────┐
       │                   │ ADS122U04    │    │ 2× ADG714        │
       │                   │ 24-bit ADC   │    │ 16× SPST switch  │
       │                   │ SPI @ 175SPS │    │ matrix (SPI)     │
       │                   └──────┬───────┘    └────────┬─────────┘
       │                          │ IN+               │ 4× sample
       │                          ▼                    ▼ contacts
       │                   ┌──────────────┐    ┌──────────────────┐
       │                   │ INA333       │    │ SAMPLE HOLDER    │
       │                   │ inst. amp    │    │ 4 pogo pins      │
       │                   │ gain 1–1000× │    │ ┌──┐  ┌──┐      │
       │                   └──────┬───────┘    │ │1●│  │●2│      │
       │                          │ V sense    │ │  SAMPLE  │    │
       │                          │            │ │4●│  │●3│      │
       │                          │            │ └──┘  └──┘      │
       │                          │            └──────────────────┘
       │                          │                     ▲ B
       │                          │            ┌──────────────────┐
       │                          │            │ N52 magnet       │
       │                          │            │ on 28BYJ-48 arm  │
       │                          │            │ + ULN2003 driver │
       │                          │            └──────────────────┘
       │                          │
       │    ┌────────────┐   ┌────┴───────┐    ┌──────────────┐
       │───►│ DAC1_OUT   │──►│ OPA2188    │───►│ I-force bus  │
       │    │ (internal) │   │ Howland    │    │ (→ switch →  │
       │    │ 12-bit     │   │ current    │    │  sample)     │
       │    │ 0–3.3V     │   │ pump       │    └──────────────┘
       │    └────────────┘   └────────────┘
       │
       │    ┌────────────┐    ┌────────────┐    ┌──────────────┐
       ├───►│ MicroSD    │    │ DS18B20    │    │ ESP32-C3     │
       │    │ FAT32 log  │    │ 1-wire     │    │ BLE + WiFi   │
       │    │ SPI2       │    │ temp sensor│    │ UART link    │
       │    └────────────┘    └────────────┘    └──────────────┘
       │
       │    ┌────────────┐    ┌────────────┐    ┌──────────────┐
       │───►│ Tactile    │    │ DRV5053    │    │ Resistive    │
       │    │ buttons×3  │    │ Hall sw    │    │ heater (opt) │
       │    │ GPIO       │    │ magnet pos │    │ PWM MOSFET   │
       │    └────────────┘    └────────────┘    └──────────────┘
```

---

## Pin Assignments (STM32G474RET6, LQFP-64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0 | I_SENSE_MON | Analog In | Current monitor (sense resistor ADC) |
| PA1 | HEATER_PWM | Output (TIM2_CH1) | Optional resistive heater MOSFET gate |
| PA2 | I_RANGE_SEL | Output | Current range select (0=high, 1=low) |
| PA3 | I_ENABLE | Output | Current source enable (high = enabled) |
| PA4 | DAC1_OUT | Analog Out | Current source programming voltage (0–3.3V) |
| PA5 | SPI1_SCK | Output | SPI1 clock (ADS122U04 + ADG714) |
| PA6 | SPI1_MISO | Input | SPI1 MISO (shared) |
| PA7 | SPI1_MOSI | Output | SPI1 MOSI (shared) |
| PA8 | ADC_CS | Output | ADS122U04 chip select |
| PA9 | USART1_TX | Output | UART to ESP32-C3 (PA9→ESP RX) |
| PA10 | USART1_RX | Input | UART from ESP32-C3 (ESP TX→PA10) |
| PA11 | INA_GAIN_SEL | Output | INA333 gain range select (0=low, 1=high) |
| PA12 | INA_GAIN_CLK | Output | INA333 gain resistor switch clock |
| PA15 | SW1_CS | Output | ADG714 #1 chip select (current matrix) |
| PB0 | SW2_CS | Output | ADG714 #2 chip select (voltage matrix) |
| PB1 | ADC_DRDY | Input | ADS122U04 data-ready interrupt |
| PB6 | I2C1_SCL | Output | Reserved (future I²C sensors) |
| PB7 | I2C1_SDA | I/O | Reserved (future I²C sensors) |
| PB10 | OLED_DC | Output | OLED data/command |
| PB11 | SD_CS | Output | MicroSD chip select |
| PB12 | OLED_CS | Output | OLED chip select |
| PB13 | SPI2_SCK | Output | SPI2 clock (OLED + SD) |
| PB14 | SPI2_MISO | Input | SPI2 MISO (SD card) |
| PB15 | SPI2_MOSI | Output | SPI2 MOSI (OLED + SD) |
| PC0 | STEP_IN1 | Output | 28BYJ-48 coil A (ULN2003 input) |
| PC1 | STEP_IN2 | Output | 28BYJ-48 coil B |
| PC2 | STEP_IN3 | Output | 28BYJ-48 coil C |
| PC3 | STEP_IN4 | Output | 28BYJ-48 coil D |
| PC4 | DS18B20_DQ | I/O (1-wire) | Sample temperature sensor |
| PC5 | MAGNET_POS | Input (ADC) | DRV5053 Hall sensor (magnet orientation) |
| PC8 | BTN_MEASURE | Input | Start measurement (active low) |
| PC9 | BTN_MODE | Input | Cycle mode (active low) |
| PC10 | BTN_MENU | Input | Menu/select (active low) |
| PC11 | STATUS_LED | Output | White status LED |
| PC12 | BUZZER | Output (TIM3_CH1) | PWM audio feedback |
| PC13 | HEATER_TEMP | Analog In | Optional heater temperature (NTC) |
| PC14 | nRST | Input | Reset button |
| PC15 | BOOT0 | Input | Boot mode |
| NRST | Reset | Input | Power-on reset |

### ESP32-C3 Companion Pin Assignments

| Pin | Function | Notes |
|-----|----------|-------|
| GPIO0 | UART_TX | To STM32 PA10 (RX) |
| GPIO1 | UART_RX | From STM32 PA9 (TX) |
| GPIO2 | STATUS_LED | Blue BLE/WiFi status LED |
| GPIO8 | I2C_SCL | Reserved |
| GPIO9 | I2C_SDA | Reserved |
| GPIO10 | WiFi_ANT | External antenna (optional) |

---

## Sample Holder Design

The sample holder uses 4 spring-loaded pogo pins arranged in a square pattern on the periphery of the sample:

```
    ┌───────────────────────────┐
    │                           │
    │  ●───────────────────●   │   Contact 1 (top-left)    Contact 2 (top-right)
    │  │                   │   │
    │  │     SAMPLE        │   │   Sample sits on thermally conductive platform
    │  │  (5–20 mm sq.)    │   │
    │  │                   │   │
    │  │                   │   │
    │  ●───────────────────●   │   Contact 4 (bot-left)    Contact 3 (bot-right)
    │                           │
    └───────────────────────────┘
              ▲ B-field
         (N52 magnet below)
```

- **Pogo pins**: P75-B2 spring-loaded test probes (0.68mm tip, 100g spring force)
- **Contact spacing**: Adjustable 5–20mm (two sliding rails)
- **Platform**: Copper-clad PCB (thermally conductive, for optional heating)
- **Sample thickness**: Up to 1.0 mm (pogo pin travel accommodates)
- **Contact placement**: Contacts must be on the periphery (Van der Pauw requirement)
- **Sample sizes**: 5mm × 5mm minimum, 20mm × 20mm maximum

For irregularly shaped samples, contacts just need to be on the boundary — the Van der Pauw method is shape-independent as long as the sample is simply connected (no holes) and uniformly thick.

---

## Measurement Theory

### Van der Pauw Method (Sheet Resistance / Resistivity)

The Van der Pauw method uses 4 contacts on the periphery of a thin, uniformly thick sample. By permuting which contacts carry current and which measure voltage, the sheet resistance is determined independent of sample shape.

**Step 1 — Resistance R_A:**
- Force current I between contacts 1→2
- Measure voltage V between contacts 3→4
- R_A = V₃₄ / I₁₂ (also measure with reversed current to cancel thermoelectric EMF)

**Step 2 — Resistance R_B:**
- Force current I between contacts 2→3
- Measure voltage V between contacts 4→1
- R_B = V₄₁ / I₂₃ (also with reversed current)

**Van der Pauw equation:**
```
exp(-π · R_A / R_s) + exp(-π · R_B / R_s) = 1
```

This is solved iteratively (Newton-Raphson) for the sheet resistance R_s. For the symmetric case R_A = R_B = R:
```
R_s = (π / ln(2)) · R ≈ 4.532 · R
```

**Resistivity:**
```
ρ = R_s · d    (Ω·cm, where d is sample thickness in cm)
```

### Hall Effect Measurement

**Step 1 — With magnetic field B+:**
- Force current I between contacts 1→3
- Measure voltage V₂₄ between contacts 2→4 with magnet in B+ orientation
- V_{+I,+B}

**Step 2 — Reverse current (still B+):**
- Force current I between contacts 3→1
- Measure V₄₂ = -V₂₄
- V_{-I,+B}

**Step 3 — Rotate magnet 180° for B-:**
- Repeat steps 1–2 with reversed field
- V_{+I,-B}, V_{-I,-B}

**Hall voltage (offset-free, 4-point method):**
```
V_H = (V_{+I,+B} - V_{-I,+B} - V_{+I,-B} + V_{-I,-B}) / 4
```

This cancels thermoelectric offsets, contact resistance asymmetries, and amplifier offsets.

**Hall coefficient:**
```
R_H = V_H · d / (I · B)    (cm³/C)
```

**Carrier concentration:**
```
n = 1 / (|R_H| · e)    (cm⁻³, where e = 1.602×10⁻¹⁹ C)
```

**Carrier type:**
- R_H > 0 → **p-type** (holes are majority carriers)
- R_H < 0 → **n-type** (electrons are majority carriers)

**Carrier mobility:**
```
μ = |R_H| / R_s    (cm²/V·s)
```

### Magnetic Field Reversal

A N52 neodymium magnet (Ø10mm × 5mm) provides ~0.48 T at the sample surface. The magnet is mounted on a rotating arm driven by a 28BYJ-48 stepper motor (2048 steps/rev via ULN2003). Rotating 180° (1024 steps) reverses the field direction through the sample. A DRV5053 Hall-effect switch provides position feedback for accurate 180° positioning.

The field strength B is calibrated using a known Hall sample (e.g., n-Si with known R_H) and stored in flash.

### Temperature-Dependent Measurement

An optional resistive heater (10 Ω polyimide film heater, 0.5W) on the sample platform allows temperature sweeps from 25–80 °C. The STM32 drives the heater via PWM and monitors temperature via DS18B20. At each temperature setpoint:

1. Wait for thermal equilibrium (±0.5 °C, 10s stable)
2. Run full Van der Pauw + Hall measurement
3. Log R_s(T), R_H(T), μ(T)
4. Advance to next setpoint

**Arrhenius analysis:**
```
μ(T) = μ₀ · T^(-n) · exp(-E_a / kT)
```

A plot of ln(μ·T^n) vs 1/T gives the activation energy E_a from the slope.

---

## Measurement Sequence

1. **Idle**: display last result, monitor sample temperature
2. **Contact check**: verify all 4 pogo pins make contact (impedance < 100 kΩ)
3. **Baseline**: zero the INA333 (auto-zero, short V+ to V-)
4. **Van der Pauw (no field)**:
   - R_A: I→1,2; V→3,4 (forward and reverse current)
   - R_B: I→2,3; V→4,1 (forward and reverse current)
   - Solve Van der Pauw equation for R_s
5. **Hall measurement (B+)**:
   - Rotate magnet to B+ position (Hall switch feedback)
   - I→1,3; V→2,4 (forward and reverse current) → V_{+I,+B}, V_{-I,+B}
6. **Hall measurement (B-)**:
   - Rotate magnet 180° to B- position
   - I→1,3; V→2,4 (forward and reverse current) → V_{+I,-B}, V_{-I,-B}
7. **Analysis**:
   - Compute V_H = (V_{+I,+B} - V_{-I,+B} - V_{+I,-B} + V_{-I,-B}) / 4
   - R_H = V_H · d / (I · B)
   - n = 1/(|R_H| · e)
   - type = sign(R_H)
   - μ = |R_H| / R_s
   - ρ = R_s · d
8. **Display + log**: show results on OLED; write CSV to SD; BLE notify via ESP32-C3

---

## Firmware

The main firmware runs on the STM32G474RET6 (bare-metal, CMSIS, no RTOS needed — the measurement is sequential). The ESP32-C3 companion runs ESP-IDF and handles BLE/Wi-Fi.

### Source layout

```
firmware/
├── Makefile                       # ARM GCC build (STM32G474)
├── STM32G474RET6_FLASH.ld         # Linker script
├── Core/
│   ├── Inc/
│   │   ├── main.h                 # Pin definitions, globals
│   │   ├── ads122u04.h            # 24-bit ADC driver (SPI)
│   │   ├── current_source.h       # Programmable Howland current pump
│   │   ├── vdp_switch.h           # ADG714 switch matrix control
│   │   ├── measurement.h          # Van der Pauw + Hall measurement engine
│   │   ├── magnet.h               # Stepper + magnet field reversal
│   │   ├── oled_display.h         # SSD1306 OLED driver (SPI)
│   │   ├── sd_logger.h            # MicroSD CSV logging
│   │   ├── esp32_link.h           # UART bridge to ESP32-C3
│   │   ├── flash_store.h          # Flash-based persistent storage
│   │   ├── buttons.h              # Debounced button input
│   │   └── database.h             # Semiconductor reference database
│   └── Src/
│       ├── main.c                 # Main application + state machine
│       ├── ads122u04.c            # ADS122U04 SPI driver
│       ├── current_source.c       # DAC → Howland pump → current
│       ├── vdp_switch.c           # ADG714 16-switch matrix
│       ├── measurement.c          # Van der Pauw solver + Hall computation
│       ├── magnet.c               # 28BYJ-48 stepper + DRV5053 feedback
│       ├── oled_display.c         # SSD1306 UI
│       ├── sd_logger.c            # FAT32 CSV logging
│       ├── esp32_link.c           # UART protocol to ESP32-C3
│       ├── flash_store.c          # STM32 flash emulation EEPROM
│       ├── buttons.c              # Debounced GPIO input
│       └── database.c             # 30-material reference library
└── esp32-c3/
    ├── CMakeLists.txt             # ESP-IDF project
    ├── sdkconfig.defaults         # ESP32-C3 config
    └── main/
        ├── CMakeLists.txt
        └── main.c                 # BLE GATT + WiFi AP + UART relay
```

### State machine

```
  ┌──────┐  button    ┌───────────┐  ok     ┌──────────┐  done    ┌──────────┐
  │ IDLE │──────────►│ CONTACT   │────────►│ VDP_MEAS │─────────►│ HALL_B+  │
  │      │           │ CHECK     │         │ (R_s)    │          │ (forward │
  │      │◄──────────│           │  fail   └──────────┘          │ + reverse│
  │      │  error    └───────────┘                               │  current)│
  │      │                                                       └────┬─────┘
  │      │                                                            │
  │      │          ┌───────────┐  done    ┌───────────┐             │
  │      │◄─────────│  RESULT   │◄─────────│ ANALYZE   │◄────────────┘
  │      │  button   │  display  │          │ compute   │      ┌──────────┐
  │      │           │  + log    │          │ R_H, n, μ │◄─────│ HALL_B-  │
  │      │           └───────────┘          └───────────┘      │ (magnet  │
  │      │                                                    │ reversed)│
  └──────┘                                                    └──────────┘
```

### Building

```bash
# STM32G474 firmware (requires arm-none-eabi-gcc toolchain)
cd firmware
make
# Flash via ST-Link:
make flash
# Or: openocd -f interface/stlink.cfg -f target/stm32g4x.cfg -c "program build/hall-puck.bin verify reset exit 0x08000000"

# ESP32-C3 companion (requires ESP-IDF v5.2+)
cd esp32-c3
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB1 flash
```

---

## BLE Interface (via ESP32-C3)

| UUID | Type | Description |
|------|------|-------------|
| 0x9201 | Service | Hall Puck Service |
| 0x9202 | Notify | Live voltage readings (8 bytes: config_u8 + V_x4_s16 + I_x4_s16) |
| 0x9203 | Read/Notify | Measurement result (28 bytes: R_s + R_H + n + μ + ρ + type + status) |
| 0x9204 | Write | Command (start/stop/set current/set thickness/set mode) |
| 0x9205 | Read | Device info (firmware version, B-field, calibration date) |

### Result Format (0x9203, 28 bytes)

| Offset | Size | Field | Unit | Type |
|--------|------|-------|------|------|
| 0 | 4 | sheet_resistance | Ω/□ | float32 LE |
| 4 | 4 | hall_coefficient | cm³/C | float32 LE (signed) |
| 8 | 4 | carrier_conc | cm⁻³ | float32 LE |
| 12 | 4 | mobility | cm²/V·s | float32 LE |
| 16 | 4 | resistivity | Ω·cm | float32 LE |
| 20 | 1 | carrier_type | enum | uint8 (0=n-type, 1=p-type) |
| 21 | 1 | status | enum | uint8 (0=done, 1=error, 2=warning) |
| 22 | 2 | temperature | °C × 100 | int16 |
| 24 | 4 | b_field | T | float32 LE |

---

## SD Card Log Format

Each measurement produces a CSV file `HP_YYYYMMDD_HHMMSS.csv`:

```csv
# Hall Puck measurement log
# Date: 2026-07-29T10:15:30Z
# Sample: n-Si wafer (unknown doping)
# Thickness: 0.500 mm
# Temperature: 24.3 C
# B-field: 0.482 T
# Current: 1.000 mA
# Result: Rs=4520.0 Ohm/sq, RH=-508.3 cm3/C, n=1.23e16 cm-3, mu=1124 cm2/Vs, type=n
# Columns: step, config, I_mA, V_uV, B_T, note
1, VDP_Ra_fwd, 1.000, 4520.0, 0.000, I=1->2, V=3->4
2, VDP_Ra_rev, -1.000, -4518.0, 0.000, I=2->1, V=4->3
3, VDP_Rb_fwd, 1.000, 3890.0, 0.000, I=2->3, V=4->1
4, VDP_Rb_rev, -1.000, -3892.0, 0.000, I=3->2, V=1->4
5, HALL_Bp_fwd, 1.000, 12.40, 0.482, I=1->3, V=2->4, B+
6, HALL_Bp_rev, -1.000, -12.38, 0.482, I=3->1, V=4->2, B+
7, HALL_Bm_fwd, 1.000, -12.42, -0.482, I=1->3, V=2->4, B-
8, HALL_Bm_rev, -1.000, 12.40, -0.482, I=3->1, V=4->2, B-
# END
```

---

## Calibration

### Magnetic field calibration
The N52 magnet field strength varies with magnet-to-sample distance and magnet grade. Calibrate using a sample with known Hall coefficient:

1. Place a reference sample (e.g., n-Si, R_H = -860 cm³/C) on the holder
2. Run Hall measurement → obtain R_H_measured and V_H
3. B_calibrated = V_H · d / (I · R_H_known)
4. Store B in flash; applied to all future measurements

### Current source calibration
1. Force 1 mA through a precision 1 kΩ resistor (0.1%)
2. Measure voltage drop with external DMM
3. Adjust DAC code → current lookup table in flash

### Voltage offset calibration
1. Short V_sense+ to V_sense- (via switch matrix)
2. Read ADS122U04 → offset code
3. Store as zero-correction; subtract from all measurements

Run `scripts/calibrate.py` for guided calibration over BLE.

---

## Comparison to Commercial Instruments

| Feature | Hall Puck | Lakeshore 8600 | Ecopia HMS-3000 | MMR H-50 |
|---------|-----------|----------------|-----------------|----------|
| Method | Van der Pauw + Hall | Van der Pauw + Hall | Van der Pauw + Hall | Van der Pauw + Hall |
| B-field | 0.48 T (permanent) | 0.5–1 T (electromagnet) | 0.55 T (permanent) | 0.5 T (permanent) |
| Current range | 1 µA – 10 mA | 10 pA – 100 mA | 1 nA – 20 mA | 1 µA – 50 mA |
| Voltage resolution | ~0.5 µV | ~10 nV | ~0.1 µV | ~1 µV |
| Temp range | 25–80 °C (heater) | 4–600 K (cryostat) | 80–500 K | 80–400 K |
| Size | Ø72×28 mm | Benchtop | Benchtop | Benchtop |
| Wireless | BLE + WiFi | None | None | None |
| Price | ~$44 | ~$20,000 | ~$15,000 | ~$12,000 |

Hall Puck trades the cryogenic temperature range, picoamp current capability, and nanovolt sensitivity of $15k+ benchtop systems for extreme portability, wireless connectivity, and 340× lower cost — sufficient for education, maker semiconductor projects, room-temperature QA, and field characterization where ~0.5 µV resolution and 25–80 °C temperature range are acceptable.

---

## Assembly Guide

See `docs/assembly_guide.md` for step-by-step build instructions, including:
- PCB fabrication (4-layer, 72mm circular)
- Sample holder and pogo pin assembly
- Magnet rotation mechanism
- Firmware flashing (STM32 + ESP32-C3)
- Calibration procedure
- 3D-printed enclosure (puck-shaped)

---

## License

MIT — build it, sell it, improve it.