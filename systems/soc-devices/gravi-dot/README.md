# Gravi Dot

**A handheld, battery-powered portable relative gravimeter that measures micro-gal (μGal) gravity anomalies using an ultra-low-noise MEMS accelerometer, thermal-stabilized reference, tilt and pressure correction, drift compensation, and GPS-stamped station surveying — for cave/void detection, archaeological prospection, mineral exploration, geothermal mapping, and geophysical education.**

---

## What It Does

The Gravi Dot is a pocket-sized **relative gravimeter** — an instrument that measures tiny local variations in Earth's gravitational acceleration (on the order of 10–500 μGal, where 1 Gal = 0.01 m/s² and Earth's mean g ≈ 981 000 000 μGal). A person walks a survey grid, sets the instrument down at each station, and the Gravi Dot records a 30-second averaged gravity reading with full environmental corrections, then tags it with GPS coordinates and stores it to SD. After the survey, the data is uploaded over BLE/Wi-Fi to a phone or laptop where a gravity-anomaly map (Bouguer/residual) is computed, revealing subsurface density variations: buried voids, caves, archaeological structures, mineral ore bodies, or geothermal reservoirs.

Professional relative gravimeters (Scintrex CG-6, Burris) cost $60 000–$120 000 and require trained operators. The Gravi Dot trades absolute accuracy (±20 μGal vs ±5 μGal) for a sub-$250 build and a 60-second learning curve, opening micro-gravity surveying to citizen scientists, university geophysics classes, cavers looking for new passages, and archaeologists doing rapid site assessment.

- **Ultra-low-noise MEMS accelerometer** — Analog Devices **ADXL355** 3-axis digital accelerometer, 20-bit resolution, noise density 25 μg/√Hz (= 245 μGal/√Hz), ±2 g range. Long-interval averaging (30 s at 250 Hz → 7 500 samples) achieves ~3 μGal repeatability per station in quiet conditions.
- **Thermal stabilization & correction** — the ADXL355 sits inside a thermally-damped copper enclosure with a multi-point DS18B20 temperature array (4 probes); the accelerometer's well-characterized temperature coefficient (≈ 0.5 mGal/°C) is calibrated out in firmware. A Peltier mini-heater + thermistor loop holds the sensor block at 35 ±0.05 °C.
- **Tilt compensation** — a precision MEMS inclinometer (**SCL3300-D01**, 0.001° resolution) measures instrument level; firmware applies the sine-cosine tilt correction for the 2-axis horizontal misalignment and rejects readings if tilt > 0.2°.
- **Drift correction** — MEMS accelerometers exhibit slow bias drift (~0.1–1 mGal/hour). The firmware uses a two-point drift model: the operator re-occupies the base station at the start and end of the loop (standard gravimetric practice), and firmware linearly interpolates the drift correction for every intermediate station.
- **Atmospheric & elevation correction** — an **MS5837-02BA** barometer measures local pressure for the free-air and atmosphere correction; GPS altitude feeds the Bouguer slab correction (2πGρh). The full correction chain (drift → free-air → Bouguer → latitude → tide) runs on-device.
- **GPS station tagging** — u-blox **NEO-M9N** receiver (72-channel, L1 C/A, 1 Hz) provides station coordinates and elevation; PPS signal discipline-synchronises the sampling window.
- **Earth-tide correction** — the firmware includes a simplified **Longman tide model** (lunar/solar gravitational tide can reach ±100 μGal diurnally) computed from GPS time and station latitude/longitude.
- **OLED survey display** — 1.3" SH1106 (128×64, I2C): current g (μGal), residual anomaly (μGal), station count, GPS fix, drift status, battery, temperature-stability indicator, and a scrolling mini-profile of the last 16 stations.
- **SD-card logging** — every station: timestamp, lat/lon/alt, raw 3-axis accel (mg), temperature (°C ×4), pressure (mbar), tilt (° ×2), corrected δg (μGal), corrections breakdown. FAT32, SPI mode.
- **BLE/Wi-Fi uplink** — ESP32-C3 streams station records over BLE GATT to a phone app and/or Wi-Fi CSV push to a laptop; companion Python script builds the anomaly map.
- **Dual processor** — STM32G474RET6 (Cortex-M4 @ 170 MHz with CORDIC/FPU for the heavy math and real-time sampling) + ESP32-C3 (BLE/Wi-Fi + GPS NMEA parse).
- **Battery** — 2 000 mAh LiPo, USB-C charging (MCP73831), ~8 hours of surveying (Peltier loop dominates consumption at ~120 mA).

