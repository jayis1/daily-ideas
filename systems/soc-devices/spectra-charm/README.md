# Spectra Charm — Pocket UV-Vis Spectrophotometer

A credit-card-thin, battery-powered UV-Vis spectrophotometer that fits in your pocket and identifies substances by their light absorption fingerprint. Drop a sample in the integrated cuvette well, press one button, and get a full 340–700 nm absorption spectrum in 3 seconds — with on-device spectral matching against a 200-compound library and BLE/Wi-Fi results to your phone.

## What It Does

| Mode | Description |
|------|-------------|
| **Spectrum Scan** | Full 340–700 nm absorption scan in ~3 s, 128-point resolution |
| **Compound ID** | Match sample against built-in library (200+ compounds: food dyes, water contaminants, pharmaceuticals, essential oils) |
| **Concentration** | Beer-Lambert quantification for matched compounds with known molar absorptivity |
| **Trend Track** | Log scans over time via BLE app, monitor degradation or reaction progress |
| **Custom Library** | Add your own reference spectra via companion app, stored in SPI flash |

## Why This Device Exists

Lab spectrophotometers cost $3,000–$15,000, weigh 5–15 kg, and take minutes per sample. Spectra Charm delivers 90 % of the capability in a 50 g pocket device at $80 BOM. Use cases:

- **Food & beverage QC** — verify dye concentrations, detect adulteration
- **Aquarium / hydroponics** — measure nitrate, phosphate, dissolved organics (with reagent kits)
- **Education** — teach spectroscopy hands-on in any classroom
- **Field science** — water quality screening without hauling a lab spectrophotometer
- **Essential oils & cosmetics** — verify authenticity by spectral fingerprint
- **Home brewing** — monitor IBU (bitterness units) via UV absorption

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Spectra Charm                     │
│                                                     │
│  ┌──────────┐    I2C     ┌──────────────────────┐   │
│  │ EEPROM    │◄──────────│                      │   │
│  │ (cal)     │           │   STM32G491RET6      │   │
│  └──────────┘           │   (Spectrometer MCU)  │   │
│                         │                        │   │
│  ┌──────────┐    SPI    │  • 12-bit ADC × 5     │   │
│  │ AS7343   │◄──────────│  • Op-amp × 4 (int.)  │   │
│  │ (sensor) │           │  • DAC × 2 (int.)      │   │
│  └──────────┘           │  • FPU (Cortex-M4F)    │   │
│                         │                        │   │
│  ┌──────────┐    SPI    │  • FFT / baseline corr │   │
│  │ W25Q128  │◄──────────│  • Spectral matching   │   │
│  │ (flash)  │           │  • Beer-Lambert calc   │   │
│  └──────────┘           └──────────┬─────────────┘   │
│                                    │ UART            │
│  ┌──────────┐                      ▼                 │
│  │ SSD1306  │    I2C     ┌──────────────────────┐    │
│  │ (OLED)   │◄──────────│   ESP32-C3-MINI-1    │    │
│  └──────────┘           │   (Wireless + UI)     │    │
│                         │                        │    │
│  ┌──────────┐           │  • BLE 5.0             │    │
│  │ Broadband│   GPIO    │  • WiFi (config/OTA)   │    │
│  │ LED src  │◄──────────│  • Button / OLED UI   │    │
│  └──────────┘           │  • JSON spectrum API   │    │
│                         └────────────────────────┘   │
│  ┌──────────┐    I2C                                 │
│  │ BQ27441  │  (fuel gauge)                          │
│  └──────────┘                                        │
│  ┌──────────┐    I2C                                 │
│  │ TP4056+  │  (charger)                             │
│  │ DW01A    │                                        │
│  └──────────┘                                        │
│                                                     │
│  ┌──────────────────────────────┐                   │
│  │  LiPo 1000 mAh   │  USB-C   │                    │
│  └──────────────────────────────┘                   │
└─────────────────────────────────────────────────────┘
```

## SoC Selection Rationale

### STM32G491RET6 — Spectrometer MCU
- **Internal op-amps (4×)** — eliminates external signal conditioning ICs; configurable gain for the photodiode front-end
- **12-bit ADC at 4 Msps** — oversample to 16-bit effective resolution for the photodiode signal
- **Internal DACs (2×)** — programmable reference voltage for the broadband LED driver
- **Cortex-M4F** — hardware FPU for real-time FFT, baseline correction, and spectral matching
- **128 KB Flash, 32 KB SRAM** — enough for firmware + 200-compound spectral library

### ESP32-C3-MINI-1 — Wireless + UI MCU
- **BLE 5.0** — low-power spectrum streaming to phone app
- **WiFi** — OTA firmware updates, JSON REST API on local network
- **RISC-V 160 MHz** — handles OLED UI, button debouncing, JSON encoding
- **Tiny footprint** — 16.5 × 20.5 mm module

## Light Path & Optics

```
         ┌──────────────────────────┐
         │    Cuvette Well (1 cm)    │
         │                          │
  LED ──►│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │──► Diffuser ──► AS7343
  src    │  ▓▓▓▓  sample   ▓▓▓▓  │    (integrating)
         │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │
         │                          │
         └──────────────────────────┘

  Light source: Broadband white LED (400-700 nm) + UV LED (340-400 nm)
  Detector:     AS7343 10-channel spectrometer (8 visible + NIR + clear)
  Path length:  10 mm standard cuvette
  Diffuser:     PTFE integrating disc before AS7343 aperture
