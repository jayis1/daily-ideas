# Dent Scope — Pocket Instrumented Indentation Tester

> **Bringing $15k–$40k benchtop instrumented indentation / nanoindentation systems (FischerScope HM2000, Anton Paar MHT, MTS Nanoindenter, Bruker Hysitron TI) down to ~$85 and large-pen size.**

Dent Scope is a pocket instrumented indentation tester that presses a diamond or tungsten-carbide tip into a surface under precise load control while simultaneously measuring indentation depth at sub-micron resolution, producing the classic **load–displacement (P–h) curve**. From the P–h curve it extracts:

- **Martens hardness (HM)** — total deformation hardness under load
- **Vickers hardness (HV)** — from the contact area at peak load
- **Brinell hardness (HB)** — from ball-indentation contact area
- **Reduced elastic modulus (E_r)** and **Young's modulus (E)** via the Oliver–Pharr method
- **Creep behavior** — depth-vs-time during a load hold
- **Strain-rate sensitivity** — from variable loading rates
- **Plastic / elastic work ratio (η)** — elastic recovery fraction
- **30-material identification** — k-NN matching against a flash library of H/E pairs

Instrumented indentation (depth-sensing indentation) is the standard method for measuring local mechanical properties of metals, ceramics, polymers, coatings, thin films, and composites. It is used in materials science, metallurgy, coating QC, microelectronics packaging, additive manufacturing, and failure analysis. Benchtop systems cost $15k–$40k+; Dent Scope brings the technique to the field for ~$85 in a pen-sized device.

## Highlights

| Feature | Detail |
|---|---|
| Force range | 0.05–20 N (load-controlled) |
| Force resolution | ~0.5 mN (with 20 N foil-strain load cell + HX711 24-bit + 16× averaging) |
| Depth range | 0.5–200 µm |
| Depth resolution | ~11 nm (capacitive parallel-plate sensor + AD7746 24-bit CDC) |
| Loading rates | 0.01–5 N/s programmable; constant strain-rate mode |
| Indenter tips | Vickers (136° diamond pyramid), Berkovich, WC ball 1 mm (Brinell) — interchangeable |
| Tip approach | 28BYJ-48 geared stepper + M4×0.35 leadscrew, 1/8 microstep ≈ 1.75 µm/step |
| Frame compliance | <0.5 µm/N, software-corrected from capacitive sensor (direct depth) |
| Temperature | DS18B20 sample temperature for modulus correction |
| Orientation | ICM-42688-P IMU for leveling (indentation must be normal to surface) |
| Safety | 25 N mechanical over-travel clutch + software force limit + IWDG + stall-detect |
| Display | 1.3" OLED (SSD1306, 128×64) live P–h curve + results |
| Logging | MicroSD (FAT32) CSV + binary; BLE + Wi-Fi live streaming via ESP32-C3 |
| Power | 2× 18650 (7.4 V) → 5 V buck; ~4 h battery or USB-C |
| Size | ~Ø34 × 180 mm (large pen / small flashlight) |
| BOM cost | ~$85 (see `hardware/BOM.csv`) |

## SoC Architecture

```
                ┌──────────────────────┐    UART (115200)
  ┌─────────────┤   ESP32-C3-MINI-1    │◄─────────────────┐
  │  BLE/Wi-Fi  │  BLE + Wi-Fi uplink   │                  │
  │  Phone/PC   │  web plotter / CSV    │                  │
  └─────────────┴──────────────────────┘                  │
                                                            │
  ┌──────────────────────┐  I²C/SPI/ADC/PWM/UART ──────────┤
  │  STM32G474RET6        │                                 │
  │  main control SoC     │                                 │
  │  • stepper + leadscrew│                                 │
  │  • HX711 force loop   │                                 │
  │  • AD7746 depth loop  │                                 │
  │  • Oliver–Pharr math  │                                 │
  │  • OLED + SD + safety │                                 │
  └──────────────────────┘
```

- **STM32G474RET6** — 170 MHz Cortex-M4F, 128 KB Flash, 32 KB SRAM, rich analog (5× ADC, CORDIC, FMAC), HRTIM for stepper microstep PWM. Runs the force/depth acquisition loop at 500 Hz, the loading-rate PID, Oliver–Pharr computation, OLED, SD, safety, and speaks to the radio.
- **ESP32-C3-MINI-1** — RISC-V Wi-Fi/BLE, offloads wireless: BLE GATT streaming + Wi-Fi captive-portal P–h plotter / CSV download. Communicates with the STM32 over UART.

