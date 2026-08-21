# Bone Echo — Pocket Quantitative Ultrasound Bone Densitometer

> A battery-powered, pocket-sized quantitative ultrasound (QUS) bone
> densitometer that measures broadband ultrasound attenuation (BUA) and
> speed of sound (SOS) through the calcaneus (heel bone), computes the
> Stiffness Index, and estimates T-score / Z-score for osteoporosis
> screening — bringing a $12k–$30k clinical QUS device down to ~$78 and
> coffee-mug size.

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                        BONE ECHO                                      │
 │        Pocket quantitative ultrasound bone densitometer               │
 │                                                                       │
 │  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐    │
 │  │ HV Pulse │───▶│ TX xdr   │───▶│  Heel     │───▶│ RX xdr     │    │
 │  │ 200V    │    │ 1 MHz    │    │ (calcaneus)│   │ 1 MHz      │    │
 │  └──────────┘    └──────────┘    └───────────┘    └─────┬──────┘    │
 │                                                       │            │
 │  ┌──────────┐    ┌──────────┐                          ▼            │
 │  │  HRTIM   │───▶│ TX pulse │                   ┌──────────────┐     │
 │  │ trigger  │    │ gen 1MHz │                   │ VGA + TGC    │     │
 │  └────┬─────┘    └──────────┘                   │ AD8331 48 dB │     │
 │       │                                          └──────┬───────┘    │
 │       │  start-of-flight                              │            │
 │       └──────────────┬───────────────────────────────┘            │
 │                      ▼                                               │
 │            ┌───────────────────┐   time-of-flight ──▶ SOS (m/s)    │
 │            │  STM32G474 ADC     │   BUA (slope of dB vs freq)       │
 │            │  3.6 Msps 16-bit   │                                   │
 │            │  DMA + CORDIC FFT  │──▶ Stiffness Index                 │
 │            └───────────────────┘    T-score / Z-score                │
 │                                                                       │
 │  SoC: STM32G474RET6 (HRTIM, CORDIC, FMAC, 3.6 Msps ADC, 12-bit)     │
 │  BLE: ESP32-C3-MINI-1  ·  OLED: SH1106 128×64  ·  SD: microSD       │
 └──────────────────────────────────────────────────────────────────────┘
