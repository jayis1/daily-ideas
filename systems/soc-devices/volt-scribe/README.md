# Volt Scribe — Portable Electrochemical Workstation

**Device #27** | SoC: **STM32G491RET6** | A pocket-sized potentiostat/galvanostat for cyclic voltammetry, differential pulse voltammetry, square-wave voltammetry, and electrochemical impedance spectroscopy — with on-device analysis, OLED plot, SD logging, and BLE streaming.

---

## Overview

Volt Scribe is a handheld three-electrode potentiostat/galvanostat designed for field electrochemistry. It drives a working electrode (WE) against a reference electrode (RE) while measuring current through a counter electrode (CE), enabling classical analytical techniques:

- **Cyclic Voltammetry (CV)** — sweep potential, measure current, detect redox peaks
- **Differential Pulse Voltammetry (DPV)** — pulse superimposed on staircase ramp for enhanced sensitivity
- **Square-Wave Voltammetry (SWV)** — advanced pulse technique for trace analysis
- **Electrochemical Impedance Spectroscopy (EIS)** — small-signal AC impedance from 1 Hz–100 kHz
- **Amperometric i-t** — constant potential, record current vs. time (biosensor mode)
- **Galvanostatic mode** — constant current, measure potential

On-device processing extracts peak potentials, peak currents, charge transfer resistance (R_ct), double-layer capacitance (C_dl), and Warburg impedance. An OLED displays the voltammogram or Nyquist plot in real time. Sessions log to microSD and stream over BLE to a companion phone/PC app.

Applications: water quality testing, heavy metal detection, battery electrode characterization, corrosion monitoring, biosensor readout, educational electrochemistry.

---

## Block Diagram

```
                         ┌──────────────────────────────────┐
                         │          STM32G491RET6           │
                         │  (170 MHz Cortex-M4F + CORDIC)   │
                         │                                  │
  ┌─────────────┐       │  DAC1 → Potentiostat Control     │
  │  Rotary      │───────│  GPIO ← Rotary Encoder            │
  │  Encoder     │       │  I2C1 ← OLED + ADS1115          │
  └─────────────┘       │  SPI1 ← SD Card                  │
                         │  UART1 ← ESP32-C3 (BLE/WiFi)   │
  ┌─────────────┐       │  ADC1 ← TIA output (current)    │
  │  SSD1306    │───────│  ADC2 ← WE sense (potential)    │
  │  128×64 OLED│       │  DAC2 ← AC stimulus (EIS)        │
  └─────────────┘       │  TIM1 → DPV/SWV pulse generator │
                         │  CORDIC → EIS fitting            │
  ┌─────────────┐       │                                  │
  │  ADS1115    │───────│  COMP1 → Overcurrent watchdog    │
  │  16-bit ADC │       │                                  │
  └─────────────┘       └──────────┬───────────────────────┘
                                   │
                    ┌───────────────┼───────────────────┐
                    │               │                   │
              ┌─────┴─────┐  ┌─────┴─────┐  ┌─────────┴────────┐
              │Potentiostat│  │  RE Buffer│  │   TIA / I-V       │
              │  Control    │  │ (AD8606)  │  │   Converter       │
              │  (AD8606)   │  │           │  │   (AD8606 +        │
              └─────┬──────┘  └─────┬─────┘  │    OPA196)        │
                    │               │         └────────┬──────────┘
                    │               │                  │
              ┌─────┴───────────────┴──────────────────┴──────┐
              │           Electrochemical Cell                  │
              │    CE ◄─────────────────────────────► WE        │
              │                    ▲                             │
              │                   RE                             │
              └─────────────────────────────────────────────────┘

                    ┌───────────────┐
                    │   ESP32-C3    │
                    │  (BLE+WiFi)   │
                    └───────┬───────┘
                            │ UART
                    ┌───────┴───────┐
                    │ Phone / PC    │
                    │ Companion App │
                    └───────────────┘
```

---

## Key Specifications

