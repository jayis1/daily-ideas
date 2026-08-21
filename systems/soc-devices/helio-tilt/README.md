# Helio Tilt — Pocket Tracking Pyrheliometer & Aerosol Optical Depth Meter

> A battery-powered, pocket-sized solar tracking radiometer that
> continuously points a narrow-field collimator at the sun using a
> 2-axis stepper mechanism, measures direct normal irradiance (DNI)
> with a thermopile detector, computes aerosol optical depth (AOD) at
> 5 wavelengths via the Beer-Lambert-Bouguer law with on-device
> Langley calibration, tracks the sun autonomously with an analytical
> solar-position algorithm (NOAA/SPA), fuses a 6-axis IMU for
> level/tilt compensation, logs to SD card, and streams over BLE —
> bringing $4k–$25k tracking pyrheliometers and sun photometers
> (Eppley NIP, Kipp & Zonen CHP1, CIMEL CE318) down to ~$74 and
> pocket size.

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         HELIO TILT                                    │
 │          Pocket Tracking Pyrheliometer + AOD Meter                    │
 │                                                                       │
 │  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐            │
 │  │ Collimator   │───▶│ Thermopile   │───▶│ ADS122U04      │            │
 │ │ tube (5° FOV)│    │ + 5 filters │    │ 24-bit ADC     │            │
 │ │ 2-axis mount │    │ wheel (405- │    │ 20 Hz, ΔΣ      │            │
 │ │ AZ + EL stepp│    │  1640 nm)   │    │ PGA 1-128×     │            │
 │  └──────┬──────┘    └──────────────┘    └───────┬────────┘            │
 │         │                                        │                     │
 │         │           ┌────────────────┐           │                     │
 │         └──────────▶│  STM32G474RET6 │◀──────────┘                     │
 │                     │  170 MHz M4F   │                                │
 │                     │  ┌──────────┐  │                                │
 │                     │  │ Solar    │  │                                │
 │                     │  │ position │  │                                │
 │                     │  │ NOAA SPA │  │                                │
 │                     │  │ + IMU    │  │                                │
 │                     │  │ level    │  │                                │
 │                     │  └──────────┘  │                                │
 │                     │  ┌──────────┐  │                                │
 │                     │  │ AOD /    │  │                                │
 │                     │  │ DNI /    │  │                                │
 │                     │  │ Langley  │  │                                │
 │                     │  └──────────┘  │                                │
 │                     └──┬────┬────┬───┘                                │
 │                        │    │    │                                     │
 │                   ┌────┘    │    └──────┐                              │
 │                   ▼         ▼           ▼                              │
 │              ┌────────┐ ┌──────┐  ┌──────────┐                         │
 │              │OLED    │ │SD    │  │ESP32-C3  │                         │
 │              │128×64  │ │FAT32 │  │BLE/WiFi  │                         │
 │              │plot    │ │CSV   │  │stream    │                         │
 │              └────────┘ └──────┘  └──────────┘                         │
 │                                                                       │
 │  Power: 18650 LiPo + TP4056 + MCP1640B boost 5V                       │
 │  Solar:  NEO-M9N GPS for time + position                              │
 │  IMU:    LSM6DSO for tilt/level compensation                          │
 │  Filter wheel: 5-band 405/440/675/870/940/1640 nm (AOD + water vapor) │
 └──────────────────────────────────────────────────────────────────────┘
