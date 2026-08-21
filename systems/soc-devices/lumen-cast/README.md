# Lumen Cast

**A pocket-sized, battery-operated 2-axis goniophotometer that sweeps a precision photometric head around a light source on a NEMA8 stepper (azimuth) + SG90 servo (elevation), measuring luminous intensity and color versus angle with a TI OPT3001 lux sensor and AMS TCS34725 RGB sensor, computing luminous flux by spherical integration, beam angle (FWHM), center-beam candlepower, CCT/Duv uniformity, and isocandela plots — built around an STM32G491RET6 motor-control MCU paired with an ESP32-C3 wireless bridge.**

---

## What It Does

The Lumen Cast is a **handheld photometric characterization instrument** — you mount an LED, lamp, or flashlight in the center cradle, press SCAN, and 90 seconds later you have a complete photometric report on the OLED and on your phone/PC. Unlike laboratory goniophotometers ($10,000–$100,000, room-sized, requiring a darkroom), the Lumen Cast costs under $90 and fits in a shoebox. It measures the full angular light distribution of any small source and computes all the quantities a lighting engineer needs: total luminous flux (lumens), beam angle, peak candela, CCT vs angle, color uniformity, and isocandela contours.

### Why affordable goniophotometry matters

Goniophotometry is the gold standard for characterizing light sources — it's how LED manufacturers bin parts, how automotive headlight designs are validated, how horticulture lighting is specified (PPFD distribution), and how flashlight/photometric data files (.IES, .LDT) are generated. Professional goniophotometers require a dedicated darkroom, a precision 2-axis turntable, a photometer head on a 5-30 m linear track, and a calibration lab. They are simply out of reach for small lighting makers, makers, horticulture growers, lighting designers, and educators. A $90 pocket goniophotometer democratizes photometric characterization: a small LED vendor can bin parts, a horticulture grower can map the PPFD footprint of a grow light, a flashlight enthusiast can measure beam angle and throw, and a university can teach photometry hands-on.

### How it works

1. **2-axis mechanical sweep** — a NEMA8 stepper motor (200 steps/rev × 16 microsteps = 3200 steps/rev via TMC2209) rotates the photometric head in azimuth (0–360°). An SG90 servo tilts the head in elevation (−90° to +90°). The light source sits in a fixed cradle at the center. The sensor head orbits at a fixed radius (150 mm) around the source.

2. **Luminance measurement** — a Texas Instruments OPT3001 ambient light sensor measures illuminance at the sensor head with 0.045–188,000 lux range, 23-bit effective resolution, and spectral response closely matched to the human photopic curve (V(λ)). At 150 mm radius, this converts to luminous intensity: `I (cd) = E (lux) × r² (m²)`.

3. **Color measurement** — an AMS TCS34725 RGB + clear sensor measures the color of the light at each angle. The firmware computes correlated color temperature (CCT) and the distance from the Planckian locus (Duv) using McCamy's approximation and the Robertson method from the RGBC channels.

4. **Spherical integration** — luminous flux is computed by integrating luminous intensity over the full sphere: `Φ (lm) = ∮ I(θ,φ) dΩ`. For a Type C goniophotometer scan, `Φ = Σ I(θ,φ) × sin(θ) × Δθ × Δφ`. The firmware performs this integration in fixed-point using the STM32G491's CORDIC coprocessor for fast sin/cos.

5. **Beam characterization** — from the luminous intensity distribution, the firmware computes:
   - **Peak candela** (I_max) — maximum luminous intensity
   - **Beam angle** — full-width half-maximum (FWHM) of the intensity distribution
   - **Field angle** — angle to 10% of peak
   - **Center beam candlepower** (CBCP) — intensity on-axis
   - **Beam uniformity** — ratio of min/max intensity within the beam cone
   - **Throw** (for flashlights) — peak candela → distance to 0.25 lux

6. **Color uniformity** — CCT and Duv are computed at each angle. The report shows CCT variation across the beam (ΔCCT), Duv range, and a color shift map. MacAdam ellipse step count is estimated for beam-edge color deviation.

7. **Photometric data export** — the firmware generates IES LM-63 (.IES) and EULUMDAT (.LDT) file content from the scan data, transmitted over BLE/WiFi to the companion app which saves ready-to-use photometric files.

