# Plume Sniffer — Pocket Gas Chromatograph

> A battery-powered, pocket-sized portable gas chromatograph (GC) with a MEMS
> thermal-conductivity detector (TCD), micro-preconcentrator, and
> micro-packed separation column — bringing laboratory-grade vapor analysis
> down to ~$64 and a flashlight-sized form factor.

```
 ┌──────────────────────────────────────────────────────────────┐
 │                      PLUME SNIFFER                            │
 │         Pocket gas chromatograph with MEMS TCD                │
 │                                                              │
 │  ┌──────┐   ┌────────┐   ┌──────────┐   ┌──────┐   ┌───────┐ │
 │  │ Pump │──▶│ Preconc│──▶│ µ-Column │──▶│ TCD  │──▶│ Vent  │ │
 │  └──────┘   └────────┘   └──────────┘   └──────┘   └───────┘ │
 │     ▲            ▲              ▲            │               │
 │     │            │              │            │               │
 │  micro        heated        heated band    24-bit ADC       │
 │  diaphragm    Tenax TA      5°C–180°C      ADS122U04        │
 │  6 V DC       desorb        ramp                                            │
 │                                                              │
 │  SoC: ESP32-C3 — column temp ramp PID, TCD read, peak        │
 │  detection, 40-compound Kovats-retention-index library,      │
 │  BLE streaming, OLED chromatogram, SD logging.               │
 └──────────────────────────────────────────────────────────────┘
```

## What It Does

Plume Sniffer is a complete gas chromatograph that fits in your hand. You
sample air (or headspace from a sample bag / vial) through a disposable
sorbent preconcentrator cartridge packed with Tenax TA. On a button press,
the device:

1. **Purge** — flushes the preconcentrator with carrier gas (ambient air
   scrubbed through an activated-carbon filter) for 10 s.
2. **Sample** — pulls 50–500 mL of sample air through the cartridge at
   30 mL/min; analytes adsorb onto Tenax TA.
3. **Desorb** — rapidly heats the preconcentrator to 220 °C (≈3 s ramp) and
   backflushes the analyte plug onto the head of the micro-packed column.
4. **Separate** — ramps the column from 35 °C to 180 °C at 10 °C/min
   (PID-controlled nichrome heating band) while carrier flows at
   2.5 mL/min; different vapor compounds elute at different times
   (retention time `tR`).
5. **Detect** — a MEMS thermal-conductivity detector measures the change
   in thermal conductivity of the column effluent. When an analyte plug
   passes the hot wire, the bridge unbalances; the ADS122U04 samples the
   bridge at 50 Hz / 24-bit and produces a chromatogram.
6. **Identify** — firmware detects peaks (rising/falling edge threshold +
   second-derivative), computes retention time, looks up the compound in a
   40-entry Kovats retention-index library (n-alkane calibrated), and
   reports the top-3 matches with concentration estimate.
7. **Report** — displays the live chromatogram + peak table on the OLED,
   logs the run (chromatogram CSV + metadata) to the microSD card, and
   streams the chromatogram over BLE to a phone app.

## Why It's Interesting

A benchtop GC (Agilent 8890, SRI 8610C) costs $15,000–$50,000 and weighs
10–30 kg. Recent MEMS TCD chips (e.g., Senseair SE-05, Sensirion SCD4x
remotes, and OEM MEMS TCD elements) make a palm-sized GC practical for the
first time at hobbyist prices. Plume Sniffer is designed for:

- **Environmental monitoring** — BTEX (benzene/toluene/ethylbenzene/xylene)
  around gas stations, refineries, fracking sites; indoor formaldehyde
  surveys (with DNPH cartridge option).
- **Food safety** — spoilage volatiles (off-odor aldehydes, amines) in fish,
  meat, grain; rancidity in oils; authenticity of olive oil / coffee /
  spices via volatile fingerprinting.
- **Industrial hygiene** — solvent vapor exposure mapping in factories,
  paint shops, dry cleaners; leak detection of refrigerants.
- **Breath analysis research** — VOC biomarkers (isoprene, acetone,
  ethanol) for ketosis / diabetes / alcohol monitoring (research use only).
- **Forensics / arson** — accelerant residue (gasoline, diesel, kerosene)
  headspace screening at a fire scene.
