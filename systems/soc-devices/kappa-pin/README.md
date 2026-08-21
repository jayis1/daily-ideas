# Kappa Pin — Pocket Transient Hot-Wire Thermal Conductivity & Diffusivity Meter

> **Bringing $2k–$15k benchtop/field thermal conductivity analyzers (Decagon KD2 Pro, C-Therm TCi, Hukseflux TP08, Thermonetics THW) down to ~$61 and pen size.**

Kappa Pin is a pocket-sized instrument that measures the **thermal conductivity (λ)**, **thermal diffusivity (α)**, **volumetric heat capacity (ρcₚ)**, and **thermal effusivity (e)** of liquids, soils, polymers, insulation, granular materials, building materials, and biological tissues using the **transient line-source (needle probe)** and **transient hot-wire (THW)** methods.

A thin probe containing a nichrome heater wire and a PT1000 RTD is inserted into (or immersed in) the material. A precisely controlled electrical heat pulse is applied, and the temperature rise vs. time is recorded at 24-bit resolution. The thermal conductivity is extracted from the slope of **ΔT vs. ln(t)** in the linear conduction regime:

```
λ = (Q / 4π) / (dΔT / d ln t)
```

where Q is the heat input per unit length (W/m). Thermal diffusivity is derived from the full transient curve fit, and volumetric heat capacity follows from **ρcₚ = λ/α**.

---

## Why thermal conductivity?

Thermal conductivity (λ, W·m⁻¹·K⁻¹) is one of the four fundamental transport properties of matter (along with viscosity, diffusivity, and electrical conductivity). It governs:

- **Building & insulation engineering** — R-value verification of foams, aerogels, fiberglass, phase-change materials
- **Geothermal & soil science** — ground heat exchanger design, permafrost monitoring, soil moisture inference
- **Food & pharmaceutical** — thermal process design, freeze-drying, shelf-life modeling
- **Polymer & composite R&D** — filler loading verification, crystallinity effects, thermal interface materials
- **Electronics packaging** — TIM (thermal interface material) characterization, potting compound selection
- **Energy storage** — phase-change material (PCM) characterization, battery thermal management
- **Refrigerants & nanofluids** — heat transfer fluid optimization

The transient line-source method is an **ASTM D5334** (soil) and **ASTM D7896** (hot-wire, liquids) standard method, and is the recommended technique for field measurements.

---

## Highlights

| Feature | Detail |
|---|---|
| Thermal conductivity range | 0.01–10 W·m⁻¹·K⁻¹ (covers air-like to metal-filled) |
| λ accuracy | ±3% typical (after calibration), ±5% worst-case |
| λ resolution | 0.001 W·m⁻¹·K⁻¹ |
| Thermal diffusivity range | 0.05–3.0 mm²/s |
| α accuracy | ±8% typical |
| Temperature range | −40 to +150 °C (probe-limited; PT1000 rated) |
| Temperature resolution | 0.001 °C (PT1000 4-wire + ADS122U04 24-bit) |
| Heat pulse power | 0.05–5 W programmable (constant power mode) |
| Heat pulse duration | 1–60 s programmable (auto-selected by material preset) |
| Sample rate | Up to 120 Hz during measurement |
| Probe types | 3 interchangeable: needle (soil/solid), hot-wire (liquid), surface (flat sheet) |
| Material presets | 6 built-in: liquid, wet soil, dry soil, polymer, insulation, metal powder |
| Measurement modes | Single-shot, continuous monitoring (every 60 s), QA mode (pass/fail vs. target λ) |
| Display | 1.3" OLED (SSD1306, 128×64) — live ΔT curve + ln(t) regression + results |
| Logging | MicroSD (FAT32) CSV + binary; BLE + Wi-Fi live streaming |
| Power | 18650 (3.7V, 3500 mAh) → 3.3V LDO; ~40 h battery or USB-C |
| Size | ~Ø28 × 160 mm (pen-sized) with probe |
| BOM cost | ~$61 (see `hardware/BOM.csv`) |

