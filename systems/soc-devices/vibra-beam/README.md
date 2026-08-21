# Vibra Beam — Pocket Laser Doppler Vibrometer

> Bringing $10k–$50k lab laser Doppler vibrometers (Polytec OFV-5000, Polytec PSV, Ometron VPI, Optomet Nova) down to ~$74 and flashlight size, with on-device quadrature DSP, self-motion compensation, and heterodyne-to-audio listening that commercial single-point LDVs charge $5k+ for.

## What It Is

**Vibra Beam** is a pocket-sized single-point laser Doppler vibrometer (LDV) that measures the vibration velocity and displacement of any reflective surface — without touching it — over a bandwidth of DC to ~100 kHz with sub-nanometer displacement resolution and sub-µm/s velocity resolution.

An LDV works by splitting a coherent laser beam into a **reference arm** (reflected off a fixed internal mirror) and a **signal arm** (reflected off the vibrating target). When the two beams recombine on a photodiode, the target's motion Doppler-shifts the signal beam, producing an interference beat. For a target moving at velocity *v*, the Doppler shift is:

```
f_D = 2·v / λ
```

For a 650 nm laser and a 1 µm/s vibration, that is f_D ≈ 3.08 mHz — far below any direct frequency measurement. Vibra Beam therefore uses a **quadrature homodyne** (Michelson-with-quarter-wave-plate) architecture: the recombined beam is split into two channels 90° apart in phase (I and Q). The target's instantaneous displacement is recovered by CORDIC `atan2(Q, I)` + phase unwrapping, with each 2π of phase equal to **λ/2 = 325 nm** of target motion. Velocity is the time-derivative of displacement; no heterodyne frequency-shift hardware (AOM) is needed, which is what makes the whole instrument fit in a flashlight.

This enables measurement of:

- **Structural health & modal analysis** — resonance frequencies, mode shapes, damping ratios of bridges, beams, PCBs, machinery
- **MEMS & ultrasonic transducer characterization** — in-plane/out-of-plane resonance, deflection, quality factor
- **Microspeaker, headphone & buzzer QC** — frequency response, THD, rub & buzz
- **Biomedical micro-vibration** — remote pulse wave velocity (skin micro-motion from arterial flow), vocal-fold vibration, hand tremor, chest-wall vibration (cardiogenic)
- **Non-contact acoustic measurement** — surface velocity of a vibrating panel (inverse acoustic radiation)
- **Material property** — Young's modulus via resonant frequency of a clamped beam (ASTM E1876)
- **Rotation & angular vibration** — of motor shafts, fans, hard-drive spindles
- **Education** — interferometry, the optical Doppler effect, quadrature demodulation, FFT/spectral analysis

## Key Features

- **650 nm 5 mW visible laser diode** with adjustable-focus collimator (visible beam doubles as alignment aid)
- **Michelson quadrature interferometer** — non-polarizing beamsplitter + quarter-wave plate + polarizing beamsplitter → I/Q photodiode pair
- **Dual 5 Msps simultaneous-sampling ADC** (STM32G474 internal) for I and Q at up to 2.5 Msps/channel
- **CORDIC atan2 + phase unwrapping** for sub-fringe displacement (λ/2 = 325 nm/fringe, ~pm-level with oversampling)
- **Velocity via differentiated phase** — DC to ~100 kHz bandwidth, ~0.5 µm/s resolution
- **On-device FFT** (CMSIS-DSP / FMAC) — vibration spectrum, peak picking, THD, octave/1/3-octave bands
- **ICM-42688-P IMU self-motion compensation** — subtracts handheld device motion from measured target velocity (essential for handheld use)
- **Heterodyne-to-audio** — translates the Doppler beat into the audible band so you can *listen* to the vibration (motor whine, bearing clicks, heartbeat) via speaker or headphone jack
- **OLED display** — live displacement/velocity waveform, scrolling spectrum, Lissajous (I/Q circle)
- **MicroSD logging** — CSV (time, displacement, velocity) + raw I/Q binary at up to 2.5 Msps
- **BLE + Wi-Fi streaming** via ESP32-C3 to a phone/PC app for live plotting
- **LiPo battery** — 6+ hours continuous
- **Laser safety** — class-2 software limit (1 mW default), 5 mW max, shutter + reed interlock, IWDG watchdog

