# Phase Scope

**Handheld 3-Phase Power Quality Analyzer**

> A pocket-sized instrument for electricians, solar installers, and facility managers that clips onto three-phase power lines and delivers real-time voltage, current, power factor, THD, harmonic spectrum, and transient capture — with on-device OLED display, BLE smartphone streaming, and SD-card data logging.

---

## Overview

Phase Scope is a battery-powered, non-invasive 3-phase power quality meter built around the **STM32G491RET6** — a Cortex-M4F MCU with dual 12-bit ADCs (4 MSPS each), hardware over-sampling, DACs, and ultra-fast comparators that make it uniquely suited for power-line waveform acquisition and analysis.

**Key capabilities:**

- **3-channel voltage measurement** (0–690V L-L, 0–400V L-N) via precision resistor dividers + isolation amplifiers
- **3-channel current measurement** via clamp-on CT inputs (1mV/A to 1V/A selectable)
- **Real-time computation**: VRMS, IRMS, active/reactive/apparent power, power factor, frequency, phase angle, THD, individual harmonics (up to 50th)
- **Transient capture**: 64-sample pre-trigger ring buffer with configurable threshold — catches voltage sags, swells, and impulses down to 100µs
- **On-device FFT**: 1024-point FFT per channel with harmonic decomposition
- **OLED display**: 1.3" 128×64 SH1106 showing real-time phasor diagram, harmonic bar graph, or numeric readout
- **BLE 5.0**: Stream live waveforms to smartphone app (nRF Connect-compatible)
- **SD card logging**: CSV and binary waveform capture to microSD
- **Safety**: Galvanic isolation on all voltage/current inputs, double-insulated enclosure, CAT III 300V rating

---

## Block Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE SCOPE                                  │
│                                                                      │
│  ┌──────────┐   ┌───────────────┐   ┌────────────────────────────┐  │
│  │ L1 Input │──▶│ Isolation     │──▶│                            │  │
│  │ L2 Input │──▶│ Amplifier     │──▶│                            │  │
│  │ L3 Input │──▶│ (AMC1301 x3)  │──▶│  STM32G491RET6            │  │
│  └──────────┘   └───────────────┘   │                            │  │
│                                       │  ADC1: V1,V2,V3           │  │
│  ┌──────────┐   ┌───────────────┐   │  ADC2: I1,I2,I3           │  │
│  │ CT Input │──▶│ Burr-Brown    │──▶│  ADC3: NTC (temp comp)     │  │
│  │ 1,2,3   │──▶│ OPA2376 x3    │──▶│  DAC1: Calib tone out     │  │
│  └──────────┘   └───────────────┘   │  DSP: FFT, THD, PF calc   │  │
│                                       │  HRTIM: zero-cross det    │  │
│  ┌──────────┐   ┌───────────────┐   │                            │  │
│  │ NTC Temp │──▶│ Voltage ref   │──▶│                            │  │
│  │ Sense   │   │ REF3030 3.0V │   │                            │  │
│  └──────────┘   └───────────────┘   └──────────┬─────────────────┘  │
│                                                           │          │
│       ┌───────────┬───────────────┬──────────────┬─────────┘          │
│       │           │               │              │                    │
│  ┌────▼───┐ ┌─────▼────┐ ┌───────▼──────┐ ┌───▼──────┐             │
│  │ SH1106 │ │ nRF52810 │ │ microSD      │ │ 4x LED   │             │
│  │ OLED   │ │ BLE 5.0  │ │ Card Slot   │ │ Status   │             │
│  │ 128×64 │ │ Module   │ │ (SPI)       │ │ Indicators│             │
│  └────────┘ └──────────┘ └──────────────┘ └──────────┘             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Li-Po 3.7V 2000mAh │ MCP73831 Charger │ TPS63020 Buck-Boost   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignments

### STM32G491RET6 (LQFP-64)

