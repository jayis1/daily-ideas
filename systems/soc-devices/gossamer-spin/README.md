# Gossamer Spin — Pocket Electrospinning Nanofiber Generator with Jet-Current Process Monitoring

> A pocket-sized, battery-powered electrospinning device that generates
> **0–30 kV** from a single 18650 cell, drives a **precision syringe pump**
> (0.1–10 mL/h) and a **rotating drum collector** (100–3000 RPM), monitors
> the **Taylor-cone jet current** at 10 nA resolution via a transimpedance
> amplifier + 24-bit ADC as a real-time process-quality indicator, tracks
> temperature/humidity (BME280) for fiber-morphology correlation, runs
> closed-loop HV voltage regulation, offers 8 preset polymer recipes with
> per-recipe voltage/flow/drum/RH setpoints, triple-redundant HV safety
> (door interlock + tilt sensor + hardware comparator cutoff + IWDG),
> OLED dashboard, SD process logging, and BLE/Wi-Fi live streaming to a
> phone/PC — bringing **$3k–$20k lab electrospinning systems** (Inovenso
> NE100, Spraybase, Linari ETM) down to **~$68** and a **coffee-mug-size**
> form factor, with open jet-current feedback that commercial benchtop
> units don't offer.

---

## 1. What it is

**Gossamer Spin** is a handheld electrospinning nanofiber generator. You
load a polymer solution into a syringe, clip the device shut, select a
recipe, and it:

1. **Generates** a programmable **0–30 kV** high voltage via a boost
   converter + 10-stage Cockcroft-Walton multiplier, with closed-loop
   voltage regulation (±0.5 kV) via HRTIM PWM at 100 kHz.
2. **Drives a syringe pump** (NEMA8 microstepper + M4×0.35 leadscrew) at
   0.1–10 mL/h, feeding polymer solution through a blunt 21G needle that
   serves as the HV electrode and spinneret.
3. **Rotates a drum collector** (NEMA8 microstepper, 100–3000 RPM
   equivalent) at a programmable speed to align or randomize the
   deposited nanofibers (high RPM → aligned fibers, low RPM → random
   mat).
4. **Monitors the jet current** — the ~100–500 nA current flowing from
   the HV needle through the whipping Taylor-cone jet to the grounded
   collector — via a 100 MΩ transimpedance amplifier + ADS122U04 24-bit
   ADC at 100 SPS. The jet current is a direct process-quality indicator:
   - **Steady ~200 nA**: stable Taylor cone, uniform fiber deposition
   - **Drops to ~0**: jet interrupted (needle clogged, solution depleted,
     or voltage too low)
   - **Spiking/erratic**: unstable multi-jet or dripping (voltage too
     high or flow too fast)
   - **Gradual decline**: solvent evaporation at the needle tip clogging
   The firmware runs a 5-second rolling-window classifier that reports
   `STABLE`, `INTERRUPTED`, `UNSTABLE`, or `DRIPPING` in real time.
5. **Tracks temperature & humidity** via a BME280 sensor inside the
   spinning chamber, because fiber diameter and morphology are strongly
   humidity-dependent (high RH → thicker, beaded fibers; low RH → thin,
   uniform fibers). Recipes include target RH ranges with process
   warnings.
6. **Runs 8 preset polymer recipes** stored in flash, each defining
   voltage, flow rate, drum RPM, needle-collector distance, target
   temperature/humidity, and run duration:
   - PVA (polyvinyl alcohol) — 18 kV, 1.0 mL/h, 800 RPM
   - PAN (polyacrylonitrile) — 20 kV, 0.8 mL/h, 1200 RPM (carbon fiber
     precursor)
   - PLLA (poly-L-lactic acid) — 15 kV, 0.5 mL/h, 600 RPM (biomedical
     scaffolds)
   - PVDF (polyvinylidene fluoride) — 22 kV, 1.2 mL/h, 1500 RPM (piezo
     sensors)
   - Nylon-6 — 20 kV, 0.6 mL/h, 1000 RPM
   - Chitosan — 12 kV, 0.3 mL/h, 400 RPM (wound dressing)
   - PS (polystyrene) — 16 kV, 0.7 mL/h, 900 RPM
   - Custom — user-defined via BLE app