```

The AS7343 provides 10 spectral channels at fixed wavelengths (F1: 415 nm, F2: 445 nm, F3: 480 nm, F4: 515 nm, F5: 555 nm, F6: 590 nm, F7: 630 nm, F8: 680 nm, NIR: 910 nm, Clear: broad). We supplement the 8 visible channels by sweeping the broadband LED current (via DAC) and the UV LED on/off to get 128 effective spectral points across 340–700 nm using a deconvolution algorithm that leverages the known LED spectral power distribution.

## Pin Assignments

### STM32G491RET6 (LQFP-64)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| PA0 | ADC1_IN1 (PD signal) | Analog In | AS7343 clear channel → internal op-amp → ADC |
| PA1 | ADC1_IN2 (PD aux) | Analog In | Backup photodiode channel |
| PA2 | OPAMP1_VINP | Analog In | Non-inverting input for PD preamp |
| PA3 | OPAMP1_VOUT | Analog Out | Internal op-amp output → ADC |
| PA4 | DAC1_OUT1 | Analog Out | LED driver reference voltage (white LED) |
| PA5 | DAC1_OUT2 | Analog Out | UV LED current setpoint |
| PA6 | SPI1_MISO | Digital In | SPI data from AS7343 |
| PA7 | SPI1_MOSI | Digital Out | SPI data to AS7343 |
| PA8 | UV_LED_EN | Digital Out | UV LED enable (active high) |
| PA9 | UART1_TX | Digital Out | UART to ESP32-C3 |
| PA10 | UART1_RX | Digital In | UART from ESP32-C3 |
| PA11 | SPI1_NSS | Digital Out | AS7343 chip select |
| PA12 | SPI1_SCK | Digital Out | SPI clock to AS7343 |
| PB0 | ADC2_IN3 (temp) | Analog In | Internal junction temperature |
| PB1 | SPI2_MISO | Digital In | SPI data from W25Q128 |
| PB2 | SPI2_MOSI | Digital Out | SPI data to W25Q128 |
| PB3 | SPI2_SCK | Digital Out | SPI clock to W25Q128 |
| PB4 | SPI2_NSS | Digital Out | W25Q128 chip select |
| PB5 | I2C1_SDA | Bidirectional | EEPROM + BQ27441 |
| PB6 | I2C1_SCL | Digital Out | I2C clock |
| PB7 | AS7343_INT | Digital In | AS7343 data-ready interrupt |
| PB8 | LED_DRV_FAULT | Digital In | LED driver fault flag |
| PB9 | WHITE_LED_EN | Digital Out | White LED enable |
| PC0 | OPAMP2_VINP | Analog In | Secondary op-amp input |
| PC1 | OPAMP2_VOUT | Analog Out | Secondary op-amp output |
| PC6 | SHUTDOWN_N | Digital Out | Power rail enable (active low) |
| PC7 | BUTTON1 | Digital In | Scan trigger button |
| PC8 | BUTTON2 | Digital In | Mode select button |
| PC9 | ESP_BOOT | Digital Out | ESP32-C3 boot mode select |
| PC10 | ESP_RST_N | Digital Out | ESP32-C3 reset |
| PC11 | STATUS_LED_G | Digital Out | Green status LED |
| PC12 | STATUS_LED_R | Digital Out | Red status LED |
| PC13 | STATUS_LED_B | Digital Out | Blue status LED |
| PD2 | AS7343_LDR | Digital Out | AS7343 LDR pin (gain select) |

### ESP32-C3-MINI-1

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| GPIO0 | UART0_TX | Digital Out | UART to STM32G491 |
| GPIO1 | UART0_RX | Digital In | UART from STM32G491 |
| GPIO2 | I2C_SDA | Bidirectional | SSD1306 OLED |
| GPIO3 | I2C_SCL | Digital Out | SSD1306 OLED |
| GPIO4 | OLED_RST | Digital Out | SSD1306 reset |
| GPIO5 | CHARGE_STAT | Digital In | TP4056 charge status |
| GPIO6 | VBUS_DET | Digital In | USB-C VBUS detect |
| GPIO7 | USER_BTN | Digital In | Power/user button |
| GPIO8 | LED_WS2812 | Digital Out | RGB indicator LED |
| GPIO9 | BOOT_BTN | Digital In | Boot button |
| GPIO10 | SPI_CS_FLASH | Digital Out | (reserved) |
| GPIO18 | USB_D- | Bidirectional | USB data- |
| GPIO19 | USB_D+ | Bidirectional | USB data+ |
| GPIO20 | USB5V_OUT | Digital Out | (reserved) |
| GPIO21 | STRAP_BOOT | Bidirectional | Boot strapping |

## Power Architecture

```
          USB-C
            │
            ▼
      ┌───────────┐
      │  TP4056   │───── VBAT (3.7-4.2V LiPo 1000 mAh)
      │  +DW01A   │───── PROG (1A charge)
      │  (charger)│───── CHG_STAT → ESP32
      └───────────┘
            │
            ▼ VBAT
      ┌───────────┐
      │  BQ27441  │───── I2C fuel gauge → STM32
      │  (gauge)  │───── Coulomb counter
      └───────────┘
            │
            ▼ VBAT
      ┌───────────────┐
      │  TPS63020     │───── 3.3V rail (MCU, sensors, OLED)
      │  (buck-boost) │───── 2A output, 96% eff.
      └───────────────┘
            │
            ▼ 3.3V
      ┌───────────────┐
      │  AP2112-3.3   │───── 3.3V low-noise (ADC reference, op-amps)
      │  (LDO)        │───── PSRR >70dB
      └───────────────┘

  LED Driver:
      VBAT ──► AL8805 (buck LED driver) ──► White LED (350 mA max)
      3.3V ──► DAC1 → AL8805 ADJ ──► current control
      3.3V ──► UV LED via MOSFET (UV_LED_EN)

  Power budget:
    • Idle (OLED on, BLE connected):  ~15 mA → ~66 hrs
    • Scanning (LED + AS7343 + MCU):   ~250 mA → ~4 hrs continuous
    • Typical intermittent use:        ~30 mA avg → ~33 hrs
