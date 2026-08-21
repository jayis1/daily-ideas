# Lode Sweep — Pocket Pulse-Induction Metal Detector with On-Device Target Identification

> A pocket-sized, battery-powered, pulse-induction (PI) metal detector that
> transmits a high-current magnetic pulse through a search coil, samples the
> decaying secondary field at **16 logarithmically-spaced time gates**
> (10–284 µs after pulse-off), performs **adaptive ground mineralization
> cancellation**, extracts a 16-feature decay-curve fingerprint, classifies
> the buried target with an on-device **k-NN classifier** (8 metal classes:
> iron, foil, nickel, pull-tab, zinc, copper, silver, gold), estimates depth
> from signal amplitude + coil tilt compensation, geo-tags every detection
> with a NEO-M9N GPS, logs a survey CSV to microSD, and streams live target
> ID + depth to a phone over BLE / Wi-Fi — bringing $900–$5,000 professional
> metal detectors (Minelab Equinox, XP Deus, Fisher CZ-21) down to **~$63**
> and a coffee-mug form factor, with an open decay-curve DSP pipeline and
> ML classifier that commercial units keep proprietary.

---

## 1. What it is

**Lode Sweep** is a handheld PI metal detector with on-device AI target
identification. You sweep the search coil over the ground, and it:

1. **Transmits** a 100 µs, ~10 A current pulse through a 25 cm air-core
   search coil (mono TX/RX configuration), building a magnetic field that
   penetrates ~30 cm into the ground. The pulse repeats at 1 kHz (100 µs on,
   900 µs off).
2. **Samples** the coil's decaying voltage at **16 logarithmically-spaced
   time gates** (10, 12.5, 15.6, 19.5, 24.4, 30.5, 38.1, 47.7, 59.6, 74.5,
   93.1, 116.4, 145.5, 181.9, 227.4, 284.2 µs after pulse-off) using a
   12-bit ADC at 1 Msps with DMA. Each gate is oversampled 16× and averaged
   for noise reduction.
3. **Cancels ground mineralization** with an adaptive ground-balance filter
   that continuously tracks the fast-decaying ground signal (τ_ground ≈
   1–5 µs) and subtracts it from each gate, leaving only the target's
   secondary-field decay.
4. **Classifies** the 16-feature decay curve with an on-device **k-NN
   classifier** (k=5, Euclidean distance, 32 reference templates across 8
   metal classes) — identifying iron, foil, nickel, pull-tab, zinc, copper,
   silver, or gold with a confidence score.
5. **Estimates depth** from the signal amplitude, target class (different
   metals have different detectability curves), and coil tilt (ICM-42688-P
   IMU compensates for non-level sweeping).
6. **Provides audio feedback** with pitch-coded target ID (low pitch = iron,
   high pitch = silver/gold) and volume proportional to signal strength,
   via a headphone jack — no speaker needed for quiet detecting.
7. **Geo-tags** each detection with a NEO-M9N GPS fix, **logs** a survey CSV
   (`lat,lon,target_class,depth_cm,confidence,signal,time`) to microSD, and
   **streams** live target ID + depth to a phone over BLE (or Wi-Fi web
   dashboard with a leaflet.js treasure/contamination map).

All DSP and classification run on a **STM32G474RET6** (170 MHz Cortex-M4F
with HRTIM for precise pulse timing and CORDIC for math), with an
**ESP32-C3** handling BLE/Wi-Fi/GPS relay.

| | |
|---|---|
| **SoC (DSP core)** | STM32G474RET6 (Cortex-M4F @ 170 MHz, CORDIC, HRTIM) |
| **SoC (radio/GPS)** | ESP32-C3-WROOM-02 (RISC-V, BLE 5.0 + Wi-Fi) |
| **Method** | Pulse induction (PI), mono coil, 100 µs pulse @ 1 kHz |
| **TX current** | ~10 A peak (12 V through 0.5 mH coil) |
| **Time gates** | 16 gates, logarithmically spaced 10–284 µs after TX off |
| **ADC** | STM32 internal ADC, 12-bit, 1 Msps, 16× oversampling |
| **RX gain** | AD8226 inst amp, gain 100×, 100 kHz BW |
| **Target classes** | 8 (iron, foil, nickel, pull-tab, zinc, copper, silver, gold) |
| **Classifier** | k-NN (k=5), 32 reference templates, Euclidean distance |
| **Max depth** | ~30 cm (coin-sized), ~80 cm (large iron) |
| **Ground balance** | Adaptive, auto-tracking magnetic susceptibility |
| **GPS** | u-blox NEO-M9N, 1 Hz, ≤1.5 m CEP |
| **IMU** | ICM-42688-P (coil tilt compensation for depth) |
| **Display** | SSD1306 OLED 0.96″ 128×64 (target ID + depth + signal bar) |
| **Audio** | PWM DAC → headphone jack, pitch-coded target ID |
| **Logging** | microSD (FAT32, survey CSV) |
| **Radio** | BLE 5.0 (target stream) + Wi-Fi (web dashboard) |
| **Power** | 18650 Li-ion + TP4056 USB-C charging, ~10 h runtime |
| **Size** | 25 cm coil + 120×40×25 mm control box, 220 g |
| **BOM cost** | **~$63** |