### Use Cases

| Application | How Gravi Dot Helps |
|------------|---------------------|
| Cave / void detection | Walk a 10×10 m grid over suspected karst terrain; a 20–100 μGal low reveals an air-filled void 5–15 m below the surface — find new caves without digging |
| Archaeological prospection | Map buried chambers, tunnels, or foundations (e.g. pyramids, tell-mounds) before excavation; residual gravity lows reveal voids, highs reveal dense walls |
| Mineral exploration | Dense ore bodies (barite, massive sulfides, magnetite) produce gravity highs; map anomalies to guide drilling at 1/100th the cost of a commercial gravimeter |
| Geothermal exploration | Map low-density zones (hydrothermal alteration, magma heat sources) that feed geothermal reservoirs |
| Engineering geophysics | Detect subsurface voids or loose fill under planned construction sites; check for sinkhole risk in limestone areas |
| Volcanology | Monitor micro-gravity changes over time at a volcano — magma injection causes ±50 μGal changes detectable with repeated surveys |
| Education | University geophysics field courses — students run a real gravity survey and process the data, instead of reading about one in a textbook |
| Water-table mapping | The water table produces a density contrast; repeated surveys can track aquifer depletion or recharge |
| Glaciology | Ice thickness estimation from Bouguer anomalies on glaciers and ice caps |
| Caving / exploration | Real-time residual anomaly display lets explorers "see" whether a passage likely continues beyond a collapse — gravity lows beyond a blockage hint at open void |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              GRAVI DOT                                            │
│                                                                                   │
│   ┌───────────────────────────────────────────┐                                  │
│   │        STM32G474RET6                       │                                  │
│   │   (Cortex-M4 170 MHz, FPU, CORDIC,        │                                  │
│   │    512 KB flash, 112 KB SRAM,             │                                  │
│   │    4× ADC, 4× COMP, 2× DAC, HRTIM)        │                                  │
│   │                                           │                                  │
│   │   ┌─────────────────────────────────────┐ │     SPI        ┌──────────────┐  │
│   │   │ gravity-acquisition task            │◄┼────────────────┤  ADXL355     │  │
│   │   │ (250 Hz → 30 s stack → average)     │ │   (SPI, 20-bit)│  3-axis MEMS │  │
│   │   │                                     │ │                │  accel       │  │
│   │   │ thermal-stability watchdog          │ │                │  25 μg/√Hz   │  │
│   │   ├─────────────────────────────────────┤ │                └──────┬───────┘  │
│   │   │ tilt correction (SCL3300)           │◄┼──── SPI ───────┐      │ copper  │
│   │   │ sine/cosine g-projection            │ │                └──────┤ thermal │
│   │   ├─────────────────────────────────────┤ │                       │ block   │
│   │   │ temperature-coeff correction        │◄├── 1-Wire ×4 ───┐      │         │
│   │   │ (4× DS18B20 gradient array)         │ │               └──────┤ 35±0.05°C│
│   │   ├─────────────────────────────────────┤ │                       │ Peltier │
│   │   │ pressure / free-air correction      │◄├── I2C ─────────┐      │ + NTC   │
│   │   │ (MS5837-02BA)                       │ │               └──────┤ loop    │
│   │   ├─────────────────────────────────────┤ │                       └─────────┘
│   │   │ Longman earth-tide model            │ │
│   │   │ (GPS time → lunar/solar tide)       │ │
│   │   ├─────────────────────────────────────┤ │
│   │   │ drift correction (base-loop linear) │ │
│   │   ├─────────────────────────────────────┤ │
│   │   │ Bouguer / latitude correction       │ │
│   │   │ (CORDIC-accelerated)                │ │
│   │   ├─────────────────────────────────────┤ │
│   │   │ station manager / survey sequencer  │ │
│   │   ├─────────────────────────────────────┤ │     I2C        ┌──────────────┐  │
│   │   │ SH1106 OLED display driver          |◄├────────────────┤  SH1106      │  │
│   │   ├─────────────────────────────────────┤ │                │  128×64 OLED │  │
│   │   │ SD-card FAT32 logger                |◄├── SPI ─────────┤  microSD     │  │
│   │   ├─────────────────────────────────────┤ │                └──────────────┘  │
│   │   │ Peltier PID thermal loop            |◄├── PWM (HRTIM) ─┐                  │
│   │   │                                     | ├────────────────►│ DRV8833 → Peltier
│   │   └─────────────────────────────────────┘ │                └── NTC ADC feedback
│   │                                           │
│   │   UART2 ◄─────────────────────────────────┼──── ESP32-C3 (UART, 1 Mbps)
│   └───────────────────┬───────────────────────┘
│                       │ UART
│   ┌───────────────────┴───────────────────────┐
│   │     ESP32-C3 (RISC-V, WiFi 4, BLE 5)      │
│   │                                           │
│   │   • GPS NMEA parse (NEO-M9N, UART1)       │────── NEO-M9N GPS (L1, 72-ch)
│   │   • BLE GATT server (station records)     │────── phone app (nRF Connect)
│   │   • Wi-Fi CSV push (HTTP POST)            │────── laptop / cloud
│   │   • GPS PPS → STM32 GPIO for sync         │
│   └───────────────────────────────────────────┘
│
│   Power: 3.7 V 2000 mAh LiPo → MCP73831 USB-C charger → TPS63020 DC-DC (3.3 V)
│          + TPS63031 (5.0 V for Peltier)
│
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Schematic Overview

