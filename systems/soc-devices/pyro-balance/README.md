# Pyro Balance — Pocket Thermogravimetric Analyzer (TGA)

> **Bringing $15k–$50k benchtop thermogravimetric analyzers (TA Q500, Mettler TGA/DSC, Netzsch TG 209) down to ~$81 and coffee-mug size.**

Pyro Balance is a pocket thermogravimetric analyzer (TGA) that measures the **mass change** of a small sample (2–50 mg) as it is heated through a programmable temperature profile (RT–600 °C), producing the classic **thermogravimetric (TG) curve** (mass % vs temperature) and its derivative (**DTG**). From the TG/DTG curves it extracts:

- **Moisture / volatile / filler content** (mass-loss steps)
- **Onset / peak / endset temperatures** of each decomposition step
- **Step magnitude** (mass %) per decomposition event
- **Residual mass** (ash / char / filler at final temperature)
- **Decomposition kinetics**: Kissinger / Ozawa–Flynn–Wall activation energy from multi-heating-rate runs
- **Oxidative vs inert atmosphere** comparison (with optional purge pump)

TGA is the complementary technique to DSC (the repo's *Thermo Trace* device measures heat flow; Pyro Balance measures mass change). Together they form the two pillars of thermal analysis, used for polymer identification, filler content QC, moisture/solvent residuals, thermal stability, oxidation onset, and additive decomposition.

## Highlights

| Feature | Detail |
|---|---|
| Sample mass | 2–50 mg (typical 5–20 mg) |
| Mass resolution | ~5 µg (with 5 g load cell + HX711 + 32× averaging) |
| Temperature range | RT → 600 °C (crucible); balance compartment < 55 °C |
| Heating rates | 0.5–20 °C/min programmable; isothermal hold; multi-segment ramps |
| Atmosphere | Ambient air; optional N₂ purge via micro diaphragm pump + flow sensor |
| Temperature sensor | PT1000 RTD (4-wire) + ADS122U04 24-bit ADC, 0.05 °C resolution |
| Balance | 5 g foil-strain load cell + HX711 24-bit ADC, alumina hang-down rod |
| Furnace | Nichrome heating coil on alumina ceramic tube, MOSFET PWM drive, PID control |
| Safety | 250 °C thermal fuse on balance bay + TLV3201 comparator + IWDG + cold-junction alarm |
| Display | 1.3" OLED (SSD1306, 128×64) live TG/DTG curve + status |
| Logging | MicroSD (FAT32) CSV + binary; BLE + Wi-Fi live streaming via ESP32-C3 |
| Power | 2× 18650 (7.4 V) → 5 V buck + 12 V boost for furnace; ~2.5 h battery or USB-C |
| Size | ~Ø70 × 110 mm (coffee-mug size) |
| BOM cost | ~$81 (see `hardware/BOM.csv`) |

## SoC Architecture

```
                ┌──────────────────────┐    UART (115200)
  ┌─────────────┤   ESP32-C3-MINI-1    │◄─────────────────┐
  │  BLE/Wi-Fi  │  BLE + Wi-Fi uplink   │                  │
  │  Phone/PC   │  SD-over-SPI proxy?   │                  │
  └─────────────┴──────────────────────┘                  │
                                                            │
  ┌──────────────────────┐  I²C/SPI/ADC/PWM/UART ──────────┤
  │  STM32G474RET6        │                                 │
  │  main control SoC     │                                 │
  │  • PID furnace loop   │                                 │
  │  • HX711 balance poll │                                 │
  │  • TG/DTG analysis    │                                 │
  │  • OLED + SD + safety │                                 │
  └──────────────────────┘
```

- **STM32G474RET6** — 170 MHz Cortex-M4F, 128 KB Flash, 32 KB SRAM, rich analog (5× ADC, 4× DAC, CORDIC, FMAC), HRTIM for high-res PWM. Runs the furnace PID loop, balance acquisition, TG/DTG computation, OLED, SD, safety, and speaks to the radio.
- **ESP32-C3-MINI-1** — RISC-V Wi-Fi/BLE, offloads wireless: BLE GATT streaming + Wi-Fi captive-portal plotter / CSV download. Communicates with the STM32 over UART.

## Block Diagram

```
 ┌──────────┐   ┌─────────────┐   ┌──────────────┐    ┌──────────────┐
 │ 18650×2  │──►│ 5V buck     │──►│ STM32G474    │───►│ SSD1306 OLED │
 │ 7.4V     │   │ + 12V boost │   │  RET6        │    └──────────────┘
 └──────────┘   └─────────────┘   └──────┬───────┘
       │           │    │                  │ I²C/SPI/UART/GPIO
       │           │    └─► Nichrome       │
       │           │        furnace (12V)  ├─► HX711 (balance) ──► 5 g load cell ──► alumina rod ──► crucible (in furnace)
       │           │                        ├─► ADS122U04 (PT1000 4-wire) ──► furnace temp
       │           │                        ├─► MOSFET (furnace PWM drive)
       │           │                        ├─► BME280 (ambient comp)
       │           │                        ├─► SFM3300 (purge flow) + pump PWM
       │           │                        ├─► MicroSD SPI
       │           │                        ├─► TLV3201 over-temp comparator
       │           │                        ├─► 250°C thermal fuse (hardware cut)
       │           │                        └─► UART ──► ESP32-C3 ──► BLE/Wi-Fi
       │           └─► USB-C 5V (alt power / charging)
```

## Pin Assignments (STM32G474RET6, LQFP64)

| Pin | Function | Detail |
|-----|----------|--------|
| PA0  | ADC1_IN1  | HX711 A-rate / not used (HX711 is serial) |
| PA1  | GPIO_OUT  | HX711 SCK (clock) |
| PA2  | GPIO_IN   | HX711 DOUT (data) |
| PA3  | GPIO_OUT  | HX711 RATE (80 Hz) |
| PA4  | DAC1_OUT1 | Furnace MOSFET setpoint (analog fallback) |
| PA5  | GPIO_OUT  | Furnace MOSFET PWM (HRTIM CHA1, 20 kHz) |
| PA6  | GPIO_OUT  | Purge pump PWM (TIM3 CH1, 1 kHz) |
| PA7  | GPIO_OUT  | Status LED (white) |
| PA8  | GPIO_OUT  | Heater-enable relay (safety cut) |
| PA9  | USART1_TX | → ESP32-C3 RX |
| PA10 | USART1_RX | ← ESP32-C3 TX |
| PA11 | GPIO_IN   | TLV3201 comparator output (over-temp) |
| PA12 | GPIO_OUT  | Buzzer (alarm) |
| PA13 | SWDIO     | Debug |
| PA14 | SWCLK     | Debug |
| PA15 | GPIO_IN   | Thermal-fuse sense (open = blown) |
| PB0  | ADC1_IN9  | Battery voltage divider (×0.25) |
| PB1  | GPIO_OUT  | OLED reset |
| PB3  | SPI1_SCK  | SD card + OLED (shared, CS-gated) |
| PB4  | SPI1_MISO | SD card |
| PB5  | SPI1_MOSI | SD card + OLED |
| PB6  | GPIO_OUT  | SD CS |
| PB7  | GPIO_OUT  | OLED CS (SPI) |
| PB8  | I2C1_SCL  | BME280 + SFM3300 + ADS122U04 (ADS on own bus, see below) |
| PB9  | I2C1_SDA  | (same) |
| PB10 | I2C2_SCL  | ADS122U04 (dedicated) — PT1000 4-wire |
| PB11 | I2C2_SDA  | (same) |
| PB12 | GPIO_OUT  | ADS122U04 CS (if SPI variant) / not used (I²C) |
| PB13 | GPIO_IN   | Button: START |
| PB14 | GPIO_IN   | Button: STOP |
| PB15 | GPIO_IN   | Button: MENU |
| PC6  | GPIO_OUT  | ESP32-C3 BOOT/RST (reset line) |
| PC13 | GPIO_IN   | Tilt/interlock (reed) |
| PC14 | GPIO_OUT  | Purge valve (N₂) |
| PC15 | GPIO_OUT  | Fan (balance-bay cooling) |

## Power Architecture

```
 18650 ×2 (7.4 V, ~3500 mAh)
   │
   ├─► MP1584 buck → 5 V / 1.5 A  (logic rail: STM32, ESP32-C3, OLED, SD, sensors)
   ├─► MT3608 boost → 12 V / 1.2 A (furnace nichrome coil, ~8 W peak)
   └─► USB-C (TP4056 charger) → charge 18650s; 5 V input can also run without battery

 Fuse: 250 °C thermal fuse in series with 12 V furnace rail (physical cut above 250 °C near balance)
```

The furnace is a ~6 Ω nichrome coil on an alumina tube; at 12 V that's ~2 A / 24 W — we throttle to ~8 W average via PID duty. Battery life ~2.5 h at full heating rate.

## Thermogravimetric Measurement Theory

TGA tracks sample mass `m(T, t)` while the furnace executes a temperature program `T(t)`. The key outputs:

- **TG curve**: `m(T)` normalized to initial mass `m₀` → mass %.
- **DTG curve**: `dm/dt` (or `dm/dT` divided by heating rate β) — peaks mark decomposition steps.
- **Step detection**: DTG peak finding → onset (extrapolated), peak temperature `T_p`, endset, and integrated mass loss `Δm` per step.
- **Residual mass**: mass at final temperature (ash/char/filler).
- **Kinetics (multi-rate)**: run at β₁, β₂, β₃ (e.g., 2/5/10 °C/min). Kissinger equation:
  ```
  ln(β/T_p²) = ln(AR/E) − E/(R·T_p)
  ```
  Plotting `ln(β/T_p²)` vs `1/T_p` gives activation energy `E` from the slope. Ozawa–Flynn–Wall uses `ln(β)` vs `1/T_p`.

Full derivation in `docs/measurement_theory.md`.

## Atmosphere Control

- **Default**: ambient air (oxidative). The furnace tube is open to air via the crucible top.
- **Inert**: optional N₂ purge via a micro diaphragm pump + SFM3300 flow sensor; a solenoid valve selects N₂ line. Flow setpoint ~50 mL/min.
- Switching atmosphere mid-run (e.g., N₂ then air) reveals oxidative stability.

## Calibration

1. **Mass**: 2-point — zero (no crucible) + 5 g reference weight. HX711 offset/scale stored in flash.
2. **Temperature**: ice bath (0 °C) + boiling water (100 °C) PT1000 two-point; optional indium melt (156.6 °C) for a third point. RTD Callendar–Van Dusen correction.
3. **Furnace lag**: measure crucible-vs-furnace RTD offset once; store as `T_lag` correction.
4. **Buoyancy blank**: run empty crucible through the same program → subtract buoyancy/flow force curve from sample runs (standard TGA practice).

See `scripts/calibrate.py`.

## On-Device Analysis

- 10 Hz mass sampling, 1 Hz temperature, downsampled to 1 Hz for the TG curve.
- Moving-average smoothing (Savitzky–Golay, window 7) on mass.
- DTG = centered finite difference of smoothed mass ÷ `dt`.
- Peak detection: threshold = mean(DTG) + k·std (k configurable, default 4), refractory 30 s.
- Per-step onset/peak/endset via DTG peak + tangent intercepts.
- Step mass loss via integral of DTG over the step window.
- Multi-rate Kissinger fit when ≥3 runs share a `method_id`.

## Firmware

Firmware is split:

- `firmware/` — STM32G474 application (HAL + bare-metal scheduler), buildable with `arm-none-eabi-gcc` + a simple Makefile (or CMake). Keil `.ioc`-style config in `firmware/Makefile`.
- `firmware/esp32-c3/` — ESP-IDF app providing BLE GATT + Wi-Fi captive plotter, UART bridge to STM32.

Key modules (STM32 side):

| File | Purpose |
|------|---------|
| `main.c` | Scheduler, state machine, mode dispatch |
| `furnace.c/h` | PID temperature control, ramp generator, safety cut |
| `balance.c/h` | HX711 driver, mass acquisition, tare, buoyancy blank |
| `ads122u04.c/h` | 24-bit ADC driver for PT1000 4-wire RTD |
| `tga.c/h` | TG/DTG computation, step detection, kinetics |
| `bme280.c/h` | Ambient T/P/H compensation |
| `oled_display.c/h` | SSD1306 driver, live TG/DTG plot |
| `sd_logger.c/h` | FATFS CSV + binary logging |
| `safety.c/h` | Thermal fuse, comparator, IWDG, interlock |
| `esp32_link.c/h` | UART protocol to ESP32-C3 |
| `purge.c/h` | Pump + valve + flow control |
| `flash_store.c/h` | NV parameters (calibration, methods) |

## Usage

1. Tare the empty crucible (MENU → Tare). Insert sample (5–20 mg).
2. Select a method (heating profile + atmosphere) or use default.
3. START. Pyro Balance ramps, logs to SD, streams over BLE, and plots live on OLED.
4. STOP / auto-end at final temperature. Results: steps, residual %, kinetics.
5. Phone app (`scripts/live_stream.py`) plots and exports CSV; `scripts/analyze_tga.py` does offline kinetics.

## Repository Layout

```
pyro-balance/
├── README.md
├── schematic/pyro-balance.kicad_sch
├── firmware/
│   ├── Makefile
│   ├── Core/Src/*.c, Core/Inc/*.h
│   ├── esp32-c3/ (ESP-IDF)
├── hardware/BOM.csv
├── docs/
│   ├── assembly_guide.md
│   ├── api_reference.md
│   └── measurement_theory.md
└── scripts/
    ├── calibrate.py
    ├── live_stream.py
    └── analyze_tga.py
```

## License

MIT — build it, sell it, improve it.