---

## 2. Block Diagram

```
         ┌──────────────────────── STM32G474RET6 ────────────────────────┐
         │  HRTIM CHA ──► MOSFET driver ──► IRFH7440 ──► Search coil    │
         │  HRTIM CMP ──► 16 ADC triggers (log-spaced 10–284 µs)        │
         │  ADC1 + DMA ◄── AD8226 inst amp ◄── AC couple ◄── Coil       │
         │        ▲                                                     │
         │  Cortex-M4F: gate extract ► ground balance ► decay features  │
         │  k-NN classifier (8 classes, 32 templates)                   │
         │  CORDIC: depth, tilt comp, audio pitch                       │
         │  I2C1: ICM-42688-P (IMU), SSD1306 (OLED)                     │
         │  SPI2: microSD (FAT32)                                       │
         │  TIM3_CH1: PWM audio → headphone jack                        │
         │  USART2 ──► ESP32-C3 (UART @ 460800, target results)         │
         │  GPIO: BUTTON, MODE_LED, CHG_STAT                            │
         └────────────────────────────┬──────────────────────────────────┘
                                      │ UART 460800
         ┌────────────────────────────▼───────────────┐
         │             ESP32-C3-WROOM-02               │
         │  UART0 ◄── STM32 (target results)           │
         │  UART1 ◄── NEO-M9N GPS (NMEA @ 38400)       │
         │  BLE 5.0 ──► phone target ID + depth stream │
         │  Wi-Fi  ──► web dashboard (survey map)      │
         └─────────────────────────────────────────────┘

         ┌── Power ──────────────────────────────────┐
         │  18650 (3.7V) → TP4056 (USB-C charging)    │
         │  → MC34063 boost → 12V (TX coil driver)    │
         │  → AP2112 LDO → 3V3 (digital + analog)     │
         └────────────────────────────────────────────┘
```

---

## 3. How it works

### 3.1 Pulse induction principle

A **pulse induction** metal detector works by transmitting a brief, high-current
pulse through a search coil, creating a magnetic field that penetrates into the
ground. When this field collapses (TX off), it induces **eddy currents** in any
nearby conductive metal target. These eddy currents generate a **secondary
magnetic field** that persists after the primary field has decayed, inducing a
voltage in the same coil (mono configuration). The **decay time constant** of
this secondary field depends on the target's conductivity, permeability, size,
and shape — providing a fingerprint for target identification.

### 3.2 TX pulse generation

The STM32G474's **HRTIM** (184 ps resolution) drives an **IRFH7440** N-channel
MOSFET that connects the search coil to a 12 V rail (boosted from the 3.7 V
battery by an MC34063). The coil is an air-core inductor of ~0.5 mH with ~2 Ω
DC resistance. The current ramps up linearly during the 100 µs on-time:

```
I_peak = V × t / L = 12 × 100µ / 0.5m ≈ 2.4 A
```

(With the 2 Ω resistance, the steady-state would be 6 A, but the 100 µs
on-time means the current only reaches ~2.4 A. The MC34063 boost regulator
replenishes the 12 V rail during the 900 µs off-time at ~250 mA average.)

A **TVS diode** (SMBJ18A) clamps the flyback voltage when the MOSFET turns off,
and a **damping resistor** (470 Ω) across the coil critically damps the
ring-down so the coil voltage settles within ~10 µs of TX off.

### 3.3 RX signal chain

After TX off, the coil voltage is a decaying signal composed of:
1. **Coil ring-down** (first ~10 µs) — from the LC resonance of coil
   inductance and parasitic capacitance, damped by the damping resistor.
2. **Ground signal** (fast decay, τ ≈ 1–5 µs) — from magnetic susceptibility
   of soil minerals (magnetite, maghemite). This is the dominant signal in
   mineralized ground.