```

## What It Does

Bone Echo is a complete quantitative ultrasound (QUS) bone
densitometer that fits in a pocket. The patient places their heel
(calcaneus) between two 1 MHz ultrasonic transducers in a
spring-loaded coupling fixture; a water-based ultrasonic gel provides
acoustic coupling. On a button press, the device:

1. **Excites** — the STM32G474's HRTIM triggers a high-voltage (200 V)
   pulse that drives the transmitter transducer with a 5-cycle 1 MHz
   tone burst, launching a longitudinal ultrasound wave through the
   heel bone.
2. **Receives** — the wave that emerges through the bone is captured
   by the receiver transducer, amplified by a time-gain-controlled
   variable-gain amplifier (AD8331, 0–48 dB, programmable TGC ramp),
   band-pass filtered (0.5–2 MHz), and digitized by the STM32G474's
   12-bit ADC at 3.6 Msps with hardware oversampling to 16-bit
   effective resolution at 28 ksps (for BUA spectral analysis) and
   at the full 3.6 Msps rate (for SOS time-of-flight).
3. **Measures time-of-flight** — the HRTIM start trigger and the
   ADC's first-received-signal threshold crossing give the
   time-of-flight `t_f` through the heel. Combined with the
   measured heel thickness `d` (entered via caliper foot or
   ultrasound-only self-calibration), the speed of sound is
   `SOS = d / t_f` (in m/s).
4. **Measures broadband attenuation** — the received signal's FFT
   (computed via CORDIC-accelerated CMSIS-DSP) yields the attenuation
   vs. frequency in the 0.2–0.6 MHz band. The slope of the linear
   regression of attenuation (dB) vs. frequency (MHz) is the **BUA**
   (dB/MHz). A reference measurement through a known phantom (water
   or acrylic block) cancels the transducer and coupling losses.
5. **Computes Stiffness Index** — `SI = 0.67·BUA + 0.28·SOS − 420`
   (the standard Langton et al. formula, configurable). SI maps to
   bone density and fracture risk.
6. **Estimates T-score / Z-score** — the device holds an age/sex/ethnicity
   normative database (WHO/ISCD reference values for the calcaneus).
   It looks up the expected SI for the patient's demographic and
   computes `T = (SI − youngAdultMean) / youngAdultSD` and
   `Z = (SI − ageMatchedMean) / ageMatchedSD`.
7. **Classifies** — per WHO criteria: T ≥ −1.0 normal, −2.5 < T < −1.0
   osteopenia, T ≤ −2.5 osteoporosis, T ≤ −2.5 with fracture severe
   osteoporosis. Reports the category, the absolute SOS/BUA/SI numbers,
   a fracture-risk percentile, and a recommendation ("normal — repeat
   in 2 years" / "osteopenia — DEXA recommended" / "osteoporosis —
   physician consult").
8. **Reports** — displays SOS, BUA, SI, T-score, Z-score, and
   classification on the OLED; logs every measurement to microSD
   (CSV with timestamp, patient ID, demographics, raw waveform
   capture); and streams the full waveform + results over BLE to a
   phone/PC app for electronic medical record (EMR) integration.

## Why It's Interesting

Osteoporosis is a silent epidemic: worldwide, 1 in 3 women and
1 in 5 men over 50 will suffer an osteoporotic fracture. Early
detection via bone densitometry enables treatment that reduces
fracture risk by 30–70%. The current standard, DEXA (dual-energy
X-ray absorptiometry), requires a $40k–$80k scanner, a certified
radiology technician, and a clinic visit — out of reach for the
>2 billion people over 50 in low- and middle-income countries.

Quantitative ultrasound (QUS) of the calcaneus is a **radiation-free,
low-cost, point-of-care** alternative validated by the International
Society for Clinical Densitometry (ISCD). QUS measures bone
*quality* (architecture, elasticity) in addition to density, and
meta-analyses of >40,000 patients show QUS of the calcaneus predicts
hip fracture as well as central DEXA. Clinical QUS devices (GE
Achilles, Hologic Sahara, DMS Pixi) cost $12k–$30k and weigh 8–15 kg,
limiting deployment to well-funded clinics.

Bone Echo is designed for:

- **Point-of-care screening** — community health workers in rural
  clinics, pharmacies, mobile screening vans can carry a pocket QUS
  device for $78 instead of a $20k Achilles.
- **Low-resource settings** — no ionizing radiation (no lead
  shielding, no radiation safety officer), no mains power (18650
  battery, 20+ hours), no calibration service contract (auto-cal
  with included acrylic phantom).
- **Epidemiology & population screening** — the BLE+SD logging +
  patient-ID input enables large-scale field screening with
  phone-based EMR integration; one operator can screen 200+ people
  per day with a device that fits in a lab-coat pocket.
- **Osteoporosis research** — the open waveform capture + raw
  SOS/BUA output enable reproducible research; the device exports
  raw A-scans, not just scores, so labs can develop new QUS indices
  (e.g., ultrasound backscatter, apparent cortical thickness).
- **Veterinary** — equine / bovine bone quality assessment; the
  adjustable heel width (10–80 mm) accommodates animal limbs.
- **Education** — every biomechanics / biomedical-engineering senior
  lab can have a real QUS densitometer for $78 instead of sharing
  one $20k Achilles among 200 students.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| SoC | STM32G474RET6 (ARM Cortex-M4F, 170 MHz, FPU, CORDIC, FMAC, HRTIM) |
| BLE / Wi-Fi bridge | ESP32-C3-MINI-1 (BLE 5, Wi-Fi 4) |
| Transducers | 2× 1 MHz longitudinal PZT, 13 mm active aperture, matched pair |
| Excitation | 200 V HV pulse, 5-cycle 1 MHz tone burst, HRTIM-triggered |
| Receiver | AD8331 VGA, 0–48 dB programmable gain, TGC ramp |
| Band-pass filter | 0.5–2 MHz 4th-order Bessel (analog) |
| ADC | STM32G474 ADC1, 12-bit, 3.6 Msps; oversample → 16-bit @ 28 ksps (spectral), full-rate 3.6 Msps (ToF) |
| Speed of sound (SOS) | 1400–2200 m/s range, ±5 m/s accuracy |
| BUA | 0–80 dB/MHz range, ±2 dB/MHz accuracy, 0.2–0.6 MHz fit band |
| Stiffness Index | 0–120 range |
| T-score / Z-score | ±5 range, 0.01 resolution |
| Normative DB | WHO/ISCD calcaneus, 9 age groups × 2 sex × 3 ethnicity = 54 entries |
| Heel width | 20–80 mm (spring-loaded caliper fixture, auto-sensed) |
| Sample rate (waveform) | 3.6 Msps raw capture, 32 ms window (115k samples) |
| Patient input | 4-button numeric pad (ID, age, sex, ethnicity) |
| Display | 1.3" OLED 128×64 I2C (SH1106) — SOS/BUA/SI/T-score + waveform |
| Logging | microSD (FAT32, CSV + raw binary waveform) |
| Wireless | BLE 5 (ESP32-C3 bridge) — waveform + results streaming |
| Power | 18650 Li-ion (3.7 V, 2600 mAh) — ~20 h / ~600 scans |
| Form factor | 140 × 72 × 30 mm (heel fixture adds 60 mm height) |
| Weight | ~180 g (with battery) + 90 g fixture |
| BOM cost | ~$78 |

## Block Diagram

```
                       ┌────────────────────────────────────────────┐
                       │           STM32G474RET6 (U1)                │
                       │  ┌──────────────────────────────────────┐ │
                       │  │ Cortex-M4F 170 MHz · CORDIC · FMAC   │ │
                       │  │ HRTIM · 4× 12-bit ADC · 4× DAC       │ │
                       │  └──────────────────────────────────────┘ │
                       │                                            │
                       │  HRTIM A ─▶ TX_PULSE_TRIG (start-of-flight)│
                       │  DAC1 ──▶ TGC ramp (VGA gain control)      │
                       │  ADC1 ──◀ RX signal (after VGA + BPF)       │
                       │  CORDIC ─▶ FFT window (CMSIS-DSP)            │
                       │  I2C1 ──▶ SH1106 OLED                       │
                       │  SPI2 ──▶ microSD                          │
                       │  USART──▶ ESP32-C3 (BLE bridge)             │
                       └────────────────────────────────────────────┘
                          │      │      │      │       │       │
                     ┌────┘  ┌───┘  ┌───┘  ┌───┘  ┌────┘  ┌────┘
                     ▼       ▼     ▼       ▼     ▼       ▼
              ┌────────┐ ┌────┐ ┌─────┐ ┌────┐ ┌─────┐ ┌──────┐
              │ HV pulse│ │AD  │ │ BPF │ │OLED│ │ μSD │ │ESP32-│
              │ 200V    │ │8331│ │0.5- │ │128 │ │ FAT│ │C3 BLE│
              │ 1MHz    │ │VGA │ │2MHz │ │×64 │ │ CSV│ │bridge│
              └────┬───┘ └─┬──┘ └──▲──┘ └────┘ └─────┘ └──────┘
                   │       │       │
                   ▼       ▼       │  RX signal
              ┌────────┐  ┌──────┐│   ┌──────┐
              │ TX xdr │  │ RX   │└──▶│ RX   │
              │ 1 MHz  │  │ xdr  │    │ xdr  │
              │ PZT    │  │ 1MHz │    │ 1MHz │
              └────────┘  └──────┘    └──────┘
                   │          ▲          │
                   └──────────┴──────────┘
                          HEEL (calcaneus)
                          in coupling fixture

  TX path:  HRTIM trigger ─▶ HV pulser (200 V, 1 MHz, 5 cycles)
            ─▶ TX transducer ─▶ heel ─▶ RX transducer ─▶ BPF
            ─▶ AD8331 VGA (TGC ramp from DAC1) ─▶ STM32 ADC1
            (3.6 Msps raw for ToF; oversampled 16-bit @ 28 ksps for BUA FFT)

  RX processing:
    ToF: HRTIM start ── ADC threshold-cross ──▶ t_f ──▶ SOS = d / t_f
    BUA: FFT(RX window) ─▶ |H(f)| ─▶ dB(f) ─▶ linear fit 0.2–0.6 MHz
         ─▶ slope = BUA (dB/MHz)
    Fusion: SI = 0.67·BUA + 0.28·SOS − 420
            T-score, Z-score from normative DB
