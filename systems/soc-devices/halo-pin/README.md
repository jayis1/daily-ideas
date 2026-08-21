# Halo Pin — Pocket Optical Particle Counter

> A battery-powered, pocket-sized optical particle counter (OPC) that
> measures airborne particle size distribution (16 bins, 0.3–40 µm)
> via 90° Mie scattering of a 650 nm laser, computes PM1/PM2.5/PM10
> mass concentration, and streams results over BLE — bringing
> $2k–$8k handheld particle counters (TSI AeroTrak, Met One HHPC)
> down to ~$52 and pocket size.

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         HALO PIN                                      │
 │        Pocket optical particle counter (OPC)                          │
 │                                                                       │
 │  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌────────────┐     │
 │  │ 650nm    │───▶│  Airflow  │───▶│ Particle │───▶│ OPT101     │     │
 │  │ 5mW laser│    │  nozzle   │    │ crosses  │    │ photodiode │     │
 │  │ (NCP500  │    │ 1.5mm jet │    │ beam at  │    │ + TIA      │     │
 │  │  driver) │    └───────────┘    │  90° scat │    └─────┬──────┘     │
 │  └────┬─────┘                     └──────────┘          │            │
 │       │  monitor PD                                      │ 0–3.3V    │
 │       ▼  (BPW34)                                        ▼            │
 │  ┌──────────┐                               ┌──────────────────┐    │
 │  │ ADC2 IN3 │                               │  STM32G474 ADC1   │    │
 │  │ laser    │                               │  500 ksps 12-bit  │    │
 │  │ power fb │                               │  DMA circular    │    │
 │  └──────────┘                               │  → pulse detect  │    │
 │                                              │  → size binning  │    │
 │  ┌──────────┐                               │  → mass conc.    │    │
 │  │ SDP810   │◀── dP across restrictor       │  → PM1/2.5/10   │    │
 │  │ flow mon │                               └────────┬─────────┘    │
 │  └──────────┘                                        │              │
 │                                            ┌─────────┴──────────┐   │
 │  ┌──────────┐                               │  OLED + SD + BLE  │   │
 │  │ SHT45/BME│── T/RH/P correction           │  SH1106 + microSD │   │
 │  └──────────┘                               │  + ESP32-C3 BLE   │   │
 │                                              └──────────────────┘    │
 │  SoC: STM32G474RET6 (170 MHz, CORDIC, FMAC, 500 ksps ADC)            │
 │  BLE: ESP32-C3-MINI-1  ·  OLED: SH1106 128×64  ·  SD: microSD        │
 └──────────────────────────────────────────────────────────────────────┘
