# Sky Lens — Pocket Cosmic-Ray Muon Telescope

> A pocket-sized, battery-powered **cosmic-ray muon detector and telescope**
> that uses two layers of plastic scintillator tiles read out by silicon
> photomultipliers (SiPMs), performs on-device coincidence discrimination,
> computes pressure- and temperature-corrected muon flux, reconstructs the
> incident track angle from the two-layer geometry, fuses with an IMU attitude
> solution to map flux onto the celestial sphere, optionally measures the
> muon **mean lifetime** from a stopped-muon decay experiment, plots a live
> flux / zenith-angle / skymap on an OLED, logs every coincidence to a
> FAT-formatted SD card, and streams a real-time event feed over BLE/Wi-Fi
> to a phone or PC app. Built around the **ESP32-S3-WROOM-1** for the whole
> signal chain, with an ADS7946 dual-channel 14-bit SAR ADC front end.

```
                 ┌──────────────────────────────────────────────────────────┐
                 │                   COSMIC-RAY TELESCOPE                      │
   sky ─▶ muon ▶ │   top scintillator tile ──▶ SiPM1 ──▶ transimpedance amp    │
                 │                                       └──▶ ADS7946 CH0    │
                 │   bottom scintillator tile ──▶ SiPM2 ──▶ transimpedance amp  │
                 │                                       └──▶ ADS7946 CH1    │
                 │                                                          │
                 │   ESP32-S3-WROOM-1                                        │
                 │   coincidence logic · pulse-height · track angle θ         │
                 │   pressure/temp correction · IMU attitude → skymap cell    │
                 │   muon-lifetime mode · deadtime · rate histograms         │
                 │                                                          │
                 │   I²C ──▶ OLED (flux/zenith/skymap)                       │
                 │   I²C ──▶ BMP390 pressure + temp                          │
                 │   I²C ──▶ ICM-42688-P IMU (attitude)                       │
                 │   SPI ──▶ microSD (event log)                              │
                 │   BLE/Wi-Fi ──▶ phone/PC app (live event feed)            │
                 └──────────────────────────────────────────────────────────┘
```

---

## 1. What It Is

**Sky Lens** is the smallest device that can make a real cosmic-ray
measurement. Cosmic-ray muons are produced when primary cosmic rays
(typically protons) strike the upper atmosphere (~15 km) and shower
secondary particles; the muons are the most penetrating component and
reach sea level at a flux of roughly **1 muon per cm² per minute**
(~10,000 per m² per minute), with a zenith-angle dependence
`I(θ) ≈ I(0)·cos²θ` (for a flat detector). Sky Lens detects them by
sandwiching two thin plastic scintillator tiles with a defined gap; a
through-going muon lights up both tiles within nanoseconds, and the
**coincidence** of the two pulses is the unambiguous cosmic-ray signature
that rejects the much larger singles rate from local radioactivity.

Each detected coincidence event is timestamped, the **pulse height** on
each channel is recorded (a proxy for energy deposit / dE/dx), the
**track zenith angle** θ is reconstructed from the small relative timing
delay between the two layers (a muon at angle θ arrives at the bottom tile
`Δt = (d·tan θ)/c` later than the top, where d is the layer gap — for a
typical 30 mm gap this is up to ~100 ps, at the edge of feasibility but
sufficient for coarse binning), and the device's **attitude** from the
onboard IMU maps the track onto the celestial sphere so a long integration
builds up a **muon skymap**.

A built-in **barometric pressure** sensor (BMP390) lets the device correct
the measured flux for atmospheric pressure — muon rate at sea level varies
by roughly **−0.7% per hPa** (the barometric coefficient), so pressure
correction is essential for any meaningful long-term or cross-site
comparison. Temperature correction (small, ~−0.1%/°C) is applied as well.

Optionally, with a small block of low-Z absorber (aluminium or, better,
a piece of plastic scintillator doped to stop ~50 MeV muons), Sky Lens
can run a **muon-lifetime** experiment: a stopping muon decays with a mean
life of **2.197 µs**, and by tagging delayed decays in the same tile one
can histogram the inter-event time and fit the exponential to extract τ_µ —
the same measurement Fermi's group made in 1947, in your pocket.

### Why the ESP32-S3

The **ESP32-S3-WROOM-1** is a sensible single-SoC choice for Sky Lens:

- **240 MHz dual-core Xtensa** — core 0 runs the coincidence / acquisition
  state machine and the realtime histogram updates; core 1 runs the
  BLE/Wi-Fi stack and the display/skymap rendering, keeping the time-
  critical pulse path off the radio core.