```

## What It Does

Helio Tilt is a complete tracking solar radiometer that fits in a
pocket. On power-up, the device:

1. **Acquires GPS fix** — a u-blox NEO-M9N provides UTC time,
   latitude, longitude, and elevation within ~10 seconds (cold start
   <30 s). This is the geolocation input for the solar position
   algorithm.

2. **Computes solar position** — the STM32 runs an analytical solar
   position algorithm (truncated NOAA/SPA, ~0.01° accuracy) that
   computes the sun's azimuth and elevation angle from GPS
   coordinates + UTC time, including nutation, aberration, and
   atmospheric refraction correction (Saemundsson formula) for
   elevations >5°.

3. **Levels itself** — an LSM6DSO 6-axis IMU measures the device's
   tilt (roll/pitch) relative to gravity. The firmware fuses this
   with the solar azimuth/elevation to compute the required
   2-axis stepper angles (azimuth + elevation) to point the
   collimator tube at the sun. A 4-point magnetometer (MMC5603NJ)
   provides absolute heading reference for azimuth calibration.

4. **Tracks the sun** — two NEMA8 stepper motors drive an azimuth
   turntable and an elevation arm, keeping the collimator tube
   (5° field-of-view) pointed at the sun. The STM32 updates the
   pointing at 1 Hz, adjusting for the sun's apparent motion
   (~15°/hr azimuth). Microstepping (1/16) gives 0.025° resolution.

5. **Measures DNI** — at the bottom of the collimator tube, a
   thermopile detector (MLX90614ESF-DCC thermal IR sensor repurposed
   as broadband solar detector, or a thin-film thermopile) measures
   the solar irradiance. A 24-bit delta-sigma ADC (ADS122U04) samples
   the thermopile at 20 Hz with programmable gain (PGA 1–128×). The
   thermopile's Seebeck output is proportional to the temperature
   difference between the hot junction (sun-illuminated) and cold
   junction (ambient), calibrated against a reference irradiance.

6. **Measures spectral AOD** — a 6-position filter wheel (405, 440,
   675, 870, 940, 1640 nm narrow-band interference filters) rotates
   in front of the thermopile. At each wavelength, the DNI is
   measured and the aerosol optical depth is computed via the
   Beer-Lambert-Bouguer law:
   ```
   τ_aero(λ) = [ln(V₀(λ)) - ln(V(λ))] / m(θ)
   ```
   where V₀(λ) is the extraterrestrial calibration constant (from
   Langley plot), V(λ) is the measured voltage, and m(θ) is the
   relative optical air mass (Kasten-Young formula) at solar zenith
   angle θ. The 940 nm channel measures precipitable water vapor
   (PWV) via the modified Langley method. A complete 6-wavelength
   sweep takes ~12 seconds.

7. **Langley calibration** — on a clear, stable-aerosol day, the
   device can run an autonomous Langley calibration: it logs V(λ)
   over a 2–3 hour period at varying solar zenith angles (morning
   or evening), then performs a linear regression of ln(V) vs. air
   mass m. The y-intercept gives ln(V₀), the extraterrestrial
   constant. This self-calibration eliminates the need for a
   reference instrument.

8. **Reports** — displays real-time DNI, AOD at each wavelength,
   Ångström exponent (α), precipitable water vapor, sun position
   (az/el), and tracking status on the OLED; logs every measurement
   to microSD (CSV with timestamp, GPS, sun position, DNI, AOD, PWV,
   temperature); and streams over BLE to a phone/PC app for live
   plotting and cloud upload (AERONET-compatible format).

## Why It's Interesting

Direct solar irradiance and aerosol optical depth are fundamental
measurements for:

- **Climate science** — aerosols are the largest source of
  uncertainty in climate models. AOD is the primary ground-truth
  for satellite aerosol retrieval (MODIS, VIIRS) and climate models.
- **Air quality** — fine particulate matter (PM2.5) correlates with
  AOD; sun photometers provide column-integrated aerosol loading
  that complements surface PM sensors.
- **Solar energy** — DNI is the key input for concentrating solar
  power (CSP) plant design and performance monitoring. A tracking
  pyrheliometer is the reference instrument for DNI.
- **Atmospheric science** — precipitable water vapor (PWV) from the
  940 nm channel is used in weather forecasting, greenhouse effect
  studies, and satellite validation.
- **Volcanic ash monitoring** — AOD spikes after eruptions; portable
  sun photometers can be deployed rapidly.
- **Agriculture** — solar radiation drives evapotranspiration models
  for irrigation scheduling.

The reference networks (AERONET, SKYNET) use CIMEL CE318 sun
photometers ($15k–$25k) and Eppley NIP pyrheliometers ($4k–$8k) on
expensive 2-axis trackers ($3k–$10k). This puts precision solar
radiometry out of reach for:

- Citizen-science atmospheric monitoring networks.
- Schools and universities teaching atmospheric science.
- Small solar farms needing DNI monitoring.
- Field campaigns in remote areas (no mains power).
- Developing countries building air quality networks.

Helio Tilt brings tracking solar radiometry to ~$74 and 120 × 80 × 60
mm, making it deployable anywhere a phone can go.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| SoC | STM32G474RET6 (ARM Cortex-M4F, 170 MHz, FPU, CORDIC, FMAC) |
| BLE / Wi-Fi bridge | ESP32-C3-MINI-1 (BLE 5, Wi-Fi 4) |
| GPS | u-blox NEO-M9N (72-channel, L1 C/A, cold start <28 s) |
| IMU | LSM6DSO (6-axis accel+gyro, ±2/±4/±8/±16 g, ±125/±250/±500/±1000/±2000 dps) |
| Magnetometer | MMC5603NJ (3-axis, ±30 G, 0.002°/√Hz noise) |
| Detector | MLX90614ESF-DCC thermopile (5.5–14 µm repurposed for solar, or thin-film thermopile) |
| ADC | ADS122U04 (24-bit ΔΣ, 20 Hz, PGA 1–128×, 4-channel) |
| Filter wheel | 6-position: 405, 440, 675, 870, 940, 1640 nm (10 nm FWHM interference filters) |
| Collimator | 5° field-of-view tube, 30 mm aperture, 350 mm focal length |
| Azimuth drive | NEMA8 stepper, 200 steps/rev, 1/16 microstep → 0.025° resolution |
| Elevation drive | NEMA8 stepper + timing belt, 1/16 microstep → 0.025° resolution |
| DNI range | 0–1400 W/m² |
| DNI resolution | ~0.5 W/m² (24-bit ADC, 0.18 µV/LSB at PGA=128) |
| DNI accuracy | ±5% (uncalibrated), ±2% (Langley-calibrated) |
| AOD range | 0.0–3.0 |
| AOD resolution | 0.001 |
| AOD accuracy | ±0.01 (Langley-calibrated, stable conditions) |
| Wavelengths | 405, 440, 675, 870, 940, 1640 nm |
| Solar position accuracy | ±0.01° (NOAA/SPA truncated) |
| Tracking accuracy | ±0.1° (stepper + IMU feedback) |
| Display | 1.3" OLED 128×64 I2C (SH1106) — DNI/AOD plot + status |
| Logging | microSD (FAT32, CSV, AERONET-compatible format) |
| Wireless | BLE 5 (ESP32-C3 bridge) — live DNI/AOD streaming |
| Power | 18650 Li-ion (3.7 V, 2600 mAh) — ~10 h continuous tracking |
| Form factor | 120 × 80 × 60 mm (tracking head + base) |
| Weight | ~280 g (with battery) |
| BOM cost | ~$74 |

## Block Diagram

```
                       ┌────────────────────────────────────────────┐
                       │           STM32G474RET6 (U1)                │
                       │  ┌──────────────────────────────────────┐ │
                       │  │ Cortex-M4F 170 MHz · CORDIC · FMAC   │ │
                       │  │ 5× ADC · 4× DAC · HRTIM · 2× TIM      │ │
                       │  └──────────────────────────────────────┘ │
                       │                                            │
                       │  I2C1 ──▶ SH1106 OLED + LSM6DSO IMU        │
                       │  I2C2 ──▶ MMC5603NJ magnetometer           │
                       │  SPI1 ──▶ microSD                          │
                       │  SPI2 ──▶ W25Q128 (data buffer)             │
                       │  UART1 ─▶ ESP32-C3 (BLE bridge)             │
                       │  UART2 ─▶ NEO-M9N GPS                       │
                       │  TIM1 ──▶ ADS122U04 ADC (SPI-like)          │
                       │  TIM2 ──▶ Azimuth NEMA8 stepper (A4988)     │
                       │  TIM3 ──▶ Elevation NEMA8 stepper (A4988)   │
                       │  TIM4 ──▶ Filter wheel servo (SG90)         │
                       │  ADC1 ─◀ Battery voltage monitor            │
                       └────────────────────────────────────────────┘
                          │      │      │      │       │       │
                     ┌────┘  ┌───┘  ┌───┘  ┌───┘  ┌────┘  ┌────┘
                     ▼       ▼     ▼       ▼     ▼       ▼
              ┌──────────┐┌────┐┌─────┐┌────┐┌─────┐┌──────┐
              │OLED      ││SD  ││ADS  ││GPS ││IMU+ ││ESP32-│
              │128×64    ││FAT ││122  ││NEO ││Mag  ││C3 BLE│
              │plot      ││32  ││U04  ││M9N ││LSM  ││bridge│
              └──────────┘└────┘└──┬──┘└────┘│+MMC │└──────┘
                                 │          └─────┘
                                 ▼
                          ┌──────────────┐
                          │ Thermopile   │
                          │ detector     │
                          │ + filter     │
                          │ wheel        │
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │ Collimator   │
                          │ tube (5° FOV)│
                          │ 2-axis mount │
                          │ AZ + EL stepp│
                          └──────────────┘
                                 │
                          ┌──────▼───────┐
                          │    ☀  SUN     │
                          └──────────────┘

  Optical path:  Sun → collimator tube (5° FOV) → filter wheel (6-pos)
                 → thermopile detector → ADS122U04 ADC (24-bit)
                 → DNI/AOD computation → OLED/SD/BLE

  Tracking:  GPS (lat/lon/time) → solar position (NOAA/SPA)
             → IMU tilt + magnetometer heading
             → AZ/EL stepper angles → NEMA8 motors → collimator points at sun
