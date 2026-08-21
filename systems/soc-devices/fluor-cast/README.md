# Fluor Cast — Pocket Spectrofluorometer with EEM Capability

> **Bringing $15k–$50k benchtop spectrofluorometers (Horiba FluoroMax, Agilent Cary Eclipse, Edinburgh FS5) down to ~$73 and coffee-mug size, with on-device EEM fingerprinting that no pocket instrument offers.**

---

## What It Is

**Fluor Cast** is a pocket-sized **spectrofluorometer** that measures the fluorescence emission spectrum of a liquid sample across multiple excitation wavelengths, producing a 3D **excitation-emission matrix (EEM)** — a "fluorescence fingerprint" that uniquely identifies and quantifies dissolved organic matter, fluorophores, contaminants, and biochemicals.

Unlike a simple single-wavelength fluorometer, Fluor Cast captures the full emission spectrum (350–750 nm, 256 channels) at 8 selectable excitation wavelengths (255–525 nm), building a complete EEM in under 30 seconds. On-device processing performs Rayleigh/Raman scatter masking, inner-filter-effect correction, and k-NN library matching against a 50-compound fluorescence fingerprint database.

### What Can It Measure?

| Application | Excitation | Emission | Detects |
|---|---|---|---|
| **DNA/RNA quantification** | 260/280 nm UV | 330–370 nm | PicoGreen/RiboGreen fluorescence assays |
| **Chlorophyll-a** | 440 nm | 680 nm | Algal biomass in water |
| **Dissolved Organic Matter (DOM)** | 240–470 nm scan | 300–600 nm | humic/fulvic/tryptophan-like components |
| **Oil-in-water** | 254/340 nm | 360–460 nm | Petroleum hydrocarbons (PAHs) |
| **Fluorescein/Rhodamine tracers** | 470/525 nm | 520–620 nm | Groundwater flow studies, leak detection |
| **Honey adulteration** | 360/440 nm | 400–500 nm | Sugar syrup fluorescence vs. natural honey |
| **Olive oil authenticity** | 360 nm | 400–600 nm | Chlorophyll/polyphenol fluorescence profile |
| **Riboflavin (B2) in food** | 440 nm | 520–560 nm | Milk/beer freshness indicator |
| **NADH in cell assays** | 340 nm | 450–470 nm | Metabolic activity monitoring |
| **Turbidity-independent CDOM** | 254–365 nm scan | 300–600 nm | Colored dissolved organic matter |
| **Fluorescent minerals** | 254/365 nm | 400–700 nm | Willemite, fluorite, calcite, scheelite |
| **Tryptophan in biologicals** | 280 nm | 330–370 nm | Protein content, fermentation monitoring |
| **Quinine sulfate** | 350 nm | 450–470 nm | Tonic water authenticity, fluorometer calibration |
| **Pesticides (carbaryl/organophosphates)** | 280–340 nm | 340–480 nm | Trace pesticide detection |
| **Pharmaceuticals** | 280–365 nm | 300–550 nm | Drug identification, polymorph discrimination |

---

## Key Specifications

| Parameter | Value |
|---|---|
| Excitation wavelengths | 255, 280, 340, 365, 405, 440, 470, 525 nm (LED wheel) |
| Emission range | 350–750 nm, 256 pixels (TSL1402R linear CCD) |
| Emission resolution | ~1.6 nm/pixel (with 600 lines/mm grating) |
| Excitation bandwidth | ~12 nm FWHM (LED + bandpass filter) |
| Detection geometry | 90° (right-angle fluorescence) |
| Sensitivity | ~0.1 µg/L fluorescein (with 470 nm excitation) |
| Dynamic range | >4 decades (log-amplified + multi-exposure HDR) |
| EEM acquisition time | ~25 seconds (8 excitation × 3 s per spectrum) |
| Sample volume | 200 µL (micro-cuvette), or 3 mL (standard cuvette) |
| Library size | 50 compounds/standards |
| Classification | k-NN (k=5) on 48-feature EEM vector |
| Battery | 3.7V 1800 mAh LiPo (8–12 hours continuous) |
| Dimensions | 95 × 55 × 28 mm (coffee-mug base footprint) |
| Weight | 115 g (with battery) |
| Power consumption | 180 mW idle, 650 mW measuring |
| Wireless | BLE 5.0 + Wi-Fi (via ESP32-C3) |
| Storage | MicroSD, CSV + binary EEM files |
| Display | 1.3" OLED (SH1106, 128×64) |