| Parameter | Value |
|---|---|
| Potential range | ±2.048 V (vs. RE) |
| Compliance voltage | ±5 V |
| Current ranges | 1 nA – 10 mA (7 auto-ranging decades) |
| Current resolution | 0.3 pA (1 nA range) |
| Potential resolution | 0.5 mV (12-bit DAC) |
| ADC resolution | 16-bit (ADS1115), 12-bit (internal) |
| Scan rate (CV) | 1 mV/s – 100 V/s |
| EIS frequency range | 1 Hz – 100 kHz |
| EIS AC amplitude | 1 mV – 100 mV rms |
| Techniques | CV, DPV, SWV, EIS, i-t, Galvanostatic |
| Communication | BLE 5 (ESP32-C3), USB-C CDC |
| Display | SSD1306 128×64 OLED |
| Logging | MicroSD (FAT32) |
| Power | 3.7 V LiPo (1000 mAh) or USB-C |
| Battery life | ~8 h continuous |
| Dimensions | 110 × 65 × 22 mm |

---

## Pin Assignments (STM32G491RET6, LQFP64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0 | DAC1_OUT | Analog out | Potentiostat setpoint voltage |
| PA1 | DAC2_OUT | Analog out | EIS AC stimulus (AC-coupled) |
| PA2 | ADC1_IN2 | Analog in | TIA output → current measurement |
| PA3 | ADC2_IN3 | Analog in | WE sense → potential measurement |
| PA4 | COMP1_INP | Analog in | Overcurrent detect |
| PA5 | SPI1_SCK | SPI out | SD card clock |
| PA6 | SPI1_MISO | SPI in | SD card data out |
| PA7 | SPI1_MOSI | SPI out | SD card data in |
| PA8 | TIM1_CH1 | PWM out | DPV/SWV pulse generator |
| PA9 | UART1_TX | UART out | ESP32-C3 communication |
| PA10 | UART1_RX | UART in | ESP32-C3 communication |
| PA11 | GPIO_OUT | Digital out | SD card CS |
| PA12 | GPIO_OUT | Digital out | ADS1115 alert (interrupt) |
| PB0 | I2C1_SDA | I2C bidir | OLED + ADS1115 data |
| PB1 | I2C1_SCL | I2C out | OLED + ADS1115 clock |
| PB2 | GPIO_IN | Digital in | Rotary encoder A |
| PB3 | GPIO_IN | Digital in | Rotary encoder B |
| PB4 | GPIO_IN | Digital in | Rotary encoder press |
| PB5 | GPIO_OUT | Digital out | TIA range relay 1 |
| PB6 | GPIO_OUT | Digital out | TIA range relay 2 |
| PB7 | GPIO_OUT | Digital out | TIA range relay 3 |
| PB8 | GPIO_OUT | Digital out | Cell enable (CE driver gate) |
| PB9 | GPIO_OUT | Digital out | LED status (green) |
| PB10 | GPIO_OUT | Digital out | LED error (red) |
| PB11 | GPIO_OUT | Digital out | Buzzer |
| PB12 | ADC3_IN7 | Analog in | Battery voltage divider |
| PB13 | GPIO_OUT | Digital out | Charge enable (MCP73871) |
| PB14 | GPIO_IN | Digital in | USB detect |
| PC4 | OPAMP1_OUT | Analog out | RE buffer (internal op-amp) |
| PC5 | OPAMP1_INP | Analog in | RE input |
| PC10 | TIM8_CH1 | PWM out | Backlight PWM |
| PC11 | GPIO_IN | Digital in | Button 1 (mode) |
| PC12 | GPIO_IN | Digital in | Button 2 (start/stop) |
| PD2 | GPIO_OUT | Digital out | ESP32-C3 EN (reset) |
| VDD | 3.3 V | Power | Main rail |
| VDDA | 3.3 V (filtered) | Power | Analog rail (LC filtered) |

---

## Power Architecture

```
  USB-C 5V ─────┬─── MCP73871 ──── LiPo 3.7V ──── TPS63020 ──── 3.3V (VDD)
                │                    1000mAh           buck-boost
                │                                       500 mA
                └─── LDO (TLV74333) ──── 3.3V (USB direct)
                        (backup)

  3.3V ──── LC filter (10µH + 100µF) ──── VDDA (3.3V clean analog)

  Analog supplies:
    +5V rail: TPS61041 boost (3.3V → 5.0V, 50 mA) — op-amp V+
    -5V rail: LM27761 inverter (5V → -5V, 50 mA) — op-amp V-
    2.048V reference: REF3030 (2.048V, 0.1%) — DAC/ADC reference
```