```

## Pin Assignments (STM32G474RET6 — LQFP64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0  | ADC1_IN1 (RX signal after VGA+BPF)     | Analog in  | 0–3.3 V, 3.6 Msps |
| PA1  | DAC1_OUT1 (TGC ramp control)          | Analog out | 12-bit, drives AD8331 VGA gain pin |
| PA2  | DAC1_OUT2 (phantom temp offset)        | Analog out | Optional |
| PA3  | ADC1_IN4 (HV monitor: 200 V sense)    | Analog in  | 100:1 divider, HV pulse verify |
| PA4  | ADC1_IN17 (battery V divider)         | Analog in  | 2:1 divider on Vbat |
| PA5  | ADC2_IN13 (heel caliper pot sense)   | Analog in  | 10 kΩ pot on caliper → heel width d |
| PA6  | ADC1_IN3 (VGA gain monitor)           | Analog in  | AD8331 gain sense feedback |
| PA7  | ADC2_IN4 (phantom temp: DS18B20 echo)| Analog in  | 1-Wire read (bit-banged) |
| PA8  | HRTIM_CHA1 (TX pulse trigger)         | PWM out    | 200 V pulser trigger, edge |
| PA9  | USART1_TX (ESP32-C3 bridge)           | UART out   | 921600 baud |
| PA10 | USART1_RX (ESP32-C3 bridge)           | UART in    | 921600 baud |
| PA11 | I2C1_SDA (OLED + ADS1115 aux)         | I2C        | 400 kHz |
| PA12 | I2C1_SCL (OLED + ADS1115 aux)         | I2C        | 400 kHz |
| PA13 | SPI1_SCK (microSD)                    | SPI out    | 25 MHz max |
| PA14 | SPI1_MISO (microSD)                   | SPI in     | SD card data |
| PA15 | SPI1_MOSI (microSD)                   | SPI out    | SD card data |
| PB0  | GPIO (mode button)                    | Input(pu)  | Long-press = menu |
| PB1  | GPIO (encoder A)                     | Input(pu)  | Rotary nav |
| PB2  | GPIO (encoder B)                     | Input(pu)  | Rotary nav |
| PB3  | GPIO (encoder push / select)          | Input(pu)  | Select |
| PB4  | GPIO (HV enable)                      | Output     | 1 = HV pulser armed |
| PB5  | GPIO (HV charge / discharge)          | Output     | Controls HV charge pump duty |
| PB6  | GPIO (PGA/AD8331 gain A0)             | Output     | VGA gain select bit 0 |
| PB7  | GPIO (PGA/AD8331 gain A1)             | Output     | VGA gain select bit 1 |
| PB8  | GPIO (microSD CS)                     | Output     | Active-low |
| PB9  | GPIO (ESP32-C3 reset)                 | Output     | BLE bridge reset |
| PB10 | GPIO (BLE bridge enable)              | Output     | 1 = enabled |
| PB11 | GPIO (RGB LED, WS2812B)               | Output(RMT)| Status |
| PB12 | GPIO (phantom detection switch)       | Input(pu)  | Reed switch: phantom present |
| PB13 | TIM2_CH1 (ToF precise timer gate)     | Timer in   | Input capture for SOS timing |
| PB14 | GPIO (patient-ID digit 0 button)      | Input(pu)  | 4-button numeric pad |
| PB15 | GPIO (patient-ID digit 1 button)      | Input(pu)  | 4-button numeric pad |
| PC0  | ADC2_IN1 (TX drive monitor)          | Analog in  | Verify pulse amplitude |
| PC1  | ADC2_IN2 (RX pre-VGA monitor)         | Analog in  | Direct RX for debug |
| PC2  | ADC2_IN3 (phanton acoustic ref)       | Analog in  | Phantom reference signal |
| PC3  | ADC2_IN4 (aux temp/humidity)          | Analog in  | BME280 aux (optional) |
| PC4  | GPIO (HV charge pump PWM)            | Output(PWM)| 50 kHz boost converter |
| PC5  | GPIO (status LED green)              | Output     | Power OK |
| PC6  | GPIO (TP4056 charge status)          | Input      | Charging LED sense |
| PC13 | GPIO (patient-ID digit 2 button)     | Input(pu)  | 4-button numeric pad |
| PC14 | GPIO (patient-ID digit 3 button)     | Input(pu)  | 4-button numeric pad |
| PC15 | GPIO (1-Wire DS18B20, phantom temp)   | Bidir      | Bit-banged 1-Wire |
| PD0  | GPIO (SWDIO / debug)                 | Debug      | SWD |
| PD1  | GPIO (SWCLK / debug)                 | Debug      | SWD |
| VDD  | 3.3 V digital power                  | Power      | From AP2112-3.3 |
| VDDA | 3.3 V analog power                   | Power      | From LP5907-3.3 (low-noise) |
| VREF+| 3.0 V reference                     | Reference  | REF3030 (0.2%, 7 ppm/°C) |
| VSS  | GND                                 | Power      | Star ground, AGND/DGND split |

> **Pin note:** The STM32G474RET6 LQFP64 exposes 50 GPIOs; ~34 are
> used here. The HRTIM peripheral provides sub-ns timing resolution
> for the transmit trigger and time-of-flight measurement; the
> CORDIC accelerator parallelizes the FFT windowing for BUA
> computation. ADC1 runs at full 3.6 Msps for ToF capture (single
> shot, 32 ms window, 115k samples into a dedicated SRAM buffer), then
> switches to oversampled 16-bit @ 28 ksps for the BUA spectral
> measurement (longer window, lower rate, higher ENOB).

## Power Architecture

```
   USB-C 5V ──┬── TP4056 (Li-ion charger) ── 18650 (3.7 V 2600 mAh)
              │
              └── MCP1640B boost (3.7 V → 5.0 V, 800 mA) ─┬── 5 V rail
                                                         │   (HV charge pump, AD8331)
                                                         │
   18650 3.7 V ── AP2112-3.3 (digital 3.3 V, 600 mA) ── STM32, ESP32-C3, OLED
                ── LP5907-3.3 (analog 3.3 V, 250 mA, ultra-low-noise)
                    ── STM32 VDDA, AD8331 VDD, REF3030
                ── REF3030 (3.0 V, 0.2%, 7 ppm/°C) ── STM32 VREF+, ADC ref

   HV rail: 5 V ── MAX668 boost (5→200 V, 10 mA) ── HV pulser
            (only armed during a scan; discharged to GND via 100 kΩ
            bleeder when PB5=0 for safety)