---

## Block Diagram

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                         FLUOR CAST                                │
 │                                                                    │
 │  ┌──────────┐    PWM     ┌───────────────┐   90° optics  ┌──────┐│
 │  │ LED Wheel│◄──────────►│  STM32G474    │◄────────────►│TSL1402││
 │  │ 8× LED + │   Stepper   │  RET6         │   SPI/GPIO   │256-px ││
 │  │ filters  │   28BYJ-48  │               │              │  CCD  ││
 │  └────┬─────┘            │  ┌──────────┐ │              └───┬──┘│
 │       │reference          │  │EEM engine│ │                  │   │
 │       ▼                   │  │k-NN lib  │ │                  │   │
 │  ┌────────┐  ADC          │  │scatter   │ │              ┌───┴──┐│
 │  │OPT101  │──────────────►│  │mask/corr │ │              │Grating││
 │  │ref pd  │               │  └──────────┘ │              │600 lp ││
 │  └────────┘               │               │              │/mm   ││
 │                            │  ┌─────┐ ┌──┐│              └──────┘│
 │  ┌────────┐    I2C        │  │OLED │ │SD││                       │
 │  │DS18B20 │──────────────►│  │SH1106│ │  ││    ┌──────────┐      │
 │  │ temp   │               │  └─────┘ └──┘│    │ESP32-C3  │      │
 │  └────────┘               │       UART    │───►│MINI-1    │      │
 │                            └───────────────┘    │BLE+WiFi  │      │
 │                                                  └──────────┘      │
 │  ┌────────────┐  USB-C charging (MCP73831)                      │
 │  │ 3.7V LiPo  │                                                  │
 │  │ 1800 mAh   │                                                  │
 │  └────────────┘                                                  │
 └──────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignments (STM32G474RET6)

| Pin | Function | Peripheral | Notes |
|---|---|---|---|
| PA0 | LED_PWM | TIM2_CH1 | Excitation LED brightness PWM |
| PA1 | REF_PD | ADC1_IN2 | OPT101 reference photodiode |
| PA2 | TEMP_ANALOG | ADC1_IN3 | Analog temp sensor (optional) |
| PA3 | CCD_AO | ADC2_IN4 | TSL1402R analog output |
| PA4 | DAC_OUT | DAC1_OUT | LED bias / CCD reference adjust |
| PA5 | CCD_SI | GPIO_OUT | TSL1402R serial-in (start integration) |
| PA6 | CCD_CLK | TIM3_CH1 | TSL1402R clock (up to 8 MHz via PWM) |
| PA7 | LED_DRV_EN | GPIO_OUT | LED driver enable |
| PA8 | STEPPER_IN1 | GPIO_OUT | 28BYJ-48 coil A+ |
| PA9 | STEPPER_IN2 | GPIO_OUT | 28BYJ-48 coil B+ |
| PA10 | STEPPER_IN3 | GPIO_OUT | 28BYJ-48 coil A- |
| PA11 | STEPPER_IN4 | GPIO_OUT | 28BYJ-28 coil B- |
| PA12 | STEPPER_HOME | GPIO_IN | Hall sensor for wheel home position |
| PB0 | CCD_RESET | GPIO_OUT | CCD pixel reset (optional) |
| PB1 | CCD_ROG | GPIO_OUT | TSL1402R readout gate |
| PB2 | BOOT1 | BOOT | Boot mode |
| PB3 | SPI1_SCK | SPI1 | SD card + OLED (shared) |
| PB4 | SPI1_MISO | SPI1 | SD card MISO |
| PB5 | SPI1_MOSI | SPI1 | SD card + OLED MOSI |
| PB6 | I2C1_SCL | I2C1 | OLED + DS18B20 (DS via 1-wire on separate pin) |
| PB7 | I2C1_SDA | I2C1 | OLED |
| PB8 | UART_TX | USART3_RX | ESP32-C3 communication (TX from STM32) |
| PB9 | UART_RX | USART3_TX | ESP32-C3 communication (RX to STM32) |
| PB10 | SD_CS | GPIO_OUT | SD card chip select |
| PB11 | OLED_CS | GPIO_OUT | OLED DC/CS |
| PB12 | OLED_DC | GPIO_OUT | OLED data/command |
| PB13 | ONEWIRE | GPIO_OD | DS18B20 1-wire bus |
| PB14 | HV_SAFE_EN | GPIO_OUT | HV interlock enable (safety) |
| PB15 | BUTTON | GPIO_IN | User button (mode select) |
| PC0 | LED_SELECT_0 | GPIO_OUT | Demux select bit 0 (LED channel) |
| PC1 | LED_SELECT_1 | GPIO_OUT | Demux select bit 1 |
| PC2 | LED_SELECT_2 | GPIO_OUT | Demux select bit 2 (3→8 decoder) |
| PC3 | CHARGE_STAT | GPIO_IN | MCP73831 charge status |
| PC4 | BATTERY_V | ADC1_IN13 | Battery voltage divider |
| PC5 | BATTERY_I | ADC1_IN14 | Battery current sense |
| PC8 | STATUS_LED_R | GPIO_OUT | Status LED red |
| PC9 | STATUS_LED_G | GPIO_OUT | Status LED green |
| PC10 | STATUS_LED_B | GPIO_OUT | Status LED blue |
| PC11 | MOTOR_EN | GPIO_OUT | Stepper enable |
| PC12 | DAC_REF | DAC2_OUT | DAC reference for CCD offset |
| PD2 | RTC_OSC | LSE | 32.768 kHz RTC crystal |