---

## Potentiostat Circuit Design

The three-electrode potentiostat uses a classic control amplifier topology with precision op-amps:

### Control Amplifier (AD8606 op-amp A)
- Non-inverting input: DAC1 output (setpoint)
- Inverting input: RE buffer output (feedback)
- Output: CE driver (through 1 kΩ current-limiting resistor)
- The control loop forces WE potential = setpoint by sourcing/sinking current through CE

### RE Buffer (AD8606 op-amp B or internal OPAMP1)
- Unity-gain buffer on reference electrode
- High input impedance (>1 TΩ) prevents current draw from RE
- Output feeds back to control amplifier and ADC

### TIA / Current-to-Voltage Converter (OPA196 + AD8606)
- Summing junction at WE
- OPA196 configured as transimpedance amplifier with 7 gain ranges:
  - R_f = 100 MΩ → 1 nA range (100 mV/nA)
  - R_f = 10 MΩ → 10 nA range
  - R_f = 1 MΩ → 100 nA range
  - R_f = 100 kΩ → 1 µA range
  - R_f = 10 kΩ → 10 µA range
  - R_f = 1 kΩ → 100 µA range
  - R_f = 100 Ω → 10 mA range (via AD8606)
- Auto-ranging via 3 GPIO-controlled analog switches (ADG1606)
- Compensation capacitor C_f (2.2 pF – 47 pF) selected per range for stability

### EIS Stimulus Path
- DAC2 generates sine wave (Direct Digital Synthesis via TIM6 DMA)
- AC-coupled through 10 µF capacitor to sum into control amplifier
- Amplitude: programmable 1–100 mV rms

---

## Firmware Architecture

```
  ┌─────────────────────────────────────────┐
  │              Application               │
  │  ┌──────┐ ┌─────┐ ┌────┐ ┌──────────┐│
  │  │  CV  │ │ DPV │ │ SWV│ │   EIS    ││
  │  │engine│ │engn │ │engn│ │  engine  ││
  │  └──────┘ └─────┘ └────┘ └──────────┘│
  ├─────────────────────────────────────────┤
  │            Middleware Layer             │
  │  ┌──────┐ ┌─────┐ ┌──────┐ ┌────────┐ │
  │  │Potent│ │ TIA │ │ DSP  │ │ Display│ │
  │  │ctrl  │ │range│ │ math │ │ render │ │
  │  └──────┘ └─────┘ └──────┘ └────────┘ │
  ├─────────────────────────────────────────┤
  │              HAL / Drivers             │
  │  DAC ADC TIM SPI I2C UART GPIO CORDIC │
  └─────────────────────────────────────────┘
```

### Key Algorithms

**CV Engine:**
1. Set start potential via DAC1
2. Ramp DAC1 from start → vertex → start at configured scan rate
3. Sample ADC1 (current) and ADC2 (potential) simultaneously at 10 kHz
4. Apply iR compensation (optional, measured from EIS R_s)
5. Store (E, i) pairs in ring buffer
6. Detect peaks: derivative zero-crossing with minimum height threshold
7. Report E_p, i_p, ΔE_p (for reversible couples)

**EIS Engine:**
1. Set DC bias via DAC1
2. Generate AC stimulus via DAC2 (DDS sine, frequency sweep 1 Hz → 100 kHz)
3. At each frequency, sample TIA output and stimulus simultaneously
4. Compute real and imaginary impedance using DFT (CORDIC-accelerated)
5. Build Nyquist and Bode plots
6. Fit Randles equivalent circuit: R_s + (C_dl ∥ (R_ct + Z_W))
7. Report R_s, R_ct, C_dl, α (CPE exponent)

---

## BOM (Bill of Materials)

See `hardware/BOM.csv` for the complete bill.

Key components:
- **U1**: STM32G491RET6 — Main MCU (Cortex-M4F @ 170 MHz, 512 KB Flash, 112 KB SRAM)
- **U2**: ESP32-C3-MINI-1 — BLE/WiFi module
- **U3**: AD8606ARDZ — Dual precision op-amp (control amp + RE buffer)
- **U4**: OPA196ID — Precision TIA op-amp (low bias current, wide band)
- **U5**: ADS1115IDGSR — 16-bit ADC (current measurement, I2C)
- **U6**: ADG1606BCPZ — 7-channel analog switch (TIA range select)
- **U7**: REF3030AIDBZR — 2.048V voltage reference (0.1%)
- **U8**: SSD1306 — 128×64 OLED display (I2C)
- **U9**: TPS63020 — Buck-boost converter (3.3V out)
- **U10**: MCP73871 — LiPo charger (USB-C)
- **U11**: TPS61041 — Boost converter (5V analog rail)
- **U12**: LM27761 — Inverting charge pump (-5V rail)

