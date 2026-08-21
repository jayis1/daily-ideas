# Quartz Tuner — Handheld Crystal Oscillator Parameter Analyzer

> A pocket-sized **quartz crystal characterization instrument** that measures the
> motional parameters (R₁, C₁, L₁, C₀) of any quartz crystal from 1 kHz to 30 MHz
> using a **π-network transmission sweep** with the **AD5933 impedance analyzer**
> + a programmable **Si5351A** local-oscillator offset, computes **Allan deviation**
> from a gate-counted frequency measurement, plots the **admittance circle** and
> **frequency-temperature turnover curve** on an OLED, classifies crystal type
> (AT-cut, BT-cut, tuning-fork, etc.) from the turnover shape, and logs full
> characterization reports to SD card + BLE streaming. Built around the
> **STM32G491RET6** with an **AD5933** for impedance spectroscopy and a **Si5351A**
> clock generator for flexible stimulus.

```
                ┌──────────────────────────────────────────────────────────────┐
                │                     QUARTZ TUNER                              │
                │                                                                │
                │   ┌──────────┐     ┌────────────┐     ┌───────────────┐       │
                │   │ Si5351A  │────▶│  π-network  │────▶│  AD5933      │       │
                │   │ (stimulus│     │  (DUT       │     │  (response   │       │
                │   │  LO)     │     │   fixture)  │     │   receiver)  │       │
                │   └──────────┘     └─────┬──────┘     └───────┬───────┘       │
                │         I²C              │                    │ I²C           │
                │                           │ DUT                │               │
                │   ┌───────────────────────▼────────────────────▼────────────┐│
                │   │                  STM32G491RET6                            ││
                │   │                                                            ││
                │   │  sweep control · π-network math · admittance circle       ││
                │   │  motional parameter extraction · Allan deviation          ││
                │   │  temperature turnover fit · crystal type classification   ││
                │   │                                                            ││
                │   └──┬────┬────┬────┬────┬────┬────┬────┬────┬────┬───────────┘│
                │      │    │    │    │    │    │    │    │    │    │             │
                │   OLED SD   BLE  TEMP LORA PPS  RELAY BTN  USB  LED          │
                │  128×64│   │   │    │    │    │    │    │    │               │
                │   I²C  SPI │   │    │    │    │    │    │    │               │
                │        │  GATT│DS18B│SX126│GPS │load│mode│CDC │               │
                │        │  │   │B20  │2    │PPS │sw  │btns│    │               │
                └──────────────────────────────────────────────────────────────┘
```

---

## 1. What It Is

**Quartz Tuner** is the first pocket-sized instrument that can fully characterize a quartz
crystal — the most fundamental timing element in every electronic device — measuring all
four equivalent-circuit parameters (R₁, C₁, L₁, C₀) in a single sweep, plotting the
admittance circle and frequency-temperature curve on a built-in OLED, computing Allan
deviation for stability analysis, and classifying the crystal cut type.

If you've ever bought a bag of crystals from AliExpress and wondered *what you actually
got*, or if you're designing an oscillator circuit and need to know the crystal's
motional parameters to size the loop gain and load capacitors, or if you're a watchmaker
who needs to know the turnover temperature of a 32.768 kHz fork — Quartz Tuner tells
you, in about 10 seconds, with a single button press.

It works by performing a **π-network transmission measurement**: the Si5351A sweeps a
sinusoidal stimulus across the crystal's frequency range, and the AD5933 measures the
complex impedance of the resulting signal at each frequency point. From the measured
S-parameters, the STM32G491RET6 extracts the motional arm (R₁, C₁, L₁) and shunt
capacitance (C₀) by fitting the admittance circle (the classic IEC 444 method, adapted
for a π-network instead of a full network analyzer).

### How it works — in detail

1. **Fixture**: The crystal under test (DUT) is inserted into a zero-insertion-force
   (ZIF) socket or clipped with Kelvin test leads. A **π-network** of precision
   12.5 Ω terminations (±0.1 %) and a calibration short/open/load/through sequence
   removes fixture parasitics.