---

## SoC Architecture

```
                ┌──────────────────────────┐
                │   ESP32-S3-WROOM-1        │
  ┌─────────────│   dual-core Xtensa LX7    │──────────────┐
  │  BLE 5.0    │   240 MHz, 512KB SRAM     │   Wi-Fi 2.4  │
  │  Phone app  │   • ADC driver (ADS122U04)│   web UI     │
  │  live data  │   • heater PID power loop │   CSV export │
  │  commands   │   • λ/α regression engine │              │
  └─────────────┤   • OLED + SD + NVS       ├──────────────┘
                │   • WiFi/BLE stack        │
                └─────────────┬────────────┘
                              │ SPI / I²C / GPIO / UART
           ┌──────────────────┼──────────────────────┐
           ▼                  ▼                      ▼
  ┌────────────────┐  ┌───────────────┐    ┌──────────────┐
  │ ADS122U04      │  │ Heater current│    │ SSD1306 OLED │
  │ 24-bit ADC     │  │ source        │    │ 128×64 SPI   │
  │ SPI            │  │ MCP4131 +     │    └──────────────┘
  │ PT1000 4-wire  │  │ OPA548 + FET  │
  │ → temp to 1mK  │  │ → 0.05–5W     │
  └────────────────┘  └───────────────┘
```

- **ESP32-S3-WROOM-1** — Dual-core 240 MHz Xtensa LX7, 512 KB SRAM, 8 MB flash. Runs the measurement state machine, ADS122U04 SPI acquisition at 120 Hz, heater constant-power PID loop, ln(t) linear regression + diffusivity curve fit, OLED UI, SD logging, and BLE + Wi-Fi stacks. Single-chip design — no companion MCU needed.
- **ADS122U04** — 24-bit delta-sigma ADC (TI). Configured for 4-wire RTD measurement with 1 mA excitation current. Provides ~0.001 °C temperature resolution. SPI interface.
- **MCP4131-103E/P** — 10 kΩ digital potentiometer for programmable heater current. Combined with OPA548 power op-amp and IRFZ44N MOSFET for constant-power heater drive (0.05–5 W).

---

## Block Diagram

```
 ┌──────────┐    ┌─────────────┐    ┌───────────────────────┐    ┌──────────────┐
 │ 18650    │───►│ TP4056      │───►│ ESP32-S3-WROOM-1      │───►│ SSD1306 OLED │
 │ 3500mAh  │    │ charger +   │    │  main SoC             │    │ 1.3" 128×64  │
 │ 3.7V     │    │ 3.3V LDO    │    │                       │    └──────────────┘
 └──────────┘    └─────────────┘    └──────────┬────────────┘
       │                                      │ SPI
       │                            ┌─────────┴──────────┐
       │                            ▼                    ▼
       │                   ┌──────────────┐    ┌──────────────────┐
       │                   │ ADS122U04    │    │ MCP4131 digipot  │
       │                   │ 24-bit ADC   │    │ 10kΩ SPI         │
       │                   │ SPI @ 120Hz  │    └────────┬─────────┘
       │                   └──────┬───────┘             │
       │                          │ 4-wire              │ control
       │                          ▼                     ▼
       │                   ┌──────────────┐    ┌──────────────────┐
       │                   │ PT1000 RTD   │    │ OPA548 + IRFZ44N │
       │                   │ (in probe)   │    │ power stage      │
       │                   │ 4-wire       │    │ → heater wire    │
       │                   └──────────────┘    └────────┬─────────┘
       │                                                 │
       │                                    ┌────────────┘
       │                                    ▼
       │              ┌──────────────────────────────────────┐
       │              │  PROBE (interchangeable)              │
       │              │  ┌─────────────────────────────────┐  │
       │              │  │ Nichrome heater wire (R≈12Ω/m)   │  │
       │              │  │ PT1000 RTD (4-wire)              │  │
       │              │  │ Stainless hypodermic sheath      │  │
       │              │  │ 100mm × Ø1.5mm (needle probe)    │  │
       │              │  │ or bare (hot-wire for liquids)   │  │
       │              │  └─────────────────────────────────┘  │
       │              └──────────────────────────────────────┘
       │
       ├─► USB-C 5V charge
       │
       │    ┌────────────┐    ┌────────────┐    ┌──────────────┐
       └───►│ MicroSD    │    │ Tactile    │    │ Active       │
            │ FAT32 log  │    │ buttons×3  │    │ buzzer       │
            │ SPI        │    │ GPIO       │    │ GPIO/PWM     │
            └────────────┘    └────────────┘    └──────────────┘
```

