# Phase Lock — Pocket Digital Lock-In Amplifier

> A battery-powered, pocket-sized digital lock-in amplifier (DLIA) that
> recovers nanovolt-level AC signals buried in 10⁵× noise by synchronous
> demodulation at a user-selected reference frequency — bringing the
> precision-signal-recovery backbone of every optics/condensed-matter /
> spectroscopy / NMR / Hall-effect lab bench down to ~$62 and a pocket-sized
> form factor.

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                       PHASE LOCK                                  │
 │           Pocket digital lock-in amplifier (DLIA)                 │
 │                                                                  │
 │  ┌────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────┐  │
 │  │ Ref OSC │──▶│ Power Amp│──▶│  DUT / DVP │──▶│ Signal Chain │  │
 │  │ DDS @f₀ │   │ (excite) │   │  (response)│   │ PGA + 24-bit │  │
 │  └────┬───┘   └──────────┘   └────────────┘   └──────┬───────┘  │
 │       │ ref I/Q (digital)                          │ analog    │
 │       └──────────────┬────────────────────────────┘           │
 │                      ▼                                          │
 │            ┌─────────────────────────┐                          │
 │            │  I/Q Demod (CORDIC)       │──▶ R, Θ, X, Y, PSD      │
 │            │  ∫ 1 kHz–100 kHz @ f_ref  │    OLED + BLE + SD        │
 │            └─────────────────────────┘                          │
 │                                                                  │
 │  SoC: STM32G491RET6 (Cordic, HRTIM, 3.6 Msps ADC, 24-bit IIR)    │
 └──────────────────────────────────────────────────────────────────┘