3. **Target signal** (slower decay, τ ≈ 10–100 µs) — from eddy currents in
   the metal target. This is what we want.

The coil voltage is **AC-coupled** (1 µF + 100 kΩ, τ_AC = 100 ms — much
slower than the signal) to remove DC offset, amplified by an **AD8226**
instrumentation amplifier (gain 100×, 100 kHz bandwidth), filtered by a
4th-order low-pass (100 kHz, Sallen-Key), and digitized by the STM32's
internal **ADC** (12-bit, 1 Msps, DMA continuous).

### 3.4 16-gate sampling

The HRTIM generates 16 ADC trigger pulses at logarithmically-spaced delays
after TX off:

| Gate | Delay (µs) | Gate | Delay (µs) |
|------|-----------|------|-----------|
| 0    | 10.0      | 8    | 59.6      |
| 1    | 12.5      | 9    | 74.5      |
| 2    | 15.6      | 10   | 93.1      |
| 3    | 19.5      | 11   | 116.4     |
| 4    | 24.4      | 12   | 145.5     |
| 5    | 30.5      | 13   | 181.9     |
| 6    | 38.1      | 14   | 227.4     |
| 7    | 47.7      | 15   | 284.2     |

At each gate, 16 consecutive ADC samples (16 µs of data at 1 Msps) are
averaged for noise reduction, yielding one 16-bit-oversampled value per gate.
The 16 values form the **decay curve fingerprint** — a feature vector for
classification.

### 3.5 Adaptive ground balance

Ground mineralization (magnetite, maghemite) produces a very fast-decaying
signal that can overwhelm target signals, especially in mineralized soil. The
**ground balance** algorithm:

1. During a "ground calibration" sweep (no targets present), estimates the
   ground decay curve `G[i]` from the first 4 gates (where ground dominates
   and target signals are minimal).
2. Models ground as `G(t) = A_g × exp(-t/τ_g)` where τ_g ≈ 2–5 µs.
3. Subtracts the scaled ground model from all 16 gates each pulse.
4. Continuously **auto-tracks** the ground amplitude `A_g` using an LMS
   adaptive filter (step size µ = 0.01) to handle changing soil conditions.

### 3.6 Target classification (k-NN)

The ground-balanced 16-gate decay curve is **normalized** (divided by the
max gate value, making the curve shape-independent of target size/depth) and
classified by a **k-NN classifier** (k=5, Euclidean distance) against a
flash library of **32 reference templates** spanning 8 metal classes:

| Class | τ_typical (µs) | Examples |
|-------|---------------|----------|
| Iron  | 4 (double-decay) | nails, bolts, scrap |
| Foil  | 10             | aluminum foil bits |
| Nickel| 17             | nickel coins |
| Pull-tab | 25          | aluminum can tabs |
| Zinc  | 35             | zinc pennies |
| Gold  | 45             | gold rings, nuggets |
| Copper| 58             | copper coins, pipes |
| Silver| 75             | silver coins, rings |

Each class has 4 reference templates (small/shallow, medium/shallow,
medium/deep, large/deep) to account for size-depth ambiguity. The k-NN
returns the class label and a confidence score (fraction of the 5 nearest
neighbors that share the majority class).

### 3.7 Depth estimation

Depth is estimated from the target signal amplitude (sum of all 16 gates),
the classified target class (different metals have different
detectability-vs-depth curves), and the coil tilt angle (from the IMU):

```
depth_cm = K[class] × (amplitude / amp_ref)^0.5 / cos(tilt)
```

Where `K[class]` is a per-class depth coefficient calibrated on reference
targets at known depths, and `cos(tilt)` compensates for non-level coil
sweeping (a tilted coil sees less flux from the target).

### 3.8 Audio feedback

A **PWM audio** output (TIM3 CH1, 8-bit duty cycle at 10 kHz carrier) drives
a headphone jack through a 2nd-order low-pass filter (3.4 kHz). The pitch is
mapped to the target class:

| Class | Pitch (Hz) | Character |
|-------|-----------|-----------|
| Iron  | 150       | Low growl |
| Foil  | 220       | Low buzz  |
| Nickel| 330       | Medium    |
| Pull-tab | 440    | Medium    |
| Zinc  | 550       | Medium-high |
| Gold  | 880       | Bright    |
| Copper| 990       | High      |
| Silver| 1100      | Crisp bell|