```

## Pin Assignments (STM32G474RET6 — LQFP64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0  | ADC1_IN1 (battery V divider)           | Analog in  | 2:1 divider on Vbat |
| PA1  | GPIO (ADS122U04 CS)                    | Output     | Active-low, ADC chip select |
| PA2  | SPI3_SCK (ADS122U04 clock)             | SPI out    | 2 MHz, ADC serial clock |
| PA3  | SPI3_MISO (ADS122U04 DOUT/DRDY)        | SPI in     | ADC data + data-ready |
| PA4  | SPI3_MOSI (ADS122U04 DIN)              | SPI out    | ADC config commands |
| PA5  | GPIO (ADS122U04 START/SYNC)            | Output     | Active-high, start conversion |
| PA6  | GPIO (thermopile shutter/calib)        | Output     | Optional calibration shutter |
| PA7  | GPIO (A4988 AZ enable)                 | Output     | Active-low, azimuth stepper |
| PA8  | TIM1_CH1 (ADS122U04 DRDY ext. IRQ)     | Input(irq) | Data-ready falling edge |
| PA9  | USART1_TX (ESP32-C3 bridge)            | UART out   | 921600 baud |
| PA10 | USART1_RX (ESP32-C3 bridge)            | UART in    | 921600 baud |
| PA11 | I2C1_SDA (OLED + LSM6DSO)              | I2C        | 400 kHz |
| PA12 | I2C1_SCL (OLED + LSM6DSO)              | I2C        | 400 kHz |
| PA13 | SPI1_SCK (microSD)                     | SPI out    | 25 MHz max |
| PA14 | SPI1_MISO (microSD)                    | SPI in     | SD card data |
| PA15 | SPI1_MOSI (microSD)                    | SPI out    | SD card data |
| PB0  | GPIO (mode button)                     | Input(pu)  | Long-press = menu |
| PB1  | GPIO (start/stop button)               | Input(pu)  | Start tracking / abort |
| PB2  | GPIO (calibrate button)                | Input(pu)  | Trigger Langley calibration |
| PB3  | SPI2_SCK (W25Q128 flash)               | SPI out    | 50 MHz |
| PB4  | SPI2_MISO (W25Q128 flash)              | SPI in     | Flash data |
| PB5  | SPI2_MOSI (W25Q128 flash)              | SPI out    | Flash data |
| PB6  | GPIO (W25Q128 CS)                      | Output     | Flash chip select |
| PB7  | GPIO (SD card detect)                  | Input(pu)  | SD card inserted |
| PB8  | TIM4_CH1 (filter wheel servo PWM)      | PWM out    | 50 Hz, SG90 servo |
| PB9  | GPIO (A4988 EL enable)                 | Output     | Active-low, elevation stepper |
| PB10 | GPIO (A4988 AZ direction)              | Output     | Azimuth dir |
| PB11 | GPIO (A4988 AZ step)                   | Output     | Azimuth step pulses |
| PB12 | GPIO (A4988 EL direction)              | Output     | Elevation dir |
| PB13 | GPIO (A4988 EL step)                   | Output     | Elevation step pulses |
| PB14 | GPIO (status LED 1: tracking)          | Output     | Green LED |
| PB15 | GPIO (status LED 2: calibrating)       | Output     | Blue LED |
| PC0  | I2C2_SDA (MMC5603NJ magnetometer)      | I2C        | 400 kHz |
| PC1  | I2C2_SCL (MMC5603NJ magnetometer)      | I2C        | 400 kHz |
| PC2  | USART2_TX (NEO-M9N GPS)                | UART out   | 38400 baud |
| PC3  | USART2_RX (NEO-M9N GPS)                | UART in    | 38400 baud |
| PC4  | GPIO (GPS PPS)                         | Input(irq) | 1 PPS rising edge |
| PC5  | GPIO (A4988 AZ/EL microstep MS1)       | Output     | Shared MS1 for both |
| PC6  | GPIO (A4988 AZ/EL microstep MS2)       | Output     | Shared MS2 for both |
| PC7  | GPIO (AZ home switch)                  | Input(pu)  | Limit switch for azimuth |
| PC8  | GPIO (EL home switch)                  | Input(pu)  | Limit switch for elevation |
| PC9  | GPIO (WS2812B status)                  | Output     | RGB status LED |
| PC10 | GPIO (filter wheel home)               | Input(pu)  | Optical slot sensor |
| PC11 | GPIO (GPS enable)                      | Output     | Active-high, GPS power |
| PC12 | GPIO (A4988 MS3)                       | Output     | 1/16 microstep |
| PC13 | GPIO (BOOT0 / debug)                   | Input      | Debug probe |
| PC14 | GPIO (reserved / expansion)            | —          | Expansion |
| PC15 | GPIO (reserved / expansion)            | —          | Expansion |

## Schematic Overview

The schematic (in `schematic/helio_tilt.kicad_sch`) is organized into
these sections:

### 1. Power
- USB-C 5 V → TP4056 charger → 18650 cell → MCP1640B boost (3.7→5 V)
- AP2112-3.3 (digital 3.3 V), LP5907-3.3 (analog 3.3 V)
- Ferrite beads (BLM18PG121) isolate analog/digital ground planes

### 2. SoC
- STM32G474RET6 (LQFP-64, 170 MHz Cortex-M4F, 512 KB flash, 128 KB SRAM)
- HSI 16 MHz → PLL → 170 MHz SYSCLK
- CORDIC for solar position trig (sin/cos/atan2 acceleration)
- HRTIM for stepper pulse generation

### 3. GPS (NEO-M9N)
- UART2 at 38400 baud, NMEA 4.1 protocol
- PPS output on PC4 for microsecond time tagging
- Active-high power enable on PC11 (power-gate for energy saving)
- Chip antenna (on NEO-M9N module)

### 4. IMU & Magnetometer
- LSM6DSO (I2C1, 0x6A): 6-axis accelerometer + gyroscope for tilt
- MMC5603NJ (I2C2, 0x60): 3-axis magnetometer for absolute heading
- Sensor fusion: accelerometer → roll/pitch; magnetometer → heading
- Tilt compensation: corrects azimuth for non-level mounting

### 5. Optical Detector
- Collimator tube: 30 mm aperture, 350 mm focal length, 5° FOV
- Filter wheel: 6-position rotating disk with narrow-band filters
  - 405 nm (10 nm FWHM) — aerosol, SO₂ absorption
  - 440 nm (10 nm FWHM) — aerosol, ocean color
  - 675 nm (10 nm FWHM) — vegetation, aerosol
  - 870 nm (10 nm FWHM) — aerosol reference (AERONET standard)
  - 940 nm (10 nm FWHM) — water vapor absorption band
  - 1640 nm (75 nm FWHM) — coarse aerosol, dust
- Thermopile detector: thin-film thermopile (2.0 mm active area,
  5.5–14 µm standard but repurposed for solar by using a
  blackened absorber, 50 µV/(W/m²) sensitivity)
- ADS122U04 24-bit ΔΣ ADC: PGA 1–128×, 20 Hz data rate, SPI config
- ADC reads thermopile Seebeck voltage with ~0.18 µV/LSB at PGA=128

### 6. Tracking Mechanism
- Azimuth: NEMA8 stepper (200 steps/rev, 1/16 microstep = 3200 steps/rev)
  drives a turntable via worm gear (60:1) → 0.011° resolution
- Elevation: NEMA8 stepper drives elevation arm via timing belt (2:1)
  → 0.025° resolution
- A4988 stepper drivers (one per axis), microstep config MS1/MS2/MS3
- Home switches (PC7 azimuth, PC8 elevation) for initial calibration
- Filter wheel: SG90 servo (TIM4, 50 Hz PWM) rotates the 6-position
  wheel; optical slot sensor (PC10) detects home position

### 7. Memory / Logging
- microSD (SPI1, FAT32): CSV measurement log (AERONET-compatible format)
- W25Q128 (SPI2, 16 MB): data ring buffer for BLE streaming

### 8. Display
- SH1106 1.3" 128×64 OLED (I2C1, 0x3D): real-time DNI/AOD + sun position

### 9. BLE Bridge
- ESP32-C3-MINI-1 (USART1, 921600 baud): BLE 5 + Wi-Fi 4 streaming

### 10. UI
- EC11 rotary encoder + 3 tactile buttons (Mode, Start/Stop, Calibrate)
- 2 status LEDs (tracking green, calibrating blue) + WS2812B RGB

## Power Architecture

```
USB-C 5V ──▶ TP4056 ──▶ 18650 (3.7V 2600mAh)
                              │
                              ▼
                        MCP1640B boost (3.7→5V, 500mA)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              AP2112-3.3   LP5907-3.3  Steppers
              (digital)    (analog)   (5V, A4988)
                    │         │
                    ▼         ▼
              STM32G474   ADS122U04
              ESP32-C3    Thermopile
              SH1106 OLED  LSM6DSO
              SD, W25Q128  MMC5603NJ
              GPS, IMU
