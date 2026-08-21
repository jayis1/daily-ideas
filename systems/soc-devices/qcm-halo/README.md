# QCM Halo — Pocket QCM-D (Quartz Crystal Microbalance with Dissipation)

> Bringing $30k–$120k lab QCM-D instruments (Q-Sense E1/E4, Bioline QCM, Stanford Research QCM200) down to ~$69 and coffee-mug size, with on-device viscoelastic modeling that commercial pocket units don't offer.

## What It Is

**QCM Halo** is a pocket-sized Quartz Crystal Microbalance with Dissipation monitoring (QCM-D) instrument that measures nanogram-scale mass changes and viscoelastic properties of thin films, coatings, biomolecular layers, and liquids in real time.

A QCM-D works by driving an AT-cut quartz crystal resonator at its series resonance frequency (typically 5–10 MHz), tracking frequency shifts (Δf) to measure mass changes via the Sauerbrey equation, and simultaneously measuring the dissipation factor (D) — the rate at which the crystal's oscillation decays when the drive is briefly turned off. The combination of Δf and ΔD reveals whether an adsorbed layer is rigid (small ΔD, Sauerbrey-valid) or viscoelastic (large ΔD, requiring Voigt modeling), enabling measurement of:

- **Thin film thickness** (sub-nanometer to micrometer)
- **Biomolecular adsorption** (protein binding, DNA hybridization, lipid bilayer formation)
- **Polymer swelling and hydration** (PNIPAM, hydrogels)
- **Cell adhesion and viscoelasticity**
- **Liquid viscosity and density** (via Kanazawa–Gordon)
- **Corrosion layer growth**
- **Drug–target binding kinetics** (kon/koff)

## Key Features

- **Dual QCM-D channel** — simultaneous measurement on 2 crystals (sample + reference)
- **5 or 10 MHz AT-cut quartz crystals** with standard crystal holders
- **Frequency tracking** with ±0.01 Hz resolution via reciprocal counting (gate time 1 s)
- **Dissipation measurement** via ring-down decay capture at 20 Msps (ADC + DMA)
- **On-device Voigt viscoelastic model fitting** (Levenberg–Marquardt) for soft films
- **Sauerbrey, Kanazawa–Gordon, and dissipation-shift (ΔD/Δf) analysis**
- **6 overtone support** (fundamental + 3rd/5th/7th/9th/11th harmonics)
- **Peristaltic liquid handling** — mini peristaltic pump + 6-way valve for buffer/sample switching
- **Peltier temperature control** — 15–50 °C ±0.01 °C for kinetic studies
- **OLED display** — live Δf/ΔD plots
- **SD card logging** — CSV at up to 10 Hz
- **BLE + Wi-Fi streaming** via ESP32-C3 to a phone/PC app
- **LiPo battery** — 8+ hours of continuous operation