Volume is proportional to signal strength (log-scaled). In **discrimination
mode**, iron/foil targets can be silenced (audio blanking).

---

## 4. Pin Assignments

### STM32G474RET6 (LQFP64)

| Pin   | Function         | Connected to                  |
|-------|------------------|-------------------------------|
| PA0   | DAC1_OUT1        | Audio out (PWM alt)           |
| PA1   | ADC1_IN1         | Battery voltage monitor (÷2)  |
| PA2   | USART2_TX        | ESP32-C3 UART RX              |
| PA3   | USART2_RX        | ESP32-C3 UART TX              |
| PA4   | HRTIM_CHA1       | MOSFET gate driver (TX pulse) |
| PA5   | HRTIM_CHA2       | MOSFET gate driver (discharge)|
| PA6   | ADC1_IN3         | Coil voltage (from AD8226)    |
| PA7   | TIM3_CH1         | PWM audio output               |
| PA8   | GPIO (GAIN_SW)   | AD8226 gain switch (optional) |
| PA9   | GPIO (BUTTON)    | Mode / ground balance button  |
| PA10  | GPIO (LED)       | Status LED                     |
| PA11  | GPIO (CHG)       | TP4056 charge status           |
| PA12  | GPIO (WATER)     | Coil water-detect (optional)  |
| PA13  | GPIO (DISC)      | Discrimination toggle button  |
| PA15  | GPIO (SENS)      | Sensitivity rotary enc. A     |
| PB0   | I2C1_SCL         | IMU / OLED SCL                |
| PB1   | I2C1_SDA         | IMU / OLED SDA                |
| PB2   | SPI2_SCK         | microSD SCK                   |
| PB3   | SPI2_MISO        | microSD MISO                  |
| PB4   | SPI2_MOSI        | microSD MOSI                  |
| PB5   | SPI2_NSS         | microSD CS                    |
| PB6   | GPIO (SENS_B)    | Sensitivity rotary enc. B     |
| PB7   | GPIO (PHONE)     | Headphone detect              |
| PC13  | GPIO (BOOT)      | Boot button                   |
| PC14  | GPIO (SD-DET)    | microSD card detect           |
| PC15  | GPIO (BOOST_EN)  | MC34063 boost enable           |
| VBAT  | 3V3              | RTC battery (CR2032)          |
| VDD   | 3V3              | Core supply                   |
| VDDA  | 3V3 (ferrite)    | Analog supply (clean)         |

### ESP32-C3-WROOM-02

| Pin   | Function    | Connected to                |
|-------|-------------|-----------------------------|
| GPIO2 | UART0_RX    | STM32 USART2_TX (results)   |
| GPIO3 | UART0_TX    | STM32 USART2_RX (commands)  |
| GPIO4 | UART1_RX    | NEO-M9N GPS TX (NMEA)       |
| GPIO5 | UART1_TX    | NEO-M9N GPS RX (config)     |
| GPIO6 | GPIO (PPS)  | NEO-M9N PPS (time-tag)      |
| GPIO7 | GPIO (LED)  | Radio status LED            |
| GPIO8 | GPIO (WAKE) | STM32 wake (deep-sleep ctl) |
| GPIO9 | GPIO (BOOT) | Boot strap                  |
| GPIO10| I2C_SCL     | (expansion)                 |
| GPIO11| I2C_SDA     | (expansion)                 |

---

## 5. Power Architecture

```
  18650 (3.7V 3500mAh)
      │
      ├──► TP4056 (USB-C charging, 1A) ──► DW02 protection
      │
      ├──► AP2112-3.3 LDO ──► 3V3 (STM32 + ESP32-C3 + sensors)
      │       │
      │       ├──► ferrite bead ──► 3V3A (clean analog: AD8226, ADC)
      │       └──► 3V3D (digital: STM32, ESP32, GPS, SD, OLED)
      │
      └──► MC34063 boost ──► 12V (TX coil driver, ~250 mA avg)
              │
              └──► 220 µF bulk cap ──► IRFH7440 MOSFET ──► Search coil
```

- **Average current**: ~90 mA (STM32 DSP + ESP32 BLE + GPS + pulse), ~10 h
  on a 3500 mAh cell.
- **Pulse burst current**: ~2.4 A for 100 µs at 1 kHz (10% duty), averaged
  by the 220 µF bulk cap on the 12 V rail. The MC34063 replenishes at
  ~250 mA during the 900 µs off-time.