---

## Pin Assignments (ESP32-S3-WROOM-1)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| GPIO3 | ADS122U04 CS | Output | SPI chip select (ADC) |
| GPIO4 | ADS122U04 DRDY | Input | Data-ready interrupt (falling edge) |
| GPIO5 | SPI CLK | Output | Shared SPI bus (ADC) |
| GPIO6 | SPI MISO | Input | Shared SPI bus (ADC) |
| GPIO7 | SPI MOSI | Output | Shared SPI bus (ADC) |
| GPIO8 | MCP4131 CS | Output | SPI chip select (digipot) |
| GPIO9 | OLED CS | Output | SPI chip select (display) |
| GPIO10 | OLED DC | Output | Data/Command |
| GPIO11 | OLED RESET | Output | Display reset |
| GPIO12 | HEATER_EN | Output | MOSFET gate enable (heater on/off) |
| GPIO13 | HEATER_SENSE | Input (ADC1) | Heater voltage monitor (power verification) |
| GPIO14 | BUTTON_MEASURE | Input | Start measurement (active low) |
| GPIO15 | BUTTON_MODE | Input | Cycle mode/material (active low) |
| GPIO16 | BUTTON_MENU | Input | Menu/select (active low) |
| GPIO17 | BUZZER | Output | PWM audio feedback |
| GPIO18 | SD CS | Output | MicroSD chip select |
| GPIO19 | USB_D- | I/O | USB-C data (native USB) |
| GPIO20 | USB_D+ | I/O | USB-C data (native USB) |
| GPIO21 | I2C_SCL | Output | Reserved (future I²C sensors) |
| GPIO35 | I2C_SDA | I/O | Reserved (future I²C sensors) |
| GPIO36 | STATUS_LED | Output | White status LED |
| GPIO37 | PROBE_DETECT | Input (ADC2) | Probe ID resistor divider |
| EN | Reset | Input | Power-on reset |

---

## Probe Design

Three interchangeable probe types connect via a 5-pin locking connector (heater+, heater−, RTD_exc+, RTD_sense+, RTD_sense−):

### 1. Needle Probe (NP-100) — soil, granular materials, polymers, semi-solids
- **Construction**: 18G stainless hypodermic needle, 100mm × Ø1.2mm
- **Internal**: Nichrome heater wire (36 AWG, ~12 Ω/m, 80mm active length ≈ 1.0 Ω) + PT1000 RTD (4-wire, centered)
- **Thermal grout**: thermally conductive epoxy (λ ≈ 1.4 W/m·K) fills needle for contact
- **Active length**: 80mm (heater + RTD co-located)
- **Insertion**: push into soil/material; minimal disturbance
- **Standard**: ASTM D5334

### 2. Hot-Wire Probe (HW-60) — liquids, gases, pastes
- **Construction**: Bare platinum-tungsten wire (25 µm Ø, 60mm length) on a fork frame
- **Wire resistance**: ~30 Ω at 25 °C (serves as both heater and sensor — R(T) calibrated)
- **Immersion**: fully submersible in liquid sample; PTFE support frame
- **Standard**: ASTM D7896 (transient hot-wire)
- **Note**: Uses single-wire mode — heater IS the sensor (resistance thermometry)