---

## Pin Assignments (ESP32-C3-MINI-1)

| Pin | Function | Notes |
|---|---|---|
| GPIO0 | BOOT | Pull-up on boot |
| GPIO1 | UART_RX | STM32 UART bridge |
| GPIO2 | UART_TX | STM32 UART bridge |
| GPIO3 | BLE_CONN | BLE connection status |
| GPIO4 | WIFI_EN | WiFi enable (active high) |
| GPIO5 | STATUS_LED | WiFi/BLE status |
| GPIO8 | SDA | I2C (optional sensor expansion) |
| GPIO9 | SCL | I2C |
| GPIO10 | CS_FLASH | External SPI flash |
| GPIO20 | USB_D+ | USB programming |
| GPIO21 | USB_D- | USB programming |

---

## Power Architecture

```
 USB-C 5V ──► MCP73831 ──► 3.7V LiPo ──► TPS63020 buck-boost ──► 3.3V rail
                               │
                               ├─► ADC battery voltage divider (PC4)
                               │
                               └─► ADC battery current (PC5, via shunt + INA181)

 3.3V rail:
   ├── STM32G474RET6  (50 mA typ)
   ├── ESP32-C3-MINI-1 (80 mA peak TX)
   ├── TSL1402R CCD  (3-5 mA)
   ├── SH1106 OLED  (12 mA, 0.1 mA standby)
   ├── OPT101 ref  (0.5 mA)
   ├── DS18B20  (1.5 mA)
   ├── LED drivers  (up to 100 mA peak per LED)
   ├── 28BYJ-48 stepper  (20 mA idle, 150 mA active)
   └── MicroSD  (100 mA write peak)

 Total: 180 mW idle, 650 mW measuring, 900 mW LED active
 Battery life: ~10 hours typical (intermittent measurement)
```

---

## Optical Architecture

### Excitation Path
1. **LED Wheel**: 8 LEDs (255, 280, 340, 365, 405, 440, 470, 525 nm) + blank position, mounted on a 3D-printed wheel rotated by a 28BYJ-48 stepper motor
2. Each LED has a dedicated narrow-bandpass filter (~12 nm FWHM) to clean up emission spectrum
3. Reference channel: OPT101 photodiode monitors each LED's actual output for ratiometric correction
4. LEDs are driven with constant current (MCP4131 digital pot + OPA548 op-amp) at 10–80 mA
5. Excitation light focused through an aspheric collimation lens into the cuvette