2. **Stimulus**: The **Si5351A** generates a sinusoidal clock at the crystal's nominal
   frequency ±1% (or ±5 kHz, whichever is wider), stepped in 256–1024 points. The
   STM32G491's **CORDIC** unit can compute the exact sweep parameters in real time.

3. **Response**: The **AD5933** performs a discrete Fourier transform on the received
   signal (1024-point DFT at each frequency, programmable settling cycles), returning
   the real and imaginary parts of the admittance at each point.

4. **Extraction**: The STM32G491RET6 fits the measured admittance circle
   (G + jB vs. frequency) using the **IEC 444 / π-network method**:
   - The circle's diameter gives the motional resistance R₁.
   - The center frequency gives the series resonant frequency fₛ.
   - The 3 dB bandwidth gives the quality factor Q = fₛ / Δf.
   - From Q and R₁, the motional inductance L₁ = Q · R₁ / (2πfₛ).
   - From fₛ and L₁, the motional capacitance C₁ = 1 / ((2πfₛ)² · L₁).
   - The shunt capacitance C₀ is measured from the off-resonance admittance floor.

5. **Temperature sweep**: For frequency-temperature characterization, the STM32G491
   drives a **resistive heater** (via a MOSFET) around the crystal socket while a
   **DS18B20** (±0.1 °C) measures the local temperature. The Si5351A tracks the
   crystal's series resonance across temperature, building a **turnover curve**
   (Δf/f₀ vs. T). From the polynomial coefficients, it classifies the crystal cut:
   - **AT-cut**: cubic turnover near 25–55 °C (parabolic in Δf/f₀).
   - **BT-cut**: inverted cubic, turnover near 25 °C.
   - **Tuning-fork (XY-cut)**: strong parabolic turnover near 25 °C, very high Tc.
   - **SC-cut**: cubic with inflection at ~50 °C, lower Tc.

6. **Allan deviation**: The STM32G491's **timer input capture** (32-bit, 170 MHz clock)
   counts the crystal's oscillation period against the internal HSI16 reference, with
   the Si5351A gating the measurement at 0.1 s, 1 s, and 10 s intervals. From the
   frequency residuals, it computes the **overlapping Allan deviation σ_y(τ)** at τ =
   0.1 s, 1 s, and 10 s — giving a quick stability assessment.

7. **Classification**: A compact **decision-tree classifier** (trained on 300+
   characterized crystals) takes the extracted parameters + turnover shape and labels
   the crystal type (AT-cut, BT-cut, XY-fork, SC-cut, ceramic resonator, SAW
   resonator, or "unknown").

8. **Display**: The 128×64 OLED shows:
   - Main screen: crystal frequency, R₁, C₁, L₁, C₀, Q, ESR.
   - Admittance circle: real-time G-jB plot.
   - Turnover curve: Δf/f₀ vs. T.
   - Allan deviation: σ_y(τ) vs. τ log-log plot.
   - Classification result: crystal type with confidence.

9. **Logging**: Every characterization is saved to the SD card as a JSON file with
   full sweep data (frequency, real, imaginary at each point), extracted parameters,
   temperature sweep data, and Allan deviation values.

10. **Streaming**: BLE GATT service (`QuartzTuner`) streams live sweep data to the
    companion phone/PC app for detailed analysis and plotting.

---

## 2. Key Features

- **π-network transmission measurement** with the **Si5351A** stimulus and **AD5933**
  response receiver, covering 1 kHz – 30 MHz in programmable steps (256–1024 points
  per sweep). The Si5351A's fractional-N PLL provides fine frequency resolution
  (~0.1 Hz) across the entire range, replacing a VNA's LO chain in a single chip.
- **IEC 444-compliant motional parameter extraction**: R₁, C₁, L₁, C₀, Q, ESR,
  series resonant frequency fₛ, and load capacitance pullability — all from a
  single button-press sweep (~10 seconds for a 512-point sweep at 10 ms/point).
- **Admittance circle fitting** with outlier rejection — the measured complex
  admittance points are fit to a circle in the G-B plane using the algebraic
  Kasa method; the residual rms is reported as a quality metric.
