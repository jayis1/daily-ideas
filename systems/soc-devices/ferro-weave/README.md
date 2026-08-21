# Ferro Weave — Pocket Magnetic Hysteresis Loop Tracer

> A portable benchtop **B-H curve analyzer** that magnetizes a toroidal or
> strip-wound specimen with a driven winding, integrates the induced
> secondary voltage to recover flux **B**, samples the magnetizing current
> for field **H**, and computes the full hysteresis loop, core loss,
> permeability, saturation, remanence and coercivity — then plots the loop
> on an OLED, logs the sweep to SD, and streams the waveform over BLE/Wi-Fi
> to a PC plotting app. Built around the **STM32G474RET6** (CORDAC + 4 Msps
> ADC + HRTIM) for the precision DAQ core and an **ESP32-C3** for BLE/Wi-Fi
> uplink.

```
                ┌──────────────────────────────────────────────┐
                │            STIMULUS / SENSE                    │
   primary  ──▶ │  HRTIM PWM  ──▶ power amp ──▶  primary winding  │ ◀── specimen
  (H drive)     │                       │                          │     (toroid)
                │                       ▼  Rsense ──▶ ADC1 CH0 (I)  │
                │                                                  │
   secondary ─▶ │  Vsec ──▶ analog integrator ──▶ ADC2 CH0 (B_int)  │
   (B sense)    │                                                  │
                │            STM32G474RET6                         │
                │   sweep controller · integrator reset · CORDAC   │
                │   B-H loop · core loss · μ · Br · Hc · Bsat      │
                │                                                  │
                │   OLED (loop plot) · SD card (CSV) · UART ──▶    │
                │            ESP32-C3  ── BLE / Wi-Fi ──▶ PC app   │
                └──────────────────────────────────────────────┘
```

---

## 1. What It Is

**Ferro Weave** is the smallest device that can produce a publishable
magnetic hysteresis loop. You wind a primary and a secondary on a toroidal
specimen (or use a standard Epstein frame / single-sheet tester jig), clip
the two leads to the front-panel terminals, press **SWEEP**, and the device
drives a programmable sinusoidal (or triangular, or quasi-DC) magnetizing
current from a few milliamps up to ±2 A, sweeps the peak field across
±10 kA/m (material- and winding-dependent), integrates the secondary
voltage, samples both channels at 1 Msps with 16-bit resolution, and
computes:

- the **B-H loop** (256–4096 points),
- the **dc and incremental permeability** μᵣ,
- the **saturation flux density** B_sat,
- the **remanence** Bᵣ and **coercivity** H_c,
- the **specific core loss** P_v (W/kg) from the loop area,
- the **loop squareness** ratio Bᵣ/B_sat.

The loop is drawn live on a 128×64 OLED, logged to a FAT-formatted SD card
as CSV, and streamed over UART to an ESP32-C3 that repackages it as a BLE
GATT characteristic and/or a Wi-Fi TCP/HTTP endpoint for the companion PC
app (Python, see `scripts/bh_plotter.py`).

It is inspired by commercial hysteresisgraph instruments (Magnet-Physik
Permeameter, Brockhaus MST-500, Laboratorio Elettrofisico AMH-50) but is
entirely open-source, costs ~$90 in parts, and fits in a pocket.

### Why the STM32G474 + ESP32-C3 split