```

- **HV rail (200 V)** for the transmitter pulser is generated by a
  MAX668 boost converter from the 5 V rail. It is only armed (PB4)
  during an active scan and is actively discharged (PB5) to GND
  within 1 s of scan completion via a 100 kΩ bleeder resistor —
  200 V × 100 kΩ = 2 mA discharge, τ = 2 ms, safe in <10 ms.
- **AD8331 VGA** is powered from the low-noise 3.3 V (LP5907) to
  minimize receiver noise. Its gain is set by a combination of the
  DAC1 ramp (TGC — time gain compensation, compensating for tissue
  attenuation vs. depth) and the 2-bit GPIO gain mode (PB6/PB7).
- **Reference voltage** is a REF3030 (3.0 V, 0.2%, 7 ppm/°C) feeding
  VREF+ of the STM32 ADC, ensuring full-scale stability for the
  quantitative BUA/SOS measurement.
- **Battery monitoring** via a 2:1 divider on PA4; read every 1 s.
- The HV charge pump is gated on `Vbat > 3.5 V` to avoid brown-out.

Power budget (continuous scanning):
| Stage | Current (from 18650) |
|-------|----------------------|
| STM32 + OLED + SD (idle) | 25 mA |
| ESP32-C3 BLE bridge (advertising) | 8 mA |
| AD8331 VGA + analog RX chain | 18 mA |
| HV charge pump (idle, armed) | 5 mA |
| HV charge pump (charging for scan) | 80 mA burst (200 ms) |
| TX pulse burst (200 V, 5 cycles) | 250 mA peak (10 µs) |
| **Total typical (standby, BLE streaming)** | **~58 mA → ~45 h on 2600 mAh** |
| **Total during active scan** | **~140 mA burst → ~600 scans per charge** |

## Firmware Architecture

Built with **STM32CubeIDE + HAL + CMSIS-DSP** for STM32G474RET6.

```
firmware/
├── CMakeLists.txt
├── Makefile
├── stm32g474_ret6.ld      — linker script
├── startup_stm32g474xx.s   — startup / vector table
├── stm32g474_conf.h       — HAL config
├── main.c                 — State machine + main loop
├── tx_pulser.c/h          — HRTIM-triggered 200 V 1 MHz 5-cycle burst
├── rx_chain.c/h           — AD8331 VGA + TGC ramp + BPF control
├── adc.c/h                — ADC1 3.6 Msps ToF capture + 28 ksps BUA oversample
├── sos.c/h                — Speed-of-sound: threshold-cross ToF + d/t_f
├── bua.c/h                — BUA: FFT, attenuation vs freq, linear fit 0.2–0.6 MHz
├── stiffness.c/h          — SI = 0.67·BUA + 0.28·SOS − 420
├── normative.c/h          — WHO/ISCD T-score / Z-score look-up
├── phantom.c/h            — Acrylic phantom reference measurement
├── heel_caliper.c/h       — Caliper pot → heel width d (mm)
├── display.c/h            — SH1106 OLED: SOS/BUA/SI/T-score + waveform
├── sd_log.c/h             — microSD CSV + raw waveform binary logging
├── ble_bridge.c/h         — UART protocol to ESP32-C3 (BLE GATT server)
├── aux_adc.c/h            — ADS1115 aux channel reads (temp, etc.)
├── battery.c/h            — Battery voltage + low-charge gating
├── patient.c/h            — Patient ID + age + sex + ethnicity input
└── ui.c/h                 — Button + rotary encoder + numeric pad menu
```

### State Machine

```
            ┌──────┐  button    ┌──────────┐  select    ┌────────────┐
            │ IDLE │───────────▶│ MENU     │───────────▶│ PATIENT    │
            └──────┘            └──────────┘           │ ENTRY      │
               ▲                                          └────┬─────┘
               │                                               │ done
               │                                               ▼
               │            ┌──────────┐  phantom   ┌─────────────┐
               │            │ REPORT  │◀───────────│ PHANTOM_REF │
               │            └────┬────┘            └─────────────┘
               │                 │                       │
               │                 │  next                 │ heel in
               │                 ▼                       ▼
               │        ┌────────────┐  result   ┌─────────────┐
               └────────│ DONE       │◀─────────│ SCAN         │
                        └────────────┘           └─────────────┘