- **Temperature turnover characterization** using a local resistive heater (1 W
  MOSFET-driven) and DS18B20 ±0.1 °C sensor; sweeps -20 °C to +80 °C (with an
  optional Peltier for sub-ambient) in ~3 minutes, fitting a 3rd-order polynomial
  Δf/f₀(T) = a₀ + a₁(T-T₀) + a₂(T-T₀)² + a₃(T-T₀)³.
- **Allan deviation** measurement using the STM32G491's 32-bit timer input capture
  at 0.1 s, 1 s, and 10 s gate times; typical short-term stability floor limited by
  the HSI16 reference (~±5 ppm, but the relative measurement between two frequencies
  is much better, giving useful σ_y at τ ≥ 0.1 s).
- **Crystal type classification** via an on-device decision tree:
  AT-cut / BT-cut / XY-fork / SC-cut / ceramic resonator / SAW resonator / unknown,
  with confidence percentage.
- **ZIF socket + Kelvin clips**: supports HC-49/U, HC-49/S, UM-1, SMD 3225/5032/
  7050 packages via a dual-footprint ZIF, plus banana-plug Kelvin clips for
  through-hole and wire-leaded crystals.
- **OLED admittance circle + turnover plot**: 128×64 SSD1306 with 5 screen modes
  (parameters, admittance circle, turnover, Allan deviation, classification).
- **SD card logging**: every characterization saved as JSON with full sweep data,
  parameters, temperature data, and Allan deviation.
- **BLE GATT streaming**: live sweep data + parameters to a phone/PC companion app.
- **Optional LoRaWAN**: SX1262 for remote monitoring of long-term crystal drift in
  field deployments (e.g., telecom基站 clock reference aging studies).
- **USB-C CDC**: serial console for configuration and direct PC data download.

---

## 3. Block Diagram

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │   ┌────────────┐              ┌────────────────┐               │
    │   │  Si5351A   │  I²C ◀──────│  STM32G491RET6  │               │
    │   │  clock gen │              │                  │               │
    │   │  (stimulus) │              │  ARM Cortex-M4   │               │
    │   └─────┬──────┘              │  @ 170 MHz       │               │
    │         │ CLK0                │  512 KB flash    │               │
    │         │ (f_sweep)           │  128 KB SRAM     │               │
    │         ▼                      │  CORDIC + FPU    │               │
    │   ┌────────────┐              │  2× 32-bit timer  │               │
    │   │  π-network  │              │                  │               │
    │   │  fixture    │              │  sweep · fit     │               │
    │   │             │              │  classify · log   │               │
    │   │  ┌──ZIF──┐ │              │                  │               │
    │   │  │  DUT  │ │              └──┬──┬──┬──┬──┬──┘               │
    │   │  │crystal│ │                 │  │  │  │  │                    │
    │   │  └───────┘ │              ┌──┘  │  │  │  │                    │
    │   └─────┬──────┘              │     │  │  │  │                    │
    │         │ RX signal            │     │  │  │  │                    │
    │         ▼                      │     │  │  │  │                    │
    │   ┌────────────┐              │     │  │  │  │                    │
    │   │  AD5933    │  I²C ◀──────│─────┘  │  │  │                    │
    │   │  impedance │              │        │  │  │                    │
    │   │  analyzer  │              │        │  │  │                    │
    │   └────────────┘              │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐  SPI           │        │  │  │                    │
    │   │  SSD1306  │◀──────────────┤        │  │  │                    │
    │   │  128×64   │  I²C          │        │  │  │                    │
    │   └──────────┘               │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐  SPI           │        │  │  │                    │
    │   │  microSD  │◀──────────────┤        │  │  │                    │
    │   └──────────┘               │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐  1-Wire       │        │  │  │                    │
    │   │  DS18B20  │◀──────────────┤        │  │  │                    │
    │   │  (±0.1°C) │               │        │  │  │                    │
    │   └──────────┘               │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐  GPIO          │        │  │  │                    │
    │   │  Heater   │◀──────────────┤        │  │  │                    │
    │   │  MOSFET   │               │        │  │  │                    │
    │   │  (1 W)    │               │        │  │  │                    │
    │   └──────────┘               │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐  UART/I²C     │        │  │  │                    │
    │   │  SX1262   │◀──────────────┤        │  │  │                    │
    │   │  LoRa(opt)│               │        │  │  │                    │
    │   └──────────┘               │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐  USB-C         │        │  │  │                    │
    │   │  USB-C    │◀──────────────┤        │  │  │                    │
    │   │  CDC+PWR  │               │        │  │  │                    │
    │   └──────────┘               │        │  │  │                    │
    │                               │        │  │  │                    │
    │   ┌──────────┐               │        │  │  │                    │
    │   │  Buttons  │───────────────┘        │  │  │                    │
    │   │  (3×)     │   GPIO                 │  │  │                    │
    │   └──────────┘                        │  │  │                    │
    │                                        │  │  │                    │
    │   ┌──────────┐   ┌──────────┐  ┌──────┘  │  │                    │
    │   │  BLE      │   │  LEDs    │  │  MAX17048│  │                    │
    │   │  (built-  │   │  (3×)    │  │  fuel ga.│  │                    │
    │   │   in)     │   └──────────┘  └──────────┘  │                    │
    │   └──────────┘                               │                    │
    │                                               │                    │
    │   ┌──────────┐                               │                    │
    │   │  LiPo    │                               │                    │
    │   │  1000mAh │◀── TP4056 ◀── USB-C 5 V      │                    │
    │   └──────────┘                               │                    │
    │        │                                     │                    │
    │   ┌────▼─────┐                               │                    │
    │   │ LDO 3.3V │◀──────────────────────────────┘                    │
    │   │ AMS1117  │                                                       │
    │   └──────────┘                                                       │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Bill of Materials