7. **Provides triple-redundant safety**: a magnetic reed door interlock
   cuts HV instantly if the chamber is opened; a tilt/bump sensor cuts HV
   if the device is knocked over; a hardware TLV3201 comparator cuts HV
   if the current exceeds 10 µA (human safety limit); and an IWDG
   watchdog reboots if firmware hangs. A 100 MΩ bleeder resistor
   discharges the HV to <60 V within 2 seconds of shutoff.
8. **Logs** every run to microSD (CSV: `time,voltage_kv,flow_mlh,drum_rpm,
   jet_current_na,temp_c,rh_pct,status`) at 10 Hz, and **streams** live
   process data to a phone/PC over BLE (or Wi-Fi web dashboard).

All HV regulation, motor control, current monitoring, and safety logic
run on a **STM32G474RET6** (170 MHz Cortex-M4F with HRTIM for precise
PWM and CORDIC for math), with an **ESP32-C3** handling BLE/Wi-Fi relay.

| | |
|---|---|
| **SoC (control core)** | STM32G474RET6 (Cortex-M4F @ 170 MHz, HRTIM, CORDIC) |
| **SoC (radio)** | ESP32-C3-WROOM-02 (RISC-V, BLE 5.0 + Wi-Fi) |
| **HV output** | 0–30 kV DC, programmable, ±0.5 kV regulation |
| **HV method** | Boost (3.7→15 V) + 10-stage Cockcroft-Walton multiplier |
| **HV power** | ~1 W max (30 kV × 33 µA), battery-powered |
| **Syringe pump** | NEMA8 stepper + M4×0.35 leadscrew, 0.1–10 mL/h |
| **Collector** | NEMA8 stepper + belt drive drum, 100–3000 RPM |
| **Jet current** | 0–1000 nA, 10 nA resolution (TIA + ADS122U04 24-bit) |
| **HV voltage sense** | 1000:1 resistive divider → ADS122U04 |
| **Environment** | BME280 (temp ±1°C, humidity ±3% RH) |
| **Safety** | Reed interlock + tilt sensor + TLV3201 comparator + IWDG |
| **Recipes** | 8 preset polymer recipes + custom |
| **Display** | SSD1306 OLED 0.96″ 128×64 (HV, flow, RPM, current, status) |
| **Logging** | microSD (FAT32, process CSV at 10 Hz) |
| **Radio** | BLE 5.0 (live stream) + Wi-Fi (web dashboard) |
| **Power** | 18650 Li-ion + TP4056 USB-C charging, ~4 h runtime |
| **Size** | 110×60×50 mm chamber + 80×40×25 mm control box, 280 g |
| **BOM cost** | **~$68** |

---

## 2. Block Diagram

```
         ┌──────────────────────── STM32G474RET6 ────────────────────────┐
         │  HRTIM CHA ──► Boost PWM ──► Boost inductor ──► CW multiplier │
         │  ADC1 ◄── ADS122U04 (SPI) ◄── TIA ◄── Collector electrode    │
         │  ADC2 ◄── HV divider (1000:1) ◄── CW multiplier output       │
         │  TIM1_CH1─2 ──► A4988 ──► NEMA8 (syringe pump microstepper)  │
         │  TIM8_CH1─2 ──► A4988 ──► NEMA8 (collector drum microstepper)│
         │  I2C1: BME280 (temp/humidity), SSD1306 (OLED)                │
         │  SPI2: microSD (FAT32 process log)                           │
         │  SPI3: ADS122U04 (jet current + HV voltage, 24-bit)          │
         │  GPIO: DOOR_INT, TILT, HV_CUTOFF, HV_EN, BUTTON, LED         │
         │  USART2 ──► ESP32-C3 (UART @ 460800, process data)           │
         │  CORDIC: HV PID, current classifier, flow calc               │
         │  IWDG: safety watchdog                                        │
         └────────────────────────────┬──────────────────────────────────┘
                                      │ UART 460800
         ┌────────────────────────────▼───────────────┐
         │             ESP32-C3-WROOM-02               │
         │  UART0 ◄── STM32 (process data)             │
         │  BLE 5.0 ──► phone live process stream      │
         │  Wi-Fi  ──► web dashboard (fiber monitor)   │
         └─────────────────────────────────────────────┘

         ┌── Power ──────────────────────────────────┐
         │  18650 (3.7V) → TP4056 (USB-C charging)    │
         │  → AP2112 LDO → 3V3 (digital + analog)     │
         │  → Boost (HRTIM PWM) → 15V → CW ×10 → 30kV │
         │  100MΩ bleeder ──► fast HV discharge       │
         └────────────────────────────────────────────┘
```