## Block Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        QCM Halo                                 │
│                                                                 │
│  ┌──────────┐    SPI     ┌──────────────┐    UART   ┌────────┐  │
│  │ Si5351A  │◄──────────►│  STM32G474   │◄────────►│ESP32-C3│  │
│  │ Clock    │            │  RET6 (MCU)  │          │ BLE/WiFi│  │
│  │ Gen      │            │              │          └────────┘  │
│  └────┬─────┘            │              │                       │
│       │ CLK              │              │                       │
│       ▼                  │              │                       │
│  ┌──────────┐   Drive    │              │                       │
│  │ TX/RX    │◄──────────►│  TIM/DMA     │                       │
│  │ Switch   │            │              │                       │
│  └────┬─────┘            │              │                       │
│       │                  │              │                       │
│       ▼                  │              │                       │
│  ┌──────────┐    RF      │              │                       │
│  │QCM Crystal│◄─────────►│  ADC+DMA     │                       │
│  │5/10 MHz  │  Sense     │  (ring-down) │                       │
│  └────┬─────┘            │              │                       │
│       │                  │              │                       │
│       ▼                  │              │                       │
│  ┌──────────┐            │              │     I2C                │
│  │ LTC1968  │───────────►│  ADC         │────────►│OLED SH1106│  │
│  │ RMS-DC   │  Dissip.   │              │         └───────────┘  │
│  └──────────┘            │              │                        │
│                          │              │     SPI                 │
│  ┌──────────┐   I2C      │              │────────►│ MicroSD    │  │
│  │ DS18B20  │──────────►│              │         └───────────┘  │
│  │ Temp     │            │              │                        │
│  └──────────┘            │              │     I2C                │
│                          │              │────────►│ BME280     │  │
│  ┌──────────┐   PWM      │              │         └───────────┘  │
│  | Peristaltic│◄─────────│              │                        │
│  | Pump      │           │              │     GPIO               │
│  └──────────┘            │              │────────►│ DRV8833    │  │
│                          │              │         │ Valve      │  │
│  ┌──────────┐   PID/PWM  │              │         └───────────┘  │
│  │ TEC1-    │◄───────────│              │                        │
│  │ 12704    │            └──────────────┘                        │
│  │ Peltier  │                                                    │
│  └──────────┘     ┌────────────┐                                 │
│                   │ ADS122U04  │  PT1000 RTD                     │
│                   │ 24-bit ADC │◄───────────────────────────────  │
│                   └────────────┘                                 │
│                                                                 │
│  Power: MCP73831 charger + TPS63020 buck-boost + TPS7A4700 LDO   │
│  Battery: 3.7V 2000mAh LiPo                                     │
└─────────────────────────────────────────────────────────────────┘
```

## SoC Architecture

### Main MCU: STM32G474RET6
- 170 MHz Cortex-M4F with FPU + CORDIC + FMAC
- 512 KB flash, 96 KB SRAM
- Multiple TIM (for reciprocal counting, PWM, pump control)
- 5 Msps ADC with DMA (ring-down capture)
- HRTIM for high-resolution drive signal
- SPI/I2C/UART peripherals

### Wireless MCU: ESP32-C3-MINI-1
- RISC-V single-core, BLE 5.0 + Wi-Fi
- UART bridge to STM32 for BLE streaming and Wi-Fi web dashboard
- OTA firmware update capability

## How QCM-D Works

### Frequency Measurement (Sauerbrey)

When mass is added to a quartz crystal surface, its resonance frequency decreases:

```
Δf = -(2 * f0² * Δm) / (A * sqrt(ρq * μq))
```

Where f0 is the fundamental frequency, Δm is the mass change, A is the active area, ρq = 2650 kg/m³ (quartz density), μq = 2.947×10¹⁰ Pa (quartz shear modulus).

For a 5 MHz crystal: sensitivity ≈ 17.7 ng/cm²/Hz. For 10 MHz: ≈ 4.42 ng/cm²/Hz.

### Dissipation Measurement (Ring-Down)

The dissipation factor D is the inverse of the quality factor Q:

```
D = 1/Q = E_dissipated / (2π * E_stored)
```

The crystal is driven at resonance, then the drive is abruptly disconnected. The oscillation decays exponentially:

```
A(t) = A0 * exp(-π * f0 * D * t)
```

By capturing the decay envelope at 20 Msps and fitting an exponential, D is extracted with ~1×10⁻⁸ resolution.

### Viscoelastic Modeling (Voigt)

When ΔD/Δf > 0.4×10⁻⁶/Hz (rule of thumb), the film is "soft" and the Sauerbrey equation underestimates mass. A Voigt viscoelastic model is fitted across multiple overtones using Levenberg–Marquardt:

- Film thickness (d_f)
- Film viscosity (η_f)
- Film shear modulus (μ_f)
- Film density (ρ_f)

The QCM Halo fits these parameters on-device using the FMAC unit for matrix operations.

### Kanazawa–Gordon (Liquid)

For a crystal in contact with a Newtonian liquid:

```
Δf = -f0^(3/2) * sqrt(ρl * ηl / (π * ρq * μq))
```

This allows liquid viscosity/density measurement without a film.

## Pin Assignments (STM32G474RET6)

| Pin | Function | Description |
|-----|----------|-------------|
| PA0  | ADC1_IN1  | Ring-down signal (analog envelope) |
| PA1  | ADC1_IN2  | RMS-DC dissipation voltage (LTC1968) |
| PA2  | USART2_TX | ESP32-C3 UART TX |
| PA3  | USART2_RX | ESP32-C3 UART RX |
| PA4  | SPI1_NSS  | Si5351A (via split: Si5351 is I2C — this is for W25Q128) |
| PA5  | SPI1_SCK  | SPI clock (W25Q128 flash) |
| PA6  | SPI1_MISO | SPI MISO |
| PA7  | SPI1_MOSI | SPI MOSI |
| PA8  | TIM1_CH1  | Drive signal gate (TX enable) |
| PA9  | TIM1_CH2  | RX enable (switch to sense) |
| PA10 | GPIO      | TX/RX switch control |
| PA11 | GPIO      | Crystal 1 select |
| PA12 | GPIO      | Crystal 2 select |
| PA13 | SWDIO     | Debug |
| PA14 | SWCLK     | Debug |
| PA15 | TIM2_CH1  | Reciprocal counting gate (frequency measurement) |
| PB0  | ADC1_IN15 | Battery voltage divider |
| PB1  | GPIO      | Pump enable |
| PB2  | GPIO      | Valve A control |
| PB3  | SPI3_SCK  | OLED (SH1106) — shared I2C |
| PB4  | GPIO      | Valve B control |
| PB5  | GPIO      | Valve C control |
| PB6  | I2C1_SCL  | Si5351A, OLED, BME280, ADS122U04 |
| PB7  | I2C1_SDA  | I2C bus |
| PB8  | TIM4_CH3  | Peltier PWM (TEC control) |
| PB9  | GPIO      | TEC enable |
| PB10 | TIM2_CH3  | Pump PWM |
| PB11 | GPIO      | Status LED R |
| PB12 | GPIO      | Status LED G |
| PB13 | GPIO      | Status LED B |
| PB14 | GPIO      | Button A (mode) |
| PB15 | GPIO      | Button B (select) |
| PC0  | ADC2_IN1  | Peltier current sense |
| PC1  | GPIO      | Heater enable (aux) |
| PC4  | GPIO      | SD card detect |
| PC10 | SPI3_NSS  | SD card CS (or use SDIO) |
| PC11 | SPI3_MISO | SD card MISO |
| PC12 | SPI3_MOSI | SD card MOSI |
| PC13 | GPIO      | Crystal holder temperature DS18B20 (1-Wire) |
| PD2  | GPIO      | Ring-down trigger |

### ESP32-C3-MINI-1

| Pin | Function | Description |
|-----|----------|-------------|
| GPIO2 | UART0_TX | To STM32 USART2_RX |
| GPIO3 | UART0_RX | To STM32 USART2_TX |
| GPIO8 | I2C_SCL  | (unused, available for expansion) |
| GPIO9 | I2C_SDA  | (unused, available for expansion) |
| GPIO10| GPIO     | Boot/Mode button |

## Power Architecture

```
USB-C 5V ──► MCP73831 ──► LiPo 3.7V 2000mAh
                              │
                              ▼
                         TPS63020 ──► +3.3V (digital rail)
                              │
                              ├──► TPS7A4700 ──► +3.3V (analog rail, low-noise)
                              │
                              └──► Boost to +12V ──► TEC driver (Peltier)
                                    (MT3601)