## Block Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Vibra Beam                                  │
│                                                                     │
│   ┌──────────┐         ┌────────────┐   ┌────────────┐              │
│   │ 650 nm   │─ beam ──►│ NPBS cube  │─►│  QWP 650nm  │              │
│   │ 5 mW LD  │         │  50:50     │   │  λ/4 plate  │              │
│   │ +collim. │         └──┬──┬──────┘   └─────┬──────┘              │
│   └──────────┘            │   │                 │                    │
│        ▲                  │   │ ref arm         │ sig arm            │
│        │                  │   ▼                 ▼                    │
│   ┌────┴─────┐            │ ┌──────┐      ┌─────────┐               │
│   │ Laser    │            │ │Fixed │      │ Target  │ (external)    │
│   │ Driver   │            │ │Mirror│      │ surface │               │
│   │+Shutter  │            │ └──┬───┘      └────┬────┘               │
│   └────┬─────┘            │    │ return       │ return               │
│        │ PWM/EN           │    ▼              ▼                     │
│        │                  │ ┌────────────┐ ◄──┘                      │
│   ┌────▼─────┐            │ │ PBS cube   │  (recombined)            │
│   │ STM32G474│            │ │ (pol.)     │                           │
│   │ RET6     │            │ └──┬───┬────┘                           │
│   │ (MCU)    │            │    │I  │Q                              │
│   │          │            │    ▼   ▼                                │
│   │ CORDIC   │            │ ┌───┐ ┌───┐                            │
│   │ FMAC     │            │ │PD1│ │PD2│  PIN photodiodes           │
│   │ ADC 5Msps│◄── ADC1 ───┤ │   │ │   │                            │
│   │          │◄── ADC2 ───┤ └─┬─┘ └─┬─┘                            │
│   │          │            │   │     │                              │
│   └──┬───┬───┘            │ ┌─▼──┐┌──▼───┐                          │
│      │   │                │ │OPA ││ OPA  │  TIAs                    │
│   I2C│   │SPI             │ │380 ││ 380  │                          │
│      │   │                │ └────┘└──────┘                          │
│      ▼   ▼                │                                         │
│ ┌──────┐ ┌──────┐         │                                         │
│ │SH1106│ │MicroSD│         │                                         │
│ │OLED  │ │ card │         │                                         │
│ └──────┘ └──────┘         │                                         │
│                                                                     │
│   ┌──────────┐    I2C    │   ┌──────────┐    UART   ┌────────────┐  │
│   │ICM-42688 │◄──────────┤   │ ESP32-C3 │◄────────►│  phone/PC  │  │
│   │  -P IMU  │           │   │ -MINI-1  │   BLE/WiFi│  app       │  │
│   └──────────┘           │   └──────────┘           └────────────┘  │
│   ┌──────────┐   1-Wire   │                                         │
│   │ DS18B20  │◄──────────┤                                         │
│   │  temp    │           │   ┌──────────┐   PWM    ┌────────────┐  │
│   └──────────┘           │   │ MAX98357 │────────►│ speaker +  │  │
│   ┌──────────┐   I2C      │   │  A amp   │         │ headphone  │  │
│   │ BME280   │◄──────────┤   └──────────┘         │ jack       │  │
│   └──────────┘           │                         └────────────┘  │
│                                                                     │
│   Power: MCP73831 charger + TPS63020 buck-boost + TPS7A4700 LDO     │
│   Battery: 3.7V 1500mAh LiPo                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## SoC Architecture

### Main MCU: STM32G474RET6
- 170 MHz Cortex-M4F with FPU + **CORDIC** (hardware atan2 for quadrature phase) + **FMAC** (FIR/IIR filtering & matrix for FFT windowing)
- 512 KB flash, 96 KB SRAM
- Dual **5 Msps 12-bit ADC** with simultaneous sampling (ADC1+ADC2) for I and Q
- HRTIM for laser PWM dimming and shutter control
- SPI/I²C/UART peripherals for SD, OLED, IMU, sensors, ESP32 bridge
- CMSIS-DSP for FFT