```

## Firmware Overview

### STM32G491 — Spectrometer Firmware (bare-metal, HAL)

```
firmware/
├── Core/
│   ├── Src/
│   │   ├── main.c           — RTOS tasks, init
│   │   ├── spectrometer.c   — AS7343 driver, spectral acquisition
│   │   ├── deconv.c         — Spectral deconvolution algorithm
│   │   ├── matching.c       — Library matching (cosine similarity)
│   │   ├── baseline.c       — Dark/baseline correction
│   │   ├── beerlambert.c    — Concentration calculation
│   │   ├── led_driver.c     — LED current control via DAC
│   │   ├── flash_store.c    — W25Q128 spectral library R/W
│   │   ├── uart_proto.c     — Binary protocol to ESP32-C3
│   │   ├── eeprom.c         — Calibration constants (24C02)
│   │   ├── fuel_gauge.c     — BQ27441 driver
│   │   └── power.c          — Sleep/wake, rail control
│   ├── Inc/
│   │   ├── spectrometer.h
│   │   ├── deconv.h
│   │   ├── matching.h
│   │   ├── baseline.h
│   │   ├── beerlambert.h
│   │   ├── led_driver.h
│   │   ├── flash_store.h
│   │   ├── uart_proto.h
│   │   ├── eeprom.h
│   │   ├── fuel_gauge.h
│   │   └── power.h
│   └── Startup/
├── Drivers/
│   └── STM32G4_HAL_Driver/
├── Middlewares/
│   └── FreeRTOS/
├── CMakeLists.txt
└── stm32g491ret6.ld
```

### ESP32-C3 — Wireless + UI Firmware (ESP-IDF)

```
firmware/esp32c3/
├── main/
│   ├── main.c            — App entry, WiFi/BLE init
│   ├── ble_spectrum.c    — BLE GATT server (spectrum service)
│   ├── wifi_api.c        — REST API endpoints (JSON)
│   ├── oled_ui.c         — SSD1306 display manager
│   ├── uart_comm.c       — UART protocol to STM32G491
│   ├── button.c          — Button handler with debouncing
│   ├── led_indicator.c   — WS2812 RGB LED control
│   ├── ota_update.c      — Over-the-air firmware update
│   └── storage.c         — NVS key-value storage
├── components/
│   └── ssd1306/
├── CMakeLists.txt
└── sdkconfig
```

## Spectral Acquisition Pipeline

1. **Dark reference** — acquire spectrum with LEDs off (offsets detector dark current + ambient)
2. **Blank reference** — acquire spectrum with empty cuvette / solvent only (I₀)
3. **Sample scan** — acquire spectrum with sample in cuvette (I)
4. **Absorbance** — A(λ) = −log₁₀(I/I₀) per channel
5. **Deconvolution** — use LED SPD model + channel response curves to interpolate 128-point spectrum
6. **Baseline correction** — subtract polynomial baseline (scattering correction)
7. **Peak detection** — find local maxima above threshold
8. **Library match** — cosine similarity against stored reference spectra
9. **Quantification** — for matched compound, calculate concentration via A = ε·c·l

## BLE GATT Service

| Service | UUID | Characteristics |
|---------|------|-----------------|
| Spectra Charm | 0xFEA0 | Scan Trigger (Write), Spectrum Data (Notify, 128 × float32), Compound ID (Read), Battery Level (Read), Device Info (Read) |

Spectrum data is sent as 512 bytes (128 × float32) in 20-byte BLE packets with sequence numbers.

## REST API (WiFi mode)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/scan` | POST | Trigger a new scan |
| `/api/v1/spectrum` | GET | Get last spectrum (JSON) |
| `/api/v1/match` | GET | Get compound match results |
| `/api/v1/library` | GET | List stored reference spectra |
| `/api/v1/library` | POST | Upload new reference spectrum |
| `/api/v1/config` | GET/PUT | Device configuration |
| `/api/v1/battery` | GET | Battery status |
| `/api/v1/ota` | POST | Firmware update |