### Emission Path (90° geometry)
1. Fluorescence emission collected at 90° from excitation axis
2. Long-pass filter (cut-on at excitation + 10 nm) blocks scattered excitation
3. Light passes through a slit (0.2 mm) and reflective diffraction grating (600 lines/mm, blazed at 500 nm)
4. Spectrum projected onto TSL1402R 256-pixel linear CCD (350–750 nm coverage)
5. CCD readout via analog ADC sampling (PA3) with clocking (PA6) and serial-in (PA5)

### Cuvette Holder
- Standard 10mm pathlength fluorescence cuvette (all 4 sides polished)
- Black PTFE holder with spring-loaded top clip
- Optical windows: UV-transmitting quartz (for <340 nm excitation) or optical glass (for ≥340 nm)
- Interchangeable micro-cuvette adapter (200 µL volume)

---

## EEM Acquisition & Processing Pipeline

### Step 1: Raw EEM Capture
For each of 8 excitation wavelengths:
- Position LED wheel (stepper, ~0.5 s)
- Measure LED intensity via reference photodiode (OPT101)
- Pulse LED on, integrate CCD for adjustable time (50–5000 ms based on signal)
- Read 256 CCD pixels → 8-bit ADC samples (or 12-bit with oversampling)
- Repeat with blank (dark) for baseline subtraction

### Step 2: Pre-processing
1. **Dark subtraction**: CCD dark current + electronic offset removed
2. **Reference normalization**: Each spectrum divided by reference photodiode reading (compensates LED aging, temperature drift)
3. **Wavelength calibration**: Map CCD pixel index → emission wavelength via polynomial fit (calibrated with Hg pen lamp or known fluorescent standards)
4. **Rayleigh scatter masking**: Mask ±15 nm windows around each excitation wavelength (1st and 2nd order)
5. **Raman scatter masking**: Mask ±15 nm around water Raman peak (excitation × 3400 cm⁻¹ shift)
6. **Inner filter effect (IFE) correction**: If absorbance at excitation/emission wavelengths known (optional absorbance pre-scan), apply:
   `F_corrected = F_observed × 10^(A_ex/2 + A_em/2)`

### Step 3: Feature Extraction (48 features per EEM)
- 8 excitation × 3 emission band integrals (280–350, 350–450, 450–750 nm): 24 features
- Peak location (ex_wl, em_wl, intensity): 3 features
- Peak area / total integral ratio
- EEM volume (sum of all pixels)
- EEM centroid (weighted mean ex/em)
- Fluorescence index (450/500 nm ratio at 370 nm excitation) — humic vs. fulvic
- BIX (biological index, 380/430 nm at 310 nm excitation)
- HIX (humification index, 435–480/300–345 at 254 nm excitation)
- β/α ratio (tryptophan-like vs. humic-like)
- 5 principal component scores (on-device PCA from training set)

### Step 4: Classification (k-NN, k=5)
- 48-dimensional feature vector
- 50-compound reference library stored in flash
- Euclidean distance with per-feature weighting (inverse variance)
- Top-5 matches with confidence scores

### Step 5: Quantification (optional)
- If a single known fluorophore is detected (dominant match >80%):
  - Apply standard calibration curve (stored in library)
  - Stern-Volmer quenching correction if quencher present
  - Report concentration in µg/L or mg/L

---

## Firmware Architecture