```

## What It Does

Phase Lock is a complete digital lock-in amplifier that fits in your
pocket. You wire it between an AC excitation source and a detector — a
photodiode, a Hall-bar sample, an LVDT position sensor, a chopper-stabilized
thermopile, an AC-impedance electrode, or any experiment where a tiny
signal sits at a known modulation frequency, buried under 10³–10⁵×
background noise and 1/f drift. On a button press, the device:

1. **Sets reference** — generates a sine-wave excitation at a user-selected
   frequency `f₀` (1 Hz–100 kHz) via the on-board programmable reference
   oscillator (DDS), output to a BNC front panel.
2. **Excites** — the excitation drives the experiment (LED, chopper,
   coil, AC voltage source) via the power-amplifier BNC output.
3. **Conditions** — the return signal from the experiment (the "signal"
   BNC input) is gained by a programmable-gain front end (1×–1024×,
   auto-ranging), band-limited, and sampled at up to 3.6 Msps by the
   STM32G491's 12-bit ADC with hardware oversampling to 16-bit
   effective resolution.
4. **Demodulates** — the STM32G491 computes I and Q at the digital
   reference frequency `f₀` using CORDIC + IIR low-pass filter chains
   running in the ARM Cortex-M4F DSP. Time constant 0.5 ms–10 s
   (12 dB/oct or 24 dB/oct selectable).
5. **Outputs** — R (magnitude) and Θ (phase) of the signal at `f₀`, plus
   X (= R·cosΘ, in-phase) and Y (= R·sinΘ, quadrature). The PSD
   (power-spectral-density) noise floor is computed in the sidebands
   around `f₀` for noise-figure readout.
6. **Sweeps** — internal frequency sweep (1 Hz–100 kHz, N log-spaced
   points) measures the full transfer function / impedance spectrum
   of the DUT. Internal amplitude sweep (10 mV–2 V) measures linearity.
7. **Reports** — displays R/Θ/X/Y and noise floor on the OLED, plots
   live time-traces and swept plots, logs to microSD card (CSV), and
   streams all four demodulation channels over BLE to a phone/PC app.

## Why It's Interesting

A benchtop lock-in amplifier (Stanford Research SR860, Zurich
HF2LI, NF LI5600) costs $4,000–$30,000 and weighs 3–8 kg. The lock-in
amplifier is the single most enabling instrument in experimental
science for extracting tiny signals from noise — it is to
precision measurement what the oscilloscope is to time-domain
viewing. Phase Lock is designed for:

- **Optics & spectroscopy** — chopping a light beam to recover
  photodiode signals buried in ambient light; modulation
  spectroscopy (wavelength modulation in TDLAS, photothermal
  deflection); pump-probe reflectance at the difference frequency.
- **Condensed-matter physics** — Hall-effect measurements at low
  temperature (where thermal noise dominates); AC resistance of
  superconductors (zero-V vs. finite-V onset); quantum Hall plateaus.
- **Electrochemistry** — EIS (electrochemical impedance spectroscopy,
  1 Hz–100 kHz) by sweeping `f₀` and reading R/Θ; corrosion-rate
  monitoring; battery impedance spectroscopy.
- **Materials science** — resonant ultrasound spectroscopy (RUS);
  dielectric spectroscopy of ferroelectrics; magneto-impedance sweeps.
- **NMR / MRI small-bore** — recovering the FID / echo envelope at
  the Larmor sideband after down-conversion.
- **Geophysics** — lock-in recovery of induction-loop signals at
  audio frequencies; telluric-current studies; soil-conductivity
  sweeps.
- **Education** — every physics senior lab can have a real lock-in
  for $62 instead of sharing one $9k SR860 among fifty students.
- **Sensor front-end** — recovering the AC output of
  modulated/oscillating sensors: LVDT (linear-variable differential
  transformer), resolver, AC-bridge strain gauge, fluxgate
  magnetometer, vibrating-sample magnetometer.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| SoC | STM32G491RET6 (ARM Cortex-M4F, 170 MHz, FPU, CORDIC, FMAC, HRTIM) |
| Reference oscillator | DDS via CORDIC + 12-bit DAC @ 1 MHz rate, 1 Hz–100 kHz |
| Reference outputs | 2× BNC: `Ref Out` (sine, ±2 V), `Aux Out` (aux TTL) |
| Excitation (power amp) | OPA569 power op-amp, ±10 V, 200 mA, 100 kHz BW |
| Signal input | 1× BNC, ±10 V full-scale, 1 MΩ | 22 pF |
| Input gain | Programmable 1×–1024× (PGA204 + PGA113 chain), auto-range |
| Input bandwidth | DC–200 kHz (analog 2nd-order Bessel anti-alias) |
| ADC | STM32G491 ADC1, 12-bit, 3.6 Msps, hardware oversample → 16-bit @ 28 ksps |
| Demodulation | Dual (I/Q) digital mix + IIR LPF, 1 Hz–100 kHz ref |
| Time constants | 0.5 ms, 1 ms, 3 ms, 10 ms, 30 ms, 100 ms, 300 ms, 1 s, 3 s, 10 s |
| Filter slope | 6, 12, 24, 48 dB/oct (cascaded IIR stages) |
| Output | R, Θ, X (= R cosΘ), Y (= R sinΘ) |
| Full-scale sensitivity | 1 nV (with 1024× gain) to 10 V (no gain) |
| Dynamic reserve | > 100 dB (with pre-filtering) |
| Noise floor | < 4 nV/√Hz at 1 kHz, 1024× gain, 1 s TC |
| Frequency sweep | 1 Hz–100 kHz, log or linear, up to 1000 points |
| Amplitude sweep | 10 mV–2 V, 100 points |
| Aux ADC | 2× 16-bit channels (ADS1115) for aux inputs (thermistor, etc.) |
| Aux DAC | 2× 12-bit (STM32 internal DAC) for aux outputs / offset |
| Wireless | BLE 5 (ESP32-C3 bridge) + Wi-Fi 4 (optional) |
| Logging | microSD (FAT32, CSV sweeps + time-traces) |
| Display | 1.3" OLED 128×64 I2C (SH1106) — live R/Θ/X/Y + plot |
| Power | 18650 Li-ion (3.7 V, 2600 mAh) — ~14 h continuous |
| Form factor | 130 × 72 × 24 mm (calculator-sized) |
| Weight | ~140 g (with battery) |
| BOM cost | ~$62 |

## Block Diagram

```
                       ┌────────────────────────────────────────────┐
                       │           STM32G491RET6 (U1)               │
                       │  ┌──────────────────────────────────────┐ │
                       │  │ Cortex-M4F 170 MHz · CORDIC · FMAC   │ │
                       │  │ HRTIM · 5× 12-bit ADC · 4× DAC       │ │
                       │  └──────────────────────────────────────┘ │
                       │                                            │
                       │  CORDIC ─▶ DAC1 (ref sine @ f₀, 1 Msps)  │
                       │  DAC2 ──▶ Aux Out (offset / bias)        │
                       │  ADC1 ──◀ signal (after PGA + LPF)        │
                       │  HRTIM ─▶ reference sync (TTL out)        │
                       │  I2C1 ──▶ SH1106 OLED + ADS1115 aux ADC   │
                       │  SPI2 ──▶ microSD                         │
                       │  USART──▶ ESP32-C3 (BLE bridge)           │
                       └────────────────────────────────────────────┘
                          │      │      │      │       │       │
                     ┌────┘  ┌───┘  ┌───┘  ┌───┘  ┌────┘  ┌────┘
                     ▼       ▼     ▼       ▼     ▼       ▼
              ┌────────┐ ┌────┐ ┌─────┐ ┌────┐ ┌─────┐ ┌──────┐
              │ OPA569  │ │PGA ││ LPF │ │OLED│ │ μSD │ │ESP32- │
              │ power   │ │204+│ │Bessel│ │128 │ │ FAT│ │C3 BLE│
              │ amp ±10V│ │113 │ │200k │ │×64 │ │ CSV│ │bridge│
              └────┬───┘ └─┬──┘ └──▲──┘ └────┘ └─────┘ └──────┘
                   │       │       │
                   ▼       ▼       │  signal input
              ┌────────┐  ┌──────┐│   ┌──────┐
              │ Ref Out│  │ Signal│└──▶│ BNC  │
              │ ±2V    │  │  in  │    │ sig  │
              │ power  │  │ BNC  │    │      │
              │ excite │  └──────┘    └──────┘
              └────────┘

  Signal chain detail:
  Signal BNC ──▶ Bessel LPF (200 kHz) ──▶ PGA204 (1×) ──▶ PGA113
  (1×–128×) ──▶ STM32 ADC1 (3.6 Msps, oversampled → 16-bit @ 28 ksps)
  ──▶ digital I/Q demod (CORDIC @ f₀) ──▶ IIR LPF (TC selectable)
  ──▶ R, Θ, X, Y.

  Reference chain:
  CORDIC sine table @ f₀ ──▶ DAC1 (12-bit, 1 Msps) ──▶ reconstruction LPF
  (10 kHz–200 kHz) ──▶ Ref Out BNC (±2 V).  Same CORDIC reference is
  used internally to multiply the digitized signal → digital I/Q demod.