| Pin | Function | Notes |
|-----|----------|-------|
| PA0 | ADC1_IN1 | L1 Voltage (after isolation amp) |
| PA1 | ADC1_IN2 | L2 Voltage (after isolation amp) |
| PA2 | ADC1_IN3 | L3 Voltage (after isolation amp) |
| PA3 | ADC2_IN4 | I1 Current (after signal conditioning) |
| PA4 | ADC2_IN5 | I2 Current (after signal conditioning) |
| PA5 | ADC2_IN6 | I3 Current (after signal conditioning) |
| PA6 | DAC1_OUT | Calibration tone output |
| PA7 | SPI1_MOSI | SD card MOSI |
| PA8 | HRTIM_CHA1 | Zero-cross comparator input (internal) |
| PA9 | USART1_TX | Debug UART TX |
| PA10 | USART1_RX | Debug UART RX |
| PA11 | USB_DM | USB-C data (future) |
| PA12 | USB_DP | USB-C data (future) |
| PB0 | ADC3_IN12 | NTC temperature sensor input |
| PB1 | ADC3_IN13 | VBUS voltage sense (battery) |
| PB3 | SPI1_SCK | OLED + SD card SPI clock |
| PB4 | SPI1_MISO | SD card MISO |
| PB5 | GPIO_OUT | OLED DC/RS |
| PB6 | I2C1_SCL | BLE module I2C (config) |
| PB7 | I2C1_SDA | BLE module I2C (config) |
| PB10 | TIM2_CH3 | BLE UART TX (via nRF52810) |
| PB11 | TIM2_CH4 | BLE UART RX (via nRF52810) |
| PB12 | GPIO_OUT | SD card CS (active low) |
| PB13 | GPIO_OUT | OLED CS (active low) |
| PB14 | GPIO_OUT | LED1 (L1 status) |
| PB15 | GPIO_OUT | LED2 (L2 status) |
| PC0 | GPIO_OUT | LED3 (L3 status) |
| PC1 | GPIO_OUT | LED4 (BLE status) |
| PC2 | GPIO_OUT | Range relay 1 (CT range select) |
| PC3 | GPIO_OUT | Range relay 2 (CT range select) |
| PC4 | GPIO_OUT | Range relay 3 (voltage range select) |
| PC5 | GPIO_OUT | OLED RESET |
| PC6 | TIM3_CH1 | Buzzer PWM |
| PC8 | SDIO_CK | SD card clock (alternate SPI) |
| PC9 | GPIO_OUT | SD card detect |
| PC10 | UART4_TX | BLE module UART TX |
| PC11 | UART4_RX | BLE module UART RX |
| PC13 | GPIO_IN | Button 1 (Mode) |
| PC14 | GPIO_IN | Button 2 (Select) |
| PC15 | GPIO_IN | Button 3 (Hold/Back) |
| PD2 | GPIO_OUT | Power enable (buck-boost) |

---

## Power Architecture

```
USB-C 5V ──► MCP73831 ──► Li-Po 3.7V 2000mAh ──► TPS63020 ──► 3.3V Main Rail
                                                          │
                                                          ├─► STM32G491 (3.3V)
                                                          ├─► OLED (3.3V)
                                                          ├─► nRF52810 BLE (3.3V)
                                                          ├─► AMC1301 x3 (5V side from iso)
                                                          └─► SD Card (3.3V)

Isolated side:
  L1/L2/L3 ──► Resistor divider ──► AMC1301 ──► ISO side 5V ──► STM32 ADCs
  CT1/2/3 ──► OPA2376 ──► STM32 ADCs (non-isolated, low-side CT)

Isolated supply:
  L-N voltage ──► LDO +5V ──► AMC1301 primary side
  (or USB-powered when bench use)
```

- **Battery life**: ~8 hours continuous measurement, ~4 hours with BLE streaming
- **Charging**: USB-C, ~2.5 hours to full
- **Quiescent current**: <500µA in sleep (OLED off, BLE advertising)

---

## Analog Front-End Design

### Voltage Input Path (per channel)