```

Power budget:
- STM32G474 @ 170 MHz: ~45 mA
- ESP32-C3 (BLE): ~25 mA
- OLED: ~20 mA
- GPS (active): ~35 mA
- ADS122U04 + thermopile: ~2 mA
- LSM6DSO + MMC5603NJ: ~2 mA
- SD card (write): ~30 mA (peak)
- NEMA8 steppers (2×, tracking): ~200 mA (both axes, microstep)
- Filter wheel servo (idle): ~10 mA
- Total during tracking: ~370 mA → 2600 mAh / 370 mA ≈ 7 h continuous
- With intermittent filter sweeps: ~10 h

## Solar Position Algorithm

The firmware implements a truncated version of the NOAA Solar
Position Algorithm (SPA), accurate to ~0.01°:

1. **Julian Day** from GPS UTC date/time
2. **Julian Century** (T = (JD - 2451545.0) / 36525)
3. **Geometric Mean Longitude** (L₀ = 280.46646° + T × 36000.76983°)
4. **Geometric Mean Anomaly** (M = 357.52911° + T × 35999.05029°)
5. **Eccentricity** (e = 0.016708634 - T × 0.000042037)
6. **Sun Equation of Center** (C, series expansion in M)
7. **True Longitude / Anomaly** (L = L₀ + C, ν = M + C)
8. **Apparent Longitude** (θ = L - 0.00569° - 0.00478° × sin(N))
9. **Obliquity of Ecliptic** (ε, with nutation correction)
10. **Right Ascension / Declination** (α, δ from θ, ε)
11. **Hour Angle** (H from observer longitude + sidereal time)
12. **Solar Zenith / Azimuth** (θ_z, φ from δ, H, observer latitude)
13. **Atmospheric Refraction** (Saemundsson formula, elevations >5°)

The CORDIC accelerator handles all trig functions (sin, cos, atan2)
in hardware, reducing computation from ~2 ms (software float) to
~0.1 ms per solar position update.

## AOD Computation

### Beer-Lambert-Bouguer Law

Solar irradiance at ground level:
```
V(λ) = V₀(λ) × exp(-τ_total(λ) × m(θ))
```
where:
- V(λ) = measured voltage at wavelength λ
- V₀(λ) = extraterrestrial calibration constant (Langley)
- τ_total = τ_Rayleigh + τ_aerosol + τ_ozone + τ_water + τ_gas
- m(θ) = relative optical air mass at zenith angle θ

### Aerosol Optical Depth
```
τ_aero(λ) = [ln(V₀(λ)) - ln(V(λ))] / m(θ) - τ_Rayleigh(λ) - τ_ozone(λ) - τ_gas(λ)
```
- Rayleigh: τ_R = 0.00864 × λ⁻⁴ × (P/P₀) (λ in µm, P in hPa)
- Ozone: τ_O₃ = α_O₃(λ) × U_O₃ (U_O₃ = 0.3 cm from climatology)
- Gas: negligible at these wavelengths except 940 nm (water vapor)

### Precipitable Water Vapor (940 nm)
```
PWV = [ln(V₀(940)) - ln(V(940)) - τ_aero(940)×m] / (m × k(940))
```
where k(940) is the water vapor absorption coefficient (calibrated).

### Ångström Exponent
```
α = -ln(τ_aero(λ₁)/τ_aero(λ₂)) / ln(λ₁/λ₂)
```
A 2-wavelength fit (440/870 nm) gives α, indicating aerosol size
distribution: α > 1.5 = fine mode (urban/industrial), α < 0.5 =
coarse mode (dust/sea salt).

### Langley Calibration
On a clear stable day, plot ln(V(λ)) vs. air mass m(θ) over 2–3
hours. Linear regression: ln(V) = ln(V₀) - τ × m. The y-intercept
gives ln(V₀), the extraterrestrial constant. The slope gives the
total optical depth τ. This self-calibration requires no reference
instrument and is the gold standard for sun photometry.

## Grounding

- **AGND / DGND split**: analog ground (ADS122U04, thermopile,
  LP5907, LSM6DSO analog) ties to AGND; digital ground (STM32,
  ESP32-C3, OLED, SD, GPS) ties to DGND. They meet at a single
  star point under the STM32.
- **Thermopile shielding**: the thermopile case is tied to AGND
  to minimize 50/60 Hz pickup and thermoelectric EMF at junctions.
- **GPS antenna**: the NEO-M9N module's patch antenna is on the
  top face of the enclosure, away from the steppers and OLED.

## Firmware Architecture

The firmware is organized into modular C files:

| Module | File | Function |
|--------|------|----------|
| System | `main.c` | Top-level state machine + main loop |
| Config | `stm32g474_conf.h` | Clock, peripheral, parameter defines |
| Solar position | `solar_pos.c/h` | NOAA/SPA truncated algorithm |
| GPS | `gps.c/h` | NEO-M9N NMEA parsing, PPS time sync |
| IMU | `imu.c/h` | LSM6DSO + MMC5603NJ fusion, tilt/heading |
| Stepper | `stepper.c/h` | NEMA8 AZ/EL drive, microstep, home |
| Filter wheel | `filter_wheel.c/h` | SG90 servo, 6-position rotation |
| Detector | `detector.c/h` | ADS122U04 ADC, thermopile read, PGA |
| Radiometry | `radiometry.c/h` | DNI calibration, AOD, PWV, Ångström |
| Langley | `langley.c/h` | Langley regression calibration |
| Display | `display.c/h` | OLED: DNI/AOD plot + status |
| SD logging | `sd_log.c/h` | CSV (AERONET-compatible format) |
| BLE bridge | `ble_bridge.c/h` | UART protocol to ESP32-C3 |
| Battery | `battery.c/h` | 18650 voltage monitor |
| UI | `ui.c/h` | Encoder + buttons + menu |

### State Machine

```
IDLE → MENU → (set site, Langley mode, wavelength set)
  → GPS_FIX (acquire GPS position + time, <30 s)
  → LEVEL (read IMU, compute tilt + heading offset)
  → HOME (home AZ + EL steppers using limit switches)
  → TRACK (compute sun position, point collimator, measure DNI)
  → SWEEP (rotate filter wheel through 6 wavelengths, measure AOD)
  → COMPUTE (AOD, PWV, Ångström exponent)
  → LOG (SD card CSV, BLE stream)
  → TRACK (loop back, continuous tracking at 1 Hz)
  → LANGLEY (optional: 2-3 hr calibration run)
  → IDLE (on stop or sunset)