```

### SOS Algorithm

1. **Acquire** — ADC1 captures 32 ms at 3.6 Msps (115,200 samples)
   starting at the HRTIM TX trigger edge. The first sample above a
   noise-proportional threshold (default 6σ above the pre-trigger
   RMS) marks the wave arrival `t_arr`.
2. **Sub-sample interpolation** — parabolic fit on the three samples
   around `t_arr` refines the crossing to 1/10 sample = 28 ns.
3. **Time-of-flight** — `t_f = t_arr − t_TX_trigger − t_probe_delay`,
   where `t_probe_delay` is the calibrated transducer + cable delay
   (from the phantom reference measurement).
4. **Heel width** — the caliper potentiometer on PA5 gives `d` in mm
   (linear fit, calibrated: 0 V = 0 mm, 3.3 V = 80 mm).
5. **SOS** — `SOS = d / t_f` (m/s). Typical calcaneus: 1450–1950 m/s.

### BUA Algorithm

1. **Acquire** — ADC1 oversamples to 16-bit @ 28 ksps for 50 ms
   (1400 samples) to get a clean narrowband snapshot of the received
   burst. (The 1 MHz carrier mixes down to baseband via digital I/Q
   demodulation at 1 MHz, yielding a complex envelope.)
2. **FFT** — CMSIS-DSP `arm_cfft_f32` on the complex envelope, with
   CORDIC for the twiddle factors. Yields `|H(f)|` in the 0.2–0.6 MHz
   band (after the envelope demodulation shifts the carrier to DC,
   the band of interest is 0.2–0.6 MHz *relative to 1 MHz* = 0.8–1.6 MHz
   absolute; the band-pass filter passes this band cleanly).
3. **Attenuation** — `A(f) = −20·log10(|H_rx(f)| / |H_ref(f)|)` dB,
   where `|H_ref(f)|` is the reference FFT from the acrylic phantom
   measurement (cancels transducer + coupling response).
4. **Linear fit** — least-squares regression of `A(f)` vs `f` over
   0.2–0.6 MHz. Slope = **BUA** (dB/MHz). Intercept is the
   frequency-independent attenuation (not used for SI).
5. **Quality check** — fit R² must be > 0.75 or the scan is flagged
   "poor coupling — reapply gel and retry."

### Stiffness Index & T-score

- `SI = 0.67·BUA + 0.28·SOS − 420` (Langton 1996, configurable).
- `T = (SI − youngAdultMean) / youngAdultSD`, where youngAdultMean/SD
  are looked up from the normative DB by sex + ethnicity
  (e.g., Caucasian female: mean = 89, SD = 12).
- `Z = (SI − ageMatchedMean) / ageMatchedSD`, age-matched from the DB.
- WHO classification:
  - T ≥ −1.0 → Normal
  - −2.5 < T < −1.0 → Osteopenia
  - T ≤ −2.5 → Osteoporosis
  - T ≤ −2.5 + prior fracture → Severe osteoporosis

## Mechanical / Front-Panel Layout

```
   ┌──────────────────────────────────────────────────────────────┐
   │                       BONE ECHO                               │
   │                                                              │
   │   ┌──────────────────────────────────────────┐               │
   │   │            Heel Coupling Fixture          │               │
   │   │   ┌─────────┐         ┌─────────┐        │               │
   │   │   │  TX     │  heel  │  RX     │        │               │
   │   │   │  xdr    │ ◀────▶ │  xdr    │        │               │
   │   │   └─────────┘         └─────────┘        │               │
   │   │   ◀──── spring-loaded, 20–80 mm ────▶    │               │
   │   └──────────────────────────────────────────┘               │
   │                                                              │
   │   ┌───────────────────────────┐                              │
   │   │       1.3" OLED           │   ┌───────┐                  │
   │   │   SOS / BUA / SI / T-score │   │ rotary│                  │
   │   │   waveform + classification│   │ enc.  │                  │
   │   └───────────────────────────┘   └───────┘                  │
   │                                                              │
   │  [ID] [AGE] [SEX] [ETH]   [SCAN]   [USB-C charge]             │
   │                                                              │
   │                                       [power: 18650 inside] │
   └──────────────────────────────────────────────────────────────┘