```

## What It Does

Halo Pin is a complete optical particle counter that fits in a
pocket. On a button press, the device:

1. **Draws air** — a micro blower pulls ambient air at 1.0 L/min
   through a focused nozzle (1.5 mm jet) across the laser beam's
   focal region. A Sensirion SDP810 differential-pressure sensor
   across a calibrated flow restrictor provides closed-loop flow
   control.
2. **Illuminates** — a 650 nm, 5 mW laser diode (driven by an NCP500
   constant-current controller with monitor-photodiode feedback)
   creates a focused beam in a black optical cell. A particle crossing
   this beam scatters light in all directions.
3. **Detects** — an OPT101 (monolithic photodiode + transimpedance
   amplifier) positioned at 90° to the beam collects the scattered
   light. Each particle produces a brief pulse (2–10 µs) whose height
   is proportional to the particle's scattering cross-section. The
   OPT101 output is digitized by the STM32G474's 12-bit ADC at 500 ksps
   via DMA into a circular buffer.
4. **Counts and sizes** — a real-time pulse detector (baseline-tracking
   + threshold-cross + peak-find) extracts each pulse's height. The
   pulse height is mapped to one of 16 size bins (0.30, 0.40, 0.50,
   0.70, 1.0, 1.3, 1.7, 2.2, 3.0, 4.0, 5.0, 7.0, 10, 15, 20, 30, 40 µm)
   via a calibration table fit from PSL sphere measurements
   (`peak_mV = A · d^B`, a Mie-scattering power law).
5. **Computes concentration** — every 1 second, the per-bin counts
   are divided by the sampled air volume (flow × time) to give number
   concentration (#/L) per bin. Mass concentration is computed assuming
   spherical particles with configurable density (default 1.65 g/cm³):
   `mass_i = N_i · (π/6) · d_i³ · ρ`. PM1, PM2.5, and PM10 are the
   sums of bin masses with d ≤ 1.0, 2.5, and 10 µm respectively.
   Optional κ-Köhler hygroscopic growth correction adjusts particle
   diameter for humidity effects at RH > 50%.
6. **Reports** — the OLED shows a live 16-bin histogram bar chart,
   PM2.5, PM10, flow rate, and battery. Data is logged to microSD
   (one CSV row per minute) and streamed over BLE to a phone/PC app
   at 1 Hz.

## Why It's Interesting

Airborne particulate matter (PM) is the world's largest environmental
health risk: the WHO attributes ~7 million premature deaths per year
to PM2.5 exposure. Yet the instruments that measure it are expensive
and inaccessible:

- **Reference-grade monitors** (Met One BAM-1020, Thermo Fisher
  Partisol) cost $5k–$25k, require a temperature-controlled shelter,
  mains power, and periodic calibration by a technician.
- **Handheld OPCs** (TSI AeroTrak 9303, Met One HHPC-6, Lighthouse
  HHPC-2) cost $2k–$8k and are used by IAQ professionals, cleanroom
  certifiers, and industrial hygienists.
- **Low-cost sensors** (Plantower PMS5003, Sensirion SPS30) cost
  $10–$30 but are opaque "black box" modules with no user-accessible
  calibration, no raw data output, and fixed bin boundaries —
  making them unsuitable for research or regulatory screening.

Halo Pin fills the gap: a **fully open, calibratable, research-grade**
OPC for $52 that fits in a pocket. It is designed for:

- **Citizen science / community air quality** — neighborhood groups
  can deploy 10 Halo Pins for the cost of one TSI AeroTrak. The open
  CSV data and BLE streaming enable community PM mapping.
- **Personal exposure assessment** — clip it to a backpack strap to
  measure your personal PM2.5 exposure during commuting, cooking,
  or wildfire smoke events. The 18650 battery lasts ~24 h.
- **Industrial hygiene** — construction dust, welding fume, silica.
  The configurable density (for silica, set ρ = 2.65 g/cm³) and
  16-bin resolution give a detailed picture of workplace aerosol.
- **Cleanroom certification** — the 0.3 µm lower cutoff suits ISO
  Class 1–5 cleanroom particle counting. The HEPA zero-air test
  verifies the baseline.
- **Pollen / allergen monitoring** — the 10–40 µm bins capture
  pollen grains. Run continuously during allergy season to track
  daily pollen exposure.
- **Wildfire smoke monitoring** — wildfire smoke is dominated by
  PM2.5 in the 0.3–1.0 µm range. Halo Pin resolves this fine mode
  and reports PM2.5 for health advisory comparison.
- **Educational** — every environmental engineering lab can have a
  real OPC for $52 instead of sharing one $5k TSI among 100 students.
  The open firmware and raw histogram data support teaching
  aerosol physics, Mie scattering, and calibration methodology.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| SoC | STM32G474RET6 (ARM Cortex-M4F, 170 MHz, FPU, CORDIC, FMAC) |
| BLE / Wi-Fi bridge | ESP32-C3-MINI-1 (BLE 5, Wi-Fi 4) |
| Laser | 650 nm, 5 mW, constant-current with monitor-PD feedback |
| Photodetector | OPT101 (monolithic PD + TIA, 650 nm responsive) |
| Sample rate | 500 ksps, 12-bit ADC, DMA circular (1 ms windows) |
| Flow rate | 1.0 L/min (closed-loop via SDP810 dP sensor) |
| Size range | 0.30–40 µm (16 bins) |
| PM1 / PM2.5 / PM10 | 0.1 µg/m³ resolution, ±15% accuracy (calibrated) |
| Concentration range | 1–100,000 #/L (1–10⁵ #/m³) |
| Coincidence limit | ~1000 #/cm³ (at 1 L/min, 1.5 mm jet) |
| Density (configurable) | 0.5–3.0 g/cm³ (default 1.65 g/cm³ atmospheric) |
| Hygroscopic correction | κ-Köhler model, κ = 0.3 (configurable) |
| Ambient sensors | SHT45 (T ±0.1°C, RH ±1.5%), BME280 (P ±1 hPa) |
| Display | 1.3" OLED 128×64 I2C (SH1106) — histogram + PM + flow |
| Logging | microSD (FAT32, CSV, one row per minute) |
| Wireless | BLE 5 (ESP32-C3) — 1 Hz streaming, command control |
| Calibration | PSL sphere power-law fit (A·d^B), NIST-traceable |
| Zero test | HEPA zero-air, < 10 counts / 60 s pass criterion |
| Power | 18650 Li-ion (3.7 V, 2600 mAh) — ~24 h continuous |
| Form factor | 80 × 50 × 25 mm (PCB) + 40 mm optical cell |
| Weight | ~120 g (with battery) + 40 g optical cell |
| BOM cost | ~$52 |

## Block Diagram

```
                       ┌────────────────────────────────────────────┐
                       │           STM32G474RET6 (U1)                │
                       │  ┌──────────────────────────────────────┐ │
                       │  │ Cortex-M4F 170 MHz · CORDIC · FMAC   │ │
                       │  │ 5× ADC (12-bit, 4 Msps) · 4× DAC    │ │
                       │  │ 2× I2C · 3× SPI · 4× USART · DMA    │ │
                       │  └──────────────────────────────────────┘ │
                       │                                            │
                       │  ADC1_IN1 (PA0) ◀── OPT101 photodiode     │
                       │  ADC2_IN3 (PA6) ◀── Monitor PD (laser fb)  │
                       │  ADC2_IN4 (PA4) ◀── Battery V divider     │
                       │  TIM3_CH1 (PB4) ──▶ NCP500 laser driver  │
                       │  TIM2_CH3 (PB0) ──▶ Blower motor PWM      │
                       │  I2C1 (PA11/12) ─▶ SHT45, BME280, OLED    │
                       │  I2C3 (PA8/PA9) ─▶ SDP810 flow sensor     │
                       │  SPI2 (PB13-15) ─▶ microSD               │
                       │  USART1 (PA9/PA10) ─▶ ESP32-C3 BLE      │
                       │  GPIO (PB5-7)   ─▶ Rotary encoder       │
                       │  GPIO (PB8/9)   ─▶ Scan/Mode buttons    │
                       │  GPIO (PB12)    ◀── Reed interlock       │
                       └────────────────────────────────────────────┘
                          │      │      │      │       │       │
                     ┌────┘  ┌───┘  ┌───┘  ┌───┘  ┌────┘  ┌────┘
                     ▼       ▼     ▼       ▼     ▼       ▼
              ┌────────┐ ┌────┐ ┌─────┐ ┌────┐ ┌─────┐ ┌──────┐
              │ OPT101 │ │SDP │ │SHT45│ │OLED│ │ μSD │ │ESP32-│
              │ PD+TIA │ │810 │ │BME  │ │128 │ │ FAT│ │C3 BLE│
              │ 90° sc │ │flow│ │T/RH/P│ │×64 │ │ CSV│ │bridge│
              └────┬───┘ └─┬──┘ └─────┘ └────┘ └─────┘ └──────┘
                   │       │
                   ▼       │
              ┌────────┐  │  dP across restrictor
              │ Laser  │  ▼
              │ 650nm  │ ┌──────┐
              │ 5mW    │ │Blower│
              └────────┘ │1L/min│
                         └──────┘

  Signal path:  Particle ─▶ 90° Mie scatter ─▶ OPT101 ─▶ ADC1 (500 ksps)
               ─▶ DMA ─▶ pulse detector ─▶ size bin ─▶ count ─▶ mass conc.
               ─▶ PM1/PM2.5/PM10 ─▶ OLED + SD + BLE

  Calibration:  PSL spheres (known d) ─▶ peak_mV(d) ─▶ fit A·d^B
               ─▶ 16 bin boundaries (mV) ─▶ flash