- **Power modes**: `ACTIVE` (full detection + GPS + BLE), `DRIFT` (detection
  only, no BLE/Wi-Fi, ~60 mA), `SLEEP` (everything off except ESP32-C3
  deep-sleep wake, ~2 mA).

---

## 6. Firmware

Located in [`firmware/`](firmware/). Build with **STM32CubeIDE** or
`arm-none-eabi-gcc` + CMake (see `firmware/CMakeLists.txt`).

### Source files

| File | Purpose |
|------|---------|
| `main.c` | Boot, task scheduler, state machine, sweep loop |
| `pi_driver.c` | HRTIM TX pulse generation, ADC DMA sampling, 16-gate extraction |
| `decay.c` | Decay curve processing, normalization, feature extraction |
| `ground.c` | Adaptive ground mineralization tracking + cancellation |
| `target_id.c` | k-NN classifier (8 classes, 32 templates) |
| `depth.c` | Depth estimation from amplitude + class + tilt |
| `audio.c` | PWM audio synthesis, pitch-coded target ID tones |
| `imuw.c` | ICM-42688-P tilt compensation for depth |
| `sd_log.c` | FatFs survey CSV logging |
| `oled.c` | SSD1306 display (target ID + depth + signal bar) |
| `uart_link.c` | Binary framing to/from ESP32-C3 |
| `model.c` | k-NN reference library data + helpers |

### ESP32-C3 firmware

A small ESP-IDF app (`firmware/esp32c3/`) handles:
- UART receive from STM32 → ring buffer
- BLE GATT server (target results stream)
- Wi-Fi AP + HTTP server (leaflet.js survey map)
- NEO-M9N NMEA parsing → GPS fix struct, sent to STM32

---

## 7. Scripts

Located in [`scripts/`](scripts/):

| Script | Purpose |
|--------|---------|
| `live_sweep.py` | BLE-connected live target ID display (matplotlib) |
| `survey_map.py` | Plot a logged survey CSV as a GPS-tagged target map |
| `sim_decay.py` | Simulate PI decay curves for different metals and verify k-NN |
| `flash_stm32.sh` | OpenOCD flash script (ST-Link) |

---

## 8. Mechanical & Search Coil

- **Control box**: 3D-printed PETG, 120×40×25 mm, IP54.
- **Search coil**: 25 cm diameter air-core, 100 turns of 0.5 mm enamelled
  copper wire on a 3D-printed spool, potted in epoxy, waterproof. ~0.5 mH,
  ~2 Ω. Cable: 1.2 m shielded twisted pair to control box.
- **Coil mount**: UHMW pole bracket for a 25 mm aluminum shaft (telescoping).
- **Headphone jack**: 3.5 mm TRS on the control box.
- **Charging**: USB-C port on the control box.
- **GPS antenna**: exposed on the top of the control box.

---

## 9. Comparison to commercial metal detectors

| Feature | Minelab Equinox 800 | XP Deus II | Fisher CZ-21 | **Lode Sweep** |
|---------|--------------------|-----------:|--------------|----------------|
| Method | VLF multi-freq | VLF multi-freq | VLF dual-freq | **PI (pulse)** |
| Target ID | 50-segment VDI | 99-segment | 2-tone | **8-class k-NN** |
| Ground balance | auto | auto | manual | **adaptive auto-track** |
| Decay curve analysis | proprietary | proprietary | n/a | **open 16-gate** |
| ML classifier | no | no | no | **yes (k-NN)** |
| Iron discrimination | yes | yes | yes | **yes (blanking)** |
| GPS survey mapping | no | no | no | **yes (NEO-M9N)** |
| Depth estimation | bar only | bar only | bar only | **cm estimate** |
| IMU tilt comp | no | no | no | **yes** |
| Open source | no | no | no | **MIT** |
| Price | ~$900 | ~$1,500 | ~$1,200 | **~$63** |

---

## 10. Applications

- **Treasure hunting / coin shooting**: identify coins and relics before
  digging, with audio pitch telling you the metal class.
- **Archaeological survey**: GPS-tagged metal contamination maps for
  non-invasive site assessment.
- **Utility location**: trace buried metal pipes, cables, and junction boxes.
- **Beach detecting**: PI handles wet salt sand better than VLF (no ground
  balance issues with salt water mineralization).
- **Environmental remediation**: map metal debris in soil for cleanup
  planning.
- **Education**: a fully open PI detector DSP pipeline — great for teaching
  electromagnetic induction, eddy currents, and ML classification.

---

## 11. License

MIT — build it, detect with it, improve it.