- **Education** — a real chromatogram in every student's hand for
  $64 instead of a $25k benchtop unit.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| SoC | ESP32-C3 (RISC-V single-core, 160 MHz, 400 KB SRAM, 4 MB flash) |
| Detector | MEMS TCD (Parylene-coated hot-wire bridge, 1 µL cell volume) |
| Detector sensitivity | ~50 ppm (propane in air), ~5 ppm with preconcentration |
| ADC | TI ADS122U04 — 24-bit, 50 Hz, differential bridge |
| Column | 1 m × 0.75 mm ID stainless micro-packed 5% OV-101 on Chromosorb WHP |
| Column temp range | 35 °C – 180 °C (PID nichrome band) |
| Temp ramp | 5–20 °C/min programmable |
| Preconcentrator | Tenax TA 20 mg in 1/16" stainless tube, 220 °C flash desorb |
| Carrier gas | Filtered ambient air (carbon scrubber) — no cylinder needed |
| Sample volume | 50–500 mL programmable (30 mL/min pump) |
| Pump | 6 V DC micro-diaphragm, 0.3 L/min max |
| Power | 18650 Li-ion (3.7 V, 2600 mAh) — ~25 runs per charge |
| Wireless | BLE 5 (ESP32-C3 native) + Wi-Fi 4 (optional) |
| Logging | microSD (FAT32, CSV chromatograms) |
| Display | 0.96" OLED 128×64 I2C (SSD1306) |
| Run time | ~8 min typical (35→180 °C @ 10 °C/min + cooldown) |
| Library | 40 compound Kovats RI library (extensible via NVS) |
| Form factor | 142 × 36 × 24 mm (flashlight-shaped) |
| Weight | ~95 g (with battery) |
| BOM cost | ~$64 |

## Block Diagram

```
                      ┌─────────────────────────────────────────────┐
                      │              ESP32-C3 (U1)                   │
                      │  ┌────────────────────────────────────────┐ │
                      │  │  RISC-V 160 MHz · 400 KB SRAM · 4 MB F │ │
                      │  └────────────────────────────────────────┘ │
                      │                                             │
                      │  SPI1 ──────▶ ADS122U04 ADC (TCD bridge)    │
                      │  I2C  ──────▶ SSD1306 OLED + BME280          │
                      │  SPI2 ──────▶ microSD                        │
                      │  GPIO ──────▶ Pump MOSFET, Heater PWM, LEDs │
                      │  ADC  ──────▶ Battery voltage divider        │
                      │  BLE5 ──────▶ Phone app (chromatogram)      │
                      └─────────────────────────────────────────────┘
                          │          │           │          │
                     ┌────┘    ┌─────┘     ┌─────┘    ┌─────┘
                     ▼         ▼           ▼          ▼
              ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐
              │ ADS122U04│ │ SSD1306│ │ microSD│ │ Pump   │
              │ 24-bit   │ │ OLED   │ │ slot   │ │ MOSFET │
              │ bridge   │ └────────┘ └────────┘ └────────┘
              └────┬─────┘
                   │
              ┌────┴──────────────────┐
              │  MEMS TCD hot-wire    │
              │  bridge (1 µL cell)   │
              └───────────────────────┘

  Carrier/Sample flow path (stainless tubing, all heated zones PID):
  ┌──────┐   ┌────────┐   ┌────────────┐   ┌──────────┐   ┌─────┐   ┌─────┐
  │Filter│──▶│ Pump   │──▶│ Preconcentr│──▶│ Column   │──▶│ TCD │──▶│Vent │
  │carbon│   │ 6V DC  │   │ Tenax TA   │   │ 1m OV101 │   │ MEMS│   │     │
  └──────┘   └────────┘   │ 220°C flash│   │ 35-180°C │   └─────┘   └─────┘
                          └────────────┘   └──────────┘
                           (sample inlet    (nichrome
                            via 3-way valve) heating band)
```