## OLED User Interface

```
┌──────────────────────┐
│ ○ Spectra Charm  87% │  ← Battery + status bar
│                      │
│  ┌────────────────┐  │
│  │  /\    /\      │  │  ← Live spectrum preview
│  │ /  \  /  \ /\  │  │
│  │/    \/    V  \  │  │
│  └────────────────┘  │
│                      │
│  ▸ Scan              │  ← Menu items
│  ▸ Library           │
│  ▸ Settings          │
│                      │
│ [BTN1:Select BTN2:↕]│
└──────────────────────┘
```

## Mechanical Design

- **Form factor**: 85 × 54 × 12 mm (credit card footprint, 12 mm thick)
- **Cuvette well**: Standard 10 mm path length, accepts 1.5 mL semi-micro cuvettes
- **Case**: 3D printed PETG, snap-fit, gasket-sealed (IP52)
- **Weight**: 48 g (without cuvette)
- **Display**: 0.96" 128×64 SSD1306 OLED
- **Buttons**: 2 tactile switches (scan, mode)
- **Port**: USB-C for charging + firmware

## Bill of Materials

See `hardware/BOM.csv` for full details. Key components:

| Ref | Part | Qty | Unit Cost | Notes |
|-----|------|-----|-----------|-------|
| U1 | STM32G491RET6 | 1 | $4.50 | Spectrometer MCU |
| U2 | ESP32-C3-MINI-1 | 1 | $2.80 | Wireless MCU module |
| U3 | AS7343 | 1 | $3.20 | 10-channel spectral sensor |
| U4 | W25Q128JVSIQ | 1 | $0.85 | 16 MB SPI flash |
| U5 | 24AA02E48 | 1 | $0.30 | 2 Kb EEPROM (calibration) |
| U6 | BQ27441YZFR | 1 | $1.80 | Fuel gauge |
| U7 | TP4056 | 1 | $0.25 | LiPo charger |
| U8 | DW01A | 1 | $0.10 | Battery protection |
| U9 | TPS63020DSKR | 1 | $1.90 | Buck-boost 3.3V |
| U10 | AP2112-3.3 | 1 | $0.40 | Low-noise LDO |
| U11 | AL8805WS6-7 | 1 | $0.65 | LED buck driver |
| U12 | SSD1306 0.96" | 1 | $1.20 | OLED display module |
| D1 | Broadband white LED | 1 | $0.80 | 400-700 nm, CRI >90 |
| D2 | UV LED 365 nm | 1 | $1.20 | 340-400 nm coverage |
| D3 | WS2812B | 1 | $0.15 | RGB indicator |
| Q1-Q2 | DMN2075U (MOSFET) | 2 | $0.20 | LED switches |
| B1 | LiPo 1000 mAh | 1 | $3.50 | 402020 cell |
| SW1-SW2 | Tactile switch | 2 | $0.10 | User buttons |
| J1 | USB-C 2.0 receptacle | 1 | $0.35 | Charge + data |
| Misc | Passives, PCB, cuvette | 1 | $5.00 | R, C, inductors, 4-layer PCB |
| **Total** | | | **~$31.65** | |