```
firmware/
├── CMakeLists.txt          # CMake build (STM32Cube)
├── Core/
│   ├── Inc/
│   │   ├── main.h
│   │   ├── config.h         # Pin definitions, constants
│   │   ├── ccd_driver.h     # TSL1402R driver
│   │   ├── led_wheel.h      # Excitation LED wheel control
│   │   ├── fluorometer.h    # Measurement engine
│   │   ├── eem.h            # EEM acquisition + processing
│   │   ├── display.h        # OLED SH1106 driver
│   │   ├── storage.h        # SD card logging
│   │   ├── ble_bridge.h     # ESP32-C3 UART bridge
│   │   ├── library.h        # 50-compound fluorescence library
│   │   ├── onewire.h        # DS18B20 1-wire driver
│   │   └── power.h           # Battery management
│   └── Src/
│       ├── main.c           # Main loop, state machine
│       ├── ccd_driver.c     # TSL1402R readout
│       ├── led_wheel.c     # LED wheel + stepper control
│       ├── fluorometer.c   # Fluorescence measurement
│       ├── eem.c            # EEM capture + feature extraction
│       ├── display.c        # OLED rendering
│       ├── storage.c        # SD card CSV/binary logging
│       ├── ble_bridge.c    # UART protocol to ESP32-C3
│       ├── library.c        # k-NN classification
│       ├── onewire.c        # DS18B20 driver
│       └── power.c          # Battery monitoring
├── sdkconfig                # STM32CubeMX configuration
└── linker_script.ld         # Linker script
```

### State Machine
```
IDLE ──(button)──► MENU ──(select)──► PREVIEW ──(button)──► ACQUIRE
  ▲                  │                    │                     │
  │                  └──(timeout)────────►│                     │
  │                                            ▼                     │
  │                                        EEM_SCAN                 │
  │                                            │                     │
  │                                            ▼                     │
  │                                        PROCESS                  │
  │                                            │                     │
  │                                            ▼                     │
  │                                        DISPLAY_RESULT            │
  │                                            │                     │
  │                                        LOG+STREAM                │
  │                                            │                     │
  └────────────────────────────────────────────┘
```

---

## Assembly Guide

### Bill of Materials Summary

| Part | Qty | Unit Price | Total |
|---|---|---|---|
| STM32G474RET6 | 1 | $5.80 | $5.80 |
| ESP32-C3-MINI-1 | 1 | $2.60 | $2.60 |
| TSL1402R linear CCD | 1 | $9.20 | $9.20 |
| OPT101 photodiode | 1 | $4.10 | $4.10 |
| 255nm LED (UVTOP255) | 1 | $8.50 | $8.50 |
| 280nm LED (UVTOP280) | 1 | $7.20 | $7.20 |
| 340nm LED (RL340-10-30) | 1 | $3.80 | $3.80 |
| 365nm LED (NCSU033B) | 1 | $1.90 | $1.90 |
| 405nm LED (NCSU033A) | 1 | $1.40 | $1.40 |
| 440nm LED (NCSU219B) | 1 | $1.20 | $1.20 |
| 470nm LED (NCSU219C) | 1 | $1.10 | $1.10 |
| 525nm LED (NCSU219D) | 1 | $1.10 | $1.10 |
| Bandpass filters (8×, 12nm FWHM) | 8 | $1.80 | $14.40 |
| Long-pass filter (320 nm) | 1 | $2.20 | $2.20 |
| Reflective grating 600 lp/mm | 1 | $3.50 | $3.50 |
| 28BYJ-48 stepper | 1 | $1.50 | $1.50 |
| SH1106 OLED 1.3" | 1 | $2.80 | $2.80 |
| MicroSD socket | 1 | $0.60 | $0.60 |
| DS18B20 | 1 | $0.80 | $0.80 |
| MCP73831 (charger) | 1 | $0.70 | $0.70 |
| TPS63020 (buck-boost) | 1 | $2.10 | $2.10 |
| INA181 current sensor | 1 | $0.50 | $0.50 |
| DRV8833 (stepper driver) | 1 | $0.80 | $0.80 |
| OPA548 (LED driver) | 1 | $1.90 | $1.90 |
| MCP4131 (digital pot) | 1 | $0.90 | $0.90 |
| 3.7V 1800 mAh LiPo | 1 | $4.50 | $4.50 |
| PCB + components (passives, connectors) | — | $2.00 | $2.00 |
| 3D-printed enclosure + wheel | — | $0.00 | $0.00 |
| **Total** | | | **~$73** |

### Assembly Steps