```

## Pin Assignments (STM32G491RET6 — LQFP64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0  | ADC1_IN1 (signal input)        | Analog in       | After PGA chain, 0–3.3 V |
| PA1  | DAC1_OUT1 (ref sine wave)       | Analog out      | 12-bit, 1 Msps, → reconstruction filter → Ref Out BNC |
| PA2  | DAC1_OUT2 (aux out / offset)   | Analog out      | 12-bit, 1 Msps, optional |
| PA3  | ADC1_IN4 (aux ADC: gain monitor) | Analog in     | Internal gain sense |
| PA4  | ADC1_IN17 (battery V divider) | Analog in       | 2:1 divider on Vbat |
| PA5  | SPI1 MOSI (microSD)            | SPI out         | SD card data |
| PA6  | ADC1_IN3 (power-amp current monitor) | Analog in | 0.1 Ω sense, OPA569 I-mon |
| PA7  | SPI1 MISO (microSD)            | SPI in          | SD card data |
| PA8  | HRTIM_CHB1 (TTL Ref Out)       | PWM out         | TTL square @ f₀ |
| PA9  | USART1_TX (ESP32-C3 bridge)    | UART out        | 921600 baud |
| PA10 | USART1_RX (ESP32-C3 bridge)    | UART in         | 921600 baud |
| PA11 | I2C1_SDA (OLED + ADS1115)      | I2C             | 400 kHz |
| PA12 | I2C1_SCL (OLED + ADS1115)      | I2C             | 400 kHz |
| PA13 | SPI1_SCK (microSD)            | SPI out         | 25 MHz max |
| PA14 | GPIO (mode button)            | Input (pull-up) | Long-press = menu |
| PA15 | GPIO (encoder A)              | Input (pull-up) | Rotary nav |
| PB0  | GPIO (encoder B)              | Input (pull-up) | Rotary nav |
| PB1  | GPIO (encoder push / select)   | Input (pull-up) | |
| PB2  | GPIO (PGA204 gain select A0)  | Output          | PGA204 gain bit 0 |
| PB3  | GPIO (PGA204 gain select A1)   | Output          | PGA204 gain bit 1 |
| PB4  | GPIO (PGA204 gain select A2)   | Output          | PGA204 gain bit 2 |
| PB5  | GPIO (PGA113 gain select A0)   | Output          | PGA113 gain bit 0 |
| PB6  | GPIO (PGA113 gain select A1)   | Output          | PGA113 gain bit 1 |
| PB7  | GPIO (PGA113 gain select A2)   | Output          | PGA113 gain bit 2 |
| PB8  | GPIO (microSD CS)             | Output          | Active-low |
| PB9  | GPIO (ESP32-C3 reset)         | Output          | BLE bridge reset |
| PB10 | GPIO (BLE bridge enable)       | Output          | 1 = enabled |
| PB11 | GPIO (RGB LED, WS2812B)        | Output (RMT)    | Status |
| PB12 | GPIO (OPA569 enable)          | Output          | Power-amp shutdown |
| PB13 | TIM2_CH1 (ref sync fan-out)    | PWM out         | Optional TTL fan-out |
| PB14 | GPIO (OPA569 current-limit set)| Output (PWM)    | OPA569 I-limit DAC |
| PC0  | ADC2_IN1 (OPA569 output monitor)| Analog in      | Power-amp output read |
| PC1  | ADC2_IN2 (Ref Out monitor)     | Analog in       | Ref amplitude feedback |
| PC2  | ADC2_IN3 (signal monitor pre-PGA) | Analog in     | ±10 V sense, divided |
| PC3  | ADC2_IN4 (aux input A)        | Analog in       | Aux 1 |
| PC4  | ADC2_IN5 (aux input B)        | Analog in       | Aux 2 |
| PC5  | GPIO (mode LED)               | Output          | Green status LED |
| PC6  | GPIO (TP4056 charge status)    | Input           | Charging LED sense |
| PC13 | GPIO (anti-alias filter sel)   | Output          | Optional analog filter relay |
| PC14 | GPIO (input coupling: DC/AC)   | Output          | Relay for AC coupling |
| PC15 | GPIO (input ground: float/gnd) | Output          | Differential vs single-ended |
| PD0  | GPIO (FPU test point)         | Output          | Debug |
| PD1  | GPIO (FPU test point)         | Output          | Debug |
| VDD  | 3.3 V digital power           | Power           | From AP2112-3.3 |
| VDDA | 3.3 V analog power            | Power           | From LP5907-3.3 (low-noise) |
| VREF+| 3.0 V reference               | Reference       | REF3030 (0.2% initial, 7 ppm/°C) |
| VSS  | GND                           | Power           | Star ground |

> **Pin note:** The STM32G491RET6 has 22 GPIO-class pins exposed (the
> LQFP64 exposes all 50 GPIOs; only ~30 are used here). The 5× 12-bit
> ADC runs at 3.6 Msps with hardware oversampling (oversampling ratio
> 256×, sample-shift 8) to give effective 16-bit resolution at 28 ksps,
> well above the 200 kHz analog BW. CORDIC generates the digital sine
> reference at any frequency 1 Hz–100 kHz with micro-Hz resolution.

## Power Architecture

```
   USB-C 5V ──┬── TP4056 (Li-ion charger) ── 18650 (3.7 V 2600 mAh)
              │
              └── MCP1640B boost (3.7 V → 5.0 V, 800 mA) ─┬── ±10 V rail (TPS65131 dual)
                                                         │    (for OPA569 power amp)
                                                         └── 5 V rail (OPA569 I/O,
                                                              ADS1115, μSD)

   18650 3.7 V ── AP2112-3.3 (digital 3.3 V, 600 mA) ── STM32, ESP32-C3, OLED
               ── LP5907-3.3 (analog 3.3 V, 250 mA, ultra-low-noise)
                   ── STM32 VDDA, PGA chain VDD, REF3030
               ── REF3030 (3.0 V, 0.2%, 7 ppm/°C) ── STM32 VREF+, ADC ref