```
L-N (0-400V) ──[470kΩ]──┬──[1kΩ]──┬─── AMC1301 VIN+ ──► Isolated side ──► ADC
                          │          │
                     [10nF]    [100Ω]
                          │          │
                        [1kΩ]   AMC1301 VIN-
                          │
                         GND (isolated)

Attenuation ratio: 470k + 1k = 471:1
  → 400V L-N → 849mV at ADC
  → With AMC1301 gain of 8.2: 6.96V → scaled to 0-3V at ADC input
  → Actually: 470k/(470k+1k) × 8.2 × (1k/(1k+100)) = calibrated in firmware

Protection: 1kV TVS on each input, 500mA fuse, 10kV ESD protection
```

### Current Input Path (per channel)

```
Clamp CT (1000:1 or 100:1) ──► Burden resistor ──► OPA2376 gain stage ──► ADC

Two ranges:
  - Low range: 0-10A (burden 100Ω, gain ×10) → 1mV/A resolution
  - High range: 0-1000A (burden 1Ω, gain ×1) → 1V/A at 1000A
  
Range selection via reed relay (PC2/PC3)
```

---

## Firmware Architecture

```
┌─────────────────────────────────────────────┐
│               Phase Scope FW                 │
│              (STM32G491RET6)                 │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ ADC1     │  │ ADC2     │  │ ADC3     │ │
│  │ V1,V2,V3│  │ I1,I2,I3│  │ NTC,Vbat │ │
│  │ 4kSPS   │  │ 4kSPS   │  │ 100SPS   │ │
│  │ DMA      │  │ DMA      │  │ Polling  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │             │        │
│  ┌────▼──────────────▼─────────────▼──────┐│
│  │        Power Quality Engine             ││
│  │  ┌─────────────────────────────────────┐│
│  │  │ Sample Buffer (6 × 1024 samples)    ││
│  │  │ Double-buffered, DMA-filled         ││
│  │  ├─────────────────────────────────────┤│
│  │  │ RMS Calculator (per-cycle)         ││
│  │  │ Vrms, Irms, Vpeak, Ipeak           ││
│  │  ├─────────────────────────────────────┤│
│  │  │ Power Calculator                    ││
│  │  │ P, Q, S, PF, phase angle           ││
│  │  ├─────────────────────────────────────┤│
│  │  │ FFT Engine (1024-pt per channel)   ││
│  │  │ THD, harmonics 1st–50th            ││
│  │  ├─────────────────────────────────────┤│
│  │  │ Transient Detector                  ││
│  │  │ Pre-trigger ring buffer (64 samples)││
│  │  │ Threshold ±10% from nominal        ││
│  │  └─────────────────────────────────────┘│
│  └─────────────────┬───────────────────────┘│
│                    │                         │
│  ┌─────────────────▼───────────────────────┐│
│  │           Display Manager               ││
│  │  ┌─────────────────────────────────────┐│
│  │  │ Page 1: Phasor Diagram (3 vectors) ││
│  │  │ Page 2: Waveform (V & I overlaid)  ││
│  │  │ Page 3: Harmonic Bar Graph          ││
│  │  │ Page 4: Numeric Readout (6 lines)  ││
│  │  │ Page 5: Transient Capture Log      ││
│  │  └─────────────────────────────────────┘│
│  └─────────────────┬───────────────────────┘│
│                    │                         │
│  ┌─────────────────▼───────────────────────┐│
│  │         Communication Layer              ││
│  │  ┌───────────┐  ┌───────────┐          ││
│  │  │ BLE UART  │  │ SD Card   │          ││
│  │  │ (nRF)    │  │ (FatFS)  │          ││
│  │  └───────────┘  └───────────┘          ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

## Display Pages

### Page 1: Phasor Diagram
```
      V1 ────►
      ╲
       ╲ 120°
        V2 ──►
       ╱
      ╱ 120°
     V3 ──►