8. **Scan modes**:
   - **Type A** (azimuth only, 0–360° @ 1° steps) — fast 30-second scan for rotationally symmetric sources (bare LEDs, omnidirectional bulbs)
   - **Type C** (2-axis, azimuth 0–360° @ 15° + elevation 0–180° @ 15°) — full 3D distribution for directional sources (~90 seconds)
   - **Meridian** (elevation sweep at fixed azimuth) — vertical plane cut for automotive/streetlight
   - **Near-field** (dense 5° grid over ±60°) — high-resolution beam profiling for narrow-beam LEDs

### Use Cases

| Application | How Lumen Cast Helps |
|------------|---------------------|
| LED binning | Sort LEDs by flux/color within a batch at production speed |
| Horticulture lighting | Map PPFD footprint of grow lights; compute uniformity over canopy |
| Flashlight characterization | Measure beam angle, throw (cd), hotspot vs spill ratio |
| Automotive lighting | Vertical plane cuts for headlight beam pattern validation |
| Streetlight design | Generate .IES files for Dialux/Relux simulation |
| Display backlight | Measure angular color uniformity of LCD/OLED panels |
| Museology | Characterize museum lighting color rendering and beam shape |
| Education | Teach photometry, luminous flux, candela, lux hands-on |
| Maker lighting | Validate DIY LED projects before installation |
| Photography | Map light falloff and color shift of speedlights/LED panels |
| Quality control | Verify lamp-to-lot consistency in small-batch manufacturing |
| Standards compliance | Pre-screen products against ENERGY STAR / IES standards before lab testing |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              LUMEN CAST                                           │
│                                                                                   │
│   ┌───────────────────────────────────────────────────┐                          │
│   │        STM32G491RET6 (Cortex-M4F @ 170 MHz)        │                          │
│   │        512 KB flash, 112 KB SRAM, LQFP64            │                          │
│   │        CORDIC + FMAC accelerators                   │                          │
│   │                                                   │                          │
│   │  ┌──────────────────────────────────────────────┐ │   I2C1 (PB6/PB7)          │
│   │  │ scan_fsm — idle → home → sweep → integrate   │◄┼──────────────────────┐   │
│   │  ├──────────────────────────────────────────────┤ │                      │   │
│   │  │ motor_task — TIM2 PWM step gen + DIR + EN    │ │   ┌──────────────┐  │   │
│   │  │  NEMA8 3200 steps/rev via TMC2209            │ │   │ OPT3001      │  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ lux sensor   │  │   │
│   │  │ servo_task — TIM3_CH1 PWM → SG90 elevation  │ │   │ I2C 0x44     │  │   │
│   │  ├──────────────────────────────────────────────┤ │   └──────────────┘  │   │
│   │  │ photometer_task — OPT3001 lux → candela      │◄┼───┌──────────────┐  │   │
│   │  │  I = E × r²  (r = 0.15 m)                   │ │   │ TCS34725     │  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ RGB+C color  │  │   │
│   │  │ color_task — TCS34725 RGBC → CCT, Duv        │◄┼───│ I2C 0x29     │  │   │
│   │  ├──────────────────────────────────────────────┤ │   └──────────────┘  │   │
│   │  │ goniometry_task — Φ = ∮ I·dΩ, beam, FWHM     │ │                      │   │
│   │  │  CORDIC sin/cos for spherical integration    │ │   ┌──────────────┐  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ SH1106 OLED  │  │   │
│   │  │ display_task — isocandela + polar plot       │◄┼───│ 128×64 I2C   │  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ 0x3C         │  │   │
│   │  │ flashlog_task — W25Q128 scan storage         │ │   └──────────────┘  │   │
│   │  ├──────────────────────────────────────────────┤ │                      │   │
│   │  │ ble_bridge_task — UART → ESP32-C3            │ │   ┌──────────────┐  │   │
│   │  │  .IES / .LDT file generation                 │ │   │ DS3231 RTC   │  │   │
│   │  └──────────────────────────────────────────────┘ │   │ I2C 0x68     │  │   │
│   │                                                   │◄───└──────────────┘  │   │
│   └──┬───────┬──────────┬──────────┬──────────┬──────┘                       │   │
│      │TIM2    │TIM3       │SPI2      │USART1    │PA0 ADC                      │   │
│      │STEP    │SERVO      │FLASH     │BRIDGE    │BATT                         │   │
│      ▼       ▼           ▼          ▼          ▼                              │   │
│  ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐                          │   │
│  │TMC2209 ││SG90    ││W25Q128 ││ESP32-C3││Batt    │                          │   │
│  │stepper ││servo   ││16MB    ││MINI-1  ││divider │                          │   │
│  │driver  ││elevat. ││flash   ││BLE+WiFi││        │                          │   │
│  └───┬────┘└────────┘└────────┘└───┬────┘└────────┘                          │   │
│      │                               │ BLE/WiFi                              │   │
│      ▼                               ▼                                       │   │
│  ┌────────┐                    ┌──────────────┐                              │   │
│  │NEMA8   │                    │Phone/PC App  │                              │   │
│  │stepper │                    │.IES/.LDT     │                              │   │
│  │+ring   │                    │isocandela    │                              │   │
│  └────────┘                    └──────────────┘                              │   │
│                                                                                   │
│   Photometry: Source cradle (center) → sensor head orbits at r=150mm             │
│                E(lux) → I(cd) = E × r² → Φ(lm) = ∮ I dΩ                          │
│   Power:      LiPo 2200mAh → DW01A/FS8205A → TPS63020 3.3V → TLV70033 (sensors) │
│   Charging:   USB-C → MCP73831 → LiPo                                           │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Mechanical Assembly