### Wireless MCU: ESP32-C3-MINI-1
- RISC-V single-core, BLE 5.0 + Wi-Fi
- UART bridge to STM32 for BLE streaming and Wi-Fi web dashboard
- OTA firmware update capability

## How the Quadrature Homodyne LDV Works

### Interferometer Geometry

The 650 nm beam from the laser diode is collimated and enters a **non-polarizing 50:50 beamsplitter (NPBS)**. One half (reference arm) reflects off a fixed internal mirror and returns. The other half (signal arm) exits the device through a focus-adjustable lens, reflects off the target, and returns. The two returns recombine at the NPBS.

A **quarter-wave plate (QWP)** at 45° in the common path converts the linear polarization to circular; after the double-pass (out and back) the polarization rotates 90°, routing the returns to the second port of the NPBS rather than back into the laser (this is the classic isolator trick and also improves SNR). The recombined beam then passes through a **polarizing beamsplitter (PBS)** oriented at 45° to the QWP axes, producing two outputs in **quadrature** (90° phase difference): the I channel and the Q channel. Each lands on a PIN photodiode + transimpedance amplifier (OPA380).

### Quadrature Demodulation

The two photodiode signals are:

```
I(t) = A + B·cos(φ(t))
Q(t) = A + B·sin(φ(t))
```

where φ(t) = (4π/λ)·x(t) is the phase proportional to target displacement x(t), and λ = 650 nm. The DC offset A is removed by high-pass or baseline tracking. The instantaneous phase is:

```
φ(t) = atan2(Q−A, I−A)        ← computed by the CORDIC unit in 7 cycles
```

**Phase unwrapping** tracks the 2π jumps: each full 2π of φ corresponds to λ/2 = **325 nm** of target motion. Accumulating the unwrapped phase gives displacement:

```
x(t) = (λ / 4π) · φ_unwrapped(t)
```

With 12-bit ADCs and coherent oversampling, the phase noise floor is ~10⁻⁴ rad, giving a displacement resolution of **~10 pm** (single-shot, 1 kHz bandwidth) — comparable to commercial LDVs.

### Velocity

Velocity is the time-derivative of displacement:

```
v(t) = dx/dt = (λ / 4π) · dφ/dt
```

The CORDIC computes φ at up to 2.5 Msps; a first-difference plus a configurable low-pass (implemented in the FMAC as an IIR) yields velocity with bandwidth DC–~100 kHz and resolution ~0.5 µm/s.

### Doppler / Beat Frequency

For users who think in frequency, the Doppler shift is f_D = 2v/λ. The quadrature fringe rate equals f_D. The on-device FFT of the velocity time series directly shows the vibration spectrum.

### Self-Motion Compensation

Because Vibra Beam is handheld, the device itself moves. The **ICM-42688-P 6-axis IMU** (accelerometer + gyro, sampled at 1 kHz) measures the device's own linear and angular motion. Low-frequency device sway (< 20 Hz) is estimated from the IMU and subtracted from the measured displacement, leaving the target's intrinsic vibration. This is the key enabler for handheld use; benchtop LDVs are rigidly mounted and need no such compensation.

### Heterodyne-to-Audio

The unwrapped phase rate dφ/dt is frequency-shifted into the audible band (1×–1000× user-selectable) and written to the MAX98357A I²S amplifier, so the user can *hear* the vibration: a motor's whine, a bearing's click, a heartbeat's lub-dub. This is inspired by the audio output of heterodyne LDVs and turns vibration inspection into a listening task.

## Schematic Overview