### 3. Surface Probe (SP-40) — flat sheets, building materials, films
- **Construction**: 40mm × 6mm Kapton flexible heater + PT1000 on flat contact face
- **Contact**: spring-loaded against surface (foam backing ensures contact pressure)
- **Use**: insulation panels, walls, composite laminates
- **Standard**: Modified hot-disk / surface line-source

### Probe ID
Each probe has an ID resistor (0Ω = needle, 10kΩ = hot-wire, 22kΩ = surface) in the connector, read via GPIO37 ADC divider. Firmware auto-selects measurement parameters.

---

## Measurement Theory

### Transient Line-Source Method

For an infinitely long line heat source of power per unit length **Q** (W/m) in an infinite homogeneous medium, the temperature rise at distance r from the source after time t is (Carslaw & Jaeger, 1959):

```
ΔT(t) = (Q / 4πλ) · [-γ - ln(4αt/r²) + O(r²/4αt)]    [r²/(4αt) << 1]
```

where:
- λ = thermal conductivity (W·m⁻¹·K⁻¹)
- α = thermal diffusivity (m²/s)
- γ = Euler-Mascheroni constant (0.5772)
- r = probe radius (negligible for needle probe at r << √(αt))

In the **linear regime** (typically 10–50s after pulse start, once r²/(4αt) << 1 and before boundary effects), ΔT is linear in ln(t):

```
ΔT(t) = (Q / 4πλ) · ln(t) + C
```

The slope **m = dΔT/d(ln t) = Q/(4πλ)** gives:

```
λ = Q / (4π · m)
```

### Thermal Diffusivity

The full curve (including the early-time quadratic term) is fitted to extract α:

```
ΔT(t) = (Q / 4πλ) · [ln(t) + ln(4α/r²) - γ]
```

By fitting ΔT vs. ln(t) and analyzing the intercept, or by nonlinear least-squares of the full model, α is recovered. Then:

```
ρcₚ = λ / α          (volumetric heat capacity, J·m⁻³·K⁻¹)
e = √(λ · ρcₚ)       (thermal effusivity, J·m⁻²·K⁻¹·s⁻⁰·⁵)
```

### Constant Power Control

The heater power Q (W/m) = V² / (R_heater · L_active), where L_active is the active heater length. Kappa Pin uses a constant-power control loop:

1. Measure heater resistance R_h(T) from the voltage across the heater and the known current
2. Adjust the digital potentiometer (MCP4131) to set the current source output
3. Maintain Q within ±1% throughout the pulse via a PI controller running at 100 Hz
4. Record V_heater and I_heater at each sample for exact Q computation

### Temperature Measurement

PT1000 4-wire RTD:
- Excitation: 1 mA constant current (ADS122U04 built-in IDAC)
- Resistance → temperature via Callendar-Van Dusen equation:
  ```
  R(T) = R₀(1 + A·T + B·T²)     for T > 0°C
  R(T) = R₀(1 + A·T + B·T² + C·(T-100)·T³)   for T < 0°C
  ```
  where A = 3.9083×10⁻³, B = -5.775×10⁻⁷, C = -4.183×10⁻¹²
- Resolution: ~0.001 °C at 24-bit / 1mA / 1× PGA
- Self-heating: < 0.01 °C at 1 mA (PT1000 dissipation ≈ 1 mW)

### Measurement Sequence

1. **Idle**: monitor probe temperature, wait for thermal equilibrium (drift < 0.01 °C/s for 10s)
2. **Baseline**: record T₀ for 5 seconds (60 samples at 12 Hz)
3. **Heat pulse**: apply constant power Q for duration t_pulse (10–30s, auto-selected)
   - Sample T at 120 Hz, V_heater at 120 Hz, I_heater at 120 Hz