| Section | Key Parts | Notes |
|---------|-----------|-------|
| MCU core | STM32G474RET6 (LQFP64), 8 MHz XTAL, 32.768 kHz RTC XTAL | M4 @ 170 MHz, FPU + CORDIC for gravity math |
| Wireless | ESP32-C3-MINI-1 module | UART bridge to STM32; runs GPS parse + BLE + WiFi |
| Gravity sensor | ADXL355BCCZ (LCC-14), SPI @ 250 Hz | Sits in copper thermal block; SPI to STM32 |
| Thermal block | 4× DS18B20 (1-Wire), 10 kΩ NTC, TEC1-03004 Peltier, DRV8833 H-bridge | PID loop holds 35 °C ±0.05 °C; copper mass ≈ 40 g thermal ballast |
| Tilt sensor | SCL3300-D01 (SPI, 0.001°) | Mounted coplanar with ADXL355 on same PCB axis |
| Barometer | MS5837-02BA (I2C) | Free-air + atmosphere correction |
| GPS | u-blox NEO-M9N (UART, 1 Hz, PPS) | Station coordinates, elevation, time, tide model input |
| Display | SH1106 1.3" OLED (I2C) | Survey UI: g, residual, station #, GPS, battery |
| Storage | microSD socket (SPI mode, FAT32) | One CSV file per survey |
| Power | MCP73831 (USB-C charger), TPS63020 (3.3 V buck-boost), TPS63031 (5.0 V Peltier), DW01A protection | 2 000 mAh LiPo, USB-C, ~8 h survey |
| User input | 3 push-buttons (STATION, BASE, MENU) + rotary encoder | STATION marks a reading, BASE marks drift base, MENU navigates |

---

## Pin Assignments

### STM32G474RET6 (LQFP64)