---

## 3. How it works

### 3.1 Electrospinning principle

**Electrospinning** uses electrostatic forces to draw ultra-fine fibers
(50–1000 nm diameter) from a polymer solution. A high voltage (typically
10–25 kV) is applied to a polymer-filled syringe needle, while a
grounded collector electrode is placed 10–20 cm away. The electric field
overcomes the surface tension at the needle tip, forming a **Taylor
cone** — a conical droplet from which a charged jet emerges. The jet
undergoes a **whipping instability** (bending instability) that
stretches it thousands of times while the solvent evaporates, leaving a
solid nanofiber deposited on the collector.

Key parameters controlling fiber morphology:
- **Voltage**: higher voltage → thinner fibers, but too high → unstable
  multi-jet or dripping. Typically 10–25 kV.
- **Flow rate**: lower flow → thinner fibers, but too low → intermittent
  jet. Typically 0.2–2.0 mL/h.
- **Needle-collector distance**: 10–20 cm. Too close → wet, beaded
  fibers. Too far → jet breaks.
- **Drum speed**: high RPM → aligned fibers (for tendon/scaffold
  applications), low RPM → random mat (for filtration).
- **Humidity**: high RH → thicker, beaded fibers (slow solvent
  evaporation); low RH → thin, uniform fibers but risk of needle
  clogging. Ideal: 20–50% RH.
- **Temperature**: affects solvent evaporation rate and viscosity.
  Typically 20–30°C.

### 3.2 HV supply: boost + Cockcroft-Walton

The HV supply is the heart of the device. It generates 0–30 kV from the
3.7 V battery in two stages:

**Stage 1 — Boost converter (3.7 V → 15 V)**:
An HRTIM-driven PWM (100 kHz) controls a boost converter using an
inductor (220 µH), a Schottky diode (SS34), and a 22 µF output cap. The
duty cycle is set by a PID loop that regulates the output voltage based
on the Cockcroft-Walton multiplier feedback (see 3.3).

**Stage 2 — Cockcroft-Walton multiplier (15 V → 30 kV)**:
A 10-stage Cockcroft-Walton voltage multiplier uses 20× 1 nF 3 kV ceramic
capacitors and 20× 1N4007 rectifier diodes (1 kV PIV each). Each stage
doubles the input voltage, so 10 stages give a theoretical 20×
multiplication: 15 V × 20 = 300 V... 

Actually, a more practical design: the boost converter generates
**~200 V DC**, and a 10-stage CW multiplier gives 200 × 20 = 4000 V
(4 kV). To reach 30 kV, we need a higher input or more stages. The
actual design uses:

- **Boost converter**: 3.7 V → **300 V** (using a flyback transformer
  topology with a custom-wound transformer, 1:80 turns ratio, driven at
  50 kHz by the HRTIM)
- **Cockcroft-Walton**: 10 stages, each stage ≈ 300 V → total ≈ **30 kV**

The flyback transformer is wound on an EE25 ferrite core: primary 15
turns, secondary 1200 turns of 0.05 mm wire. The HRTIM drives a
IRFH7440 MOSFET on the primary at 50 kHz with duty cycle controlled by
the PID loop. The secondary voltage is rectified and fed to the CW
multiplier.

**Output current**: limited to ~33 µA at 30 kV (1 W), which is below
the 100 µA human safety threshold. A series 910 MΩ resistor limits
short-circuit current to 33 µA at 30 kV.