```

- **±10 V rail** for the OPA569 power amplifier is generated by a
  TPS65131 dual-output inverting + buck-boost converter from the 5 V
  boost rail. This allows ±10 V excitation at up to 200 mA (2 W).
- **PGA chain** is powered from the low-noise 3.3 V (LP5907) to
  minimize input-referred noise. The PGA204 (instrumentation amp,
  1×/2×/4×/8×) and PGA113 (1×/2×/4×/8×/16×/32×/64×/128×) chain
  gives 1×–1024× programmable gain.
- **Reference voltage** is a REF3030 (3.0 V, 0.2%, 7 ppm/°C) feeding
  VREF+ of the STM32 ADC, ensuring full-scale stability.
- **Battery monitoring** via a 2:1 divider on PA4; read every 1 s.
- **Power amp (OPA569)** can be shut down (PB12) when not in use to
  save ~20 mA quiescent.

Power budget (continuous operation):
| Stage | Current (from 18650) |
|-------|----------------------|
| STM32 + OLED + SD (idle) | 25 mA |
| ESP32-C3 BLE bridge (advertising) | 8 mA |
| PGA + analog front-end | 15 mA |
| OPA569 power amp (idle, enabled) | 20 mA |
| OPA569 (driving ±10 V, 200 mA peak) | up to 250 mA burst |
| TPS65131 ±10 V converter quiescent | 5 mA |
| **Total typical (signal acquisition, BLE streaming)** | **~75 mA → ~14 h on 2600 mAh** |
| **Total worst case (full sweep, 2 W excitation)** | **~300 mA → ~8 h** |

## Firmware Architecture

Built with **STM32CubeIDE + HAL + CMSIS-DSP** for STM32G491RET6.

```
firmware/
├── CMakeLists.txt
├── Makefile
├── stm32g491_ret6.ld      — linker script
├── startup_stm32g491xx.s   — startup / vector table
├── stm32g491_conf.h       — HAL config
├── main.c                 — State machine + main loop
├── ref_osc.c/h             — CORDIC sine reference + DAC1 drive @ 1 Msps
├── adc.c/h                — ADC1 oversampled sampling @ 28 ksps, DMA double-buffer
├── demod.c/h              — I/Q digital demodulation + IIR LPF
├── pga.c/h                — PGA204/PGA113 gain control + auto-range
├── power_amp.c/h          — OPA569 enable + current limit + output monitor
├── sweep.c/h              — Frequency + amplitude sweep engine
├── display.c/h            — SH1106 OLED: live R/Θ/X/Y + sweep plot
├── sd_log.c/h             — microSD CSV sweep / time-trace logging
├── ble_bridge.c/h         — UART protocol to ESP32-C3 (BLE GATT server)
├── aux_adc.c/h            — ADS1115 aux channel reads
├── battery.c/h            — Battery voltage + low-charge gating
└── ui.c/h                  — Button + rotary encoder menu
```

### State Machine

```
            ┌──────┐  button    ┌──────────┐  user      ┌──────────┐
            │ IDLE │───────────▶│ MENU     │──────────▶│ CONFIG   │
            └──────┘            └──────────┘  select    └────┬─────┘
               ▲                                              │
               │                                              │ start
               │                                              ▼
               │            ┌──────────┐  sweep     ┌─────────────┐
               │            │ REPORT  │◀───────────│ ACQUIRE     │
               │            └────┬────┘            └─────────────┘
               │                 │                       │
               │                 │  stop                 │ sweep
               │                 ▼                       ▼
               │        ┌────────────┐  points   ┌─────────────┐
               └────────│ STOP       │◀─────────│ SWEEP_STEP  │
                        └────────────┘           └─────────────┘