```

## Pin Assignments (STM32G474RET6 — LQFP64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0  | ADC1_IN1 (OPT101 photodiode output)   | Analog in  | 0–3.3 V, 500 ksps, DMA circular |
| PA4  | ADC2_IN4 (battery voltage divider)    | Analog in  | 2:1 divider on Vbat |
| PA6  | ADC2_IN3 (monitor PD — laser power)   | Analog in  | Laser power feedback for PI loop |
| PA8  | I2C3_SCL (SDP810 flow sensor)         | I2C        | 400 kHz |
| PA9  | I2C3_SDA (SDP810 flow sensor)         | I2C        | 400 kHz |
| PA11 | I2C1_SDA (SHT45, BME280, OLED)        | I2C        | 400 kHz, shared |
| PA12 | I2C1_SCL (SHT45, BME280, OLED)        | I2C        | 400 kHz, shared |
| PB0  | TIM2_CH3 (blower motor PWM)           | PWM out    | 25 kHz, blower driver input |
| PB4  | TIM3_CH1 (NCP500 laser driver SET)    | PWM out    | 500 Hz, laser current control |
| PB5  | GPIO (encoder A)                     | Input(pu)  | Rotary nav |
| PB6  | GPIO (encoder B)                     | Input(pu)  | Rotary nav |
| PB7  | GPIO (encoder push / select)          | Input(pu)  | Select |
| PB8  | GPIO (scan button)                    | Input(pu)  | Start sampling |
| PB9  | GPIO (mode button)                    | Input(pu)  | Stop / menu |
| PB12 | GPIO (SPI2 CS / microSD)              | Output     | Active-low SD card CS |
| PB13 | SPI2_SCK (microSD)                    | SPI out    | 5 MHz |
| PB14 | SPI2_MISO (microSD)                   | SPI in     | SD card data |
| PB15 | SPI2_MOSI (microSD)                   | SPI out    | SD card data |
| PC0  | GPIO (WS2812B status LED)             | Output     | Status (optional) |
| PC13 | GPIO (TP4056 charge status)           | Input      | Charging LED sense |
| PC14 | GPIO (ESP32-C3 reset)                 | Output     | BLE bridge reset |
| PC15 | GPIO (ESP32-C3 enable)                | Output     | 1 = enabled |
| PD0  | GPIO (SWDIO / debug)                  | Debug      | SWD |
| PD1  | GPIO (SWCLK / debug)                  | Debug      | SWD |
| VDD  | 3.3 V digital power                   | Power      | From AP2112-3.3 |
| VDDA | 3.3 V analog power                    | Power      | From LP5907-3.3 (low-noise) |
| VREF+| 3.0 V reference                       | Reference  | REF3030 (0.2%, 7 ppm/°C) |
| VSS  | GND                                   | Power      | Star ground, AGND/DGND split |

> **Pin note:** The STM32G474RET6 LQFP64 exposes 50 GPIOs; ~22 are
> used here. ADC1 runs continuously at 500 ksps with DMA circular
> mode; the half-transfer and full-transfer interrupts each process
> 512 samples (1 ms) through the pulse detector. The I2C1 bus is
> shared by three devices (SHT45, BME280, SH1106 OLED) at different
> addresses (0x44, 0x77, 0x3C).

## Power Architecture

```
   USB-C 5V ──┬── TP4056 (Li-ion charger) ── 18650 (3.7 V 2600 mAh)
              │
              └── MCP1640B boost (3.7 V → 5.0 V, 800 mA) ─┬── 5 V rail
                                                         │   (blower, NCP500)
                                                         │
   18650 3.7 V ── AP2112-3.3 (digital 3.3 V, 600 mA) ── STM32, ESP32-C3, OLED
                ── LP5907-3.3 (analog 3.3 V, 250 mA, ultra-low-noise)
                    ── STM32 VDDA, OPT101 VDD, REF3030
                ── REF3030 (3.0 V, 0.2%, 7 ppm/°C) ── STM32 VREF+, ADC ref