### 3.3 HV voltage feedback

The HV output voltage is measured via a **1000:1 resistive divider**
using a 900 MΩ high-value resistor (Vishay HVC series) and a 900 kΩ
bottom resistor. The divided voltage (0–30 V from 0–30 kV) is fed to
the ADS122U04 24-bit ADC on a separate channel.

The STM32 runs a **PID controller** at 1 kHz:
- **P**: proportional to (V_set − V_measured)
- **I**: integral with anti-windup clamp
- **D**: derivative with low-pass filter
- Output: HRTIM duty cycle (0–95%)

This maintains the HV within ±0.5 kV even as the jet current varies
(which loads the CW multiplier and would otherwise cause voltage sag).

### 3.4 Jet current monitoring

The most novel feature is real-time **jet current monitoring**. The
electrospinning jet carries a small DC current (typically 100–500 nA)
from the HV needle through the charged jet to the grounded collector.
This current is a direct indicator of process stability:

```
Needle (HV) ──► Taylor cone ──► Whipping jet ──► Collector (ground)
                                                          │
                                                    ┌─────┴─────┐
                                                    │ 100 MΩ TIA │
                                                    │ (ADA4530-1)│
                                                    │   → ADC    │
                                                    └────────────┘
```

The collector electrode connects to the **virtual ground** input of an
**ADA4530-1** electrometer-grade op-amp configured as a transimpedance
amplifier with 100 MΩ feedback resistor. This gives:

```
V_out = I_jet × R_fb = 100 nA × 100 MΩ = 10 V
```

With a 1/10 voltage divider at the TIA output (to match the ADS122U04's
0–3.3 V input range), the ADC sees 0–1 V for 0–1000 nA, giving
**1 nA/LSB** at the ADS122U04's 24-bit resolution with PGA gain of 1
(roughly; actual effective resolution is ~10 nA after noise filtering).

The firmware samples at 100 SPS, applies a 10-point moving average, and
runs a 5-second rolling-window **process-state classifier**:

| State | Jet current signature | Action |
|-------|----------------------|--------|
| `STABLE` | Steady 100–500 nA, σ < 50 nA | Normal operation |
| `INTERRUPTED` | Drops to <20 nA for >2 s | Warn: check needle/solution |
| `UNSTABLE` | σ > 100 nA or rapid oscillation | Warn: reduce voltage or flow |
| `DRIPPING` | Periodic spikes >800 nA every 1–5 s | Warn: increase voltage or reduce flow |

### 3.5 Syringe pump

A **NEMA8 stepper motor** (200 steps/rev) with an **A4988 driver**
(microstepping at 1/16) drives an **M4×0.35 leadscrew** through a
flexible coupler. The syringe plunger is pushed by a carriage on a
linear rail.

```
Flow rate = (π × r² × pitch × step_rate) / (steps_per_rev × microsteps)
```

For a 5 mL syringe (inner diameter ~12 mm, r = 6 mm):
- At 1 mL/h: step rate ≈ 1.5 steps/s (16× microstepping)
- At 10 mL/h: step rate ≈ 15 steps/s
- At 0.1 mL/h: step rate ≈ 0.15 steps/s (1 step every ~7 seconds)

The TIM1 timer generates the step pulses with programmable frequency.
A limit switch at the rear of the carriage detects when the syringe is
empty (carriage fully forward).

### 3.6 Rotating drum collector

A **NEMA8 stepper motor** with a **belt drive** (GT2, 1:1 ratio) rotates
an aluminum drum (20 mm diameter, 60 mm length) at 100–3000 RPM. The
TIM8 timer generates step pulses at the appropriate rate. The drum is
electrically connected to the TIA's virtual ground input via a slip ring
(mercury-free, gold-on-gold contact).

```
Drum RPM = step_rate × 60 / (steps_per_rev × microsteps × belt_ratio)
```

At 16× microstepping, 200 steps/rev, 1:1 belt:
- 100 RPM → 533 steps/s
- 3000 RPM → 16000 steps/s

### 3.7 Safety architecture