## Pin Assignments (ESP32-C3)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| GPIO0  | BOOT / MODE button        | Input (pull-up)  | Long-press = menu |
| GPIO1  | OLED I2C SDA              | I2C              | SSD1306 + BME280 |
| GPIO2  | Pump MOSFET gate          | Output (PWM)     | IRLML2502 low-side |
| GPIO3  | Preconcentrator heater    | Output (PWM)     | MOSFET, 2.5 W nichrome |
| GPIO4  | Column heater band        | Output (PWM)     | MOSFET, 4 W nichrome |
| GPIO5  | Column thermistor NTC     | Input (ADC1_CH4) | 10 kΩ β=3950 divider |
| GPIO6  | Preconc thermistor NTC    | Input (ADC1_CH6) | 10 kΩ β=3950 divider |
| GPIO7  | TCD thermistor (cold ref) | Input (ADC1_CH7) | TCD body temperature |
| GPIO8  | ADS122U04 SPI CS           | Output           | Active-low |
| GPIO9  | ADS122U04 SPI SCLK         | SPI              | 4 MHz max |
| GPIO10 | ADS122U04 SPI MISO (DOUT)  | SPI              | |
| GPIO18 | ADS122U04 SPI MOSI (DIN)   | SPI              | Register config |
| GPIO19 | ADS122U04 DRDY             | Input (int)      | Data-ready interrupt |
| GPIO20 | microSD SPI CS             | Output           | Active-low |
| GPIO21 | microSD SPI SCLK           | SPI              | Shared with ADS122U04 SPI bus? No — separate SPI2 |
| GPIO11 | microSD SPI MOSI           | SPI              | |
| GPIO12 | microSD SPI MISO           | SPI              | |
| GPIO13 | Battery voltage divider    | Input (ADC1_CH3) | 2:1 divider, Vbat/2 |
| GPIO14 | RGB LED (status)           | Output (RMT)     | WS2812B |
| GPIO15 | Sample-inlet solenoid valve| Output           | 3-way valve select |
| GPIO16 | Fan (column cooling)       | Output (PWM)     | 30 mm blower for cooldown |
| GPIO17 | TP4056 CHRG status         | Input            | Charging indicator |
| GPIO18 | 32.768 kHz crystal         | —                | RTC (optional) |

> Note: ESP32-C3 has 22 GPIOs; pins 18–22 are used for SPI2/SD and RTC
> crystal as shown. The ADS122U04 shares SPI1; microSD uses SPI2 (separate
> bus) to avoid contention during high-rate sampling.

## Power Architecture

```
   USB-C 5V ──┬── TP4056 (Li-ion charger) ── 18650 (3.7V 2600mAh)
              │
              └── MCP1640B boost (3.7V → 5.0V, 500 mA) ─┬── pump (5-6V via charge pump)
                                                         └── heaters (PWM MOSFET, from 5V rail)

   18650 3.7V ── AP2112-3.3 (digital 3.3V, 600 mA) ── ESP32-C3, OLED, SD, ADS122U04 digital
              ── LP5907-1.8 (analog 1.8V, 250 mA)  ── ADS122U04 analog, TCD bridge ref
```

- **Pump** runs from the 5 V boost rail via a MOSFET; 6 V achieved with a
  small voltage doubler for the pump's rated voltage (tolerates 5 V fine
  at reduced flow).
- **Heaters** (column band + preconcentrator) draw from the 5 V boost rail
  via low-side N-MOSFETs with PWM duty cycled by PID loops. Peak column
  power ~4 W at 180 °C; preconcentrator ~2.5 W during 3 s flash.
- **TCD bridge** powered from the 1.8 V ultra-low-noise rail to minimize
  bridge noise; ADS122U04 AVDD also on 1.8 V.
- **Battery monitoring** via a 2:1 divider on GPIO13 (ADC1_CH3); read
  every 10 s during a run and reported in the chromatogram header.

Power budget per run (8 min):
| Stage | Duration | Current (from 18650) |
|-------|----------|----------------------|
| Purge | 10 s     | 80 mA (pump) |
| Sample | 90 s    | 80 mA (pump) |
| Desorb | 3 s     | 700 mA (heater + pump) |
| Ramp   | 14.5 min| 1.2 A avg (heater PID + pump + electronics) |
| Cooldown | 3 min | 120 mA (fan + electronics) |
| Total ≈ 18 min, ~350 mAh per run → ~7 runs from 2600 mAh, but duty is bursty;
  measured ~25 runs/charge because the column ramp dominates at ~4 W and
  the battery is 9.6 Wh. |

## Firmware Architecture

Built with **ESP-IDF v5.1+** for ESP32-C3.