| Pin | Function | Connection |
|-----|----------|------------|
| PA0  | ADC1_IN1  | NTC thermistor (Peltier feedback) |
| PA2  | USART2_TX | ESP32-C3 UART RX |
| PA3  | USART2_RX | ESP32-C3 UART TX |
| PA4  | SPI1_NSS  | ADXL355 CS |
| PA5  | SPI1_SCK  | ADXL355 SCK |
| PA6  | SPI1_MISO | ADXL355 SDO |
| PA7  | SPI1_MOSI | ADXL355 SDI |
| PA8  | GPIO_OUT  | ADXL355 DRDY interrupt |
| PA9  | GPIO_OUT  | SD card CS |
| PA10 | SPI2_SCK  | SD card SCK |
| PA11 | SPI2_MISO | SD card MISO |
| PA12 | SPI2_MOSI | SD card MOSI |
| PB0  | GPIO_OUT  | SCL3300 CS |
| PB1  | SPI1_SCK  | SCL3300 SCK (shared SPI1 bus, alt CS) |
| PB2  | SPI1_MISO | SCL3300 SDO |
| PB3  | SPI1_MOSI | SCL3300 SDI |
| PB4  | GPIO_IN   | SCL3300 DRDY |
| PB5  | HRTIM_CHA | DRV8833 IN1 (Peltier PWM) |
| PB6  | HRTIM_CHB | DRV8833 IN2 (Peltier direction) |
| PB7  | GPIO_OUT  | Status LED (green) |
| PB8  | GPIO_IN   | STATION button |
| PB9  | GPIO_IN   | BASE button |
| PB10 | I2C2_SCL  | SH1106 OLED SCL |
| PB11 | I2C2_SDA  | SH1106 OLED SDA |
| PB12 | GPIO_IN   | MENU button |
| PB13 | I2C1_SCL  | MS5837 SCL |
| PB14 | I2C1_SDA  | MS5837 SDA |
| PB15 | GPIO_IN   | GPS PPS (from ESP32-C3) |
| PC0  | GPIO_OUT  | 1-Wire bus (4× DS18B20) |
| PC1  | GPIO_OUT  | SD card power enable |
| PC4  | ADC2_IN1  | battery voltage divider (÷2) |
| PC6  | GPIO_OUT  | DRV8833 nSleep |
| PC13 | GPIO_OUT  | status LED (red, error) |
| PC14 | GPIO_IN   | rotary encoder A |
| PC15 | GPIO_IN   | rotary encoder B |
| PF0  | GPIO_IN   | USB-C VBUS detect |
| PF1  | GPIO_OUT  | USB-C charge enable |

### ESP32-C3-MINI-1

| Pin | Function | Connection |
|-----|----------|------------|
| GPIO0  | UART0_TX  | NEO-M9N GPS RX |
| GPIO1  | UART0_RX  | NEO-M9N GPS TX |
| GPIO2  | GPIO_IN   | NEO-M9N PPS → STM32 PB15 |
| GPIO3  | UART1_TX  | STM32 PA3 (RX) |
| GPIO4  | UART1_RX  | STM32 PA2 (TX) |
| GPIO5  | GPIO_OUT  | NEO-M9N EXTINT (wake) |
| GPIO6  | GPIO_OUT  | status LED (blue, BLE) |
| GPIO8  | strapping | pulled down (normal boot) |
| GPIO9  | strapping | pulled up (normal boot) |

---

## Power Architecture

```
                    USB-C 5V
                      │
              ┌───────┴───────┐
              │  MCP73831     │   LiPo charger (4.2 V, 500 mA)
              │  + DW01A      │   battery protection
              └───────┬───────┘
                      │  3.0–4.2 V
                ┌─────┴──────┐
                │ LiPo 2000  │
                │ mAh        │
                └─────┬──────┘
                      │
           ┌──────────┼──────────────┐
           │          │              │
   ┌───────┴──────┐  ┌┴───────────┐  │
   │ TPS63020     │  │ TPS63031   │  │
   │ buck-boost   │  │ buck-boost │  │
   │ → 3.3 V/2A   │  │ → 5.0 V/1A │  │
   └───────┬──────┘  └─────┬──────┘  │
           │               │         │
    [3.3 V rail]     [5.0 V rail]    │
    STM32, ESP32,    DRV8833 →       │
    sensors, OLED    Peltier         │
    SD, GPS          (120 mA)        │

  Battery: 3.7 V × 2000 mAh = 7.4 Wh
  Loads: 3.3 V rail ≈ 60 mA avg
         5.0 V rail (Peltier PID) ≈ 120 mA avg (duty-cycled)
         Total ≈ 180 mA → ~11 h (8 h with Peltier overhead + margin)
```

---

## Gravity Correction Pipeline