```
                     ┌─────────────────────┐
                     │   Sensor Head       │
                     │  ┌───────────────┐  │
                     │  │ OPT3001 lux   │  │
                     │  │ TCS34725 RGB  │  │
                     │  └───────────────┘  │
                     │  ← SG90 servo tilt  │
                     └────────┬────────────┘
                              │ arm (150mm)
                              │
                    ┌─────────▼─────────┐
                    │  Rotating Ring    │
                    │  (NEMA8 driven)   │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         Azimuth bearing   NEMA8 stepper   Azimuth bearing
              │           (base)              │
              └───────────────┼───────────────┘
                              │
                     ┌────────▼────────┐
                     │  Source Cradle   │  ← LED/lamp under test
                     │  (center, fixed) │
                     └─────────────────┘
```

The sensor head is mounted on a 150 mm arm extending from a rotating ring. The ring is driven by a NEMA8 stepper motor (belt or direct). The sensor head tilts on an SG90 servo for elevation. The light source under test sits in a fixed cradle at the center. A removable dark cloth shroud (included) blocks ambient light during scanning.

---

## Pin Assignments (STM32G491RET6 LQFP64)

| Pin | GPIO | Function | Direction | Connected To |
|-----|------|----------|-----------|-------------|
| 1 | PA0 | TIM2_CH1 STEP | OUT | TMC2209 STEP |
| 2 | PA1 | Stepper DIR | OUT | TMC2209 DIR |
| 3 | PA2 | Stepper EN | OUT | TMC2209 EN (active low) |
| 4 | PA3 | Battery ADC | AN | 2:1 battery divider |
| 5 | PA4 | SCAN button | IN | SW1 (active low) |
| 6 | PA5 | MODE button | IN | SW2 (active low) |
| 7 | PA6 | TIM3_CH1 servo | OUT | SG90 servo signal |
| 8 | PA8 | Status LED | OUT | Green LED |
| 9 | PA9 | USART1 TX | OUT | ESP32-C3 GPIO5 (RX) |
| 10 | PA10 | USART1 RX | IN | ESP32-C3 GPIO4 (TX) |
| 11 | PA11 | USB D- | I/O | USB-C connector |
| 12 | PA12 | USB D+ | I/O | USB-C connector |
| 13 | PB0 | WS2812B data | OUT | WS2812B LED |
| 14 | PB1 | Charger status | IN | MCP73831 STAT |
| 15 | PB3 | ESP32-C3 EN | OUT | ESP32-C3 EN |
| 16 | PB4 | ESP32-C3 BOOT | OUT | ESP32-C3 IO9 (pull-up) |
| 17 | PB6 | I2C1 SCL | I/O | OPT3001, TCS34725, SH1106, DS3231 |
| 18 | PB7 | I2C1 SDA | I/O | OPT3001, TCS34725, SH1106, DS3231 |
| 19 | PB12 | Flash CS | OUT | W25Q128 CS |
| 20 | PB13 | SPI2 SCK | OUT | W25Q128 SCK |
| 21 | PB14 | SPI2 MISO | IN | W25Q128 DO |
| 22 | PB15 | SPI2 MOSI | OUT | W25Q128 DI |