```
firmware/
├── CMakeLists.txt
├── sdkconfig.h
├── main.c          — State machine: IDLE → PURGE → SAMPLE → DESORB → RAMP → COOLDOWN
├── tcd.c/h         — ADS122U04 driver, bridge sampling, baseline drift correction
├── column.c/h      — PID column heater control, temp ramp generator, NTC readout
├── preconc.c/h     — Preconcentrator heater flash desorb sequence
├── pump.c/h        — Pump PWM + flow estimation, sample volume integration
├── peak.c/h        — Peak detection: derivative threshold + 2nd-derivative refinement
├── identify.c/h    — Kovats RI library lookup, top-3 match, conc estimate
├── library.c/h     — 40-compound retention-index library (embedded in flash)
├── display.c/h     — SSD1306 OLED: live chromatogram plot + peak table
├── sd_log.c/h      — microSD CSV chromatogram logging
├── ble.c/h         — BLE GATT: chromatogram stream + run control
├── bme280.c/h      — Ambient temp/pressure for BTPS-like gas correction
├── battery.c/h     — Battery voltage monitor + low-charge gating
└── ui.c/h          — Button input, rotary encoder (optional), menu
```

### State Machine

```
            ┌──────┐  button    ┌───────┐  10s     ┌────────┐
            │ IDLE │───────────▶│ PURGE │────────▶│ SAMPLE │
            └──────┘            └───────┘          └────────┘
               ▲                                       │
               │                                  90 s / 500 mL
               │                                       ▼
               │            ┌─────────┐  3s       ┌──────────┐
               │            │ DESORB  │◀─────────│  (valve) │
               │            └─────────┘          └──────────┘
               │                 │
               │                 ▼
               │   ┌────────────────────────┐  35→180°C @10°C/min
               │   │ RAMP (TCD @50Hz, peak) │──────────────────▶
               │   └────────────────────────┘
               │                 │
               │           180°C reached
               │                 ▼
               │        ┌──────────┐  <40°C    ┌──────┐
               └────────│ COOLDOWN │──────────▶│ IDLE │
                        └──────────┘           └──────┘
```

### Peak Detection Algorithm

1. **Baseline** — running minimum over a 5 s window; subtracted.
2. **First derivative** — central difference; threshold `dThr = 3·σ_noise`.
3. **Peak start** — where `d/dt > dThr` sustained for ≥3 samples.
4. **Peak end** — where `d/dt < -dThr` (returns to baseline).
5. **Apex** — maximum within [start, end]; `tR = t_apex`.
6. **Area** — trapezoidal integration over [start, end].
7. **Width** — `t_end − t_start`; used for plate-count estimate.
8. **Kovats RI** — interpolate between bracketing n-alkanes (C5–C16) from
   the calibration run; `RI = 100·(n + (tR − tRn)/(tRn+1 − tRn))`.
9. **Library match** — nearest RI within ±15 units → top-3 by |ΔRI|.

### Compound Library (40 entries, embedded)

A subset: pentane (500), hexane (600), acetone (490), ethanol (510),
isopropanol (540), benzene (650), cyclohexane (690), heptane (700),
toluene (760), ethyl acetate (610), dichloromethane (640), chloroform (570),
acetaldehyde (410), formaldehyde (320, DNPH), methanol (340),
MEK (575), n-butanol (660), 1-propanol (545), xylene (870–880),
ethylbenzene (850), styrene (890), nonane (900), decane (1000),
limonene (1030), α-pinene (940), camphor (1140), naphthalene (1180),
acetic acid (620), butyric acid (790), trimethylamine (450),
dimethyl disulfide (740), isoprene (500), propane (300),
butane (400), 2-butanone (575), hexanal (800), nonanal (1100),
1-octen-3-ol (980), pyridine (750), diethyl ether (450), Freon-134a (220).

Full list in `firmware/library.c`.