---

## Mechanical

- **Enclosure**: SLA-printed 110 × 65 × 22 mm, split clamshell
- **Electrode connector**: 3.5 mm TRS jack (CE/RE/WE) or banana jacks
- **Display window**: 128×64 OLED visible area
- **Controls**: Rotary encoder + 2 tactile buttons
- **Ports**: USB-C, microSD slot
- **Weight**: ~85 g (with battery)

---

## Usage

### Cyclic Voltammetry (CV)
```
VS> mode cv
VS> set potential_start -0.2
VS> set potential_vertex 0.8
VS> set potential_end -0.2
VS> set scan_rate 0.05
VS> set cycles 3
VS> run
Running CV: -200 mV → 800 mV → -200 mV @ 50 mV/s
Peak 1: E = 0.312 V, i = 4.7 µA (anodic)
Peak 2: E = 0.248 V, i = -4.2 µA (cathodic)
ΔE_p = 64 mV (quasi-reversible)
Result saved to SD: cv_20260626_001.csv
```

### Electrochemical Impedance Spectroscopy (EIS)
```
VS> mode eis
VS> set dc_bias 0.25
VS> set ac_amplitude 0.010
VS> set freq_start 1
VS> set freq_end 100000
VS> set points_per_decade 10
VS> run
Running EIS: 1 Hz → 100 kHz, 50 points
Fitting Randles circuit...
  R_s  = 127 Ω
  R_ct = 2.34 kΩ
  C_dl = 18.7 µF
  α    = 0.91
Result saved to SD: eis_20260626_001.csv
```

### Amperometric i-t
```
VS> mode amperometric
VS> set potential 0.45
VS> set duration 60
VS> set sample_rate 10
VS> run
Running i-t at 450 mV for 60 s @ 10 Hz
Average current: 1.23 µA
Result saved to SD: it_20260626_001.csv
```

---

## Directory Structure

```
volt-scribe/
├── README.md              # This file
├── schematic/
│   ├── volt-scribe.kicad_sch
│   ├── volt-scribe.kicad_pcb
│   └── volt-scribe.kicad_pro
├── firmware/
│   ├── main.c             # Main application
│   ├── potentiostat.c     # Potentiostat control & TIA ranging
│   ├── potentiostat.h
│   ├── cv_engine.c        # Cyclic voltammetry engine
│   ├── cv_engine.h
│   ├── dpv_engine.c       # Differential pulse voltammetry
│   ├── dpv_engine.h
│   ├── swv_engine.c       # Square-wave voltammetry
│   ├── swv_engine.h
│   ├── eis_engine.c       # Electrochemical impedance spectroscopy
│   ├── eis_engine.h
│   ├── amperometric.c     # Amperometric i-t mode
│   ├── amperometric.h
│   ├── dsp.c              # DSP: DFT, peak detection, circuit fitting
│   ├── dsp.h
│   ├── display.c          # OLED rendering (voltammograms, Nyquist)
│   ├── display.h
│   ├── sd_log.c           # SD card CSV logging
│   ├── sd_log.h
│   ├── ble_relay.c        # UART→ESP32-C3 BLE relay protocol
│   ├── ble_relay.h
│   ├── CMakeLists.txt     # Build system
│   └── sdkconfig          # ESP-IDF / STM32Cube config
│   └── sim/
│       └── main_sim.c     # Desktop simulation build
├── hardware/
│   └── BOM.csv            # Bill of materials
├── docs/
│   ├── assembly_guide.md  # Assembly & calibration guide
│   └── api_reference.md   # Serial/BLE protocol reference
└── scripts/
    ├── volt_scribe_cli.py # Python CLI for BLE control & plotting
    └── eis_fit.py         # Python EIS circuit fitting tool
```

---

## License

MIT — build it, measure it, improve it.