The Gravi Dot applies the full standard gravimetric correction chain on-device. Each station reading passes through:

1. **Raw average** — 7 500 samples at 250 Hz over 30 s; reject outliers > 3σ; compute mean of vertical axis (z) and horizontal (x, y).
2. **Tilt projection** — compute true vertical g from 3-axis using the SCL3300 tilt angles:
   `g_vert = g_z·cos(θx)·cos(θy) + g_x·sin(θx) + g_y·sin(θy)` where θx, θy are tilt angles.
3. **Temperature correction** — apply calibrated ADXL355 bias temperature coefficient: `Δg_temp = k_T × (T_sensor − T_cal)`, where k_T ≈ 0.5 mGal/°C (measured in factory calibration).
4. **Pressure correction** — atmospheric gravity effect: `Δg_atm = 0.3 μGal/hPa × (P − P_ref)`.
5. **Drift correction** — linear interpolation between base-station readings at survey start and end: `Δg_drift(t) = (g_base_end − g_base_start) × (t − t_base_start) / (t_base_end − t_base_start)`.
6. **Latitude correction** — normal gravity formula (WGS84):
   `γ₀ = 978032.677 × (1 + 0.00193185138639·sin²φ) / √(1 − 0.00669437999014·sin²φ)` in mGal.
7. **Free-air correction** — `Δg_FA = +0.3086 mGal/m × h` (h = GPS elevation in metres).
8. **Bouguer correction** — `Δg_B = −0.04191 × ρ × h` mGal (ρ = crustal density, default 2670 kg/m³).
9. **Earth-tide correction** — Longman lunar/solar tide formula (simplified): up to ±100 μGal, computed from GPS time, station lat/lon, and the positions of the Sun and Moon.
10. **Residual anomaly** — `δg = g_corrected − γ₀ − Δg_FA − Δg_B` — the final value displayed and logged.

The CORDIC unit on the STM32G474 accelerates the `sin`/`cos`/`√` operations in the latitude and tilt corrections.

---

## Firmware

The firmware is written in C using the STM32Cube HAL and FreeRTOS. It is organized into the following tasks:

| Task | Priority | Function |
|------|----------|----------|
| `gravity_task` | High | 250 Hz SPI reads from ADXL355, 30 s stack averaging, outlier rejection |
| `thermal_task` | High | PID loop (10 Hz) for Peltier → 35 °C ±0.05 °C |
| `correction_task` | Medium | Runs the full correction pipeline when a station is marked |
| `display_task` | Medium | 10 Hz OLED refresh — g, residual, station list, GPS, battery |
| `gps_task` | Medium | ESP32-C3 UART protocol: parse GPS packets, sync PPS |
| `sdlog_task` | Low | FAT32 file writes (one CSV per survey) |
| `ble_task` | Low | BLE GATT notifications on new station (via ESP32-C3) |

### Building

```bash
cd firmware
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../cmake/gcc-arm-none-eabi.cmake ..
make -j8
# Flash:
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
        -c "program gravi_dot.elf verify reset exit"
```

### ESP32-C3 companion firmware

```bash
cd firmware/esp32c3
idf.py set-target esp32c3
idf.py build flash monitor
```

---

## Bill of Materials

See `hardware/BOM.csv` for the full Digi-Key/Mouser part numbers.