```

- **5 V rail** powers the blower motor and the NCP500 laser driver
  (which needs > 3.5 V for the 650 nm laser diode forward voltage).
- **3.3 V digital** (AP2112) powers the STM32, ESP32-C3, and OLED.
- **3.3 V analog** (LP5907, ultra-low-noise) powers the OPT101 and
  the STM32 VDDA, minimizing ADC noise.
- **3.0 V reference** (REF3030) feeds VREF+ for quantitative ADC
  measurements.
- **Battery monitoring** via a 2:1 divider on PA4; read every 1 s.

Power budget (continuous sampling):

| Stage | Current (from 18650) |
|-------|----------------------|
| STM32 + OLED + SD (idle) | 25 mA |
| ESP32-C3 BLE bridge (advertising) | 8 mA |
| OPT101 photodiode + TIA | 3 mA |
| NCP500 laser driver + laser diode | 25 mA |
| SDP810 flow sensor (sampling) | 2 mA |
| SHT45 + BME280 (intermittent) | 1 mA avg |
| Blower motor (1 L/min) | 80 mA |
| **Total typical (sampling + BLE)** | **~144 mA → ~18 h on 2600 mAh** |
| **Total (idle, BLE only)** | **~35 mA → ~74 h standby** |

## Firmware Architecture

Built with **arm-none-eabi-gcc + bare-metal CMSIS** for STM32G474RET6
(no HAL dependency; direct register access).

```
firmware/
├── CMakeLists.txt
├── Makefile
├── stm32g474_ret6.ld      — linker script
├── startup_stm32g474xx.s   — startup / vector table
├── stm32g474_conf.h        — register definitions + clock config
├── main.c                 — State machine + main loop
├── laser.c/h              — NCP500 laser driver + PI power control
├── airflow.c/h            — Blower PWM + SDP810 flow feedback
├── adc.c/h                — ADC1 500 ksps DMA circular + pulse callback
├── pulse.c/h              — Baseline tracking + threshold + peak-find + binning
├── calibration.c/h        — PSL sphere power-law fit + bin boundary generation
├── concentration.c/h       — Number conc. (#/L) + mass conc. (µg/m³) per channel
├── ambient.c/h            — SHT45 T/RH + BME280 pressure
├── display.c/h            — SH1106 OLED: histogram + PM + flow + battery
├── sd_log.c/h             — microSD CSV logging (one row per minute)
├── ble_bridge.c/h         — UART protocol to ESP32-C3 (BLE GATT server)
├── battery.c/h            — 18650 voltage monitor
└── ui.c/h                 — Button + rotary encoder + menu
```

### State Machine

```
            ┌──────┐  button    ┌──────────┐  select    ┌────────────┐
            │ IDLE │───────────▶│ MENU     │───────────▶│ SAMPLING   │
            └──────┘            └──────────┘           └─────┬──────┘
               ▲                                             │
               │  mode                                        │ 1 s tick
               │                                              ▼
               │        ┌──────────┐  finish    ┌─────────────┐
               └────────│ STOP     │◀──────────│ CONCENTRATION│
                        └──────────┘           │ UPDATE      │
                                               └─────┬───────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ SD + BLE    │
                                              │ push        │
                                              └─────────────┘
```

### Pulse Detection Algorithm

1. **Baseline tracking** — a slow IIR low-pass (τ ~10 ms) on the
   minimum of each 1 ms chunk gives the baseline DC level.
2. **Noise estimation** — the RMS of the first 64 samples (assumed
   pulse-free) gives the noise sigma σ.
3. **Threshold** — `V_threshold = V_baseline + max(4σ, 30 mV)`.
4. **Peak detection** — when a sample exceeds threshold, scan the
   next 20 µs (10 samples) for the local maximum. The peak height
   (above baseline) is the scattering amplitude.
5. **Size binning** — the peak height is mapped to one of 16 bins
   via the calibrated boundaries table (from PSL calibration).
6. **Callback** — the main loop's callback function increments the
   per-bin counter.

### Mass Concentration Algorithm

For each bin `i` with midpoint diameter `d_i` (µm) and count `N_i`:

```
number_conc_i = N_i / V          (#/L, where V = flow × dt in liters)
mass_i = N_i × (π/6) × (d_i/1e4)³ × ρ × 1e6   (µg per particle)
PM_x = Σ mass_i × 1000 for bins with d_i ≤ x   (µg/m³, #/L → #/m³)
```

Where:
- `d_i` in cm = `d_i_µm / 1e4`
- `ρ` = particle density (default 1.65 g/cm³)
- `V` = sampled volume = `flow_lpm / 60 × dt_s` (liters)

Hygroscopic growth (optional, κ-Köhler):
```
d_wet = d_dry × (1 + κ·aw/(1−aw))^(1/3)
where aw = RH/100, κ = 0.3 (ammonium sulfate proxy)
```

### PSL Calibration Algorithm

1. **Collect** — for each PSL size `d_k`, nebulize the suspension
   into the inlet for 60 s. Record all peak heights.
2. **Median** — compute the median peak height `V_k` for each size
   (median is robust to coincident-particle outliers).
3. **Log-log regression** — fit `ln(V) = ln(A) + B·ln(d)` via
   least-squares. This gives the power-law `V = A·d^B`.
4. **Boundaries** — compute the 16 bin boundary heights:
   `V_boundary_i = A · d_edge_i^B`.
5. **Flash** — store A, B, and the boundaries in flash (NVS).

Typical fit values: A ≈ 50–150, B ≈ 2.0–2.5 (Mie theory predicts
V ∝ d² in the geometric scattering regime for particles much larger
than the wavelength, with oscillations).

## Mechanical / Front-Panel Layout

```
   ┌──────────────────────────────────────────────────────────────┐
   │                       HALO PIN                                │
   │                                                              │
   │   ┌──────────────────────────────────┐                        │
   │   │       Optical Cell (black)        │                        │
   │   │   ┌─────────┐    ┌─────────┐     │                        │
   │   │   │  Laser  │    │ OPT101  │     │                        │
   │   │   │  650nm  │ ▶  │  90° PD │     │                        │
   │   │   └─────────┘    └─────────┘     │                        │
   │   │        ▲ inlet nozzle (1.5mm)  │                        │
   │   │        │  ▼ exhaust             │                        │
   │   └──────────────────────────────────┘                        │
   │                                                              │
   │   ┌───────────────────────────┐                              │
   │   │       1.3" OLED           │   ┌───────┐                  │
   │   │   16-bin histogram        │   │ rotary│                  │
   │   │   PM2.5 / PM10 / flow     │   │ enc.  │                  │
   │   └───────────────────────────┘   └───────┘                  │
   │                                                              │
   │  [SCAN]   [MODE]                        [USB-C charge]       │
   │                                                              │
   │                              [18650 battery inside]          │
   └──────────────────────────────────────────────────────────────┘
```

- The **optical cell** is a 3D-printed black PLA chamber (40 × 25 ×
  20 mm) that houses the laser diode, OPT101 photodiode, and airflow
  nozzle in a 90° scattering geometry. A light-absorbing baffle
  prevents direct laser light from reaching the photodiode.
- The **inlet nozzle** tapers from 6 mm to 1.5 mm, focusing the
  airflow into a narrow jet that crosses the laser beam at the
  focal point.
- A **reed switch** on the cell cover provides a laser safety
  interlock — the firmware refuses to fire the laser if the cover
  is open.
- A **HEPA prefilter** (optional) attaches to the inlet for the
  zero-air test.
- The 1.3" SH1106 OLED shows a live 16-bin histogram (8 px per bin),
  PM2.5, PM10, flow rate, and battery voltage.
- A rotary encoder (with push) navigates the menu.
- A SCAN button starts/stops sampling; a MODE button cycles modes.

## Using Halo Pin

### Quick Start

1. **Charge** via USB-C until the green LED stops pulsing.
2. **Power on** — the OLED shows "HALO PIN v1.0 ready".
3. **Zero test** (recommended first use) — attach the HEPA prefilter,
   select "ZERO" in the menu, press SELECT. Wait 60 s. The total
   count should be < 10. If higher, clean the optical cell.
4. **Calibrate** (recommended every 6 months) — see
   `docs/calibration-guide.md` for the PSL sphere procedure.
5. **Sample** — remove the HEPA filter, select "SAMPLE", press
   SELECT (or press the SCAN button). The OLED shows the live
   histogram and PM2.5/PM10.
6. **Stop** — press MODE. Data is logged to microSD.
7. **Stream** — if a phone/PC is connected over BLE, the companion
   app (`scripts/halo_pin_app.py`) shows a live histogram, PM
   time-series, and logs to CSV.

### Calibration

- **PSL calibration** — use NIST-traceable PSL spheres (0.5, 1.0,
  2.0, 5.0 µm). For each size, nebulize the PSL suspension into the
  inlet for 60 s. The device records peak heights; the companion
  script (`scripts/psl_calibrate.py`) fits the power law and
  updates the bin boundaries. See `docs/calibration-guide.md`.
- **Zero-air test** — attach a HEPA filter, run for 60 s. Total
  counts should be < 10. This verifies the optical cell is clean
  and there are no electronic noise issues.
- **Flow verification** — connect a reference flow meter at the
  exhaust. The reported flow should match within ±5%. If not,
  adjust `FLOW_CALIB_K` in `airflow.c`.

### Phone / PC App

The companion app (`scripts/halo_pin_app.py`) connects over BLE,
subscribes to the status characteristic, and displays:
- PM1, PM2.5, PM10 (µg/m³) with WHO AQI color coding
- 16-bin histogram (bar chart)
- Flow rate, battery, temperature, humidity, pressure
- CSV logging for offline analysis

```bash
python3 scripts/halo_pin_app.py --log session.csv --duration 3600
```

## Example Scenarios

### 1. Wildfire Smoke Monitoring
- During a wildfire smoke event, place Halo Pin on a windowsill.
- PM2.5 spikes to 150–300 µg/m³. The 0.3–1.0 µm bins dominate
  (combustion aerosol). The device runs for 24 h on one charge,
  streaming to a phone for continuous monitoring.

### 2. Construction Dust Exposure
- An industrial hygienist clips Halo Pin to a worker's lapel during
  concrete cutting. The density is set to 2.65 g/cm³ (mineral dust).
  PM10 and the 3–10 µm bins track respirable dust exposure for
  OSHA compliance logging.

### 3. Cleanroom Certification
- A cleanroom certifier uses Halo Pin for routine ISO Class 5
  checks. The 0.3 µm lower cutoff captures the critical 0.3–0.5 µm
  range. The HEPA zero test verifies baseline before each use.

### 4. Citizen Science Air Quality Mapping
- A community group deploys 20 Halo Pins across a neighborhood near
  a highway. Each unit logs to SD and streams via BLE to a phone
  app. The resulting PM2.5 map identifies hotspots with 20 m
  resolution — for $1040 total (vs. one $5k reference monitor).

### 5. Pollen Monitoring
- An allergy sufferer runs Halo Pin continuously during spring. The
  10–40 µm bins capture pollen grains. The daily histogram shows
  pollen peaks at midday, correlating with symptoms.

### 6. Educational Lab
- An environmental engineering course has 10 Halo Pins ($520 total).
  Students calibrate with PSL spheres, measure classroom air quality,
  study Mie scattering physics, and compare OPC data against a
  reference PM2.5 monitor.

## Limitations & Safety

- **0.3 µm lower limit** — particles smaller than 0.3 µm produce
  scattering signals below the detection threshold. For ultrafine
  particles (< 100 nm), a condensation particle counter (CPC) is
  needed.
- **40 µm upper limit** — large particles may not be aspirated
  efficiently into the 1.5 mm nozzle.
- **Coincidence loss** — at concentrations > 1000 #/cm³, two particles
  may cross the beam simultaneously and be counted as one. The
  firmware detects abnormally wide pulses but does not correct.
  For high-concentration environments, dilute the sample.
- **Humidity** — at RH > 80%, hygroscopic particles grow, increasing
  their scattering cross-section. The κ-Köhler correction
  (`HYGR:1`) partially compensates, but the κ parameter is a rough
  average. For accurate mass at high RH, use a dryer.
- **Class 3R laser** — the 650 nm, 5 mW laser is Class 3R (IEC 60825).
  Direct eye exposure to the beam can cause injury. The optical cell
  is fully enclosed with a reed-switch interlock that disables the
  laser when the cover is removed. **Never look into the inlet while
  the laser is on.**
- **Flow dependency** — the concentration calculation depends on
  accurate flow measurement. Dust accumulation in the flow restrictor
  shifts calibration. Check flow monthly with a reference meter.
- **Not reference-grade** — Halo Pin is designed for screening,
  personal exposure, and educational use. For regulatory compliance,
  use a FRM/FEM-certified monitor.

## Bill of Materials

See `hardware/BOM.csv` — total ~$52.

## Documentation

- `docs/assembly-guide.md` — PCB assembly, optical cell fabrication,
  mechanical assembly, firmware flashing.
- `docs/api-reference.md` — BLE GATT characteristics, SD card format,
  UART protocol, firmware build instructions, size bin table.
- `docs/calibration-guide.md` — PSL sphere calibration procedure,
  zero-air test, flow verification, density configuration.
- `docs/field-guide.md` — Quick start, interpreting results, WHO PM
  guidelines, deployment tips, limitations.

## License

MIT — build it, sell it, improve it.

---