## Block Diagram

```
 ┌──────────┐   ┌─────────────┐   ┌──────────────┐    ┌──────────────┐
 │ 18650×2  │──►│ 5V buck     │──►│ STM32G474    │───►│ SSD1306 OLED │
 │ 7.4V     │   │ MP1584      │   │  RET6        │    └──────────────┘
 └──────────┘   └─────────────┘   └──────┬───────┘
      │                                │ I²C/SPI/UART/GPIO
      │                                ├─► DRV8833 ──► 28BYJ-48 stepper ──► M4×0.35 leadscrew ──► indenter tip
      │                                ├─► HX711 (force) ──► 20 N load cell ──► indenter shaft
      │                                ├─► AD7746 I²C (capacitance) ──► parallel-plate depth sensor
      │                                ├─► DS18B20 1-wire (sample temp)
      │                                ├─► ICM-42688-P SPI (IMU leveling)
      │                                ├─► MicroSD SPI
      │                                ├─► Over-travel clutch GPIO (stall detect)
      │                                └─► UART ──► ESP32-C3 ──► BLE/Wi-Fi
      └─► USB-C 5V (TP4056 charger)

 Reference ring (contacts sample surface):
   ├── capacitive sensor fixed plate (AD7746 measures gap to indenter shaft)
   └── provides reference for depth measurement (frame-compliance free)
```

## Mechanical Design

```
         ┌──────────────┐  ← pen-style enclosure (Ø34 × 180 mm PETG)
         │  18650 + PCB │
         ├──────────────┤
         │ 28BYJ-48     │  ← geared stepper motor (1/64 gearbox)
         │  + leadscrew │     M4×0.35 fine thread, 2 mm travel
         ├──────────────┤
         │  20 N load   │  ← sub-miniature foil-strain load cell
         │  cell + HX711│     measures reaction force on indenter
         ├──────────────┤
         │ capacitive   │  ← parallel-plate gap sensor (AD7746)
         │ depth sensor  │     fixed plate on reference ring, moving plate on shaft
         ├──────────────┤
         │ reference    │  ← spring-loaded ring contacts sample surface
         │ ring (spring)│     isolates frame compliance from depth measurement
         ├──────────────┤
         │ indenter tip │  ← interchangeable: Vickers / Berkovich / WC ball
         └──────┬───────┘
                │
           sample surface
```

**Key mechanical insight:** The capacitive parallel-plate sensor measures the gap between the **reference ring** (which sits on the sample surface) and the **indenter shaft** (which moves with the indenter). This means depth is measured *relative to the sample surface*, completely eliminating frame compliance — the #1 source of error in cheap instrumented indentation systems. The reference ring is spring-loaded so it stays in contact with the surface at all times.

## Pin Assignments (STM32G474RET6, LQFP64)

| Pin | Function | Detail |
|-----|----------|--------|
| PA0  | ADC1_IN1  | Battery voltage divider (×0.25) |
| PA1  | GPIO_OUT  | HX711 SCK (clock) |
| PA2  | GPIO_IN   | HX711 DOUT (data) |
| PA3  | GPIO_OUT  | HX711 RATE (80 Hz) |
| PA4  | GPIO_OUT  | DRV8833 IN1 (stepper A+ dir) |
| PA5  | GPIO_OUT  | DRV8833 IN2 (stepper A- dir) |
| PA6  | GPIO_OUT  | DRV8833 IN3 (stepper B+ dir) |
| PA7  | GPIO_OUT  | DRV8833 IN4 (stepper B- dir) |
| PA8  | GPIO_OUT  | DRV8833 EN (stepper enable) |
| PA9  | USART1_TX | → ESP32-C3 RX |
| PA10 | USART1_RX | ← ESP32-C3 TX |
| PA11 | GPIO_IN   | Over-travel clutch / stall detect |
| PA12 | GPIO_OUT  | Buzzer (alarm / done) |
| PA13 | SWDIO     | Debug |
| PA14 | SWCLK     | Debug |
| PA15 | GPIO_OUT  | Status LED (white) |
| PB0  | GPIO_OUT  | DS18B20 1-wire data |
| PB1  | GPIO_OUT  | OLED DC (data/command) |
| PB3  | SPI1_SCK  | SD card + OLED (shared, CS-gated) |
| PB4  | SPI1_MISO | SD card |
| PB5  | SPI1_MOSI | SD card + OLED |
| PB6  | GPIO_OUT  | SD CS |
| PB7  | GPIO_OUT  | OLED CS (SPI) |
| PB8  | I2C1_SCL  | AD7746 (capacitive sensor) |
| PB9  | I2C1_SDA  | AD7746 (capacitive sensor) |
| PB10 | SPI2_SCK  | ICM-42688-P IMU |
| PB11 | SPI2_MISO | ICM-42688-P |
| PB12 | GPIO_OUT  | ICM-42688-P CS |
| PB13 | GPIO_IN   | Button: START |
| PB14 | GPIO_IN   | Button: STOP |
| PB15 | GPIO_IN   | Button: MENU |
| PC6  | GPIO_OUT  | ESP32-C3 BOOT/RST (reset line) |
| PC13 | GPIO_IN   | Tip-present interlock (reed) |
| PC14 | GPIO_OUT  | OLED RST |
| PC15 | GPIO_OUT  | Motor brake (passive clutch disengage) |