```
Shows 3-phase voltage vectors with magnitude and angle. Current vectors overlaid in dashed lines.

### Page 2: Waveform View
```
  V1 ╱╲     ╱╲     ╱╲
    ╱  ╲   ╱  ╲   ╱  ╲
   ╱    ╲ ╱    ╲ ╱    ╲
  ───────╳──────╳──────╳──
         ╲    ╱ ╲    ╱
     I1   ╲  ╱   ╲  ╱   (phase shift visible)
           ╲╱     ╲╱
```
2-cycle capture with V and I overlaid.

### Page 3: Harmonic Bar Graph
```
  THD: 4.2%
  ▁▂▃▅▇▆▃▂▁▁▁▁▁▁▁
  1 3 5 7 9 11 13 15...
  Fundamental: 230.1V
```

### Page 4: Numeric Readout
```
 L1: 230.1V  5.2A  PF0.93
 L2: 229.8V  4.8A  PF0.91
 L3: 230.5V  5.0A  PF0.92
 Freq: 50.01Hz  P:3.58kW
```

---

## BLE Protocol

Phase Scope streams data over BLE UART (Nordic UART Service) at 115200 baud.

### Command Interface (BLE → Device)

| Command | Hex | Description |
|---------|-----|-------------|
| `GET_STATUS` | `0x01` | Returns current RMS, power, PF for all phases |
| `GET_WAVEFORM` | `0x02` | Streams 1024-sample waveform buffers |
| `GET_HARMONICS` | `0x03` | Returns 50th-order harmonic magnitudes |
| `GET_TRANSIENT` | `0x04` | Returns last captured transient |
| `START_LOG` | `0x10` | Begin SD card logging (continuous) |
| `STOP_LOG` | `0x11` | Stop SD card logging |
| `SET_RANGE_V` | `0x20` | Set voltage range (400V/690V) |
| `SET_RANGE_I` | `0x21` | Set current range (10A/100A/1000A) |
| `SET_DISPLAY` | `0x30` | Set OLED display page (1-5) |
| `CALIBRATE` | `0x40` | Enter calibration mode |

### Data Format (Device → BLE)

```
Status packet (64 bytes, sent every 500ms):
  [0]     0x01 (status)
  [1:3]   V1_rms (Q12.4 fixed point, units: 0.1V)
  [3:5]   V2_rms
  [5:7]   V3_rms
  [7:9]   I1_rms (Q12.4, units: 0.01A)
  [9:11]  I2_rms
  [11:13] I3_rms
  [13:15] P1 (Q16.0, units: W)
  [15:17] P2
  [17:19] P3
  [19:21] PF1 (Q1.15 fixed point)
  [21:23] PF2
  [23:25] PF3
  [25:27] Frequency (Q8.8, units: 0.01Hz)
  [27:31] Timestamp (Unix epoch)
  [31:33] THD1 (Q4.12, units: 0.01%)
  [33:35] THD2
  [35:37] THD3
  [37:39] Phase angle V1-V2 (Q4.12, degrees)
  [39:41] Phase angle V2-V3
  [41:43] Phase angle I1-V1
  [43:45] Flags (overvoltage, undervoltage, transient, etc.)
  [45:64] Reserved (zero-padded)