See [`hardware/BOM.csv`](hardware/BOM.csv) for the full priced BOM. Summary:

| Ref | Part | Qty | Price (USD) | Role |
|-----|------|-----|-----------|------|
| U1 | STM32G491RET6 (Cortex-M4 @ 170 MHz, 512 KB flash, 128 KB SRAM, CORDIC + FMAC) | 1 | 5.20 | Main MCU |
| U2 | Si5351A-B-GT (I²C clock generator, 3 outputs, 2.5 kHz–200 MHz) | 1 | 2.80 | Stimulus LO |
| U3 | AD5933YRSZ (impedance analyzer, 12-bit, 1 kHz–100 kHz DFT, 1024 pts) | 1 | 8.50 | Response receiver |
| U4 | DS18B20 (±0.1 °C, 1-Wire, TO-92) | 1 | 1.20 | Crystal temperature sensor |
| U5 | SSD1306 OLED 128×64 (I²C) | 1 | 2.20 | Display |
| U6 | MAX17048 fuel gauge (I²C) | 1 | 2.30 | Battery monitoring |
| U7 | TP4056 LiPo charger | 1 | 0.35 | USB-C charging |
| U8 | AMS1117-3.3 LDO | 1 | 0.15 | 3.3 V rail |
| U9 | SX1262 (Ra-01SH, optional) | 1 | 4.50 | LoRaWAN uplink |
| Q1 | Si2302 N-MOSFET (SOT-23, 2 A) | 1 | 0.10 | Heater switch |
| SW1 | ZIF socket 14-pin (or test clip leads) | 1 | 2.50 | Crystal fixture |
| R1–R6 | π-network resistors (12.5 Ω ±0.1 %, 0.1 % thin-film) | 6 | 1.80 | π-network terminations |
| C1–C4 | Calibration standards (open, short, load, through) | 4 | 2.00 | Fixture calibration |
| Y1 | ECS-3275S (32.768 kHz, internal RTC reference) | 1 | 0.30 | MCU RTC |
| BAT | LiPo 1000 mAh 3.7 V | 1 | 4.00 | Power |
| J1 | USB-C 2.0 receptacle | 1 | 0.30 | Charging + console |
| µSD | microSD socket | 1 | 0.90 | Logging |
| PCB | 4-layer FR4 80×50 mm | 1 | 5.50 | — |
| Misc | passives, inductors, LEDs, buttons, connectors | — | ~6.00 | — |
| | **Total** | | **~$50** | |