4. **Cooling**: stop heating, continue sampling for 2× t_pulse
5. **Analysis**:
   - Compute ΔT = T(t) − T₀
   - Identify linear regime: iteratively find the ln(t) window where R² > 0.9998
   - Linear regression: ΔT = m·ln(t) + c → λ = Q/(4π·m)
   - Full curve fit for α (Levenberg-Marquardt, 20 iterations)
   - Compute ρcₚ and effusivity
6. **Display + log**: show λ, α, ρcₚ on OLED; write CSV to SD; BLE notify

### Error Sources & Mitigations

| Source | Effect | Mitigation |
|--------|--------|------------|
| Probe thermal contact resistance | Underestimates λ | Thermal grease fill; long probe (L/d > 50) |
| Finite probe length | Edge effects | Only use central 60% of data; L/d > 30 |
| Axial heat flow | Overestimates λ | Correction term (Blackwell, 1956) |
| Natural convection (liquids) | Overestimates λ | Short pulse (< 10s), small ΔT (< 2K), horizontal wire |
| Radiation (high-λ materials) | Negligible < 200°C | N/A for this range |
| Temperature drift | Bias in slope | Baseline subtraction + drift compensation |
| Power instability | Bias in Q | Constant-power PI loop, per-sample Q measurement |

---

## Material Presets

| Preset | λ range (W/m·K) | Power (W) | Pulse (s) | Sample rate (Hz) | Probe |
|--------|-----------------|-----------|-----------|-------------------|-------|
| Liquid | 0.1–0.7 | 0.3 | 8 | 120 | Hot-wire |
| Wet soil | 0.5–2.5 | 1.0 | 30 | 60 | Needle |
| Dry soil | 0.1–0.5 | 0.5 | 30 | 60 | Needle |
| Polymer | 0.1–0.5 | 0.5 | 20 | 60 | Needle |
| Insulation | 0.01–0.08 | 0.2 | 60 | 30 | Needle/surface |
| Metal powder | 1.0–10.0 | 3.0 | 10 | 120 | Needle |

---

## Firmware

The firmware is built with ESP-IDF v5.2+ and runs on the ESP32-S3-WROOM-1.

### Source layout

```
firmware/
├── CMakeLists.txt           # ESP-IDF project
├── sdkconfig.defaults       # Default configuration
├── main/
│   ├── CMakeLists.txt
│   ├── main.c               # Main application + state machine
│   ├── adc24.c / .h         # ADS122U04 SPI driver (24-bit RTD)
│   ├── heater.c / .h        # Constant-power heater control (PI loop)
│   ├── probe.c / .h         # Probe interface (RTD → temperature, ID detection)
│   ├── measurement.c / .h   # λ/α/ρcₚ computation (regression + LM fit)
│   ├── oled_display.c / .h  # SSD1306 OLED UI
│   ├── sd_logger.c / .h     # MicroSD CSV + binary logging
│   ├── ble_stream.c / .h    # BLE GATT data streaming
│   ├── wifi_web.c / .h      # Wi-Fi AP web UI + CSV download
│   ├── flash_store.c / .h   # NVS settings (calibration, presets)
│   ├── database.c / .h      # Material reference library
│   └── buttons.c / .h       # Debounced button input
```

### State machine

```
  ┌──────┐  button    ┌──────────┐  stable    ┌──────────┐  timeout
  │ IDLE │──────────►│  ARMING  │───────────►│ MEASURE  │──────────┐
  │      │           │ (equil.) │            │ (heating)│          │
  │      │◄──────────│          │   drift    │          │          │
  │      │  cancel   └──────────┘  >0.01K/s  └────┬─────┘          │
  │      │                                             │                │
  │      │          ┌──────────┐   done               ▼                │
  │      │◄─────────│  RESULT  │◄──────────────┌──────────┐            │
  │      │  button   │ (display)│               │ COOLING  │            │
  └──────┘           │  + log   │               │ (sample) │────────────┘
                     └──────────┘               └──────────┘
```

### Building