Electrospinning involves **potentially lethal high voltage** (30 kV at
up to 33 µA = 1 W, which can cause cardiac arrest). The safety system
is triple-redundant:

1. **Door interlock** (primary): A magnetic reed switch on the spinning
   chamber door. If the door opens, the HV enable signal is **hardware
   pulled low** (diode-OR with the GPIO), instantly cutting the boost
   converter. The firmware also detects the door-open state and enters
   `SAFE` mode.

2. **Tilt sensor** (secondary): A ball-and-roller tilt sensor detects if
   the device is tipped more than 30° from vertical. If triggered, HV is
   cut via a separate hardware path (transistor pull-down on HV_EN).

3. **Hardware current limit** (tertiary): A **TLV3201** comparator
   monitors the TIA output. If the jet current exceeds 10 µA (indicating
   a short or human contact), the comparator output **hardware-disables**
   the boost converter via a dedicated cutoff line, independent of
   firmware.

4. **IWDG watchdog**: If the firmware hangs, the IWDG resets the MCU,
   which defaults all GPIOs to input (HV_EN is pulled low by external
   resistor → HV off).

5. **Bleeder resistor**: A 100 MΩ resistor across the CW output
   discharges the HV to <60 V within 2 seconds of shutoff
   (τ = R×C = 100MΩ × 10nF = 1 s, 5τ = 5 s for <1% of 30 kV = 300 V,
   but with the 910 MΩ series resistor the effective discharge is
   faster through the TIA path).

The three hardware cutoffs (door, tilt, comparator) are diode-ORed into
a single `HV_CUTOFF` line that physically disables the boost converter
MOSFET gate driver, regardless of firmware state.

---

## 4. Pin Assignments

### STM32G474RET6 (LQFP64)

| Pin   | Function         | Connected to                  |
|-------|------------------|-------------------------------|
| PA0   | DAC1_OUT1        | (unused, reserved)            |
| PA1   | ADC1_IN1         | Battery voltage monitor (÷2)  |
| PA2   | USART2_TX        | ESP32-C3 UART RX              |
| PA3   | USART2_RX        | ESP32-C3 UART TX              |
| PA4   | HRTIM_CHA1       | Boost MOSFET gate driver (PWM)|
| PA5   | HRTIM_CHA2       | Boost MOSFET (discharge path) |
| PA6   | TIM1_CH1         | Syringe pump step (A4988 STEP)|
| PA7   | TIM1_CH2         | Syringe pump dir (A4988 DIR)  |
| PA8   | TIM8_CH1         | Collector drum step (A4988)   |
| PA9   | TIM8_CH2         | Collector drum dir (A4988)    |
| PA10  | GPIO (HV_EN)     | Boost converter enable        |
| PA11  | GPIO (HV_CUTOFF) | Hardware HV cutoff (input)    |
| PA12  | GPIO (DOOR_INT)  | Reed door interlock           |
| PA13  | GPIO (TILT)      | Tilt/bump sensor              |
| PA14  | GPIO (SYR_LIMIT) | Syringe empty limit switch    |
| PA15  | GPIO (BUTTON)    | Start/stop button             |
| PB0   | I2C1_SCL         | BME280 / OLED SCL             |
| PB1   | I2C1_SDA         | BME280 / OLED SDA             |
| PB2   | SPI2_SCK         | microSD SCK                   |
| PB3   | SPI2_MISO        | microSD MISO                  |
| PB4   | SPI2_MOSI        | microSD MOSI                  |
| PB5   | SPI2_NSS         | microSD CS                    |
| PB6   | SPI3_SCK         | ADS122U04 SCK                 |
| PB7   | SPI3_MISO        | ADS122U04 DOUT/DRDY           |
| PB8   | SPI3_MOSI        | ADS122U04 DIN                 |
| PB9   | SPI3_NSS         | ADS122U04 CS                  |
| PB10  | GPIO (CHG_STAT)  | TP4056 charge status          |
| PB11  | GPIO (STATUS_LED)| Status LED                    |
| PB12  | GPIO (SAFE_LED)  | HV-safe (green) LED           |
| PC13  | GPIO (BOOT)      | Boot button                   |
| PC14  | GPIO (SD_DET)    | microSD card detect           |
| PC15  | GPIO (BOOST_EN)  | Boost enable (secondary)      |
| VBAT  | 3V3              | RTC battery (CR2032)          |
| VDD   | 3V3              | Core supply                   |
| VDDA  | 3V3 (ferrite)    | Analog supply (clean)         |