## Power Architecture

```
 18650 ×2 (7.4 V, ~3500 mAh)
   │
   ├─► MP1584 buck → 5 V / 1.5 A  (logic rail: STM32, ESP32-C3, OLED, SD, sensors)
   └─► USB-C (TP4056 charger) → charge 18650s; 5 V input can also run without battery

 Stepper draws ~200 mA at 5 V during approach; ~50 mA during hold (idle winding).
 AD7746 internal excitation: no external HV needed.
 Load cell excitation: 5 V from HX711 onboard LDO.
```

Battery life ~4 h in typical use (intermittent testing). Stepper only active during approach/retract (~3 s per test).

## Instrumented Indentation Measurement Theory

### Load–Displacement Curve

The instrument records force `P(t)` and depth `h(t)` simultaneously during a loading–hold–unloading cycle:

```
 P (mN)
  │        ╱╲         ← peak load P_max
  │       ╱  ╲___      ← creep hold (constant P)
  │      ╱       ╲    ← elastic unloading
  │     ╱         ╲
  │    ╱            ╲  ← plastic + elastic loading
  │   ╱              ╲
  │__╱________________╲___
  │         h_f           ← residual depth (plastic)
  └──────────────────────── h (µm)
         h_max
```

### Oliver–Pharr Method

1. **Contact stiffness** `S = dP/dh` at `h_max` — from the slope of the upper 30–60% of the unloading curve, fitted to `P = α(h − h_f)^m` (power law).

2. **Contact depth** `h_c = h_max − ε·P_max / S`, where `ε = 0.75` (Vickers/Berkovich).

3. **Contact area** `A(h_c)`:
   - Vickers: `A = 24.5 · h_c²` (projected area of 136° pyramid)
   - Berkovich: `A = 24.5 · h_c²`
   - Ball (Brinell): `A = π · D · h_c` (D = ball diameter)

4. **Hardness** `H = P_max / A(h_c)` (in Pa; convert to HV/HB via standard tables).

5. **Reduced modulus** `E_r = S / (2·β·√(A/π))`, `β = 1.012` (Vickers), `β = 1.034` (Berkovich).

6. **Young's modulus** `E = (1−ν²) / (1/E_r − (1−ν_i²)/E_i)`, with `ν` = Poisson's ratio of sample, `E_i = 1141 GPa, ν_i = 0.07` (diamond indenter).

### Additional Measurements

- **Martens hardness** `HM = P_max / (26.43 · h_max²)` (Vickers) — total deformation (elastic + plastic).
- **Elastic work ratio** `η = W_elastic / W_total`, where `W_total = ∫₀^{h_max} P dh` (area under loading curve), `W_elastic = ∫_{h_f}^{h_max} P dh` (area under unloading curve).
- **Creep** `C(t) = (h(t) − h(t_hold_start)) / P_max` — depth increase during constant-load hold.
- **Strain-rate sensitivity** `m = d(ln H)/d(ln ε̇)`, from runs at different loading rates.

Full derivation in `docs/measurement_theory.md`.

## Indenter Tips

| Tip | Geometry | Use | Hardness Formula |
|-----|----------|-----|-----------------|
| Vickers | 136° diamond pyramid | General metals, ceramics | `HV = 0.1891·P/A` (kgf/mm²) |
| Berkovich | 65.27° 3-sided pyramid | Thin films, nano-range | `H_B = P/(24.5·h_c²)` |
| WC Ball 1 mm | 1 mm tungsten carbide sphere | Soft metals, polymers | `HB = 0.102·P/A` |