```

- The heel coupling fixture is a spring-loaded caliper that grips the
  calcaneus between the two 1 MHz transducers. Ultrasonic gel is
  applied to both transducer faces. The caliper auto-senses heel
  width via the PA5 potentiometer (20–80 mm range).
- A 1.3" SH1106 OLED shows SOS, BUA, SI, T-score, Z-score, the
  WHO classification, and a scrolling waveform (raw A-scan in SCAN
  mode, BUA spectrum fit in REPORT mode).
- A rotary encoder (with push) navigates the menu.
- 4 tactile buttons enter the patient ID (numeric pad: ID, AGE, SEX
  toggle, ETHNICITY cycle).
- A SCAN button starts the measurement.
- USB-C charges the 18650 (TP4056) and can also stream data via
  CDC-ACM if the BLE bridge is unused.

## Using Bone Echo

### Quick Start

1. **Charge** via USB-C until the green LED stops pulsing.
2. **Phantom calibration** — place the included 25 mm acrylic phantom
   between the transducers (the reed switch on PB12 detects it
   automatically). Press SCAN. The device measures the phantom SOS
   (≈ 2700 m/s for acrylic) and the reference FFT `|H_ref(f)|`,
   stores them in NVS. Do this once per session (or per day).
3. **Patient setup** — enter the patient ID (4-digit numeric pad),
  age (rotary encoder), sex (toggle), ethnicity (cycle: Caucasian /
  Asian / African / Hispanic / Other). The normative DB is
  selected accordingly.
4. **Apply gel** — ultrasonic coupling gel on both transducer faces.
5. **Position heel** — place the calcaneus in the fixture; the
  caliper closes on the heel with gentle spring pressure.
6. **Press SCAN** — the HV pulser fires, the ADC captures, the
  firmware computes SOS + BUA + SI + T-score in ~2 s.
7. **Read result** — the OLED shows:
   ```
   SOS: 1562 m/s   BUA: 58.4 dB/MHz
   SI:  84.2       T:  -1.2   Z: -0.3
   OSTEOPENIA
   DEXA recommended
   ```
8. **Log** — every scan is saved to microSD as `PT_NNNN.csv`
  (demographics, SOS, BUA, SI, T, Z, classification, timestamp) plus
  `PT_NNNN.bin` (raw 115k-sample A-san waveform).
9. **Stream** — if a phone/PC is connected over BLE (or USB-CDC),
  the full waveform + results stream in real time; the companion
  app (`scripts/boneecho_app.py`) plots the A-scan and the BUA
  spectrum fit, and can export to HL7 for EMR integration.

### Calibration

- **Phantom calibration** — the included 25 mm acrylic phantom has
  a known SOS (2700 ± 30 m/s) and known attenuation slope. The
  device measures it at the start of each session; the measured
  SOS is compared to 2700 m/s and the `t_probe_delay` is adjusted
  so `d_phantom / t_f = 2700`. The phantom FFT `|H_ref(f)|` is
  stored for the BUA reference. Run `scripts/phantom_cal.py` to
  generate the procedure and read it over BLE.
- **Heel caliper calibration** — with the fixture closed (d = 0),
  press and hold SCAN for 5 s; the firmware reads PA5 and stores
  the zero. Open to 80 mm (max), repeat; stores the full-scale.
  Linear fit gives `d(mm) = (V_PA5 − V0) / (V80 − V0) × 80`.
- **HV pulse verification** — the PA3 ADC monitors the 200 V pulse
  via a 100:1 divider (200 V → 2 V). If the pulse amplitude is
  outside 180–220 V, the scan aborts with "HV FAULT."

### Phone / PC App

A companion app (`scripts/boneecho_app.py` is a minimal Python BLE
client / plotter) subscribes to the SOS/BUA/SI/T-score
characteristics, plots the live A-scan and BUA spectrum fit, and
can export a patient report (PDF or HL7 v2.5). Full mobile/desktop
app is out of scope for this repo.

## Example Scenarios

### 1. Community Osteoporosis Screening
- A community health worker in a rural clinic carries Bone Echo in
  a lab-coat pocket. Over a 6-hour screening camp, 200 women aged
  50–75 are screened. Each scan takes ~30 s (positioning + 2 s scan).
  Those flagged osteopenia/osteoporosis are referred to a district
  hospital for confirmatory DEXA. Cost per screen: ~$0.13 amortized
  over the device lifetime.

### 2. Pharmacy Bone-Health Check
- A pharmacy offers a "bone health check" service: walk in, place
  your heel in the device, get a T-score in 30 s for $5. The
  pharmacist recommends calcium/vitamin D for normal, refers
  osteopenia to a GP, and refers osteoporosis to a specialist.

### 3. Osteoporosis Research
- A research lab uses the raw waveform export to develop a new
  QUS index: apparent cortical thickness from the echo pattern,
  or ultrasound backscatter (BUB) from the trabecular structure.
  The open CSV + binary waveform format supports reproducible
  analysis.

### 4. Veterinary Bone Quality
- An equine vet assesses a racehorse's cannon bone quality via
  QUS; the adjustable caliper (20–80 mm) accommodates the
  cannon bone (≈ 25 mm). SOS < 3200 m/s flags stress-fracture risk.

### 5. Education
- A biomedical-engineering senior lab has 10 Bone Echo devices
  ($780 total vs. one shared $20k Achilles). Students measure
  SOS/BUA on phantoms, on their own heels, and study the
  trade-offs between QUS and DEXA.

## Limitations & Safety

- **Heel-only** — the calcaneus is the validated QUS site. Other
  sites (radius, phalanx) require different transducer spacing and
  are not supported by the standard normative DB.
- **200 V HV** — the transmitter pulser operates at 200 V. The
  firmware arms the HV only during a scan and discharges it to GND
  within 1 s of completion (100 kΩ bleeder, τ = 2 ms). The
  transducer is isolated from the patient by the coupling gel and
  the transducer face; the 200 V is a short (10 µs) burst, not a
  sustained voltage. Still, the fixture is designed so the
  transducers cannot be touched with the HV armed (spring-loaded
  cover interlock).
- **Single heel thickness** — the caliper auto-senses 20–80 mm.
  For very thin or very thick heels, the spring pressure may be
  insufficient; an optional strap ensures consistent coupling.
- **Coupling gel required** — dry contact gives no signal; the
  firmware detects poor coupling (R² < 0.75 on the BUA fit) and
  prompts to reapply gel.
- **Normative DB is population-specific** — the WHO/ISCD reference
  values are based on Caucasian populations; using them for other
  ethnicities may bias the T-score. The device includes 3 ethnicity
  options (Caucasian / Asian / African / Hispanic) with
  population-specific means/SDs where available; "Other" uses the
  Caucasian reference with a warning.
- **Not a DEXA replacement** — QUS measures bone quality, not
  areal BMD. The ISCD position is that QUS is a *screening* tool;
  a positive screen should be confirmed by central DEXA before
  treatment. Bone Echo reports the WHO classification and
  explicitly recommends "DEXA confirmation" for osteopenia/
  osteoporosis.
- **Single measurement** — the device takes one measurement per
  scan. For clinical use, ISCD recommends the average of 3
  measurements; the firmware supports a "3-scan average" mode
  that runs 3 scans and reports the mean SOS/BUA/SI.
- **Temperature sensitivity** — SOS varies by ~3 m/s/°C in soft
  tissue. The phantom reference (at room temp) cancels the
  transducer/cable drift, but heel temperature (cool vs. warm)
  adds ~±10 m/s variability. The optional BME280 (PC3) reads room
  temp; the firmware applies a soft-tissue temperature correction
  if the patient reports foot temperature (cold/warm/normal).

## Bill of Materials

See `hardware/BOM.csv` — total ~$78.

## Documentation

- `docs/assembly-guide.md` — step-by-step build, heel fixture
  fabrication, transducer mounting, HV safety, grounding.
- `docs/api-reference.md` — BLE GATT characteristics, SD card file
  format, firmware build instructions, UART bridge protocol.
- `docs/clinical-guide.md` — phantom calibration, patient
  positioning, interpretation of SOS/BUA/SI/T-score, WHO
  classification, limitations vs. DEXA, normative DB notes.
- `docs/normative-db.md` — full WHO/ISCD calcaneus reference table
  (54 entries: 9 age groups × 2 sex × 3 ethnicity).

## License

MIT — build it, sell it, improve it.

---