```

### Main Loop Timing

- **1 kHz**: stepper pulse generation, IMU read, UI poll
- **1 Hz**: solar position update, sun tracking correction, DNI measurement
- **0.1 Hz**: filter wheel sweep (6 wavelengths, ~12 s per full sweep)
- **10 Hz**: BLE status stream
- **1 Hz**: SD card logging (every measurement)
- **0.1 Hz**: OLED display update

## BOM

See `hardware/BOM.csv` for the full bill of materials. Key cost
drivers:

| Part | Cost | Note |
|------|------|------|
| STM32G474RET6 | $6.40 | SoC |
| ESP32-C3-MINI-1 | $2.70 | BLE/WiFi bridge |
| NEO-M9N GPS module | $7.50 | 72-channel L1 GNSS |
| LSM6DSO | $2.50 | 6-axis IMU |
| MMC5603NJ | $1.80 | 3-axis magnetometer |
| ADS122U04 | $3.20 | 24-bit ΔΣ ADC |
| Thermopile detector | $4.50 | Thin-film thermopile |
| Interference filters (6×) | $6.00 | 405/440/675/870/940/1640 nm |
| NEMA8 steppers (2×) | $8.00 | AZ + EL drive |
| A4988 drivers (2×) | $2.00 | Stepper drivers |
| SG90 servo | $1.50 | Filter wheel rotation |
| Collimator tube | $3.00 | 30 mm aperture, 350 mm FL |
| SH1106 OLED | $2.80 | 128×64 display |
| W25Q128 flash | $1.10 | Data buffer |
| PCB (4-layer, 80×50 mm) | $4.00 | JLCPCB |
| **Total** | **~$74** | |

## Applications

### AERONET Citizen-Science Network
Deploy in schools, rural areas, and developing countries to
augment the AERONET sun photometer network. Data in AERONET-
compatible CSV format can be submitted to the network.

### Solar Energy Site Assessment
Measure DNI over weeks/months to assess concentrating solar power
(CSP) site feasibility. DNI > 6 kWh/m²/day is the threshold for
viable CSP.

### Air Quality Monitoring
AOD correlates with surface PM2.5. Use Helio Tilt as a
column-integrated aerosol reference alongside surface PM sensors
for calibration and satellite validation.

### Volcanic Ash Tracking
After eruptions, deploy rapidly to measure AOD spikes at 6
wavelengths. The Ångström exponent distinguishes fine volcanic ash
(α > 1.5) from coarse ash (α < 1.0).

### Education
Teach atmospheric science hands-on: solar position, Beer-Lambert
law, Langley calibration, aerosol physics, and remote sensing
principles — all from a pocket device.

### Precipitable Water Vapor
The 940 nm channel measures column water vapor for weather
forecasting validation and greenhouse effect studies.

## Assembly

See `docs/assembly-guide.md` for detailed assembly instructions.

## Calibration

1. **Initial**: Point at sun manually, verify DNI matches a
   reference pyranometer within ±10%.
2. **Langley**: On a clear stable day, run Langley calibration mode
   (2–3 hours morning or evening). The device self-calibrates V₀(λ).
3. **Field**: Re-calibrate monthly or after filter changes. The
   Langley regression quality (R²) is reported; R² > 0.99 indicates
   a good calibration.

## License

MIT — build it, sell it, improve it.