## Safety

- **UV LED interlock** — UV LED disabled when cuvette removed (hall sensor)
- **Thermal shutdown** — LED driver and MCU monitor junction temp
- **Battery protection** — DW01A overcharge/overdischarge + BQ27441 coulomb counting
- **Watchdog** — Independent IWDG on STM32, task watchdog on ESP32-C3
- **USB isolation** — USB data lines have ESD protection (USBLC6-2)

## Assembly Guide

See `docs/assembly_guide.md` for step-by-step instructions including:
- Soldering the 4-layer PCB (0.4 mm pitch QFP for STM32G491)
- Aligning the AS7343 sensor with the cuvette well optical path
- Mounting the broadband LED and UV LED in the light source cavity
- Installing the PTFE integrating diffuser
- Calibrating with deionized water blank and potassium dichromate standard
- 3D printing and assembling the case

## Calibration

1. **Dark calibration** — close cuvette well, run dark scan (stores dark offsets)
2. **Blank calibration** — insert solvent-filled cuvette, run blank scan (stores I₀)
3. **Wavelength calibration** — factory calibrated with mercury-argon emission lines
4. **Linearity check** — measure potassium permanganate dilution series (R² > 0.998)
5. **Stray light check** — measure with cutoff filter (stray light < 0.1 %T)

Calibration constants stored in 24AA02E48 EEPROM, backed up to W25Q128.

## Companion App

The companion mobile app (React Native, open source) provides:
- Real-time spectrum viewer with zoom and pan
- Compound library browser and editor
- Scan history with trend plotting
- Export to CSV / JSON
- Firmware OTA updates
- Custom reagent kits for quantification (nitrate, phosphate, iron, etc.)

## Performance Specifications

| Parameter | Value |
|-----------|-------|
| Wavelength range | 340–700 nm (effective 128 points) |
| Wavelength accuracy | ±2 nm |
| Photometric range | 0–2.0 AU |
| Photometric accuracy | ±0.005 AU at 1.0 AU |
| Photometric repeatability | ±0.002 AU |
| Stray light | <0.5 %T |
| Scan time | ~3 seconds |
| Battery life | 500+ scans per charge |
| Wireless range | 10 m (BLE), 30 m (WiFi) |
| Operating temp | 5–40 °C |
| Dimensions | 85 × 54 × 12 mm |
| Weight | 48 g |

## License

MIT — build it, sell it, improve it.