| Ref | Part | Function |
|-----|------|----------|
| U1 | STM32G474RET6 | Main MCU — ADC sampling, CORDIC atan2, FMAC filtering, FFT, state machine |
| U2 | ESP32-C3-MINI-1 | BLE/Wi-Fi bridge |
| U3 | ADL-65005TL (or generic 650 nm 5 mW LD) | Coherent light source |
| U4 | NPBS cube 50:50 @ 650 nm | Beam splitter (Michelson) |
| U5 | QWP 650 nm λ/4 plate | Polarization rotation for quadrature + isolation |
| U6 | PBS cube @ 650 nm | Quadrature separation (I/Q) |
| U7, U8 | TEMD5010 PIN photodiode | I and Q detectors |
| U9, U10 | OPA380 | Transimpedance amplifiers (1 MΩ feedback, ~350 kHz BW) |
| U11 | MAX98357A | I²S class-D audio amplifier (speaker + headphone) |
| U12 | SH1106 OLED 128×64 | Display |
| U13 | MicroSD socket | Logging |
| U14 | ICM-42688-P | 6-axis IMU for self-motion compensation |
| U15 | DS18B20 | Temperature (laser wavelength + thermal correction) |
| U16 | BME280 | Ambient T/RH/P |
| U17 | LP403450 1500 mAh LiPo | Battery |
| U18 | MCP73831 | LiPo charger |
| U19 | TPS63020 | 3.3 V buck-boost |
| U20 | TPS7A4700 | Low-noise 3.3 V analog rail |
| U21 | DRV8833 (1 ch) | Laser shutter / electromechanical shutter driver |
| SW1 | Reed switch | Laser shutter interlock (lid open → laser off) |

## Pin Assignments (STM32G474RET6)

| Pin | Function | Notes |
|-----|----------|-------|
| PA0 | ADC1_IN1 | I channel (photodiode 1 → OPA380) |
| PA1 | ADC2_IN2 | Q channel (photodiode 2 → OPA380) |
| PA2 | USART2_TX | UART to ESP32-C3 (BLE/Wi-Fi bridge) |
| PA3 | USART2_RX | UART from ESP32-C3 |
| PA4 | DAC1_OUT1 | Laser power setpoint (PWM via DAC→LD driver) |
| PA5 | GPIO_OUT | Laser enable |
| PA6 | TIM3_CH1 (PWM) | Shutter PWM / hold |
| PA7 | GPIO_OUT | Shutter enable (DRV8833) |
| PA8 | I2S2_WS | MAX98357A LRCLK |
| PA9 | I2S2_BCK | MAX98357A BCLK |
| PA10 | I2S2_SD | MAX98357A data |
| PB6 | I2C1_SCL | OLED, BME280, ICM-42688-P |
| PB7 | I2C1_SDA | (shared I²C bus) |
| PB10 | SPI2_SCK | MicroSD |
| PB11 | SPI2_MISO | MicroSD |
| PB12 | SPI2_NSS | MicroSD CS |
| PB13 | SPI2_MOSI | MicroSD |
| PB14 | GPIO_IN | Reed interlock (lid) |
| PB15 | GPIO_IN | Button A (navigate) |
| PC0 | GPIO_IN | Button B (select) |
| PC1 | GPIO_OUT | Status LED R |
| PC2 | GPIO_OUT | Status LED G |
| PC3 | GPIO_OUT | Status LED B |
| PC4 | TIM8_CH1 (PWM) | Laser diode current modulation (optional AC dither) |
| PC10 | UART4_TX | (debug / SWO) |
| PC11 | UART4_RX | (debug) |
| PC13 | GPIO_OUT | Boot LED |
| PA13/PA14 | SWDIO/SWCLK | Programming |
| PD2 | GPIO_OUT | MicroSD detect power |
| OneWire | PA8 alt / PC8 | DS18B20 (1-Wire, bit-banged) |

> Note: where two functions share a pin in the summary above, the firmware selects one role per pin at runtime; the full KiCad netlist has the canonical assignment. DS18B20 1-Wire uses a dedicated GPIO (PC8) bit-banged.

## Power Architecture

```
USB-C 5V ──► MCP73831 ──► LiPo 3.7V 1500mAh
                              │
                              ▼
                         TPS63020 buck-boost ──► 3.3V digital rail
                              │
                              ▼
                         TPS7A4700 LDO ──► 3.3V analog rail (photodiode TIAs, laser driver ref)
```