- **12-bit ADC** at up to 2 Msps is *not* precise enough for the pulse-
  height measurement (cosmic muons deposit ~1–5 MeV in a thin tile, a
  modest dynamic range), so we use an external **ADS7946** 14-bit
  1 Msps dual-channel SAR ADC sampled via SPI at the trigger instant;
  the ESP32's own ADC is used only for battery/bias monitoring.
- **RMT (Remote Control) peripheral** is repurposed as a fast
  sub-microsecond timestamping input — the two SiPM discriminator
  edges drive RMT channels whose arrival timestamps give the
  coincidence window and the Δt used for angle reconstruction.
- **Wi-Fi 2.4 GHz + BLE 5 (NimBLE)** give a live event feed and a
  web dashboard, with a captive-portal config.
- **USB-Serial-JTAG** and a second UART make flashing and debug trivial.
- Lots of SRAM (512 KB) and PSRAM (8 MB on the WROOM-1U variant) for the
  skymap histogram (a 64×32 cell histogram is 2048 int32 = 8 KB, trivial)
  and a circular event buffer.

This is the same connectivity/peripheral pattern used across the
collection (e.g. **Echo Mote #8**, **Echo Trap #16**, **Pulse Hound #18**),
but pointed at a wholly different problem domain: **astroparticle physics
and citizen-science cosmic-ray observation.**

---

## 2. Key Features

- **Two-layer plastic-scintillator + SiPM coincidence detector** — a
  through-going muon lights both tiles within a ~60 ns window; the
  coincidence cleanly rejects the singles background (local
  radioactivity, dark counts) which is ~1000× higher. Adjustable
  coincidence window (default 60 ns, settable 20–500 ns).
- **14-bit pulse-height capture on both channels** — a triggered ADS7946
  dual SAR ADC samples the peak of each SiPM pulse ~50 ns after the
  coincidence; pulse height is a proxy for dE/dx and is used to reject
  low-energy noise and to characterise the deposit.
- **Track zenith-angle reconstruction** — the relative arrival time Δt
  of the two discriminator edges (RMT-timestamped to ~12.5 ns resolution,
  oversampled to ~3 ns by averaging many events in a zenith bin) gives a
  coarse zenith angle, augmented by the geometric lever arm of the tile
  gap. Long integrations refine this into a flux-vs-zenith histogram.
- **IMU attitude → celestial skymap** — an ICM-42688-P 6-axis IMU
  (accel + gyro) tracks the device orientation; each coincidence is
  mapped onto a 64×32 cell (az × zen) skymap so you can point Sky Lens
  at a patch of sky and watch muon flux accumulate. The famous "muon
  shadow of the Sun/Moon" (a ~1% deficit at the Sun/Moon position)
  is within reach of a long integration.
- **Pressure- and temperature-corrected flux** — a BMP390 barometer gives
  pressure to ±3 Pa and temperature to ±0.5 °C; the firmware applies the
  standard barometric correction (`R_corr = R_meas · exp(β·(P0−P))`,
  β ≈ 0.012 /hPa near sea level) so cross-site and cross-weather
  comparisons are meaningful. The instrument also reports the raw rate.
- **Muon-lifetime mode** (optional) — with a stopping absorber, the
  firmware tags single-tile pulses that are followed, within a 20 µs
  window, by a second pulse on the *same* tile (the Michel-decay
  electron), histograms the inter-pulse delay, and fits the exponential
  to extract τ_µ ≈ 2.197 µs. A built-in goodness-of-fit reports the
  extracted lifetime and its error.
- **Live OLED dashboard** (SSD1306 128×64) — flux rate (cpm), corrected
  flux, zenith histogram bar chart, current skymap cell, pressure/temp,
  battery, and event counter. A long-press cycles between dashboard /
  zenith-histogram / skymap views.
- **SD card logging** — every coincidence event is appended to
  `EVENTS/ev_YYYYMMDD.csv` with timestamp, channel heights, Δt,
  reconstructed θ, attitude quaternion, pressure, temperature. Daily
  rollups write a `daily_YYYYMMDD.json` with the flux, zenith histogram,
  and skymap. The muon-lifetime run writes a `lifetime_*.csv` of
  inter-event delays.
- **BLE + Wi-Fi streaming**:
  - **BLE**: a `SkyLens` GATT service with an event characteristic
    (live coincidences, chunked) and a command characteristic (start/
    stop, set window, set mode, request skymap).
  - **Wi-Fi**: a captive-portal config page, an HTTP `/events.json`
    (last 100 events), `/skymap.json` (the histogram),
    `/lifetime.json` (the decay histogram), and a raw TCP stream mode
    for live plotting.
- **Companion app** (`scripts/skylens_app.py`) — live event feed, skymap
  rendering, zenith-histogram fit (cos²θ), lifetime exponential fit,
  batch processing of SD dumps, and a "map my house" mode that overlays
  the muon flux on a phone-camera AR view using the device attitude.
- **Rechargeable LiPo** (3.7 V 1500 mAh) with USB-C charging — ~10 h of
  continuous acquisition, weeks in duty-cycled "leave it in the garden"
  mode where the ESP32 deep-sleeps between coincidence interrupts
  (wakes on the SiPM pulse via a hardware gate to the RTC GPIO).
- **Bias supply safety** — the SiPMs need ~29–30 V reverse bias, which is
  generated by a small boost converter; the bias is current-limited and
  monitored, and is discharged through a 10 MΩ bleeder on power-down.

---

## 3. Block Diagram

```
                 ┌───────────────────────────────────────────────────────┐
                 │                     DETECTOR                           │
                 │                                                       │
   sky           │   ┌─────────────────────┐  ← top scintillator tile      │
    │            │   │  EJ-200 50×50×5 mm  │                              │
    ▼  muon      │   └──────────┬──────────┘                              │
                 │              │  ~5 photons/MeV → SiPM                  │
                 │   ┌──────────▼──────────┐  30 mm gap (mechanical spacer)│
                 │   │  SiPM1 (Onsemi C-S)  │  ──▶ transimpedance amp ──▶ │
                 │   │  6×6 mm, 35 µm cell  │      (OPA2356)              │
                 │   └─────────────────────┘                  │           │
                 │                                            ├─▶ fast    │
                 │   ┌─────────────────────┐  ← bottom tile     │  comp    │
                 │   │  EJ-200 50×50×5 mm  │                (TLV3501)    │
                 │   └──────────┬──────────┘                  │           │
                 │              │                            ├─▶ RMT CH0  │
                 │   ┌──────────▼──────────┐                  │   (stamp)  │
                 │   │  SiPM2 (Onsemi C-S)  │ ──▶ TIA ──▶ comp ┼─▶ RMT CH1  │
                 │   └─────────────────────┘                  │   (stamp)  │
                 │                                            └─▶ ADS7946  │
                 │   coincidence = (|stamp0−stamp1| < window)      CH0/CH1  │
                 │                                                       │
                 │              ESP32-S3-WROOM-1                         │
                 │   coin logic · pulse-height · track θ · IMU fusion     │
                 │   pressure/temp corr · lifetime fit · skymap           │
                 │                                                       │
                 │   I²C ──▶ SSD1306 OLED 128×64                         │
                 │   I²C ──▶ BMP390 (P/T)  ──  I²C ──▶ ICM-42688-P (IMU)  │
                 │   SPI ──▶ ADS7946 ADC   ──  SPI ──▶ microSD             │
                 │   GPIO ──▶ SiPM bias boost enable, fault, buttons, LED │
                 │   BLE / Wi-Fi ──▶ phone / PC app                       │
                 └───────────────────────────────────────────────────────┘
```

---

## 4. Bill of Materials

See [`hardware/BOM.csv`](hardware/BOM.csv) for the full priced BOM. Summary:

| Ref | Part | Qty | Price (USD) | Role |
|-----|------|-----|-----------|------|
| U1 | ESP32-S3-WROOM-1 (16 MB flash, 8 MB PSRAM) | 1 | 4.20 | Core SoC |
| U2 | ADS7946SRHFR | 1 | 6.10 | Dual 14-bit 1 Msps SAR ADC (pulse height) |
| U3 | Onsemi C-Serie J-Series 60035 SiPM (6×6 mm, 35 µm) | 2 | 14.00 × 2 = 28.00 | Scintillator readout |
| U4 | Eljen EJ-200 plastic scintillator, 50×50×5 mm | 2 | 9.50 × 2 = 19.00 | Detector tiles |
| U5 | OPA2356 (dual, 50 MHz, rail-to-rail) | 1 | 3.20 | Transimpedance amp (TIA) for SiPMs |
| U6 | TLV3501 (comparator, 4.5 ns prop) | 2 | 1.10 × 2 = 2.20 | Fast discriminators |
| U7 | SSD1306 OLED 128×64 I2C | 1 | 2.20 | Dashboard display |
| U8 | BMP390 | 1 | 3.40 | Pressure + temperature |
| U9 | ICM-42688-P | 1 | 3.60 | 6-axis IMU (attitude) |
| U10 | TPS61158 | 1 | 1.60 | SiPM bias boost (~30 V) |
| U11 | AMS1117-3.3 | 1 | 0.15 | 3.3 V LDO |
| U12 | TP4056 | 1 | 0.35 | LiPo USB-C charger |
| U13 | MAX17048 | 1 | 2.30 | LiPo fuel gauge |
| D1,D2 | 1N4148 | 2 | 0.10 | Clamp diodes for TIA input protection |
| J1 | USB-C 2.0 receptacle | 1 | 0.30 | Charging + ESP32 console |
| µSD | microSD socket (Molex 502570-0893) | 1 | 0.90 | Event logging |
| BAT | 3.7 V 1500 mAh LiPo | 1 | 4.50 | Battery |
| Q1 | SiPM bias N-FET (DMN2041L) | 1 | 0.40 | Bias enable switch |
| PCB | 4-layer FR4 70×100 mm + 3D-printed tile cage | 1 | 7.00 | — |
| Misc | passives, optocoupler, LEDs, buttons, light-tight foil | — | ~9.00 | — |
| | **Total** | | **~$95** | |

> The two SiPMs and two scintillator tiles dominate the cost (~$47). The
> detector is the part that is genuinely hard to shrink below this; the
> rest of the bill is standard SoC peripheral hardware.

---

## 5. Pin Assignments

### ESP32-S3-WROOM-1 pin map

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| GPIO1 | RMT_SIG_IN0 | SIPM1_DISC | top-SiPM discriminator edge → RMT CH0 |
| GPIO2 | RMT_SIG_IN1 | SIPM2_DISC | bottom-SiPM discriminator edge → RMT CH1 |
| GPIO4 | SPI_CLK | ADS_SCK | ADS7946 SPI clock (40 MHz) |
| GPIO5 | SPI_CS0 | ADS_CS | ADS7946 chip-select |
| GPIO6 | SPI_MISO | ADS_SDO | ADS7946 data out (14-bit sample) |
| GPIO7 | SPI_MOSI | ADS_SDI | ADS7946 config in |
| GPIO8 | GPIO | ADC_TRIG | trigger output → ADS7946 CONVST (from coincidence) |
| GPIO9 | I2C1_SCL | I2C_SCL | OLED + BMP390 + ICM-42688-P + MAX17048 |
| GPIO10 | I2C1_SDA | I2C_SDA | |
| GPIO11 | SPI2_SCK | SD_SCK | microSD (25 MHz) |
| GPIO12 | SPI2_MISO | SD_MISO | |
| GPIO13 | SPI2_MOSI | SD_MOSI | |
| GPIO14 | SPI2_CS | SD_CS | microSD chip-select |
| GPIO15 | GPIO | BIAS_EN | enables the SiPM 30 V boost (Q1 gate) |
| GPIO16 | ADC1_CH5 | BIAS_MON | monitor SiPM bias voltage (÷30 divider) |
| GPIO17 | ADC1_CH6 | VBAT_DIV | battery voltage divider |
| GPIO18 | GPIO | FAULT_LED | red LED, lit on acquisition fault |
| GPIO19 | GPIO | RUN_LED | green LED, lit during acquisition |
| GPIO20 | GPIO | MODE_BTN | cycle OLED views |
| GPIO21 | GPIO | START_BTN | start / stop acquisition |
| GPIO38 | GPIO | BIAS_FAULT | read back the boost OCP latch |
| GPIO39 | GPIO | IMU_INT | ICM-42688-P data-ready interrupt |
| GPIO40 | UART1_TX | DBG_TX | debug UART |
| GPIO41 | UART1_RX | DBG_RX | |
| GPIO42 | GPIO | BUZZER | optional event-click buzzer |
| 19/20 | USB D-/D+ | USB | console + firmware flash |
| EN | — | EN | 10 kΩ pull-up, RC delay |
| BOOT | — | BOOT | 10 kΩ pull-up, also MODE_BTN on the front panel |

### ADS7946 wiring

| ADS pin | Net | ESP32 pin | Notes |
|---------|-----|-----------|-------|
| SCLK | ADS_SCK | GPIO4 | |
| CS\# | ADS_CS | GPIO5 | |
| SDO | ADS_MISO | GPIO6 | |
| SDI | ADS_MOSI | GPIO7 | config register |
| CONVST | ADC_TRIG | GPIO8 | asserted by the coincidence logic |
| CH0 | TIA1_OUT | — | top SiPM pulse peak (held by peak detector) |
| CH1 | TIA2_OUT | — | bottom SiPM pulse peak (held by peak detector) |
| REF | +4.5 V | — | external reference (REF5045) |

### SiPM bias chain

| Net | Part | Notes |
|-----|------|-------|
| +30 V | TPS61158 boost output | ~29.5 V (set by Rfb; C-Serie breakdown ~27.5 V, overvoltage +2 V) |
| BIAS_MON | ÷30 divider → ADC1_CH5 | 30 V → 1.0 V at the ADC |
| BIAS_EN | GPIO15 → Q1 gate | N-FET high-side switch using a small PMOS pass |
| BIAS_FAULT | GPIO38 | open-drain from the TPS61158 OCP flag |

---

## 6. Power Architecture

```
                         USB-C (5 V)
                            │
                  ┌─────────▼──────────┐
                  │      TP4056         │  LiPo charge @ 400 mA
                  └─────────┬──────────┘
                            │  VBAT (3.0–4.2 V)
                  ┌─────────▼──────────┐
                  │  3.7 V 1500 mAh LiPo│
                  └─────────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
       │ TPS61158    │ │ AMS1117  │ │ MAX17048   │
       │ boost       │ │ 3.3 V    │ │ fuel gauge │
       │ +30 V, 5 mA │ │ LDO 400mA│ │ I²C → ESP32│
       │ (SiPM bias) │ └────┬─────┘ └────────────┘
       └──────┬──────┘      │ 3V3
              │             ├──▶ ESP32-S3
              │ +30 V       ├──▶ ADS7946 (3.3 V) + REF5045 (4.5 V ref)
              │             ├──▶ OLED / BMP390 / ICM-42688-P / MAX17048
              ▼             └──▶ SD card (3.3 V)
        SiPM1, SiPM2 cathodes
```

- The **+30 V bias rail** for the SiPMs is generated by a TPS61158 boost
  converter current-limited to 5 mA; the SiPMs draw only ~1 µA each in the
  dark, so the rail is essentially a voltage reference. `BIAS_EN` (GPIO15)
  gates the boost so the high voltage is only present during acquisition —
  standby current is ~2 mA. A 10 MΩ bleeder discharges the rail in <1 s on
  power-down.
- The ADS7946 needs a 4.5 V reference (REF5045) for its full-scale; this is
  derived from the LiPo via a small LDO and is only powered when the ADC
  is enabled.
- Typical acquisition current ≈ 70 mA (ESP32 active + Wi-Fi + OLED + ADC +
  bias boost) → ~21 h on a 1500 mAh pack; in deep-sleep duty-cycle mode
  (wake on coincidence via the RTC GPIO) the average drops to ~3 mA and
  the pack lasts a week.

---

## 7. Detector Physics

### Why coincidence detection

A single scintillator tile of this size sees a **singles rate** of perhaps
1–2 kHz dominated by the natural radioactivity of the surroundings
(K-40, Bi-214 gammas, radon daughters) and SiPM dark counts (~50 kHz per
mm² at the overvoltage used, but the discriminator threshold cuts this
sharply). The cosmic-ray muon rate through a 50×50 mm tile is only
`~1 cm⁻² min⁻¹ × 25 cm² ≈ 0.4 s⁻¹` ≈ 25 cpm — four orders of magnitude
smaller. The coincidence of two tiles in a stack within a short window
rejects essentially all the uncorrelated singles and leaves a clean
`~cos²θ` muon signal. This is exactly the principle of the classic
cosmic-ray telescope and is the only practical way to count muons with
small tiles.

### Coincidence window

A through-going relativistic muon crosses the 30 mm gap in
`d/c ≈ 100 ps`, far below the ESP32 RMT resolution (~12.5 ns). We therefore
set the coincidence window to the discriminator jitter + SiPM pulse
width, ~60 ns by default. This is wide enough to catch real muons at any
angle up to ~80° from zenith (where Δt ≈ d·tanθ/c ≈ 570 ps — still
within the window because the window is dominated by the pulse shape,
not the geometry) and narrow enough to keep accidental coincidences
negligible:

```
R_accidental ≈ 2 · R1 · R2 · τ_window
            ≈ 2 · (100 s⁻¹) · (100 s⁻¹) · (60e-9 s)
            ≈ 1.2e-3 s⁻¹ ≈ 0.07 cpm
```

i.e. a few accidental coincidences per hour, well below the ~25 cpm
true muon rate. The window is settable in firmware from 20–500 ns.

### Pulse height

A minimum-ionising muon deposits ~`2 MeV cm² g⁻¹ × 1.03 g cm⁻³ × 0.5 cm`
≈ 1 MeV in a 5 mm EJ-200 tile. With a typical SiPM photon-detection
efficiency of ~40% and ~10,000 photons/MeV in plastic scintillator, that
gives ~4000 detected photons → a comfortable signal well above the
single-photo-electron noise. The ADS7946 captures the peak voltage from a
fast peak-hold on each TIA output; the height is logged per event and
used for a rough energy cut and to monitor detector health (a slow drift
indicates scintillator aging or SiPM gain change).

### Zenith-angle reconstruction

The relative arrival time Δt between the two discriminators is, for a
muon at zenith angle θ with a layer gap d:

```
Δt = (d / c) · tan(θ)   (≈ 100 ps at θ = 45°, d = 30 mm)
```

This is below the single-event timing resolution but, with many events
per zenith bin, the **mean** Δt in a bin is measurable to a few ns and
gives a usable zenith estimate; the firmware bins events by Δt and the
skymap accumulates by attitude. The geometric lever arm (knowing which
sub-tile area was hit) is not resolved at this tile size, so angular
resolution is coarse (~10°) — sufficient for a cos²θ fit and for building
up a skymap of the overhead flux.

### Pressure and temperature correction

The muon flux at the ground varies with atmospheric pressure because the
atmosphere is the target that produces the muons; the barometric
coefficient is approximately

```
R_corr(P0) = R_meas(P) · exp[ β · (P0 − P) ],  β ≈ 0.012 hPa⁻¹  (≈ 0.7%/hPa near sea level)
```

The BMP390 gives P to ±3 Pa (±0.03 hPa), so the correction is good to
~0.02% — far smaller than the Poisson counting error for any reasonable
integration. The firmware stores both the raw and corrected rates.

### Muon-lifetime mode

Negative muons stopped in low-Z matter are captured by nuclei on a
timescale of ~80 ns; **positive** muons (the majority at sea level, ~80%
positive) decay with the free muon lifetime τ_µ = **2.197 µs**. With a
stopping absorber above a single tile, a stopping muon gives a prompt
pulse (the stop) followed ~2 µs later by a decay-electron pulse in the
*same* tile. The firmware tags these "prompt–delayed" pairs in a 20 µs
window, histograms the inter-event delay, and fits an exponential
`N(t) = N0·exp(−t/τ) + bg` to extract τ_µ. With a few thousand stops (a
few days of integration with a modest absorber) the lifetime is
recoverable to a few percent — a genuine tabletop particle-physics
experiment.

---

## 8. Firmware

The firmware is bare-metal-ish C built with **ESP-IDF v5.2** (the
ESP32-S3 native toolchain). The time-critical path (RMT timestamping,
coincidence logic, ADC trigger) runs in an ISR on core 0; the
histogramming, display, IMU fusion, and BLE/Wi-Fi run as FreeRTOS tasks
on core 1.

```
firmware/
├── CMakeLists.txt              # top-level (builds the esp32 target + the sim target)
├── esp32/
│   ├── CMakeLists.txt
│   ├── main/
│   │   ├── main.c              # app entry, acquisition FSM, task wiring
│   │   ├── coincidence.c / .h  # RMT timestamping + coincidence window logic
│   │   ├── adc.c / .h          # ADS7946 SPI driver + peak capture
│   │   ├── sipm_bias.c / .h     # TPS61158 boost enable / fault / monitor
│   │   ├── imu.c / .h           # ICM-42688-P driver + attitude (Mahony filter)
│   │   ├── pressure.c / .h      # BMP390 driver + barometric correction
│   │   ├── skymap.c / .h        # 64×32 az×zen histogram + celestial mapping
│   │   ├── zenith.c / .h        # Δt → θ + cos²θ fit
│   │   ├── lifetime.c / .h      # muon-lifetime (prompt–delayed) mode
│   │   ├── display.c / .h       # SSD1306 dashboard / zenith / skymap views
│   │   ├── sdlog.c / .h         # FatFS event CSV + daily JSON
│   │   ├── ble.c / .h           # GATT SkyLens service
│   │   ├── wifi.c / .h          # AP+STA, captive portal, HTTP /events /skymap /lifetime
│   │   ├── proto.c / .h         # event frame protocol shared with the app
│   │   ├── power.c / .h         # MAX17048 fuel gauge + deep-sleep duty cycle
│   │   ├── sdkconfig.defaults
│   │   └── CMakeLists.txt
│   └── sim/
│       └── CMakeLists.txt
├── port_sim.c                  # host simulation shim for `make sim`
└── sim/
    └── CMakeLists.txt           # native simulation of the physics path
```

### Building

**ESP32-S3 (ESP-IDF v5.2):**
```bash
cd firmware/esp32
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

**Simulation (host, exercises the physics + histogram math without hardware):**
```bash
cd firmware
cmake -B build-sim -S sim
cmake --build build-sim
./build-sim/sky_lens_sim
# prints a synthetic 24-hour run: rate, zenith cos²θ fit, skymap, lifetime fit
```

The simulation links `port_sim.c` (stubbed RMT/ADC/I²C) and feeds
`coincidence.c` + `zenith.c` + `skymap.c` a synthetic muon flux model
(sea-level rate, cos²θ angular distribution, barometric drift, an
optional muon-lifetime exponential) so the full math path can be verified
on a host.

### Configuration

`sdkconfig.defaults` (ESP32-S3) sets:
- 240 MHz dual-core, 8 MB PSRAM enabled,
- FreeRTOS tick 1 ms, RMT clock 80 MHz (12.5 ns resolution),
- BLE NimBLE (1 connection), SkyLens GATT service,
- Wi-Fi AP+STA, mDNS `sky-lens.local`,
- FatFS on SPI2 with long filenames,
- I²C1 at 400 kHz for the OLED/BMP390/IMU/fuel gauge.

---

## 9. Acquisition Protocol

A full acquisition cycle is event-driven:

1. **Arm** — enable `BIAS_EN`, stabilise the 30 V rail (50 ms), zero the
   peak detectors, enable the RMT channels and the ADS7946.
2. **Wait for edges** — each SiPM discriminator edge is RMT-timestamped.
3. **Coincidence** — if `|stamp1 − stamp0| < window` (default 60 ns),
   declare a coincidence: trigger the ADS7946 (CONVST on GPIO8), read both
   channels (peak heights), compute Δt → θ, read the IMU attitude, read
   the BMP390 P/T, increment the skymap cell and the zenith histogram,
   and push the event to the event queue.
4. **Log** — the event task drains the queue, appends to the SD CSV,
   and (if BLE/Wi-Fi connected) sends the event frame.
5. **Dashboard** — the display task updates the OLED at 4 Hz with the
   rolling rate, zenith histogram, and current skymap cell.
6. **Daily rollup** — at local midnight the firmware writes a
   `daily_YYYYMMDD.json` with the corrected flux, zenith histogram, and
   skymap, and resets the in-memory histograms (configurable).

**Deep-sleep duty-cycle mode** — for long unattended runs, the firmware
can put the ESP32 into light-sleep between coincidence interrupts (the
SiPM discriminator edges are wired to RTC GPIO wake pins); the average
current drops to ~3 mA and a 1500 mAh pack lasts a week.

**Muon-lifetime mode** — the user places a stopping absorber above the
bottom tile and selects the mode over BLE/Wi-Fi or the MODE button. The
firmware then additionally searches for prompt–delayed pairs on the
*same* channel within a 20 µs window, histograms the delays, and on
demand fits the exponential and reports τ_µ with a 1-σ error.

---

## 10. Companion App

`scripts/skylens_app.py` is a Python (matplotlib + bleak/requests) app that:

- **Live mode** — connects over BLE (or Wi-Fi TCP) and shows a live event
  feed, a rolling rate plot, a zenith histogram with a cos²θ fit, and a
  64×32 skymap of the celestial muon flux.
- **Lifetime mode** — plots the inter-event delay histogram and fits the
  exponential to extract τ_µ, displaying the lifetime and its error.
- **Batch mode** — reads a folder of SD-card CSV dumps and produces a
  summary table + per-day PNG plots (rate, zenith, skymap).
- **AR skymap mode** — uses the device attitude quaternion streamed over
  BLE to overlay the accumulated muon flux on a phone-camera AR view
  (a "see the sky through muons" overlay).

```bash
python3 scripts/skylens_app.py --ble --device SkyLens
python3 scripts/skylens_app.py --wifi --host 192.168.4.1
python3 scripts/skylens_app.py --lifetime --ble --device SkyLens
python3 scripts/skylens_app.py --batch /mnt/sd/EVENTS/ev_*.csv
```

`scripts/skymap_proj.py` is a helper that converts an attitude quaternion
plus a reconstructed θ into a (az, zen) skymap cell and can render a
HEALPix-equivalent 64×32 cell skymap to PNG.

---

## 11. Assembly

See [`docs/assembly-guide.md`](docs/assembly-guide.md) for the full
step-by-step. In brief:

1. Solder the ESP32-S3-WROOM-1 module and the ADS7946 + REF5045.
2. Populate the power section: TP4056, MAX17048, AMS1117, TPS61158 boost.
3. Populate the analog front end: two OPA2356 TIAs, two TLV3501
   discriminators, the peak-hold + ADS7946 input network.
4. Populate the I²C peripherals: SSD1306 OLED, BMP390, ICM-42688-P,
   MAX17048.
5. Populate the microSD socket and the user buttons / LEDs.
6. Mechanically assemble the scintillator stack: the two EJ-200 tiles are
   held in a 3D-printed light-tight cage (`docs/tile_cage.stl`) with a
   30 mm spacer; each SiPM is optically coupled to its tile with a small
   dab of optical grease (Eljen EJ-550) and the whole stack is wrapped in
   PTFE tape (diffuse reflector) + black foil for light-tightness.
7. Flash the ESP32-S3 over USB-C.
8. Calibrate: see [`docs/calibration-guide.md`](docs/calibration-guide.md)
   (threshold scan, coincidence-window scan, pressure-barometric-coefficient
   fit, IMU attitude alignment).

---

## 12. Safety

This device generates up to **30 V** for the SiPM bias. Read
[`docs/safety-notes.md`](docs/safety-notes.md) before powering it on.

- The +30 V rail is **current-limited to 5 mA** by the TPS61158 — a fault
  (shorted SiPM, broken lead) cannot deliver dangerous current, but the
  voltage is enough to bite.
- `BIAS_EN` gates the boost and the rail is discharged through a 10 MΩ
  bleeder within 1 s of power-down; the firmware also forces the boost
  off on any fault (over-current, over-temperature, low battery).
- The scintillator and SiPM are **not** radioactive and present no
  radiological hazard; the device only *detects* cosmic rays.
- The LiPo has the usual TP4056 charge / over-discharge protection.

---

## 13. API Reference

See [`docs/api-reference.md`](docs/api-reference.md) for full firmware
API docs. Key functions:

- `acquisition_start(void)` — arm the detector and begin event collection.
- `acquisition_stop(void)` — disarm and flush buffers.
- `acquisition_status_t acquisition_get_status(void)` — IDLE / ARM /
  RUN / FAULT / SLEEP.
- `event_t *event_pop(void)` — pop the next coincidence event from the
  queue (or NULL).
- `skymap_t *skymap_get(void)` — the 64×32 az×zen histogram.
- `zenith_fit_t zenith_fit(const int *bins, int n)` — fit `cos²θ` and
  return I(0), χ².
- `float lifetime_fit(const int *delays, int n_bins, float bin_us,
  lifetime_result_t *out)` — exponential fit, returns τ_µ + error.
- `float pressure_correct(float rate, float p_hpa, float t_c)` — apply
  the barometric correction (returns corrected cpm).
- `ble_send_event(const event_t *ev)` — push an event frame over BLE.
- `sdlog_write_event(const event_t *ev)` — append to the daily CSV.
- `sdlog_write_daily(const skymap_t *m, const zenith_fit_t *z,
  const daily_t *d)` — write the daily JSON rollup.

---

## 14. What Makes It Different

| | Echo Mote (#8) | Hive Mind (#7) | Pulse Hound (#18) | **Sky Lens** |
|---|---|---|---|---|
| Domain | Room acoustics | Beehive health | RF hunting | **Astroparticle physics** |
| Stimulus | Swept-sine speaker | Passive | Passive | **The cosmos (passive)** |
| Sense | MEMS mic array | Load cell / temp / IR | Log RF detector | **Scintillator + SiPM** |
| Physics | Acoustic RT60 | Hive weight + bees | RF power vs angle | **Cosmic-ray muon flux** |
| Math | FFT / RT60 | Anomaly detection | Direction finding | **Coincidence + skymap + lifetime** |
| Output | Room report | Beehive health | RF bearing | **Muon flux / skymap / τ_µ** |

Sky Lens is the first device in this collection aimed at **particle
physics and cosmic-ray science** — a domain normally served by lab-grade
scintillator telescopes or desktop muon detectors costing $500–$2000,
here shrunk to a pocket instrument for ~$95 that anyone can build and
leave in a garden to watch the sky in muons.

---

## 15. License

MIT — build it, detect it, improve it. See repo root LICENSE.