```

### Demodulation Algorithm

The demodulation runs at the oversampled ADC rate `f_s = 28 ksps`:

1. **Sample** — ADC1 hardware-oversamples to 16-bit @ 28 ksps, DMA
   ping-pong double-buffer (1 kHz ISR rate).
2. **Mix** — multiply the signal by the digital reference `sin(2πf₀n/f_s)`
   and `cos(2πf₀n/f_s)`, generated by the CORDIC peripheral at each
   sample tick. This yields I (in-phase) and Q (quadrature) at baseband.
3. **Low-pass filter** — IIR low-pass filter on I and Q with selectable
   time constant (0.5 ms–10 s) and slope (6/12/24/48 dB/oct). The
   filter is a cascade of 2nd-order biquads (CMSIS-DSP `arm_biquad_…`).
4. **R/Θ** — `R = √(I² + Q²)`, `Θ = atan2(Q, I)`. R is the signal
   magnitude at `f₀`; Θ is the phase relative to the reference.
5. **X/Y** — `X = R·cosΘ = I` (in-phase component), `Y = R·sinΘ = Q`
   (quadrature component). Output X and Y as the lock-in outputs.
6. **Noise floor** — compute the RMS of the demodulated signal in the
   sidebands (off `f₀` by ±10/TC), giving the noise spectral density
   at `f₀` in V/√Hz. This is the standard lock-in noise readout.

### Reference Oscillator (CORDIC + DAC)

The STM32G491 has a dedicated CORDIC peripheral that computes
`sin/cos` of a 32-bit phase accumulator at one cycle per sample. The
phase accumulator advances by `Δφ = 2π·f₀/f_s` per sample. The CORDIC
output (signed 16-bit) drives DAC1 at 1 Msps; the reconstruction
filter (a 5th-order Bessel low-pass at 200 kHz) smooths the DAC
staircase into a clean sine at `f₀`. The same phase accumulator
serves the digital demodulator, so the reference and the demodulator
are phase-coherent by construction (no PLL needed).

## Mechanical / Front-Panel Layout

```
   ┌──────────────────────────────────────────────────────────────┐
   │                       PHASE LOCK                              │
   │                                                              │
   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
   │  │ Ref Out │  │ Aux Out │  │ Signal  │  │ Aux In  │         │
   │  │  BNC    │  │  BNC    │  │  BNC    │  │  BNC    │         │
   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘         │
   │                                                              │
   │   ┌───────────────────────────┐                              │
   │   │       1.3" OLED           │   ┌───────┐                 │
   │   │       R / Θ / X / Y        │   │ rotary│                 │
   │   │       sweep plot           │   │ enc.  │                 │
   │   └───────────────────────────┘   └───────┘                 │
   │                                                              │
   │   [MODE]           [RUN/STOP]          [USB-C charge]        │
   │                                                              │
   │                                       [power: 18650 inside] │
   └──────────────────────────────────────────────────────────────┘