Tips are interchangeable via a threaded collet. A reed interlock detects tip presence before allowing a test.

## Calibration

1. **Force**: 2-point — zero (no contact) + known reference weight (5 g = 49.1 mN). HX711 offset/scale stored in flash.
2. **Depth (capacitive)**: 3-point using precision gauge blocks (0 µm contact, 50 µm, 100 µm shim). AD7746 raw counts → µm polynomial fit stored in flash.
3. **Frame compliance**: not needed — depth measured relative to reference ring.
4. **Tip area function**: factory-calibrated `A(h_c)` polynomial for each tip, stored in flash. User can recalibrate against a fused silica standard (known E = 72 GPa, ν = 0.17).
5. **Temperature**: DS18B20 factory-trimmed ±0.5 °C; optional ice-bath calibration.

See `scripts/calibrate.py`.

## On-Device Analysis

- 500 Hz force + depth acquisition during loading/unloading.
- Unloading curve fitted to `P = α(h − h_f)^m` via Levenberg–Marquardt (iterative, 10 iterations).
- Oliver–Pharr H, E_r, E computed at end of each test.
- Creep depth logged during hold segment.
- 30-material k-NN (k=3) identification using {H, E, η} features.
- Hardness conversions: HV, HB, HRA/HRB/HRC from standard ASTM E140 tables.

## Firmware

Firmware is split:

- `firmware/` — STM32G474 application (HAL + bare-metal scheduler), buildable with `arm-none-eabi-gcc` + Makefile.
- `firmware/esp32-c3/` — ESP-IDF app providing BLE GATT + Wi-Fi captive plotter, UART bridge to STM32.

Key modules (STM32 side):

| File | Purpose |
|------|---------|
| `main.c` | Scheduler, state machine, mode dispatch |
| `stepper.c/h` | 28BYJ-48 stepper + DRV8833 driver, microstep, approach/retract |
| `loadcell.c/h` | HX711 driver, force acquisition, tare |
| `displacement.c/h` | AD7746 capacitive sensor driver, depth computation |
| `indentation.c/h` | P–h curve capture, Oliver–Pharr analysis, H/E computation |
| `ds18b20.c/h` | Temperature sensor driver |
| `imu.c/h` | ICM-42688-P driver, tilt/leveling |
| `oled_display.c/h` | SSD1306 driver, live P–h curve plot |
| `sd_logger.c/h` | FATFS CSV + binary logging |
| `safety.c/h` | Overload, stall detect, watchdog, interlock |
| `esp32_link.c/h` | UART protocol to ESP32-C3 |
| `flash_store.c/h` | NV parameters (calibration, tip profiles) |
| `database.c/h` | 30-material H/E library + k-NN matching |

## Usage

1. Select indenter tip (Vickers/Berkovich/WC ball) and insert into collet.
2. Place Dent Scope perpendicular to the sample surface. The IMU confirms leveling (±2° of normal).
3. MENU to select test parameters: peak load (1–20 N), loading rate (0.1–5 N/s), hold time (1–30 s).
4. Press START. The stepper approaches the surface at low speed until the load cell detects contact (~50 mN threshold).
5. Loading begins at the programmed rate. The P–h curve streams to OLED, SD, and BLE simultaneously.
6. At peak load, the hold segment begins (creep measurement).
7. Unloading at the same rate. At completion, results (H, E, HV, η) display on OLED.
8. Stepper retracts. Ready for next test.
9. Phone app (`scripts/live_stream.py`) plots the P–h curve and exports CSV; `scripts/analyze_indentation.py` does offline Oliver–Pharr analysis and material identification.

## Repository Layout

```
dent-scope/
├── README.md
├── schematic/dent-scope.kicad_sch
├── firmware/
│   ├── Makefile
│   ├── STM32G474RET6_FLASH.ld
│   ├── Core/Src/*.c, Core/Inc/*.h
│   └── esp32-c3/ (ESP-IDF)
├── hardware/BOM.csv
├── docs/
│   ├── assembly_guide.md
│   ├── api_reference.md
│   └── measurement_theory.md
└── scripts/
    ├── calibrate.py
    ├── live_stream.py
    └── analyze_indentation.py
```

## License

MIT — build it, sell it, improve it.