## I2C Bus Devices

| Device | Address | Function |
|--------|---------|----------|
| OPT3001DNPT | 0x44 | Precision photopic illuminance sensor (0.045–188k lux) |
| TCS34725 | 0x29 | RGB + clear color sensor for CCT/Duv computation |
| SH1106 OLED | 0x3C | 128×64 monochrome display |
| DS3231SN | 0x68 | RTC for scan timestamping |

---

## Power Architecture

```
USB-C 5V ──→ MCP73831 ──→ LiPo 3.7V 2200mAh
                              │
                              ▼
                         DW01A + FS8205A (protection)
                              │
                              ▼
                         TPS63020 (buck-boost 3.3V)
                              │
                         ┌────┴────┐
                         ▼         ▼
                      +3V3      +3V3_SENS (TLV70033 LDO)
                      │           │
                   STM32G491    OPT3001
                   ESP32-C3     TCS34725
                   SH1106       DS3231
                   W25Q128
                   TMC2209
                   WS2812B
                   SG90 servo
```

- **Battery life:** ~6 hours continuous scanning (motor + sensors), ~100 full Type C scans
- **Charge time:** ~4.5 hours via USB-C
- **Low-power:** STM32G491 standby (~3µA), ESP32-C3 deep sleep (~5µA), TMC2209 stealthChop idle
- **Motor power:** NEMA8 draws ~400mA at 3.3V during sweep; TMC2209 standby <1mA

---

## Photometric Theory

### Luminous intensity from illuminance

The sensor head orbits at radius `r = 0.15 m` from the source. By the inverse-square law:

```
E (lux) = I (cd) / r² (m²)
→ I (cd) = E (lux) × r² = E × 0.0225
```

### Luminous flux by spherical integration

For a Type C goniophotometer, luminous intensity `I(θ, φ)` is sampled on a spherical grid. Luminous flux:

```
Φ (lm) = ∮ I(θ,φ) dΩ = ∫₀²π ∫₀π I(θ,φ) sin(θ) dθ dφ
```

Discretized: `Φ ≈ Σ I(θᵢ, φⱼ) × sin(θᵢ) × Δθ × Δφ`

The STM32G491's CORDIC coprocessor computes sin/cos in 8 cycles, enabling real-time integration during the sweep.

### Correlated color temperature (CCT)

From the TCS34725 RGBC channels, chromaticity (x, y) is computed via the sensor's spectral response matrix. CCT is then computed using McCamy's approximation:

```
n = (x - 0.3320) / (0.1858 - y)
CCT = 449n³ + 3525n² + 6823.3n + 5520.33
```

### Duv (distance from Planckian locus)

The perpendicular distance from the chromaticity point to the Planckian locus in the CIE 1960 uv diagram. Duv < 0.006 is generally acceptable for general lighting.

### Beam angle (FWHM)

The full angle of the cone where luminous intensity ≥ 50% of peak. Computed by finding the two angles where I crosses 0.5 × I_max and taking their separation.

---

## Firmware

### Build

**STM32G491 (main MCU):**
```bash
cd firmware
make          # requires arm-none-eabi-gcc + STM32G4 HAL
make flash    # requires ST-Link V2 SWD programmer
```