### ESP32-C3-WROOM-02

| Pin   | Function    | Connected to                |
|-------|-------------|-----------------------------|
| GPIO2 | UART0_RX    | STM32 USART2_TX (data)      |
| GPIO3 | UART0_TX    | STM32 USART2_RX (commands)  |
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
      │       ├──► ferrite bead ──► 3V3A (clean analog: TIA, ADC)
      │       └──► 3V3D (digital: STM32, ESP32, SD, OLED)
      │
      └──► Flyback boost (HRTIM PWM, 50 kHz)
              │  IRFH7440 MOSFET → EE25 transformer (1:80)
              │  → 300V rectified → 10-stage CW multiplier → 30 kV
              │
              ├──► 910 MΩ series resistor (current limit)
              ├──► 100 MΩ bleeder resistor (fast discharge)
              └──► Spinneret needle (HV electrode)
```

- **Average current**: ~350 mA (STM32 control + ESP32 BLE + steppers +
  HV 1W, ~270 mA from battery for HV alone at 30 kV), ~4 h on a 3500 mAh
  cell.
- **HV power**: 30 kV × 33 µA = ~1 W. The flyback converter efficiency is
  ~60%, so battery draw for HV is ~1.7 W (~460 mA). With steppers
  (~100 mA) and electronics (~80 mA), total is ~640 mA, giving ~5.5 h
  runtime. In practice, most runs are 15–60 minutes.
- **Power modes**: `IDLE` (no HV, steppers off, ~30 mA), `READY` (HV
  off, steppers homed, BLE on, ~60 mA), `RUNNING` (full power, ~640 mA),
  `SAFE` (everything off after safety trip, ~2 mA).

---

## 6. Firmware

Located in [`firmware/`](firmware/). Build with **STM32CubeIDE** or
`arm-none-eabi-gcc` + CMake (see `firmware/CMakeLists.txt`).

### Source files

| File | Purpose |
|------|---------|
| `main.c` | Boot, state machine, run loop, recipe management |
| `hv_supply.c` | Flyback boost PWM, Cockcroft-Walton, PID voltage regulation |
| `syringe_pump.c` | NEMA8 stepper + A4988 driver, flow rate computation |
| `collector.c` | NEMA8 drum stepper, RPM control |
| `jet_current.c` | ADS122U04 24-bit ADC, TIA current computation, state classifier |
| `safety.c` | Door interlock, tilt sensor, comparator cutoff, IWDG watchdog |
| `env_monitor.c` | BME280 temperature/humidity reading |
| `oled.c` | SSD1306 display (HV, flow, RPM, current, status) |
| `sd_log.c` | FatFs process CSV logging at 10 Hz |
| `uart_link.c` | Binary framing to/from ESP32-C3 |
| `recipe.c` | 8 preset polymer recipes + custom recipe storage |

### ESP32-C3 firmware

A small ESP-IDF app (`firmware/esp32c3/`) handles:
- UART receive from STM32 → ring buffer
- BLE GATT server (live process data stream)
- Wi-Fi AP + HTTP server (web dashboard with live charts)
- Recipe upload and remote start/stop commands

---

## 7. Scripts

Located in [`scripts/`](scripts/):

| Script | Purpose |
|--------|---------|
| `live_monitor.py` | BLE-connected live process monitor (matplotlib) |
| `sim_fiber.py` | Simulate electrospinning fiber diameter vs parameters |
| `flash_stm32.sh` | OpenOCD flash script (ST-Link) |

---

## 8. Mechanical & Chamber

- **Spinning chamber**: 3D-printed PETG, 110×60×50 mm, with a hinged
  lid (magnetic reed interlock). The chamber is sealed with a gasket to
  maintain humidity control. A small vent with a removable solvent
  filter cap allows solvent vapor to escape safely.
- **Syringe pump assembly**: NEMA8 stepper + M4×0.35 leadscrew + linear
  rail, mounted on the side of the chamber. Accepts standard 1–10 mL
  Luer-lock syringes. 21G blunt needle (0.8 mm OD, 0.5 mm ID, 25 mm
  length) as the spinneret.
- **Drum collector**: Aluminum drum, 20 mm diameter × 60 mm length, on
  a belt-driven NEMA8 stepper shaft. Gold slip ring for electrical
  contact to the TIA. Drum surface accepts aluminum foil wraps for
  easy fiber removal.
- **Needle-collector distance**: adjustable from 8–18 cm via a sliding
  needle mount (manual set, calibrated with markings).
- **Control box**: 80×40×25 mm, houses the PCB, battery, USB-C port,
  OLED, and start/stop button. Connects to the chamber via a 6-pin
  cable (HV, ground, door interlock, tilt, motor power).
- **HV cable**: silicone-insulated 30 kV wire from the control box to
  the needle mount.

---

## 9. Comparison to commercial electrospinning systems

| Feature | Inovenso NE100 | Spraybase | Linari ETM | **Gossamer Spin** |
|---------|---------------|-----------|------------|-------------------|
| Max voltage | 35 kV | 30 kV | 40 kV | **30 kV** |
| Syringe pump | yes | yes | yes | **yes (microstepper)** |
| Drum collector | optional | optional | yes | **yes (standard)** |
| Jet current monitor | no | no | no | **yes (10 nA res.)** |
| Process classifier | no | no | no | **yes (4 states)** |
| Humidity control | optional | optional | no | **monitor + warn** |
| Recipe presets | no | no | no | **8 polymer presets** |
| Battery powered | no | no | no | **yes (18650)** |
| Portable | no | no | no | **yes (pocket size)** |
| Safety interlock | yes | yes | yes | **triple redundant** |
| BLE/Wi-Fi streaming | no | no | no | **yes** |
| Open source | no | no | no | **MIT** |
| Price | ~$3,000 | ~$5,000 | ~$20,000 | **~$68** |

---

## 10. Applications

- **Nanofiber filtration**: produce PAN or PVDF nanofiber membranes for
  HEPA-grade air and water filtration at a fraction of commercial cost.
- **Biomedical scaffolds**: electrospin PLLA or chitosan nanofiber mats
  for tissue engineering, wound dressings, and drug delivery — the high
  surface-area-to-volume ratio mimics the extracellular matrix.
- **Piezoelectric sensors**: PVDF nanofibers are piezoelectric and can
  be used for flexible pressure sensors and energy harvesters.
- **Carbon fiber precursors**: PAN nanofibers can be carbonized to
  produce carbon nanofibers for electrodes and composites.
- **Education**: a fully open electrospinning system — great for
  teaching polymer physics, electrostatics, and nanofabrication.
- **Research screening**: quickly test different polymer/solvent
  combinations and process parameters without booking time on a
  $20k lab system.
- **Smart textiles**: coat fabrics with functional nanofibers
  (antimicrobial, hydrophobic, conductive).

---

## 11. Safety Warning

**This device generates potentially lethal high voltage (up to 30 kV).**
While the current is limited to ~33 µA (below the 100 µA human safety
threshold), the energy stored in the CW multiplier capacitors can still
deliver a painful and potentially dangerous shock. Always:

1. **Never open the chamber while HV is active.** The door interlock is
   a safety backup, not a primary control.
2. **Wait 5 seconds after shutdown** before opening the chamber — the
   bleeder resistor discharges the HV.
3. **Use in a ventilated area** — electrospinning solvents (DMF, DCM,
  THF, ethanol) are toxic/flammable. The vent cap must be open.
4. **Do not modify the safety circuitry.** The door interlock, tilt
   sensor, and current comparator are there to save your life.
5. **Keep away from children and pets.**
6. **Use only non-flammable solvents** or ensure adequate ventilation.
   Electrospinning with flammable solvents in a sealed chamber creates
   an explosion hazard.

---

## 12. License

MIT — build it, spin with it, improve it.