```bash
# Requires ESP-IDF v5.2+
cd firmware
idf.py set-target esp32s3
idf.py menuconfig    # optional
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

---

## BLE Interface

| UUID | Type | Description |
|------|------|-------------|
| 0x9101 | Service | Kappa Pin Service |
| 0x9102 | Notify | Temperature data stream (ΔT samples, 8 bytes each: ts_u16 + dT_x4_s16 + Q_x4_s16) |
| 0x9103 | Read/Notify | Measurement result (λ_f32 + α_f32 + rhocp_f32 + effusivity_f32 + status_u8) |
| 0x9104 | Write | Command (start/stop/set material/set power) |
| 0x9105 | Read | Device info (firmware version, probe type, calibration date) |

---

## SD Card Log Format

Each measurement produces a CSV file `KP_YYYYMMDD_HHMMSS.csv`:

```csv
# Kappa Pin measurement log
# Date: 2026-07-27T14:32:15Z
# Probe: NP-100 (needle)
# Material preset: wet_soil
# Power: 1.023 W
# Pulse duration: 30.0 s
# T0: 23.451 C
# Result: lambda=1.234 W/m.K, alpha=0.567 mm2/s, rhocp=2.176e6 J/m3.K, effusivity=1638 J/m2.K.s0.5
# Columns: t_s, T_C, dT_mK, V_heater_V, I_heater_A, Q_W
0.000,23.451,0.000,0.000,0.000,0.000
0.008,23.451,0.000,0.000,0.000,0.000
...
30.000,25.890,2439.000,1.012,1.010,1.021
...
90.000,24.120,669.000,0.000,0.000,0.000
# END
```

---

## Calibration

### Single-point calibration (glycerin reference)
Glycerin has a well-known λ = 0.292 W/m·K at 25 °C (NIST SRM 1469):

1. Immerse hot-wire probe in glycerin at 25 °C
2. Run measurement → obtain λ_measured
3. Calibration factor: **CF = 0.292 / λ_measured**
4. Store CF in NVS; applied to all future measurements

### Two-point calibration (glycerin + dry silica gel)
- Glycerin: λ = 0.292 W/m·K (low-λ point)
- Dry silica gel: λ = 0.020 W/m·K (very-low-λ point)
- Fit correction: λ_corrected = a·λ_measured + b

### Probe resistance calibration
- Measure heater wire resistance at 25 °C (4-wire)
- Measure PT1000 R₀ at 0 °C (ice bath)
- Store in NVS per probe

Run `scripts/calibrate.py` for guided calibration over BLE.

---

## Assembly Guide

See `docs/assembly_guide.md` for step-by-step build instructions, including:
- PCB fabrication (2-layer, 28×80mm)
- Probe construction (needle, hot-wire, surface)
- Firmware flashing
- Calibration procedure
- 3D-printed enclosure

---

## Comparison to Commercial Instruments

| Feature | Kappa Pin | Decagon KD2 Pro | C-Therm TCi | Hukseflux TP08 |
|---------|-----------|-----------------|-------------|----------------|
| Method | Transient line-source | Transient line-source | Modified transient plane source | Needle probe |
| λ range | 0.01–10 | 0.02–2 | 0.004–500 | 0.1–6 |
| Accuracy | ±3% | ±5% | ±1% | ±3% |
| Size | Ø28×160mm | Handheld | Benchtop | 600mm probe |
| Battery | 40h (18650) | 50h (AA×4) | N/A (AC) | N/A (datalogger) |
| Wireless | BLE+WiFi | None | None | None |
| Price | ~$61 | ~$1,900 | ~$8,000 | ~$2,500 |

Kappa Pin trades the very-high-λ range (>10 W/m·K) and ±1% accuracy of $8k benchtop units for portability, wireless connectivity, and 130× lower cost — sufficient for field work, education, and QC where ±3% is acceptable.

---

## License

MIT — build it, sell it, improve it.