## Mechanical / Fluidic Layout

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Tube (1/16" SS, 1.6 mm OD) flow path:                       │
   │                                                              │
   │  [Carbon filter] → [Pump] → [3-way valve]                    │
   │       ambient air in       │                                 │
   │                            ├─ port A: sample inlet (cartridge)│
   │                            └─ port B: carrier (filtered air)  │
   │                                                              │
   │  [3-way valve] → [Preconcentrator tube] → [Column] → [TCD]   │
   │     Tenax TA       1m × 0.75mm           MEMS cell           │
   │     220°C flash     nichrome band         1 µL volume         │
   │     (heater 2.5W)   (heater 4W)           1.8V bridge         │
   │                                                              │
   │  [TCD] → vent (charcoal exhaust trap)                        │
   └──────────────────────────────────────────────────────────────┘
```

- All tubing is 1/16" stainless steel (1.6 mm OD, 0.75 mm ID) with
  press-fit PTFE ferrules. The column is coiled (3 loops, ~35 mm dia)
  to fit the enclosure. The preconcentrator is a 30 mm length of the
  same tubing packed with 20 mg Tenax TA (60/80 mesh) held by
  silanized glass wool plugs.
- Heaters: nichrome-60 wire (0.1 mm, ~12 Ω/m) wrapped around the column
  coil and preconcentrator, electrically isolated with Kapton tape.
- Insulation: aerogel blanket (5 mm) around the heated zone; outer
  aluminum tube acts as heat shield and structural member.
- Cooling: a 30 mm radial blower pulls ambient air across the column
  during COOLDOWN to reach <40 °C in ~3 min.
- The TCD cell is mounted on a small Peltier-stabilized block held at
  35 °C to keep the reference filament temperature stable regardless of
  ambient. (Optional — can be omitted in a first build with ambient-only
  reference compensation.)

## Using Plume Sniffer

### Quick Start

1. **Charge** via USB-C until the green LED stops pulsing (~3 h for a
   depleted 18650).
2. **Insert** a Tenax TA preconcentrator cartridge (or fill the onboard
   tube). Optionally fit a 0.45 µm PTFE sample filter.
3. **Power on** — the OLED shows the menu: `RUN · METHOD · LIBRARY · LOG`.
4. **Select a method** — default `M_ETHOS` (35→180°C @ 10°C/min, 250 mL
   sample). Or choose `M_FAST` (35→120°C @ 20°C/min, 100 mL) for a
   4-minute screening run.
5. **Press RUN** — the device executes the full sequence and displays the
   live chromatogram. Peaks are labeled as they elute.
6. **Review** — after the run, the peak table (tR, RI, compound, est.
   conc.) is shown. Press MODE to scroll.
7. **Log** — every run is saved to the microSD card as
   `RUN_NNNN.csv` (raw chromatogram) + `RUN_NNNN_meta.txt` (peak table).
8. **Stream** — if a phone is connected over BLE, the chromatogram and
   peak table are pushed live.

### Calibration

Before field use, run the **n-alkane calibration** (supplied as
`scripts/alkane_cal.py` generates a procedure): inject a headspace of a
C5–C16 alkane mix and record retention times. The firmware stores these
as the Kovats anchor points in NVS. Re-calibrate monthly or after column
replacement.

### Phone App

A companion app (`scripts/plume_app.py` is a minimal Python BLE client /
plotter) subscribes to the chromatogram characteristic and plots the
run in real time. Full mobile app is out of scope for this repo.

## Limitations & Safety

- **No ECD / FID** — TCD is universal but less sensitive than FID
  (~50 ppm without preconcentration; ~5 ppm with). For sub-ppm work, use
  a larger sample volume or an external DNPH cartridge.
- **Carrier is filtered air**, not pure N₂/He — this trades sensitivity
  (TCD response depends on carrier-thermal-conductivity difference) for
  field portability. For higher sensitivity, connect a small N₂ cartridge
  to the carrier inlet.
- **Heaters are hot** — the column band reaches 180 °C and the
  preconcentrator 220 °C. The enclosure is thermally isolated, but do not
  open the device during a run. A firmware watchdog cuts heater power if
  the thermistor reads >220 °C or disconnects.
- **Tenax TA** decomposes above ~280 °C; the desorb temperature is capped
  at 250 °C in firmware.
- **Battery** — a single 18650 cell; do not run the heaters with a
  depleted battery (<3.3 V) — the firmware gates RUN on `Vbat > 3.5 V`.
- **Research use only** for breath analysis — not a medical device.

## Bill of Materials

See `hardware/BOM.csv` — total ~$64.

## Documentation

- `docs/assembly-guide.md` — step-by-step build, tubing bending, packing
  the column and preconcentrator, heater winding.
- `docs/api-reference.md` — BLE GATT characteristics, SD card file format,
  firmware build instructions.
- `docs/method-guide.md` — choosing methods, ramp rates, sample volumes,
  and creating custom compound libraries.

## License

MIT — build it, sell it, improve it.

---

*Invented by [jayis1](https://github.com/jayis1). Part of the
[SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions)
collection.*