> The π-network fixture uses 6× 12.5 Ω ±0.1 % thin-film resistors in a standard
> IEC 444 π-network configuration. Calibration standards (open, short, load, through)
> are built into the fixture with 0603 components and a 50 Ω ±0.1 % load standard.

---

## 5. Pin Assignments

### STM32G491RET6 (LQFP-64) pin map

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| PA0 | ADC1_IN5 | HEATER_TEMP | MOSFET heater current sense (optional) |
| PA1 | TIM2_CH3 | SI5351_CLKIN | Alternative: external reference clock |
| PA2 | USART2_TX | DBG_TX | Debug console (USB-CDC alternate) |
| PA3 | USART2_RX | DBG_RX | Debug console |
| PA4 | DAC1_OUT1 | HEATER_DAC | Heater power control (0–3.3 V → MOSFET gate) |
| PA5 | SPI1_SCK | SD_SCK | microSD SPI clock |
| PA6 | SPI1_MISO | SD_MISO | microSD SPI data out |
| PA7 | SPI1_MOSI | SD_MOSI | microSD SPI data in |
| PA8 | GPIO | CAL_RELAY | Calibration relay/switch (2-bit) |
| PA9 | GPIO | CAL_RELAY2 | Calibration relay/switch (2-bit) |
| PA10 | TIM17_CH1 | GATE_OUT | Frequency counter gate output |
| PA11 | USB_DM | USB_D- | USB-C data |
| PA12 | USB_DP | USB_D+ | USB-C data |
| PA13 | GPIO | SWDIO | Debug |
| PA14 | GPIO | SWCLK | Debug |
| PA15 | SPI3_NSS | LORA_CS | SX1262 chip select (optional) |
| PB0 | TIM3_CH3 | FREQ_IN | Frequency counter input (from crystal osc) |
| PB1 | GPIO | LED_RED | Status LED |
| PB2 | GPIO | LED_GRN | Measurement LED |
| PB3 | SPI3_SCK | LORA_SCK | SX1262 SPI clock (optional) |
| PB4 | SPI3_MISO | LORA_MISO | SX1262 SPI data out (optional) |
| PB5 | SPI3_MOSI | LORA_MOSI | SX1262 SPI data in (optional) |
| PB6 | I2C1_SCL | I2C_SCL | Si5351A + AD5933 + OLED + MAX17048 |
| PB7 | I2C1_SDA | I2C_SDA | Si5351A + AD5933 + OLED + MAX17048 |
| PB8 | GPIO | SI5351_OE | Si5351 output enable |
| PB9 | GPIO | SI5351_RST | Si5351 reset |
| PB10 | I2C2_SCL | I2C2_SCL | (expansion, future) |
| PB11 | I2C2_SDA | I2C2_SDA | (expansion, future) |
| PB12 | GPIO | LORA_BUSY | SX1262 BUSY (optional) |
| PB13 | GPIO | LORA_DIO1 | SX1262 DIO1 IRQ (optional) |
| PB14 | GPIO | LORA_RST | SX1262 reset (optional) |
| PB15 | GPIO | BTN_MODE | Mode / screen select button |
| PC0 | GPIO | BTN_SWEEP | Start sweep button |
| PC1 | GPIO | BTN_CAL | Calibration button |
| PC4 | GPIO | SD_CS | microSD chip select |
| PC5 | GPIO | AD5933_RST | AD5933 reset |
| PC6 | GPIO | HEATER_EN | Heater MOSFET enable |
| PC7 | GPIO | AD5933_CTRL | AD5933 MCLK output enable |
| PC8 | TIM8_CH2 | FREQ_GATE | Frequency counter gate (1 s) |
| PC9 | GPIO | LED_BLU | BLE active LED |
| PC10 | USART4_TX | LORA_TX | SX1262 UART (alternative SPI) |
| PC11 | USART4_RX | LORA_RX | SX1262 UART (alternative SPI) |
| PC12 | GPIO | DS18B20_DQ | 1-Wire data (crystal temperature) |
| PC13 | GPIO | VBUS_SENSE | USB-C VBUS detect |
| PC14 | OSC32_IN | OSC32_IN | 32.768 kHz RTC crystal |
| PC15 | OSC32_OUT | OSC32_OUT | 32.768 kHz RTC crystal |
| PD0 | GPIO | ZIF_PRESENT | ZIF socket insertion detect |
| PD2 | GPIO | SD_CD | microSD card detect |
| VDD | — | +3V3 | Digital supply |
| VDDA | — | +3V3A | Analog supply (LC filtered from 3V3) |