```

---

## Safety Considerations

⚠️ **This device connects to mains voltage. Design and build with extreme caution.**

1. **Galvanic isolation**: All voltage inputs pass through AMC1301 reinforced isolation amplifiers (5kV isolation, 8mm creepage). The digital side is fully isolated from mains.
2. **Input protection**: Each voltage channel has:
   - 500mA fuse (5×20mm)
   - 1kV bidirectional TVS (SMBJ1000A)
   - 10kV ESD protection (TPD4E05U06)
   - Input rated for CAT III 300V per IEC 61010
3. **Current inputs**: CT inputs are non-invasive — the CT clamp is isolated from the conductor. Burden resistors on the low-voltage side only.
4. **Enclosure**: Double-insulated, IP54 rated. No exposed metal. Banana jack inputs recessed with shrouds.
5. **Firmware safety**: Watchdog enforces maximum measurement timeout. If zero-cross detection fails for >500ms, all inputs are disconnected via relay and a "FAULT" message is displayed.

---

## Calibration

Phase Scope includes a self-calibration routine accessible via BLE or button combo (hold Mode + Select for 3 seconds).

### Voltage Calibration
1. Apply known voltage (e.g., 230V from a calibrated source)
2. Enter calibration mode via BLE command `0x40`
3. Device measures raw ADC counts and computes correction factor
4. Store calibration constants in STM32 flash (OB area)

### Current Calibration
1. Apply known current through CT clamp (e.g., 10A)
2. Same procedure as voltage
3. Two-point calibration: zero (open circuit) and full-scale

### Phase Calibration
1. Apply resistive load (PF ≈ 1.0)
2. Device adjusts internal phase compensation to achieve PF > 0.999
3. Stores phase offset per channel

All calibration constants stored in STM32 option bytes flash area, retentive across power cycles.

---

## Specifications

| Parameter | Value |
|-----------|-------|
| Voltage ranges | 0–400V L-N, 0–690V L-L |
| Current ranges | 0–10A / 0–100A / 0–1000A (CT dependent) |
| Voltage accuracy | ±0.5% of reading ±0.2V |
| Current accuracy | ±0.5% of reading ±0.01A |
| Power accuracy | ±1.0% of reading |
| Frequency range | 45–65 Hz |
| THD measurement | Up to 50th harmonic |
| FFT resolution | 1024-point, ~0.5 Hz/bin @ 4kSPS |
| Transient capture | 100µs minimum event width |
| Display | 1.3" SH1106 OLED, 128×64 |
| Connectivity | BLE 5.0 (nRF52810), UART @ 115200 |
| Logging | microSD, FAT32, CSV + binary |
| Battery | 3.7V 2000mAh Li-Po |
| Battery life | ~8 hours measurement, ~4 hours BLE streaming |
| Charging | USB-C, MCP73831, ~2.5 hours |
| Operating temp | 0°C to 50°C |
| Dimensions | 160mm × 80mm × 30mm |
| Safety rating | CAT III 300V, IEC 61010 |
| Enclosure | IP54, double-insulated ABS |

---

## Directory Structure

```
phase-scope/
├── README.md
├── schematic/
│   ├── phase-scope.kicad_pro
│   ├── phase-scope.kicad_sch
│   └── phase-scope.kicad_pcb
├── firmware/
│   ├── CMakeLists.txt
│   ├── main.c
│   ├── adc.c / adc.h
│   ├── power_quality.c / power_quality.h
│   ├── fft.c / fft.h
│   ├── display.c / display.h
│   ├── ble_uart.c / ble_uart.h
│   ├── sd_log.c / sd_log.h
│   ├── calibration.c / calibration.h
│   ├── stm32g491ret6.ld
│   └── sdkconfig
├── hardware/
│   └── BOM.csv
├── docs/
│   ├── assembly-guide.md
│   └── api-reference.md
└── scripts/
    ├── phase_scope_viewer.py
    ├── calibrate.py
    └── waveform_analyzer.py
```

---

## Quick Start

1. **Assemble the PCB** following the assembly guide in `docs/assembly-guide.md`
2. **Flash firmware** using SWD (SWDIO/SWCLK pads on PCB):
   ```bash
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
     -c "program firmware.bin verify reset exit 0x08000000"
   ```
3. **Connect CT clamps** around the three phase conductors (arrows on clamp pointing toward load)
4. **Connect voltage probes** — L1/L2/L3/N clips to the corresponding terminals
5. **Power on** — the OLED shows a splash screen then enters measurement mode
6. **Press Mode** to cycle through display pages
7. **Pair BLE** — search for "PhaseScope-XXXX" in nRF Connect or the companion app
8. **Start logging** — press Select to start/stop SD card recording

---

## License

MIT — build it, sell it, improve it.