Battery life: ~8 hours continuous QCM-D + Peltier
Charge time: ~4 hours via USB-C
```

## Liquid Handling

- **Peristaltic pump**: Gardena-style mini peristaltic pump (0.5–5 mL/min) driven by a small DC motor with PWM speed control
- **6-way rotary valve**: 3D-printed valve body with 28BYJ-48 stepper for buffer/sample switching
- **Flow cell**: 3D-printed PEEK-compatible flow cell holding the QCM crystal, ~50 µL volume
- **Temperature-controlled crystal holder**: Aluminum block with TEC1-12704 Peltier, PT1000 RTD feedback via ADS122U04

## BOM Summary

| Component | Part | Qty | Price |
|-----------|------|-----|-------|
| Main MCU | STM32G474RET6 | 1 | $5.80 |
| Wireless | ESP32-C3-MINI-1 | 1 | $2.60 |
| Clock Gen | Si5351A-B-GT | 1 | $2.50 |
| RMS-DC | LTC1968 | 1 | $4.20 |
| ADC | ADS122U04 | 1 | $3.40 |
| OLED | SH1106 1.3" | 1 | $2.80 |
| SD Card | MicroSD socket | 1 | $0.60 |
| Flash | W25Q128JVSIQ | 1 | $0.60 |
| Temp | DS18B20 | 1 | $0.80 |
| Env | BME280 | 1 | $1.20 |
| Peltier | TEC1-12704 | 1 | $2.10 |
| RTD | PT1000 4-wire | 1 | $1.50 |
| Pump | Mini peristaltic | 1 | $3.20 |
| Valve | 28BYJ-48 + 3D valve | 1 | $1.80 |
| Motor drv | DRV8833 | 1 | $0.80 |
| Crystal | 5 MHz AT-cut QCM | 3 | $4.50 |
| Holder | QCM crystal holder | 2 | $6.00 |
| RF switch | ADG918 RF switch | 2 | $2.40 |
| Op-amp | OPA656 | 2 | $3.40 |
| Charger | MCP73831 | 1 | $0.70 |
| Buck-boost | TPS63020 | 1 | $2.10 |
| LDO | TPS7A4700 | 1 | $0.90 |
| Boost | MT3601 | 1 | $0.50 |
| LiPo | 2000mAh | 1 | $4.50 |
| USB-C | 16-pin receptacle | 1 | $0.40 |
| Passives | 0603 set | 60 | $1.20 |
| PCB | 4-layer 90×60mm | 5 | $2.00 |
| Enclosure | 3D printed PETG | 1 | $0.00 |
| Misc | M2 screws, connectors | — | $1.50 |
| **TOTAL** | | | **~$69.30** |

See `hardware/BOM.csv` for the full detailed BOM.

## Firmware

The firmware is written in C and built with CMake + arm-none-eabi-gcc. See `firmware/` for source code.

### Build

```bash
cd firmware
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=../cmake/arm-none-eabi.cmake
make -j$(nproc)
```

Flash with ST-Link:
```bash
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
  -c "program qcm_halo.elf verify reset exit"