```

- The four BNC connectors are on the top edge (Ref Out ±2 V sine at
  `f₀`, Aux Out TTL/offset, Signal In ±10 V, Aux In differential).
- A 1.3" SH1106 OLED shows R, Θ, X, Y, the noise floor, and a
  scrolling plot (time-trace in ACQUIRE mode, swept curve in SWEEP
  mode).
- A rotary encoder (with push) navigates the menu; a MODE button
  cycles between R/Θ/X/Y/noise/sweep-plot views.
- A RUN/STOP button starts and halts acquisition.
- USB-C charges the 18650 (TP4056) and can also stream data via
  CDC-ACM if the BLE bridge is unused.

## Using Phase Lock

### Quick Start

1. **Charge** via USB-C until the green LED stops pulsing.
2. **Connect** the experiment:
   - `Ref Out` → your excitation driver (LED modulator, chopper coil,
     AC voltage source, transformer primary).
   - `Signal In` ← your detector (photodiode, Hall probe, LVDT
     secondary, electrode).
   - Optionally `Aux In` ← a thermistor or other slowly-varying
     input (the aux ADC reads it at 10 Hz).
3. **Power on** — the OLED shows the menu:
   `FREQ · TC · SLOPE · GAIN · SWEEP · RUN · LOG`.
4. **Set frequency** — rotate to FREQ, push, set `f₀` (1 Hz–100 kHz,
   default 1 kHz). The reference starts immediately.
5. **Set time constant** — TC = 300 ms, slope = 12 dB/oct (good
   starting point).
6. **Set gain** — AUTO (the firmware auto-ranges the PGA chain to
   keep the ADC in the top 80% of full-scale).
7. **Press RUN** — the OLED shows live R, Θ, X, Y. Rotate to switch
   the plot between time-trace and swept view.
8. **Sweep** (optional) — set SWEEP = FREQ, 1 Hz–100 kHz, 100 points,
   log. The device sweeps `f₀`, records R/Θ at each point, plots the
   Bode magnitude/phase, and saves to SD as `SWP_NNNN.csv`.
9. **Log** — every RUN and SWEEP is saved to microSD as CSV
   (time-trace: `t, R, Θ, X, Y, noise`; sweep: `f, R, Θ, X, Y, noise`).
10. **Stream** — if a phone/PC is connected over BLE (or USB-CDC),
    all four channels stream at 100 Hz (time-trace) or per-point
    (sweep).

### Calibration

- **Gain calibration**: connect Ref Out directly to Signal In (a
  short BNC cable), set gain = 1×, sweep amplitude 10 mV–2 V. The
  firmware measures the gain flatness vs. frequency and stores the
  correction table in NVS. Run `scripts/gain_cal.py` to generate the
  procedure and read the table over BLE.
- **Phase calibration**: same loopback; the firmware measures the
  phase shift vs. frequency (a function of the analog filter +
  DAC reconstruction filter group delay) and stores the phase
  correction table.
- **Noise floor calibration**: short the Signal In to GND; the
  firmware records the noise spectral density for each gain
  setting and stores it for the noise-figure readout.

### Phone / PC App

A companion app (`scripts/phaselock_app.py` is a minimal Python BLE
client / plotter) subscribes to the R/Θ/X/Y characteristics and
plots the live time-trace or swept curve. Full mobile/desktop app
is out of scope for this repo.

## Example Experiments

### 1. Chopped Photodiode Signal Recovery
- Excitation: Ref Out (1 kHz sine) → LED driver → LED illuminates
  the sample.
- Signal: Photodiode (reverse-biased) → TIA → Signal In.
- Result: R is the photodiode signal at 1 kHz; recover signals
  100 dB below the ambient-light DC level.

### 2. Hall-Effect Measurement at Low Temperature
- Excitation: Ref Out (113 Hz AC) → current source → Hall bar
  (sample in cryostat).
- Signal: Hall voltage (differential) → instrumentation amp →
  Signal In.
- Result: R/Θ gives the Hall resistance; sweep B-field (aux input)
  to map the Hall plateau.

### 3. Electrochemical Impedance Spectroscopy (EIS)
- Excitation: Ref Out (10 mV AC, swept 1 Hz–100 kHz) →
  potentiostat → electrochemical cell.
- Signal: Cell current → TIA → Signal In.
- Result: R(f) and Θ(f) are the impedance magnitude and phase;
  fit to a Randles equivalent circuit for R_ct, C_dl, R_s, W.

### 4. LVDT Position Readout
- Excitation: Ref Out (5 kHz sine) → LVDT primary.
- Signal: LVDT secondary (differential) → Signal In.
- Result: R is proportional to core displacement; Θ flips 180°
  when the core crosses null.

### 5. Dielectric Spectroscopy of a Ferroelectric
- Excitation: Ref Out (swept 100 Hz–100 kHz, 100 mV) → sample
  capacitor.
- Signal: Sample current → TIA → Signal In.
- Result: ε(f) from R/Θ; track the Curie transition with the
  aux-input temperature.

## Limitations & Safety

- **No differential input** (single-ended BNC) — for true
  differential measurements, add an external instrumentation amp
  or use the aux inputs in differential mode. The front-end PGA204
  is differential internally, but the front-panel BNC is
  single-ended for compactness; a differential version would
  replace the BNC with a 3-pin LEMO.
- **±10 V full-scale** — exceeding this on Signal In may damage
  the input protection (back-to-back Schottky clamps to ±10.7 V).
  The firmware watches the pre-PGA monitor and disconnects via
  the analog filter relay if > ±11 V.
- **Power amp (OPA569)** can source 200 mA continuously, 500 mA
  peak. Short-circuit protection is internal; the firmware also
  monitors the current-sense output and shuts down at 250 mA.
- **Battery** — a single 18650 cell; the firmware gates excitation
  (power amp enable) on `Vbat > 3.5 V` to avoid brown-out.
- **Reference oscillator** is a DDS (CORDIC + DAC) — phase noise
  is set by the DAC clock jitter (~1 ns RMS → -100 dBc/Hz at 1 kHz
  offset, 10 kHz carrier), not a crystal oscillator. For ultra-low
  phase-noise work, an external reference can be fed to Aux In.
- **Single demodulator** — one channel only. Dual-channel
  (dual-harmonic, 2f) detection is supported in firmware by running
  a second demodulator at `2·f₀`; see `dual_mode` in the menu.

## Bill of Materials

See `hardware/BOM.csv` — total ~$62.

## Documentation

- `docs/assembly-guide.md` — step-by-step build, front-panel wiring,
  BNC connector mounting, analog chain layout, grounding.
- `docs/api-reference.md` — BLE GATT characteristics, SD card file
  format, firmware build instructions, UART bridge protocol.
- `docs/experiment-guide.md` — example experiments (chopped
  photodiode, Hall effect, EIS, LVDT, dielectric spectroscopy)
  with wiring and parameter setup.

## License

MIT — build it, sell it, improve it.

---

*Invented by [jayis1](https://github.com/jayis1). Part of the
[SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions)
collection.*