1. **PCB fabrication**: Order 4-layer PCB from JLCPCB (Gerbers in `schematic/`)
2. **Solder SoC and passives**: Start with STM32G474, then ESP32-C3-MINI-1 module
3. **Mount optical components**: Solder TSL1402R, OPT101, LED driver, grating mount
4. **3D-print LED wheel**: STL file in `docs/` — holds 8 LEDs + filters in radial slots
5. **Attach wheel to stepper**: Press-fit onto 28BYJ-48 shaft, add Hall sensor magnet for home
6. **Install in enclosure**: Align optical path, insert cuvette holder
7. **Flash firmware**: ST-Link to STM32, USB to ESP32-C3
8. **Calibrate**: Run `scripts/calibrate.py` with quinine sulfate standard (see below)

### Calibration Procedure

1. Prepare 1 µg/mL quinine sulfate in 0.1 M H₂SO₄ (standard fluorescence reference)
2. Insert cuvette, select "Calibrate" mode
3. Device sweeps all 8 excitation wavelengths, captures emission spectra
4. Wavelength calibration: fit peak position to known quinine emission (455 nm at 350 nm excitation)
5. Intensity calibration: normalize response against NIST-traceable standard
6. Results stored in flash, valid for 6 months

---

## Calibration Standards & Library

### 50-Compound Fluorescence Library

| # | Compound | Ex (nm) | Em peak (nm) | Category |
|---|---|---|---|---|
| 1 | Tryptophan | 280 | 350 | Amino acid |
| 2 | Tyrosine | 275 | 305 | Amino acid |
| 3 | Phenylalanine | 260 | 282 | Amino acid |
| 4 | NADH | 340 | 460 | Cofactor |
| 5 | FAD | 450 | 525 | Cofactor |
| 6 | Riboflavin (B2) | 440 | 530 | Vitamin |
| 7 | Thiamine (B1) | 365 | 440 | Vitamin |
| 8 | Pyridoxine (B6) | 320 | 390 | Vitamin |
| 9 | Chlorophyll-a | 440 | 680 | Pigment |
| 10 | Chlorophyll-b | 470 | 660 | Pigment |
| 11 | Phycocyanin | 620 | 650 | Pigment |
| 12 | Fluorescein | 470 | 520 | Tracer dye |
| 13 | Rhodamine B | 525 | 580 | Tracer dye |
| 14 | Rhodamine 6G | 525 | 560 | Tracer dye |
| 15 | Quinine sulfate | 350 | 455 | Standard |
| 16 | Esculin | 365 | 460 | Coumarin |
| 17 | Umbelliferone | 365 | 455 | Coumarin |
| 18 | 4-Methylumbelliferone | 365 | 445 | Coumarin |
| 19 | Humic acid (Suwannee) | 320 | 420 | DOM |
| 20 | Fulvic acid (Suwannee) | 320 | 400 | DOM |
| 21 | Tryptophan-like (protein) | 280 | 340 | DOM |
| 22 | Tyrosine-like (protein) | 275 | 310 | DOM |
| 23 | Crude oil (freshwater) | 254 | 340 | Petroleum |
| 24 | Diesel fuel | 254 | 320 | Petroleum |
| 25 | Motor oil | 280 | 360 | Petroleum |
| 26 | Gasoline | 254 | 310 | Petroleum |
| 27 | BTEX mixture | 254 | 290 | Petroleum |
| 28 | PAH (naphthalene) | 280 | 340 | Petroleum |
| 29 | PAH (phenanthrene) | 260 | 370 | Petroleum |
| 30 | PAH (pyrene) | 340 | 390 | Petroleum |
| 31 | Carbaryl (pesticide) | 280 | 340 | Pesticide |
| 32 | Carbofuran | 280 | 330 | Pesticide |
| 33 | Chlorpyrifos | 290 | 350 | Pesticide |
| 34 | Atrazine | 254 | 310 | Pesticide |
| 35 | Aspirin (acetylsalicylic acid) | 280 | 350 | Pharmaceutical |
| 36 | Paracetamol (acetaminophen) | 280 | 360 | Pharmaceutical |
| 37 | Caffeine | 275 | 340 | Pharmaceutical |
| 38 | Warfarin | 320 | 400 | Pharmaceutical |
| 39 | Doxorubicin | 470 | 590 | Pharmaceutical |
| 40 | Hoechst 33342 | 360 | 460 | DNA stain |
| 41 | SYBR Green | 470 | 520 | DNA stain |
| 42 | Ethidium bromide | 300 | 600 | DNA stain |
| 43 | PicoGreen | 470 | 520 | DNA quant assay |
| 44 | Coenzyme Q10 | 280 | 350 | Supplement |
| 45 | Curcumin | 440 | 540 | Natural compound |
| 46 | Olive oil (extra virgin) | 360 | 440 | Food |
| 47 | Honey (pure clover) | 360 | 420 | Food |
| 48 | Beer (fresh lager) | 340 | 440 | Beverage |
| 49 | Wine (red, resveratrol) | 340 | 390 | Beverage |
| 50 | Tap water (baseline) | 254 | 350 | Reference |