```

### Main modules

| File | Description |
|------|-------------|
| `main.c` | State machine, UI, orchestration |
| `qcm_driver.c` | Crystal drive, frequency counting, ring-down capture |
| `dissipation.c` | Ring-down exponential fitting, D computation |
| `sauerbrey.c` | Sauerbrey mass, Kanazawa–Gordon liquid analysis |
| `voigt.c` | Voigt viscoelastic model fitting (Levenberg–Marquardt) |
| `overtone.c` | Multi-overtone measurement sequencing |
| `temperature.c` | Peltier PID control via ADS122U04 + PT1000 |
| `liquid.c` | Peristaltic pump + valve control |
| `display.c` | OLED rendering (Δf/ΔD plots, menus) |
| `storage.c` | SD card CSV logging + W25Q128 flash |
| `ble_bridge.c` | UART protocol to ESP32-C3 |
| `esp_bridge.c` | ESP32-C3 firmware (BLE GATT + Wi-Fi) |
| `power.c` | Battery monitoring, power management |

## Python Scripts

| Script | Description |
|------|-------------|
| `live_view.py` | Real-time BLE dashboard (Δf/ΔD plots) |
| `voigt_fit.py` | Offline Voigt model fitting (cross-check) |
| `sauerbrey_calc.py` | Mass/thickness calculator |
| `calibrate.py` | Crystal calibration (air + water baseline) |
| `export_csv.py` | Export SD logs to analysis-ready CSV |
| `experiment.py` | Scripted experiment runner (binding kinetics) |

## Applications

### Biomolecular Binding Kinetics
Real-time protein–ligand binding (kon, koff, KD) by flowing analyte over an immobilized target on the crystal surface. Δf tracks mass accumulation; ΔD reveals conformational changes.

### Lipid Bilayer Formation
Monitor supported lipid bilayer (SLB) formation from vesicle rupture — a characteristic Δf/ΔD signature shows the vesicle-to-bilayer transition.

### Polymer Swelling
Track PNIPAM or hydrogel swelling/deswelling as temperature crosses LCST — Δf and ΔD show water uptake and structural change.

### Liquid Viscosity/Density
Quick measurement of liquid viscosity (0.1–100 cP) and density using the Kanazawa–Gordon equation — useful for fuel, lubricant, beverage, and pharmaceutical QC.

### Corrosion Monitoring
Track oxide/hydroxide layer growth on metal-coated crystals in corrosive environments — nanogram sensitivity detects early-stage corrosion.

### Drug Film Dissolution
Monitor dissolution rate of thin drug films under simulated gastric/intestinal fluid — pharmaceutical formulation screening.

## Comparison to Commercial Instruments

| Feature | Q-Sense E4 ($95k) | SRS QCM200 ($4.5k) | **QCM Halo (~$69)** |
|---------|-------------------|--------------------|-----------------------|
| Channels | 4 | 1 | 2 |
| Dissipation (D) | ✓ | ✗ | ✓ |
| Multi-overtone | ✓ (7) | ✗ | ✓ (6) |
| Voigt modeling | Software (PC) | ✗ | On-device |
| Liquid flow | ✓ | Optional | ✓ |
| Temperature control | ✓ (20–80°C) | ✗ | ✓ (15–50°C) |
| Battery | ✗ | ✗ | ✓ |
| BLE/Wi-Fi | ✗ | ✗ | ✓ |
| Size | Benchtop | Benchtop | Pocket |
| Price | $95,000 | $4,500 | $69 |

## License

MIT — build it, sell it, improve it.

---

*Invented as device #56 in the SoC Device Inventions collection.*