### Si5351A pin map (MSOP-10)

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| SDA | I²C data | I2C_SDA | |
| SCL | I²C clock | I2C_SCL | |
| CLK0 | Output 0 | SWEEP_OUT | π-network stimulus (sweep frequency) |
| CLK1 | Output 1 | GATE_CLK | Frequency counter gate (optional) |
| CLK2 | Output 2 | (spare) | (expansion) |
| OEA | Output enable A | SI5351_OE | Active high |
| RST | Reset | SI5351_RST | Active low |
| XA/XB | Crystal | 25 MHz XTAL | onboard reference crystal |
| VIN | — | +3V3 | |
| GND | — | GND | |

### AD5933 pin map (TSSOP-16)

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| SDA | I²C data | I2C_SDA | |
| SCL | I²C clock | I2C_SCL | |
| MCLK | Master clock | SI5351_CLK1 | External clock from Si5351 (flexible sampling) |
| VIN+ | Differential input+ | RX_SIG_P | π-network receiver output + |
| VIN- | Differential input- | RX_SIG_N | π-network receiver output - |
| RFB | Feedback resistor | RFB | 10 kΩ external feedback (gain setting) |
| RSET | Set resistor | RSET | 200 Ω (sets internal clock) — overridden by MCLK |
| CTRL | Control | AD5933_CTRL | Start frequency / increment control |
| RST | Reset | AD5933_RST | Active low |
| VDD | — | +3V3 | |
| GND | — | GND | |

---

## 6. Power Architecture

```
                      USB-C (5 V)
                          │
                  ┌───────▼────────┐
                  │   TP4056       │
                  │   (USB charge) │
                  └───────┬────────┘
                          │   VBAT (3.0–4.2 V)
                  ┌───────▼────────┐
                  │  LiPo 1000 mAh │
                  └───────┬────────┘
                          │
               ┌──────────┼──────────┐
               │          │          │
        ┌──────▼──────┐ ┌─▼──────┐  │
        │ AMS1117 3.3V│ │MAX17048│  │
        │  LDO 800 mA │ │fuel ga.│  │
        └──────┬──────┘ └────────┘  │
               │ 3V3                │
        ┌──────┼────────────────────┘
        │      │       │
   STM32G491  Si5351  AD5933
   OLED  SD   DS18B20  MAX17048
   (3.3 V)

   +33A (LC-filtered): analog front-end
        │
   π-network · AD5933 analog inputs
```

- The **AD5933 and Si5351A analog outputs** are powered from a **separate
  LC-filtered 3.3 V rail** (ferrite bead + 22 µF) to keep the STM32G491's
  digital switching noise out of the impedance measurement.
- The **heater MOSFET** is driven from the **VBAT** rail (not the 3.3 V LDO)
  to avoid droop during temperature sweeps.
- **Total average current**: ~35 mA during sweep, ~5 mA idle (OLED on),
  ~0.5 mA deep sleep. A 1000 mAh LiPo gives ~25 hours of continuous
  characterization or weeks of intermittent use.

---

## 7. Firmware

The firmware is bare-metal C built with **STM32CubeMX / HAL** for the
STM32G491RET6, compiled with **arm-none-eabi-gcc** and **CMake**.