**ESP32-C3 (BLE/WiFi bridge):**
```bash
cd firmware/esp32_c3_bridge
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

### Source files

| File | Description |
|------|-------------|
| `main.c` | Super-loop, scan state machine, button handling |
| `goniometry.c` | Spherical integration, beam angle, FWHM, flux computation |
| `photometer.c` | OPT3001 lux sensor driver |
| `color.c` | TCS34725 RGBC → CCT/Duv computation |
| `motor.c` | TMC2209 stepper driver (TIM2 PWM step generation) |
| `servo.c` | SG90 servo PWM control (TIM3) |
| `sh1106.c` | OLED display driver with polar/isocandela plotting |
| `ble_bridge.c` | UART binary protocol to ESP32-C3 (.IES/.LDT export) |
| `flashlog.c` | W25Q128 SPI flash scan logging |
| `ds3231.c` | RTC driver for scan timestamping |
| `ws2812.c` | WS2812B RGB LED status indicator |
| `linker.ld` | STM32G491 linker script (512KB flash, 112KB SRAM) |
| `Makefile` | Build system for arm-none-eabi-gcc |
| `esp32_c3_bridge/` | ESP-IDF project for BLE/WiFi bridge |

---

## Python Companion App

```bash
cd scripts
python3 lumen_cast_viewer.py --demo
```

Output:
```
  LUMEN CAST — Photometric Report
  Source: Demo LED  |  Scan: Type C  |  2025-06-28 14:32:01
  Radius: 150mm  |  Steps: 24 azimuth × 12 elevation
  ---------------------------------------------------------------
  LUMINOUS FLUX:        847.3 lm
  PEAK CANDela:         1,240 cd  @ (θ=0°, φ=0°)
  BEAM ANGLE (FWHM):    38.2°
  FIELD ANGLE (10%):    72.5°
  CBCP (on-axis):       1,240 cd
  BEAM UNIFORMITY:      0.82
  THROW (0.25 lux):     70.4 m
  ---------------------------------------------------------------
  COLOR (on-axis):      3120 K  Duv: 0.0021
  COLOR (beam edge):    3185 K  Duv: 0.0038
  ΔCCT across beam:     65 K
  MacAdam steps (edge): 2.1
  ---------------------------------------------------------------
  .IES file: scan_0001.ies  (12,288 bytes)
  .LDT file: scan_0001.ldt  (15,104 bytes)
```

---

## BOM Summary

| Part | Qty | Unit Cost | Source |
|------|-----|-----------|--------|
| STM32G491RET6 | 1 | $5.50 | Mouser |
| ESP32-C3-MINI-1 | 1 | $2.80 | Mouser |
| OPT3001DNPT | 1 | $4.20 | Digi-Key |
| TCS34725 | 1 | $4.50 | Digi-Key |
| SH1106 OLED 1.3" | 1 | $3.50 | AliExpress |
| W25Q128 16MB | 1 | $1.20 | Digi-Key |
| TMC2209 v1.2 | 1 | $3.50 | AliExpress |
| NEMA8 stepper 20mm | 1 | $8.00 | AliExpress |
| SG90 servo | 1 | $3.00 | AliExpress |
| DS3231SN | 1 | $2.50 | Digi-Key |
| TPS63020 | 1 | $3.90 | Digi-Key |
| MCP73831 | 1 | $0.60 | Digi-Key |
| LiPo 2200mAh | 1 | $5.50 | BatteryJunction |
| Mechanical (ring, arm, cradle) | 1 | $15.00 | 3D printed + bearings |
| Passives + misc | — | $5.00 | Digi-Key |
| PCB (4-layer) | 1 | $5.00 | PCBWay |
| Dark cloth shroud | 1 | $2.00 | fabric |
| **Total** | | **~$77** | |

Full BOM: `hardware/BOM.csv`

---

## Calibration

The Lumen Cast is calibrated against a known reference lamp (included in optional kit: a calibrated 1000 lm LED module with NIST-traceable flux certificate). The calibration procedure:

1. Mount the reference lamp in the cradle
2. Press and hold MODE for 3 seconds → enters CALIBRATION mode
3. Run a Type A scan
4. The firmware computes a calibration factor `k = Φ_known / Φ_measured` and stores it in flash
5. All subsequent scans are multiplied by `k`

The OPT3001's factory trim provides ±10% absolute accuracy; calibration brings this to ±3%.

---

## Limitations & Notes

- **Source size:** The source under test should be ≤ 30mm diameter for the 150mm radius inverse-square law to hold (far-field condition: r ≥ 10× source size). Larger sources require a longer arm (extension kit).
- **Ambient light:** Scanning must be performed in subdued light. The dark cloth shroud attenuates ambient by ~95%. The firmware subtracts a pre-scan ambient reading.
- **Speed:** Type A scan (360° @ 1°) takes ~30 seconds. Type C (24×12 grid) takes ~90 seconds. Motor speed is limited to 20 rpm to allow sensor settling.
- **Spectral mismatch:** The OPT3001 photopic response is within 5% of CIE V(λ). For high-accuracy work on non-white sources, a spectral mismatch correction factor should be applied.
- **Weight:** ~350g including battery. Portable in a backpack.

---

## License

MIT — build it, sell it, improve it.