---

## Communication Protocol (STM32 ↔ ESP32-C3)

UART at 921600 baud, 8N1. Binary framed protocol:

```
Frame: [SOF:0xAA][LEN:2][CMD:1][PAYLOAD:LEN-1][CRC16:2][EOF:0x55]

Commands (STM32 → ESP32):
  0x01 EEM_DATA     - Full EEM matrix (8×256 × 2 bytes = 4 KB)
  0x02 RESULT       - Classification result (top-5 matches)
  0x03 STATUS       - Device status (battery, temp, state)
  0x04 LOG_ENTRY    - SD log entry (CSV line)
  0x05 CALIBRATION  - Calibration data

Commands (ESP32-C3 → STM32):
  0x10 START_SCAN   - Trigger EEM acquisition
  0x11 SET_PARAMS   - Set acquisition parameters
  0x12 GET_STATUS   - Request status
  0x13 CALIBRATE    - Start calibration
  0x14 SET_LIBRARY  - Update compound library
  0x15 SET_TIME     - Sync RTC
```

---

## Python Companion App

The `scripts/` directory contains:

- `calibrate.py` — Calibration wizard (quinine sulfate standard, wavelength + intensity calibration)
- `live_view.py` — Real-time EEM heatmap viewer over BLE
- `library_manager.py` — Add/edit/remove compounds from the 50-entry library
- `export_eem.py` — Export SD card logs to ParafacView / MATLAB format
- `stern_volmer.py` — Stern-Volmer quenching analysis tool

---

## Comparison to Commercial Instruments

| Feature | Horiba FluoroMax | Agilent Cary Eclipse | Edinburgh FS5 | **Fluor Cast** |
|---|---|---|---|---|
| Price | $15,000–$40,000 | $20,000–$50,000 | $25,000–$50,000 | **~$73** |
| Size | Benchtop, 15 kg | Benchtop, 20 kg | Benchtop, 12 kg | **Pocket, 115 g** |
| Excitation source | Xenon arc lamp | Xenon flash | Xenon arc | **8-LED wheel** |
| Excitation range | 200–950 nm (continuous) | 200–900 nm (continuous) | 200–870 nm (continuous) | **255–525 nm (8 discrete)** |
| Emission detection | PMT | PMT | PMT | **Linear CCD** |
| Emission resolution | 1 nm | 1.5 nm | 1.5 nm | **1.6 nm** |
| EEM capability | Yes | Yes | Yes | **Yes** |
| On-device classification | No | No | No | **k-NN, 50-compound** |
| Battery powered | No | No | No | **Yes (10 h)** |
| Wireless | No | No | No | **BLE + Wi-Fi** |
| Open source | No | No | No | **Yes (MIT)** |

Fluor Cast trades excitation wavelength flexibility (8 discrete vs. continuous scan) for extreme portability and cost. The 8-wavelength set was chosen to cover the most important fluorophore excitation maxima and is sufficient for >90% of common fluorescence applications.

---

## Safety Notes

- **UV LEDs**: 255/280 nm LEDs emit UV-C radiation. Never look directly at LED output. The cuvette holder enclosure blocks direct viewing. Interlock switch disables LEDs when lid open.
- **Battery**: Use protected 3.7V LiPo only. MCP73831 handles charging from USB-C. Do not short-circuit.
- **Chemicals**: Some fluorescence standards (quinine, ethidium bromide, pesticides) are toxic. Handle with appropriate PPE.

---

## License

MIT — build it, sell it, improve it.

---

*Invented as part of the [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) collection.*