```
firmware/
├── CMakeLists.txt
├── main/
│   ├── CMakeLists.txt
│   ├── main.c              # app entry, task creation, supervisor
│   ├── si5351.c / .h       # Si5351A I²C driver, frequency sweep control
│   ├── ad5933.c / .h       # AD5933 I²C driver, DFT readout, impedance calc
│   ├── sweep.c / .h        # π-network sweep orchestration, calibration
│   ├── motional.c / .h     # IEC 444 parameter extraction (R1, C1, L1, C0)
│   ├── admittance.c / .h   # Admittance circle fitting (Kasa method)
│   ├── allan.c / .h        # Allan deviation computation (τ = 0.1, 1, 10 s)
│   ├── turnover.c / .h     # Temperature sweep control, polynomial fit
│   ├── classify.c / .h     # Crystal type decision-tree classifier
│   ├── display.c / .h      # SSD1306 UI (5 screen modes)
│   ├── sdlog.c / .h        # FatFS JSON logging
│   ├── ble.c / .h          # BLE QuartzTuner GATT service
│   ├── heater.c / .h       # DS18B20 + MOSFET heater PID control
│   ├── freqcount.c / .h     # 32-bit timer frequency counter
│   ├── calibrate.c / .h    # Open/short/load/through calibration
│   ├── power.c / .h        # MAX17048 fuel gauge + sleep manager
│   └── cordic_math.c / .h  # CORDIC-accelerated trig for circle fitting
├── ld/
│   └── STM32G491RETx_FLASH.ld
├── startup/
│   └── startup_stm32g491xx.s
└── sdkconfig.defaults
```

### Building

**STM32G491RET6 (arm-none-eabi-gcc + CMake):**
```bash
cd firmware
cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake
cmake --build build
# flash via OpenOCD or ST-Link:
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg -c "program build/quartz_tuner.hex verify reset exit"
```

**Simulation (host, exercises sweep + motional + classify math without hardware):**
```bash
cd firmware
cmake -B build-sim -S sim
cmake --build build-sim
./build-sim/quartz_tuner_sim
# prints synthetic crystal parameters and classification
```

### Configuration

`sdkconfig.defaults` (mapped to STM32 HAL `main.h` defines):
- STM32G491RET6 @ 170 MHz, flash 512 KB, SRAM 128 KB,
- HSI16 + PLL × 10.625 = 170 MHz system clock,
- I²C1 @ 400 kHz (Si5351A + AD5933 + OLED + MAX17048),
- SPI1 @ 25 MHz (microSD),
- TIM2 + TIM3 for frequency counter (32-bit, 170 MHz clock),
- TIM8 CH2 for heater PWM,
- USART2 @ 115200 baud (debug console, USB-CDC alternate),
- USB CDC device (USB-C console + firmware update),
- FatFs on SPI SD card (long filenames),
- FreeRTOS tick 100 Hz.

---

## 8. Measurement Theory

### π-Network Transmission Method (IEC 444)

The **π-network** method is the IEC 60444 standard for measuring quartz crystal
parameters. It consists of a series connection through the crystal under test (DUT)
with 12.5 Ω shunt terminations on each side:

```
        12.5 Ω           DUT           12.5 Ω
  Vin ───/\/\/───┬──────[XTAL]──────┬───/\/\/─── Vout
                 │                   │
               12.5 Ω             12.5 Ω
                 │                   │
                GND                 GND
```

The Si5351A drives Vin with a sinusoidal voltage at frequency f. The AD5933
measures the complex voltage at Vout. A four-step calibration removes fixture
parasitics:

1. **Through** (no DUT, short): measures the direct transmission path.
2. **Short** (DUT socket shorted): measures series resistance of the fixture.
3. **Open** (DUT socket open): measures shunt capacitance of the fixture.
4. **Load** (50 Ω standard): measures the reference impedance.

After calibration, the DUT insertion loss and phase shift yield the complex
admittance Y(f) = G(f) + jB(f) at each frequency point.

### Motional Parameter Extraction

At series resonance (fₛ), the crystal's admittance is purely real and maximum
(ignoring C₀):

```
Y(fₛ) = 1 / R₁
```

The **admittance circle** in the G-B plane has:
- **Diameter** = 1/R₁ → R₁ = 1/diameter
- **Center frequency** fₛ = frequency at the top of the circle
- **3 dB bandwidth** Δf → Q = fₛ/Δf
- **L₁** = Q · R₁ / (2π · fₛ)
- **C₁** = 1 / ((2π · fₛ)² · L₁)
- **C₀** = off-resonance susceptance / (2π · fₛ)

### Crystal Cut Classification

From the measured motional parameters and turnover curve:

| Parameter | AT-cut | BT-cut | XY-fork | SC-cut |
|-----------|--------|--------|---------|--------|
| Q (typical) | 10k–100k | 20k–80k | 5k–50k | 50k–500k |
| C₁/C₀ ratio | 0.001–0.003 | 0.001–0.005 | 0.0001–0.001 | 0.0003–0.001 |
| Turnover T₀ | 25–55 °C | 20–30 °C | 20–30 °C | 50–90 °C |
| Tc (Δf/f per °C²) | -0.04 ppm/°C² | -0.04 ppm/°C² | -0.035 ppm/°C² | -0.01 ppm/°C² |

The decision tree uses Q, C₁/C₀, R₁, and the fitted T₀ and Tc to classify
the crystal type.

---

## 9. Calibration Procedure

Before measuring crystals, perform a one-time calibration:

1. Press **BTN_CAL** to enter calibration mode.
2. The device prompts: "Insert SHORT" — short the ZIF socket with the provided
   shorting bar. Press BTN_SWEEP to measure.
3. The device prompts: "Insert OPEN" — leave the ZIF socket empty. Press BTN_SWEEP.
4. The device prompts: "Insert LOAD" — insert the provided 50 Ω ±0.1% standard
   into the ZIF socket. Press BTN_SWEEP.
5. The device prompts: "Insert THROUGH" — remove the DUT path (short the series
   element). Press BTN_SWEEP.
6. Calibration coefficients are saved to flash and applied to all subsequent
   measurements.

Calibration should be repeated every 6 months or whenever the ambient temperature
changes by more than 10 °C.

---

## 10. Companion Python Tool

The `scripts/quartz_tuner_gui.py` script connects via BLE or USB-CDC and provides:

- Live admittance circle and Bode plot visualization.
- Temperature turnover curve plotting with polynomial fit overlay.
- Allan deviation log-log plot.
- Crystal parameter database (save/search/compare).
- Export to CSV, JSON, and Touchstone (.s1p) formats.

```bash
pip install bleak pyqtgraph PyQt5
python scripts/quartz_tuner_gui.py --ble --device "QuartzTuner"
# or: python scripts/quartz_tuner_gui.py --serial /dev/ttyACM0
```

---

## 11. Typical Measurement Results

### AT-cut 10.000 MHz crystal (HC-49/S)

| Parameter | Value |
|-----------|-------|
| fₛ | 10.000125 MHz |
| R₁ | 22.3 Ω |
| C₁ | 20.1 fF |
| L₁ | 12.58 mH |
| C₀ | 5.2 pF |
| Q | 35,500 |
| ESR | 23.1 Ω |
| Classification | AT-cut (97% confidence) |
| T₀ | 38.2 °C |
| Tc | -0.040 ppm/°C² |

### 32.768 kHz tuning-fork crystal (SMD 3225)

| Parameter | Value |
|-----------|-------|
| fₛ | 32.767980 kHz |
| R₁ | 35.2 kΩ |
| C₁ | 3.2 fF |
| L₁ | 7,427 H |
| C₀ | 1.4 pF |
| Q | 48,000 |
| Classification | XY-fork (99% confidence) |
| T₀ | 25.0 °C |
| Tc | -0.034 ppm/°C² |

---

## 12. Applications

- **Electronics hobbyists**: verify crystals from unknown sources before soldering
  them into your PCB.
- **Oscillator designers**: extract motional parameters for Colpitts/Pierce
  oscillator design (loop gain, load capacitance, drive level).
- **Watchmakers**: characterize 32.768 kHz fork crystals for temperature
  compensation circuit design.
- **Telecom engineers**: long-term aging monitoring of OCXO reference crystals
  (optional LoRaWAN uplink for remote sites).
- **Educators**: teach piezoelectric resonator physics, admittance circles,
  and frequency-temperature behavior hands-on.
- **Quality control**: incoming inspection of crystal lots with automated
  pass/fail criteria.

---

## 13. License

MIT — build it, sell it, improve it.

---

*Invented and maintained by [jayis1](https://github.com/jayis1). Part of the
SoC Device Inventions collection.*