The **STM32G474RET6** is the precision DAQ core: it has the **HRTIM**
(high-resolution timer, 184 ps resolution) for low-jitter PWM stimulus,
a pair of 4 Msps 12-bit ADCs (oversampled to 16-bit) for simultaneous I/V
sampling, the **CORDIC** and **FMAC** hardware accelerators for fast
trig / FIR math, and enough SRAM (128 KB) to buffer a full 4096-point
sweep. The **ESP32-C3** is the connectivity co-processor: it owns BLE and
Wi-Fi, exposes a simple UART command protocol to the STM32, and serves the
sweep data to a phone or PC. This split keeps the DAQ real-time loop
deterministic and lets the radio run on a separate core without stealing
ADC/DMA bandwidth — the same pattern used in **Spectra Charm (#13)** and
**Ping Caliper (#15)**.

---

## 2. Key Features

- **Programmable magnetizing-current sweep** — sinusoidal, triangular,
  or quasi-DC (slow ramp) waveforms from **±50 mA to ±2 A** peak,
  frequency 0.1 Hz to 1 kHz, with software current limiting and a hard
  hardware OCP at 2.5 A.
- **Flux integration via analog integrator + digital reset** — a
  chopper-stabilized OPA2188 integrator converts the secondary voltage
  `V_sec = -N·A·dB/dt` to a voltage proportional to **B**; the STM32
  resets the integrator (analog switch across the cap) at the start of
  each half-cycle to kill drift.
- **Simultaneous 1 Msps / 16-bit dual-channel ADC** — ADC1 samples the
  current-sense voltage (→ **H**), ADC2 samples the integrator output
  (→ **B**), triggered from the same HRTIM update event for true
  simultaneous sampling.
- **On-device computation** (CORDIC-accelerated):
  - B-H loop, μ_dc, μ_inc, B_sat, Bᵣ, H_c, P_v (W/kg), squareness.
  - Air-flux correction (secondary winding self-flux subtraction) with a
    user-entered `N₂·A₂` constant.
  - Demagnetization (degauss) sequence before measurement.
- **OLED loop plot** (SSD1306 128×64) — live B-H loop with axis ticks,
  plus a numeric readout of B_sat / H_c / P_v.
- **SD card logging** — every sweep is stored as `BH_YYYYMMDD_HHMMSS.csv`
  with N, A, ρ (material density), sweep params, and the raw B/H arrays,
  plus a JSON summary.
- **BLE + Wi-Fi streaming** via the ESP32-C3:
  - **BLE**: a `FerroWeave` GATT service with a sweep-data characteristic
    (chunked) and a command characteristic.
  - **Wi-Fi**: a captive-portal config page + an HTTP `/sweep.json`
    endpoint that returns the last sweep, plus a raw TCP stream mode for
    live plotting.
- **Companion PC app** (`scripts/bh_plotter.py`) — plots the loop,
  computes derived quantities, exports PNG/CSV, and batch-processes
  SD-card dumps.
- **Rechargeable LiPo** (3.7 V 2200 mAh) with USB-C charging — ~6 h of
  continuous sweeping, or ~30 h of BLE-only polling.
- **Safety**: hardware OCP at 2.5 A, thermal shutdown on the power amp
  (LM5035 + external FETs monitored via an NTC), a front-panel **STOP**
  button wired directly to the HRTIM fault input, and a degauss-on-disarm
  routine so the specimen is left unmagnetized after a sweep.

---

## 3. Block Diagram

```
                 ┌───────────────────────────────────────────────────────┐
                 │                     STIMULUS                           │
                 │   HRTIM-A  PWM (184 ps) ──▶ LM5035 half-bridge driver  │
                 │                                  │                      │
                 │                          ┌───────▼────────┐              │
                 │                          │  power stage    │  ±15 V rail │
                 │                          │  (2× IRFH7446)  │ ◀── boost    │
                 │                          └───────┬────────┘              │
                 │                                  │  H-drive               │
                 │   primary winding (N₁) ◀─────────┘                       │
                 │                                  │                       │
                 │                          Rsense 0.1Ω  ──▶ ADC1_IN1 (I→H) │
                 │                                                          │
                 │   secondary winding (N₂) ──▶ analog integrator           │
                 │           (OPA2188 + analog switch reset)               │
                 │                                  │                       │
                 │                                  ▼                       │
                 │                          ADC2_IN1 (B_int)                │
                 │                                                          │
                 │                  STM32G474RET6                           │
                 │   sweep FSM · integrator reset · CORDIC μ/Bsat/Hc       │
                 │   air-flux corr · degauss · OCP watchdog · SD/FATFS      │
                 │                                                          │
                 │   SPI  ──▶ microSD   I²C ──▶ SSD1306 OLED 128×64         │
                 │   GPIO ──▶ STOP btn, FAULT, TEMP_NTC, 4×LED              │
                 │   UART4 ──▶ ESP32-C3 (115200, command/sweep protocol)    │
                 └──────────────────────────────────┬──────────────────────┘
                                                    │ UART
                                     ┌──────────────▼──────────────┐
                                     │        ESP32-C3-MINI-1       │
                                     │   BLE GATT (FerroWeave svc)  │
                                     │   Wi-Fi AP+STA / HTTP / TCP  │
                                     │   captive config portal      │
                                     └──────────────┬──────────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │  phone / PC app      │
                                         │  bh_plotter.py       │
                                         └─────────────────────┘
```

---

## 4. Bill of Materials

See [`hardware/BOM.csv`](hardware/BOM.csv) for the full priced BOM. Summary:

| Ref | Part | Qty | Price (USD) | Role |
|-----|------|-----|-----------|------|
| U1 | STM32G474RET6 | 1 | 6.80 | DAQ + sweep SoC |
| U2 | ESP32-C3-MINI-1 | 1 | 2.60 | BLE / Wi-Fi co-processor |
| U3 | LM5035C | 1 | 4.20 | Half-bridge MOSFET driver / controller |
| Q1,Q2 | IRFH7446 | 2 | 1.10 | Power-stage FETs |
| U4 | OPA2188 | 1 | 2.90 | Chopper integrator op-amp (2 ch, use 1) |
| U5 | TS5A3166 | 1 | 0.40 | Analog switch for integrator reset |
| U6 | SSD1306 OLED 128×64 I2C | 1 | 2.20 | Loop display |
| U7 | AMS1117-3.3 | 1 | 0.15 | 3.3 V LDO (logic) |
| U8 | TPS61040 | 1 | 1.30 | Boost to ±15 V rail (single-inductor + charge pump) |
| U9 | TP4056 | 1 | 0.35 | LiPo USB-C charger |
| U10 | MAX17048 | 1 | 2.30 | LiPo fuel gauge |
| J1 | 4 mm banana binding posts (red/black pair) | 2 | 2.40 | Primary + secondary terminals |
| J2 | USB-C 2.0 receptacle | 1 | 0.30 | Charging + ESP32 console |
| µSD | microSD socket (Molex 502570-0893) | 1 | 0.90 | Logging |
| BAT | 3.7 V 2200 mAh LiPo | 1 | 5.50 | Battery |
| NTC | 10 kΩ B3950 NTC | 1 | 0.20 | Power-stage temp monitor |
| Rsense | 0.1 Ω 1% 1 W (CSS2H-2512K-0R1) | 1 | 0.60 | Current sense resistor |
| PCB | 4-layer FR4 80×120 mm | 1 | 8.00 | — |
| Misc | passives, inductors, LEDs, buttons | — | ~12.00 | — |
| | **Total** | | **~$52** | |

> The BOM intentionally uses a **boost converter** to generate the ±15 V
> rail from the 3.7 V LiPo rather than a charge-pump-only design, so the
> power stage can deliver ±2 A into a low-impedance primary without
> drooping. The negative rail is generated by an inverting charge-pump
> stage off the same inductor (see `docs/assembly-guide.md` §4).

---

## 5. Pin Assignments

### STM32G474RET6 pin map

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| PA0 | ADC1_IN1 | I_SENSE | current-sense voltage (H = N₁·I/(lₑ)) |
| PA1 | ADC2_IN1 | B_INT | integrator output (B = −∫V_sec/(N₂·A₂) dt) |
| PA2 | HRTIM_CHA1 | PWM_HI | high-side PWM to LM5035 HSG |
| PA3 | HRTIM_CHA2 | PWM_LO | low-side PWM to LM5035 LSG |
| PA4 | GPIO / DAC1_OUT1 | V_DRIVE_SET | analog sweep-amplitude reference (optional) |
| PA5 | GPIO | INTG_RESET | drives TS5A3166 to short the integrator cap |
| PA6 | HRTIM_FLTA | STOP_BTN | hardware fault input (front-panel STOP) |
| PA7 | GPIO / ADC1_IN7 | TEMP_NTC | power-stage temperature |
| PA8 | GPIO | FAULT_LED | red LED, lit on OCP/thermal fault |
| PA9 | GPIO | RUN_LED | green LED, lit during a sweep |
| PA10 | GPIO | OCP_LATCH | reads back the LM5035 fault latch |
| PA11 | SPI1_NSS | SD_CS | microSD chip-select |
| PA12 | SPI1_SCK | SD_SCK | |
| PB13 | SPI1_MISO | SD_MISO | |
| PB14 | SPI1_MOSI | SD_MOSI | |
| PA15 | I2C1_SCL | I2C_SCL | OLED + MAX17048 |
| PB7 | I2C1_SDA | I2C_SDA | |
| PA9 alt | UART1_TX | ESP_TX | → ESP32-C3 UART RX (console + protocol) |
| PA10 alt | UART1_RX | ESP_RX | ← ESP32-C3 UART TX |
| PC10 | UART4_TX | DBG_TX | optional debug UART |
| PC11 | UART4_RX | DBG_RX | |
| PC13 | GPIO | ESP_BOOT | reset/boot the ESP32-C3 |
| PC14 | GPIO | ESP_EN | |
| PC15 | GPIO | AMP_EN | enable the ±15 V boost (power stage) |
| PB0 | ADC1_IN9 | VBAT_DIV | battery voltage divider |
| PB1 | GPIO | SWEEP_BTN | front-panel "start sweep" button |
| PB2 | GPIO | MODE_BTN | cycle sweep waveform / amplitude |
| NRST | — | NRST | 10 kΩ pull-up + 100 nF |
| BOOT0 | — | BOOT0 | tied to GND |
| VDD, VDDA | — | +3V3 | decoupled per datasheet |
| VSS | — | GND | |

### ESP32-C3-MINI-1 pin map

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| GPIO2 | UART RX | STM_TX | ← STM32 UART1 TX |
| GPIO3 | UART TX | STM_RX | → STM32 UART1 RX |
| GPIO8 | BOOT | — | 10 kΩ pull-up |
| GPIO9 | EN | — | 10 kΩ pull-up, from STM32 PC14 |
| GPIO10 | LED | BLE_LED | status LED |
| 19/20 | USB D-/D+ | USB | console + firmware flash |

---

## 6. Power Architecture

```
                         USB-C (5 V)
                            │
                  ┌─────────▼──────────┐
                  │      TP4056         │  LiPo charge @ 500 mA
                  └─────────┬──────────┘
                            │  VBAT (3.0–4.2 V)
                  ┌─────────▼──────────┐
                  │  3.7 V 2200 mAh LiPo│
                  └─────────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
       │ TPS61040     │ │ AMS1117  │ │ MAX17048   │
       │ boost        │ │ 3.3 V    │ │ fuel gauge │
       │ +15 V (1 A)  │ │ LDO      │ │ I2C → STM32│
       │ + inv. charge│ │ 500 mA   │ └────────────┘
       │ pump → −15 V │ └────┬─────┘
       └──────┬──────┘      │ 3V3
              │             ├──▶ STM32G474
              │ ±15 V       ├──▶ ESP32-C3
              │             ├──▶ SSD1306 OLED
              ▼             └──▶ SD card (3.3 V)
       power stage (LM5035 + IRFH7446)
              │
              ▼  ±2 A magnetizing current → primary
```

- The **±15 V rail** is generated by a TPS61040 boost to +15 V followed
  by an inverting charge-pump stage (two Schottky diodes + 2× 4.7 µF) to
  −15 V, supplying the OPA2188 integrator and the LM5035 high-side driver
  bootstrap. The power stage FETs switch the ±15 V into the primary.
- `AMP_EN` (PC15) gates the boost so the ±15 V rail is only energized
  during a sweep — standby current is ~3 mA.
- Typical sweep current ≈ 600 mA average (peak 2 A) → ~4 h of continuous
  sweeping; BLE-only polling lasts ~30 h.

---

## 7. Firmware

The STM32 firmware is bare-metal C built with **CMake + arm-none-eabi-gcc**
and the STM32CubeG4 HAL. The ESP32-C3 firmware uses **ESP-IDF v5.2**.

```
firmware/
├── CMakeLists.txt              # top-level (builds both stm32 + esp32 targets)
├── stm32/
│   ├── CMakeLists.txt
│   ├── core/                   # startup_stm32g474xx.s, system_stm32g4xx.c
│   ├── Drivers/                # STM32G4 HAL (subset)
│   ├── main.c                  # app entry, sweep FSM
│   ├── sweep.c / .h            # sweep waveform generator + HRTIM config
│   ├── adc.c / .h              # dual-ADC 1 Msps DMA + oversample to 16-bit
│   ├── integrator.c / .h       # integrator reset + air-flux correction
│   ├── bh.c / .h               # B-H loop, μ, B_sat, B_r, H_c, P_v (CORDIC)
│   ├── power.c / .h            # boost enable, OCP, thermal, fuel gauge
│   ├── display.c / .h          # SSD1306 loop plot
│   ├── sdlog.c / .h            # FatFS CSV/JSON logging
│   ├── esp_link.c / .h         # UART protocol to ESP32-C3
│   └── port_sim.c              # host simulation shim for `make sim`
├── esp32/
│   ├── CMakeLists.txt
│   ├── main/
│   │   ├── main.c              # ESP-IDF entry, UART bridge, BLE/Wi-Fi
│   │   ├── proto.c / .h        # frame protocol shared with stm32/esp_link.c
│   │   ├── ble.c / .h          # GATT FerroWeave service
│   │   ├── wifi.c / .h         # AP+STA, HTTP /sweep.json, TCP stream
│   │   └── sdkconfig.defaults
│   └── sim/                    # native sim build (no ESP-IDF)
└── sim/
    └── CMakeLists.txt          # native simulation of the stm32 math path
```

### Building

**STM32 (arm-none-eabi-gcc + STM32CubeG4 HAL):**
```bash
cd firmware
cmake -B build-stm32 -S stm32 -DCMAKE_TOOLCHAIN_FILE=stm32/arm-gcc.cmake
cmake --build build-stm32
# flash with OpenOCD / ST-Link:
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
        -c "program build-stm32/ferro_weave.elf verify reset exit"
```

**ESP32-C3 (ESP-IDF v5.2):**
```bash
cd firmware/esp32
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

**Simulation (host, exercises the B-H math without hardware):**
```bash
cd firmware
cmake -B build-sim -S sim
cmake --build build-sim
./build-sim/ferro_weave_sim
# prints a synthetic B-H loop + computed B_sat / H_c / P_v
```

The simulation build links `port_sim.c` (stubbed HAL/ADC/HRTIM) and feeds
`bh.c` a synthetic sinusoidal H + saturating B model so the full math path
(CORDIC-free pure-C fallback) can be verified on a host.

### Configuration

`stm32/STM32G474RETx_FLASH.ld` and `stm32/stm32g4xx_hal_conf.h` set:
- 170 MHz system clock (PLL from 16 MHz HSI),
- HRTIM at 4.2 GHz equivalent (170 MHz × 32× HRTIM prescaler),
- ADC1+ADC2 at 1 Msps, dual-mode regular simultaneous, DMA 2× 4096 samples,
- hardware oversampling ×16 → effective 16-bit at 62.5 ksps (used for the
  final B/H arrays; raw 1 Msps is used for OCP detection),
- SPI1 at 25 MHz for the SD card (FatFs, long filenames),
- UART1 at 115200 8N1 to the ESP32-C3.

`sdkconfig.defaults` (ESP32-C3) sets:
- BLE NimBLE (1 connection), FerroWeave GATT service,
- Wi-Fi AP+STA, mDNS `ferro-weave.local`,
- 160 MHz CPU.

---

## 8. Measurement Theory

### Recovering B and H

For a toroidal specimen with primary turns **N₁**, secondary turns **N₂**,
magnetic path length **lₑ**, and cross-sectional area **A₂** of the
secondary winding (≈ specimen cross-section + winding area):

- The applied field **H** is set by the primary current **I** measured
  across `R_sense`:

  `H(t) = N₁ · I(t) / lₑ`

- The secondary voltage **V_sec** is, by Faraday's law:

  `V_sec(t) = −N₂ · A₂ · dB/dt`

  Integrating:

  `B(t) = −1/(N₂·A₂) · ∫ V_sec dt`

The analog integrator (OPA2188 + 100 nF cap + reset switch) performs the
integration in hardware; its output is sampled by ADC2. The STM32 resets
the integrator at the start of each half-cycle (driven by the HRTIM
update event) so the integration constant is zero at the beginning of
every loop.

### Air-flux correction

The secondary winding encloses a small amount of air (the winding area
`A₂` is larger than the specimen area `A_core`). The air contributes a
linear, non-hysteretic flux `B_air = μ₀·H·(A₂−A_core)/A₂` that is
subtracted in software:

`B_corrected(t) = B_measured(t) − μ₀ · H(t) · (A₂ − A_core)/A₂`

The user enters `N₁`, `N₂`, `lₑ`, `A₂`, `A_core`, and the material
density `ρ` (kg/m³) via the captive Wi-Fi portal or the Python script.

### Derived quantities

| Quantity | Computation |
|----------|-------------|
| **B_sat** | max |B(t)| over the loop |
| **H_c**  | H at the B=0 crossing (linear interp between samples) |
| **B_r**  | B at the H=0 crossing |
| **μ_dc** | slope of the line from origin to (H_peak, B_peak) |
| **μ_inc**| local dB/dH at the operating point |
| **P_v**  | loop area × f / ρ (W/kg); for DC/quasi-DC, loop area × ρ gives the per-cycle loss density (J/m³) |
| **Squareness** | B_r / B_sat |

### Demagnetization

Before each sweep, Ferro Weave runs a **degauss** sequence: a sinusoidal
current whose amplitude decays exponentially from ±I_peak to zero over
~2 s, leaving the specimen in a demagnetized state so the first sweep
starts from the origin.

---

## 9. Sweep Protocol

A full measurement cycle is:

1. **Disarm** — turn off `AMP_EN`, reset the integrator.
2. **Degauss** — 2 s exponential-decay sinusoid at the sweep frequency.
3. **Arm** — enable `AMP_EN`, energize ±15 V, reset integrator.
4. **Pre-loop** — 2 cycles at low amplitude to stabilize the integrator.
5. **Sweep** — ramp the amplitude from 0 to the user-set peak over 1 s
   (so the loop is traced from the origin outward), then hold at peak
   for a configurable number of cycles (default 5). The *last* cycle is
   captured to the 4096-sample buffer.
6. **Compute** — B-H loop, derived quantities, air-flux correction.
7. **Disarm** — degauss again, disable `AMP_EN`.
8. **Log** — write CSV + JSON to SD, send to ESP32-C3 for BLE/Wi-Fi.

The whole cycle takes ~8–10 s by default, faster at higher sweep
frequencies.

---

## 10. Companion App

`scripts/bh_plotter.py` is a Python (matplotlib + bleak/requests) app that:

- **Live mode**: connects over BLE (or Wi-Fi TCP) and plots the B-H loop
  in real time as sweeps complete.
- **Batch mode**: reads a folder of SD-card CSV dumps and produces a
  summary table + per-sample PNG plots.
- Computes the same derived quantities as the firmware (cross-check) and
  lets you fit a **Jiles-Atherton** model to the measured loop.

```bash
python3 scripts/bh_plotter.py --ble --device FerroWeave
python3 scripts/bh_plotter.py --wifi --host 192.168.4.1
python3 scripts/bh_plotter.py --batch /mnt/sd/BH_*.csv
```

`scripts/wind_calc.py` helps you compute N₁, N₂, lₑ, A₂, A_core from a
toroid geometry (OD, ID, height) before you start.

---

## 11. Assembly

See [`docs/assembly-guide.md`](docs/assembly-guide.md) for the full
step-by-step. In brief:

1. Solder the STM32G474 (LQFP64) and ESP32-C3-MINI-1 module.
2. Populate the power section: TP4056, MAX17048, AMS1117, TPS61040 boost,
   inverting charge pump, LM5035 + IRFH7446 FETs.
3. Populate the analog front end: OPA2188 integrator, TS5A3166 reset
   switch, 0.1 Ω sense resistor, NTC.
4. Populate the user interface: SSD1306 OLED, microSD socket, 4 mm banana
   posts, STOP / SWEEP / MODE buttons, status LEDs.
5. Wind the test specimen (instructions + a 3D-printed winding jig STL in
   `docs/`).
6. Flash the STM32 over SWD, the ESP32-C3 over USB-C.
7. Calibrate: see [`docs/calibration-guide.md`](docs/calibration-guide.md).

---

## 12. Safety

This device drives up to **±2 A through an inductive load**. Read
[`docs/safety-notes.md`](docs/safety-notes.md) before powering it on.

- A **hard hardware OCP** at 2.5 A latches off the LM5035 within 200 ns
  and asserts a fault to the STM32 `HRTIM_FLTA` input, which immediately
  forces all HRTIM outputs to their safe state.
- The front-panel **STOP** button is wired directly to `HRTIM_FLTA` — it
  does not depend on firmware.
- An NTC on the power-stage FETs trips a thermal shutdown at 85 °C.
- The specimen is always **degaussed** before disarm, so you don't walk
  away with a magnetized core.
- The ±15 V boost is gated by `AMP_EN` and is off in standby.

---

## 13. API Reference

See [`docs/api-reference.md`](docs/api-reference.md) for full firmware
API docs. Key functions:

- `sweep_start(const sweep_params_t *p)` — kick off a measurement cycle.
- `sweep_status_t sweep_get_status(void)` — IDLE / DEGAUSS / ARM /
  SWEEP / COMPUTE / LOG / FAULT.
- `bh_result_t *bh_get_last(void)` — last computed loop + derived q's.
- `bh_compute(const int16_t *H, const int16_t *B, int n, const geom_t *g,
  bh_result_t *out)` — pure-C loop computation (used by sim + firmware).
- `esp_link_send_sweep(const bh_result_t *r, const int16_t *H,
  const int16_t *B, int n)` — push a sweep to the ESP32-C3.
- `sdlog_write(const bh_result_t *r, const int16_t *H, const int16_t *B,
  int n)` — write CSV + JSON to the SD card.

---

## 14. What Makes It Different

| | Spectra Charm (#13) | Ping Caliper (#15) | Phase Scope (#14) | **Ferro Weave** |
|---|---|---|---|---|
| Domain | UV-Vis spectroscopy | Ultrasonic NDT | Power quality | **Magnetic materials** |
| Stimulus | LED sweep | HV GaN pulser | Galvanically-isolated V/I | **Programmable current sweep** |
| Sense | AS7343 10-ch | TGC receiver | Isolated V/I ADCs | **Analog integrator + I-sense** |
| Math | Spectral deconvolution | A-scan echo | FFT harmonics | **B-H loop, μ, core loss** |
| SoC | STM32G491 + ESP32-C3 | STM32G474 + ESP32-C3 | STM32G491 | **STM32G474 + ESP32-C3** |
| Output | Compound ID | Thickness + flaws | Phasor diagram | **B-H loop + B_sat/H_c/P_v** |

Ferro Weave is the first device in this collection aimed at
**magnetic-materials characterization** — a mainstay of power-electronics
and motor-design labs that is normally served by $10k+ instruments.

---

## 15. License

MIT — build it, measure it, improve it. See repo root LICENSE.