| Ref | Part | Qty | Unit (USD) | Notes |
|-----|------|-----|-----------|-------|
| U1 | STM32G474RET6 | 1 | 7.20 | Main MCU |
| U2 | ESP32-C3-MINI-1 | 1 | 2.70 | Wireless + GPS parse |
| U3 | ADXL355BCCZ | 1 | 18.50 | Ultra-low-noise MEMS accelerometer |
| U4 | SCL3300-D01 | 1 | 9.80 | Precision inclinometer |
| U5 | MS5837-02BA | 1 | 5.40 | Barometric pressure |
| U6 | NEO-M9N | 1 | 14.00 | GPS receiver |
| U7 | SH1106 OLED 1.3" | 1 | 3.50 | 128×64 display |
| U8 | MCP73831 | 1 | 0.60 | LiPo charger |
| U9 | TPS63020 | 1 | 3.90 | 3.3 V buck-boost |
| U10 | TPS63031 | 1 | 3.40 | 5.0 V buck-boost |
| U11 | DRV8833 | 1 | 1.80 | Peltier H-bridge |
| U12 | DW01A + FS8205A | 1 | 0.30 | Battery protection |
| Q1–Q4 | DS18B20 | 4 | 1.20 | Temperature array |
| M1 | TEC1-03004 Peltier | 1 | 2.50 | 3×3 mm, 0.4 A |
| BAT1 | LiPo 2000 mAh | 1 | 6.00 | 3.7 V, 503040 |
| J1 | USB-C 2.0 | 1 | 0.50 | Charging + data |
| J2 | microSD socket | 1 | 0.80 | SPI mode |
| SW1–SW3 | Tactile buttons | 3 | 0.15 | STATION/BASE/MENU |
| ENC1 | EC11 rotary encoder | 1 | 0.80 | Menu navigation |
| Misc | passives, PCB, copper block, enclosure | 1 | 12.00 | |
| **Total** | | | **~$97** | |

---

## Physical Design

The Gravi Dot is housed in a **106×55×28 mm** machined aluminium enclosure (anodized). The ADXL355 + SCL3300 sit on a small daughterboard inside a **copper thermal mass** (40 g, 30×30×15 mm) mounted on silicone vibration isolators. The Peltier element sits between the copper mass and the aluminium case (which acts as the heat sink). This provides both thermal stability and mechanical isolation from hand vibration.

The instrument sits on three **levelling feet** (adjustable M3 thumb-screws) for station setup. A small **bullseye bubble level** is centred on the top face for coarse levelling; the SCL3300 provides precision tilt data.

---

## Field Survey Procedure

1. **Power on** — wait 60 s for thermal block to stabilize at 35 °C (OLED shows "STABILIZING…").
2. **Base reading** — set the instrument on the base station, level it, press **BASE**. The Gravi Dot records the first base reading (time, g, GPS).
3. **Survey loop** — walk to each station, set down, level, press **STATION**. A 30 s reading is taken, fully corrected, and logged. The OLED shows the residual anomaly vs. base.
4. **Close the loop** — return to the base station, press **BASE** again. The firmware computes the drift rate and applies it retroactively to all stations.
5. **Upload** — connect over BLE or Wi-Fi; the companion Python script downloads all stations and produces a **gravity-anomaly contour map** (matplotlib).

---

## Companion Software

`scripts/gravi_dot_plot.py` — reads the survey CSV, applies any additional processing, and produces a contour map + residual profile:

```bash
python3 scripts/gravi_dot_plot.py survey_001.csv --rho 2670 --output map.png
```

---

## Limitations & Honest Notes

- **Not an absolute gravimeter.** The Gravi Dot measures *relative* gravity differences between stations. It cannot give you the absolute value of g to FG5-precision. Its strength is spatial anomaly mapping.
- **MEMS noise floor.** The ADXL355 is the best low-noise MEMS accelerometer available at this price, but it is still ~100× noisier than a spring-based Scintrex sensor per sample. We compensate by long averaging (30 s) and thermal stabilization. Repeatability is ~20 μGal (1σ) under good conditions (still air, stable temperature, solid ground).
- **Vibration sensitivity.** Micro-gravity measurements are extremely sensitive to ground vibration (traffic, wind, footsteps). The Gravi Dot includes a vibration-quality metric (RMS of the 30 s stack) and flags noisy readings. Best results are obtained in quiet, calm conditions.
- **Drift.** MEMS accelerometers drift more than spring/fused-quartz sensors. The base-loop method corrects linear drift; non-linear drift limits loop duration to ~2–3 hours. For long surveys, re-occupy the base every 30–45 minutes.
- **Calibration required.** The ADXL355 bias temperature coefficient and scale factor must be calibrated once per unit (the firmware includes a calibration mode that sweeps temperature and fits the coefficient). Pre-built units ship calibrated.

---

## License

MIT — build it, use it, improve it. If you find a cave with it, name it after the dog.

---

*Invented as device #23 in the SoC Device Inventions collection.*