- **Digital 3.3 V** — MCU, ESP32, OLED, SD, IMU, BME280, MAX98357A
- **Analog 3.3 V** — OPA380 TIAs, laser driver reference, ADC VREF (via separate LDO for noise isolation)
- **Laser supply** — separate 5 V boost (MT3601) for the laser diode driver, current-limited
- Battery life: ~6 h continuous laser-on streaming; ~20 h laser-off standby

## Laser Safety

- Default software power limit: **1 mW** (IEC Class 2 — eye-safe blink reflex)
- Max setting: 5 mW (Class 3R) — requires menu confirmation
- **Electromechanical shutter** (DRV8833-driven) closes on:
  - Lid open (reed switch interlock)
  - Tilt > 45° (IMU)
  - Watchdog timeout (IWDG)
  - User OFF
- Visible 650 nm beam aids alignment without a separate pilot laser

## Specifications (Target)

| Parameter | Value |
|-----------|-------|
| Wavelength λ | 650 nm |
| Laser power | 1 mW (default) / 5 mW (max) |
| Working distance | 10 cm – 5 m (focus adjustable) |
| Displacement range | ±2 mm (before re-acquire; unlimited with tracking) |
| Displacement resolution | ~10 pm (1 kHz BW, single-shot) |
| Velocity range | ±0.5 m/s (±500 mm/s) |
| Velocity resolution | ~0.5 µm/s |
| Bandwidth | DC – 100 kHz |
| Sample rate (I/Q) | up to 2.5 Msps/ch |
| FFT size | 256–8192 (configurable) |
| IMU sample rate | 1 kHz (self-motion compensation) |
| Logging | SD CSV @ up to 25 ksps; raw I/Q binary @ up to 2.5 Msps |
| Wireless | BLE 5.0 + Wi-Fi (ESP32-C3) |
| Battery | 3.7 V 1500 mAh LiPo, ~6 h |
| Size | ~35 mm dia × 140 mm (flashlight form) |
| Weight | ~90 g (without battery) |
| BOM cost | ~$74 |

## Use Cases

1. **Bearing fault detection** — point at a motor housing, listen for click/buzz, FFT shows BPFO/BPFI sidebands
2. **PCB resonance** — find board resonances that cause accelerometer/gyro noise
3. **Speaker QC** — frequency response, THD, rub & buzz in seconds, non-contact
4. **Remote pulse** — aim at wrist/neck skin, measure pulse wave velocity and heart rate from skin micro-motion
5. **Bridge/structural** — modal frequencies, damping, long-term drift
6. **MEMS characterization** — drive a MEMS mirror/gyro and measure its actual out-of-plane motion
7. **Material Young's modulus** — ASTM E1876: measure resonance of a clamped beam, compute E
8. **Education** — Doppler effect, interferometry, quadrature, FFT, signal processing

## File Layout

```
vibra-beam/
├── README.md            (this file)
├── schematic/
│   ├── vibra-beam.kicad_sch
│   ├── vibra-beam.kicad_pro
│   └── vibra-beam.kicad_pcb
├── firmware/
│   ├── CMakeLists.txt
│   ├── sdkconfig
│   ├── linker_script.ld
│   └── Core/
│       ├── Inc/  (main.h, config.h, interferometer.h, dsp.h, ...)
│       └── Src/  (main.c, interferometer.c, dsp.c, display.c, ...)
├── hardware/
│   └── BOM.csv
├── docs/
│   ├── assembly-guide.md
│   └── api-reference.md
└── scripts/
    ├── live_view.py      (BLE/Wi-Fi live waveform + spectrum)
    ├── export_csv.py     (SD → CSV/Pandas)
    ├── fft_analyze.py    (offline spectrum / spectrogram)
    ├── modal_fit.py      (resonance + damping extraction)
    └── calibrate.py      (fringe/phase calibration)
```

## Building the Firmware

```bash
cd vibra-beam/firmware
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../arm-none-eabi-gcc.cmake ..
make -j
# flash: openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
#        -c "program vibra_beam.elf verify reset exit"
```

Requires `arm-none-eabi-gcc` (≥ 10.3), CMake ≥ 3.22, and the STM32G4 HAL + CMSIS sources placed under `firmware/Drivers/`.

## License

MIT — build it, sell it, improve it. Laser safety is your responsibility.