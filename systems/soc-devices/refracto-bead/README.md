# Refracto Bead

**A pocket digital Abbe refractometer for liquid identification and concentration measurement, using a critical-angle TIR shadow edge on a 256-pixel linear CCD, 4-wavelength dispersion measurement, prism-temperature correction, and on-device compound library matching.**

---

## What It Does

The Refracto Bead is a credit-card-sized PCB with a small flint-glass prism on top. You place **a single drop of liquid** on the prism, press the button, and 4 seconds later you have:

- **Refractive index (n_D)** at the sodium D-line (589 nm), measured to ±0.0003 — matching benchtop Abbe refractometers (e.g., Atago NAR-1T, ±0.0002)
- **Dispersion (n_F − n_C)** computed from 4-wavelength measurements (470/525/589/655 nm), giving the **Abbe number V_D**
- **Brix (sugar %)** — 0–95 °Bx with ±0.1 °Bx accuracy, for food & beverage quality control
- **Specific gravity (SG)** — for clinical urine / serum samples (1.000–1.070 range)
- **Coolant / antifreeze concentration** (ethylene glycol & propylene glycol)
- **Ethanol / alcohol concentration** (0–100 %ABV)
- **Honey moisture content** (16–28 %)
- **Compound identification** — k-NN matching against a 60-entry flash library of known RI + dispersion fingerprints (water, oils, alcohols, sugars, solvents, honey, beverages, clinical fluids, pharmaceuticals)

All processing runs on the **STM32G491RET6** (170 MHz Cortex-M4F with CORDIC accelerator for fast sin/arctan). Results are displayed on a **0.96" OLED** (SSD1306, 128×64) and streamed over **BLE 5.0** or **Wi-Fi** (via the co-located **ESP32-C3**) to a companion app for logging, plotting, and library editing.

Battery life: **2,000+ measurements** on a single 800 mAh LiPo (each measurement: ~3 s active, ~12 µA sleep between).

Use cases:
- **Food & beverage** — Brix of fruit/juice/wine, honey moisture, maple syrup grading, jam/jelly setting point
- **Clinical / point-of-care** — urine specific gravity for dehydration screening, serum protein estimation
- **Automotive** — coolant freeze-point / boil-over protection, battery electrolyte SG (lead-acid), brake fluid water content (DOT 4 RI shift)
- **Pharma / cosmetics** — raw-material identity verification (RI is a pharmacopeia ID test — USP <831>), essential-oil authentication
- **Solvent recovery** — distinguish acetone / IPA / ethanol / methanol / toluene / hexane (each has a distinct RI)
- **Education** — undergraduate optics & analytical chemistry labs

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         REFRACTO BEAD                                 │
│                                                                       │
│   ┌──────────────┐   ┌──────────────┐   ┌────────────────────────┐   │
│   │ LED1 589 nm  │   │ LED2 525 nm  │   │ LED3 470 nm   LED4 655 │   │
│   │ (D-line)     │   │ (green)      │   │ (blue)        (red)    │   │
│   └──────┬───────┘   └──────┬───────┘   └─────┬──────────┬────────┘   │
│          │                  │                 │          │            │
│          ▼ diffuser ◄───────┴─────────────────┴──────────┘            │
│   ┌──────────────────────────────────────────────────────────┐       │
│   │  SF11 Flint Glass Prism  (n_D = 1.78472 @ 589 nm)        │       │
│   │  ┌──────────────────────────────────────────────────┐    │       │
│   │  │  Sample well (1 drop of liquid on top surface)   │    │       │
│   │  └──────────────────────────────────────────────────┘    │       │
│   │  Total internal reflection boundary at critical angle θ_c│       │
│   └───────────────────────┬──────────────────────────────────┘       │
│                            │ refracted/reflected ray bundle            │
│                   ┌────────▼─────────┐                                │
│                   │  Plano-convex    │                                │
│                   │  lens (f=12 mm)  │   angle → position             │
│                   └────────┬─────────┘                                │
│                            │                                          │
│                   ┌────────▼─────────┐    CLK (1 MHz)   SI pulse      │
│                   │  TSL1402R        │◄──────┬──────────┬─────────    │
│                   │  256×1 linear    │       │          │             │
│                   │  CCD array       │───────┼──────────┘             │
│                   │  AO (analog out) │       │                        │
│                   └────────┬─────────┘       │                        │
│                            │ analog 0–3.3V   │                        │
│   ┌────────────────────────▼─────────────────▼───────────────────┐    │
│   │                  STM32G491RET6                                │    │
│   │  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐    │    │
│   │  │ 12-bit ADC │  │ TIM2 PWM     │  │ CORDIC             │    │    │
│   │  │ 1 MSPS     │  │ CLK + SI gen │  │ sin / arctan       │    │    │
│   │  │ DMA scan   │  │              │  │ (RI computation)   │    │    │
│   │  └────────────┘  └──────────────┘  └────────────────────┘    │    │
│   │  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐    │    │
│   │  │ I²C1       │  │ SPI2 (SD)    │  │ USART1 → ESP32-C3  │    │    │
│   │  │ OLED+BME280│  │ micro-SD     │  │ UART 460800         │    │    │
│   │  └────────────┘  └──────────────┘  └────────────────────┘    │    │
│   │  ┌────────────┐  ┌──────────────┐                           │    │
│   │  │ 1-Wire     │  │ GPIOs        │                           │    │
│   │  │ DS18B20    │  │ 4× LED_EN    │                           │    │
│   │  │ (prism T)  │  │ 3× buttons   │                           │    │
│   │  └────────────┘  └──────────────┘                           │    │
│   └────────────────────────┬──────────────────────────────────────┘    │
│                            │ USART                                      │
│   ┌────────────────────────▼──────────────────────────────────────┐    │
│   │  ESP32-C3-MINI-1                                              │    │
│   │  BLE 5.0 GATT server (RI/Brix/SG/compound/dispersion)         │    │
│   │  Wi-Fi HTTP REST API + MQTT                                   │    │
│   │  Receives measurements from STM32 over UART @ 460800           │    │
│   └───────────────────────────────────────────────────────────────┘    │
│                                                                       │
│   ┌──────────────────────────────────────────────────────────────┐    │
│   │  Power: MCP73831 charger + AP2112-3.3V LDO + 800mAh LiPo     │    │
│   │  USB-C: charging + SWD (STM32) + UART flash (ESP32-C3)       │    │
│   │  User: 3 buttons (Measure, Mode, Power)                      │    │
│   └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Measurement Principle — Critical-Angle Abbe Refractometer

### The Physics

When light traveling inside a high-index prism hits the boundary with a lower-index liquid sample, it undergoes **total internal reflection (TIR)** when the angle of incidence exceeds the **critical angle**:

```
sin(θ_c) = n_liquid / n_prism
```

Light arriving at angles **below** θ_c partially transmits into the liquid (this region appears dark when viewed from below because the light escapes). Light arriving at angles **above** θ_c is totally reflected back (this region appears bright). The boundary between bright and dark is a sharp edge whose angular position **is** θ_c.

### The Geometry

The Refracto Bead illuminates the underside of the prism with diffuse LED light (through a ground-glass diffuser). A plano-convex lens (f = 12 mm) images the angular distribution of light emerging from the prism's exit face onto a **256-pixel linear CCD (TSL1402R)**. The bright/dark boundary position on the CCD is linearly related to the angle θ of the ray that just grazes the critical condition:

```
pixel_position  ⟷  tan(θ_exit) × f / pixel_pitch
```

After calibration with two reference liquids of known RI (distilled water n_D = 1.3330 and a certified RI standard oil, e.g., n_D = 1.5150), we map pixel index `p_edge` to refractive index directly:

```
n(p_edge) = a + b·p_edge + c·p_edge²     (3-point quadratic fit)
```

The quadratic accounts for the slight non-linearity of the lens's tan(θ) projection. With 256 pixels covering RI 1.30–1.70 (typical), each pixel ≈ 0.0016 RI; sub-pixel edge detection via linear interpolation of the derivative peak gives **±0.0003 RI** resolution.

### Multi-Wavelength Dispersion

Refractive index varies with wavelength (the **dispersion** of the material, governed by the Sellmeier equation). By measuring at 4 wavelengths we compute:

| Quantity | Formula | Wavelengths Used |
|----------|---------|------------------|
| n_D | RI at sodium D-line | 589 nm |
| n_F − n_C | mean dispersion | 470 nm (≈Hβ 486) and 655 nm (≈Hα 656) |
| V_D (Abbe number) | (n_D − 1) / (n_F − n_C) | all three |
| Sellmeier fit | n(λ) = A + B/λ² + C/λ⁴ (Cauchy 3-term) | all 4 (470/525/589/655) |

The dispersion fingerprint dramatically improves compound discrimination — e.g., ethanol (n_D=1.361, V_D=59) vs. acetone (n_D=1.359, V_D=54.6) have nearly identical n_D but differ by 4.4 Abbe number units.

### Temperature Correction

Refractive index is strongly temperature-dependent (typically dn/dT ≈ −4×10⁻⁴ /°C for aqueous solutions). The Refracto Bead measures:

1. **Prism temperature** — DS18B20 sensor bonded to the prism body (±0.1 °C)
2. **Ambient temperature** — BME280 (for reference and humidity compensation)

and applies correction:

```
n_corrected = n_measured + (T_prism − 20.0) × dn_dT[compound_class]
```

The dn/dT coefficient is selected automatically based on the closest library match (e.g., −0.00045/°C for water-based, −0.00038/°C for oils). For highest accuracy, a small **Peltier heater (TEC1-04030)** with PID control holds the prism at a stable 20.0 °C (optional, see Power section).

---

## Pin Assignment (STM32G491RET6, LQFP64)

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| PA0 / ADC1_IN1 | TSL_AO | TSL1402R analog output | 12-bit, 1 MSPS, DMA |
| PA1 / TIM2_CH1 | TSL_CLK | TSL1402R CLK | 1 MHz PWM, 50% duty |
| PA2 / TIM2_CH2 | TSL_SI | TSL1402R SI | One-shot pulse per read |
| PA3 | LED1_EN | 589 nm LED anode driver (NPN) | Active high |
| PA4 | LED2_EN | 525 nm LED driver | Active high |
| PA5 | LED3_EN | 470 nm LED driver | Active high |
| PA6 | LED4_EN | 655 nm LED driver | Active high |
| PA7 | TEC_EN | TEC1-04030 peltier driver | PWM, optional temp control |
| PA8 | SD_CS | microSD card CS | SPI2 CS, active low |
| PA9 / USART1_TX | UART_TX | ESP32-C3 GPIO2 (RX) | 460800 baud |
| PA10 / USART1_RX | UART_RX | ESP32-C3 GPIO3 (TX) | 460800 baud |
| PA11 | USB_D- | USB-C D- | Native USB (DFU) |
| PA12 | USB_D+ | USB-C D+ | Native USB (DFU) |
| PA13 | SWDIO | Debug header | SWD programming |
| PA14 | SWCLK | Debug header | SWD programming |
| PA15 / TIM2_CH3 | BACKLIGHT | OLED backlight (PWM) | Optional dimming |
| PB0 / I2C1_SCL | I2C_SCL | SSD1306 OLED + BME280 | 4.7 kΩ pullup |
| PB1 / I2C1_SDA | I2C_SDA | SSD1306 OLED + BME280 | 4.7 kΩ pullup |
| PB2 | ESP_EN | ESP32-C3 EN | Reset / power-gate ESP32 |
| PB3 / SPI2_SCK | SD_SCK | microSD SCK | 25 MHz max |
| PB4 / SPI2_MISO | SD_MISO | microSD MISO | |
| PB5 / SPI2_MOSI | SD_MOSI | microSD MOSI | |
| PB6 | OLED_RST | SSD1306 RES | Active low reset |
| PB7 | STAT_LED | Status LED (dual-color) | Green = ready, Red = error |
| PB8 | BTN_MEASURE | Tactile switch | Active-low, internal pullup |
| PB9 | BTN_MODE | Tactile switch | Active-low, internal pullup |
| PB10 | BTN_POWER | Tactile switch | Active-low, internal pullup |
| PB11 | DS18B20_DATA | DS18B20 1-Wire data | 4.7 kΩ pullup to 3.3V |
| PB12 | CHARGE_STAT | MCP73831 STAT | Charge status input |
| PB13 / ADC1_IN11 | VBAT_SENSE | 1:2 voltage divider | Battery voltage monitor |
| PB14 / ADC1_IN5 | TEC_VSENSE | TEC current-sense amp | Over-current protection |
| PC13 | BAT_TEMP | NTC 10k to VDD | Battery temperature |
| PC14 | SD_DETECT | microSD card detect | Active low (card present) |
| PC15 | SPARE | — | Unconnected / expansion |
| PF0 / OSC_IN | HSE_IN | 8 MHz crystal | Main clock source |
| PF1 / OSC_OUT | HSE_OUT | 8 MHz crystal | Main clock source |

### ESP32-C3-MINI-1 Pin Assignment

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| GPIO2 | UART_RX | STM32 PA9 (USART1_TX) | 460800 baud |
| GPIO3 | UART_TX | STM32 PA10 (USART1_RX) | 460800 baud |
| GPIO8 | BOOT_STRAP | 10 kΩ pullup | Boot from flash |
| GPIO9 | EN | STM32 PB2 (ESP_EN) | Enable / power-gate |
| GPIO10 | LED_DATA | WS2812B status LED | RGB status |
| GPIO18 / USB_D- | USB_D- | USB-C D- (via mux) | Native USB CDC |
| GPIO19 / USB_D+ | USB_D+ | USB-C D+ (via mux) | Native USB CDC |

---

## Power Architecture

```
USB-C (5V) ──► MCP73831 ──► LiPo (3.7V, 800 mAh) ──► AP2112-3.3V ──► VDD (3.3V)

Quiescent: ~12 µA (Stop mode, RTC on, OLED off, ESP32-C3 powered down)
Active (measurement, 3 s): ~95 mA avg (LED + CCD + ADC + OLED)
Active (BLE only, ESP32-C3): ~18 mA avg
Active (Wi-Fi streaming): ~95 mA
TEC heating (optional): +120 mA peak (PID-controlled, duty-cycled)
```

Power states:
1. **STOP** — STM32 Stop 2 mode, RTC on, ESP32-C3 EN low, OLED off (~12 µA)
2. **IDLE** — OLED on, waiting for button press (~25 mA with ESP32-C3 in light sleep)
3. **MEASURING** — LEDs + CCD + ADC active, 4-wavelength sweep (~95 mA, 3–4 s)
4. **STREAMING** — Wi-Fi connected, sending results to app (~95 mA, 2 s)

Battery life: 800 mAh / (3 s × 95 mA + sleep) ≈ **2,000+ measurements per charge**

---

## Measurement Pipeline

### Step 1: Sample Application

Place 1–2 drops of the liquid sample on the clean prism surface. The sample well (a 5 mm × 10 mm recessed area on top of the prism) holds the liquid in place. The prism must be clean and dry before applying — wipe with lens tissue between measurements.

### Step 2: Temperature Stabilization (≤1 s)

Read the DS18B20 bonded to the prism body. If the optional TEC heater is enabled and the prism is more than 0.5 °C from the target (20.0 °C default), wait for the PID loop to settle. Otherwise, record the temperature and apply software correction at compute time.

### Step 3: 4-Wavelength Sweep (3 s total)

For each of the 4 LEDs (589 → 525 → 470 → 655 nm):

1. Turn on the LED (constant-current driver, ~5 mA, ~20 mW optical)
2. Wait 20 ms for illumination to stabilize
3. Pulse the TSL1402R SI pin to start integration
4. Clock out 256 pixels at 1 MHz (256 µs), sampling AO with the ADC at 1 MSPS via DMA
5. Wait for integration time to complete (auto-exposure: if pixel max > 90% FS, reduce integration; if < 10%, increase — bounded to 0.5–10 ms)
6. Store the 256-sample waveform in SRAM
7. Turn off the LED
8. Repeat for next wavelength

### Step 4: Edge Detection (per wavelength)

For each 256-pixel waveform:

1. Subtract dark offset (measured with all LEDs off at boot)
2. Apply 5-tap moving-average smoothing
3. Compute the first derivative (5-tap central difference)
4. Find the pixel index where the derivative crosses zero with the steepest negative transition (bright→dark boundary)
5. Sub-pixel refinement: linear interpolation between the two pixels straddling the derivative peak gives **p_edge** to ±0.1 pixel

### Step 5: Refractive Index Computation

Using the per-wavelength calibration coefficients (stored in flash, calibrated against water + RI-standard oil at 20 °C):

```
n(λ, p_edge) = a[λ] + b[λ]·p_edge + c[λ]·p_edge²
```

Apply prism-temperature correction:

```
n_corrected = n + (T_prism − 20.0) × dn_dT_prism    (SF11: −6.4×10⁻⁵ /°C)
```

Then apply sample-class temperature correction based on preliminary library match.

### Step 6: Derived Quantities

| Output | Formula | Range |
|--------|---------|-------|
| **n_D** | n(589 nm) | 1.3000 – 1.7000 |
| **n_F** | n(470 nm) | — |
| **n_C** | n(655 nm) | — |
| **Dispersion** | n_F − n_C | 0.005 – 0.080 |
| **Abbe number V_D** | (n_D − 1)/(n_F − n_C) | 20 – 90 |
| **Brix** | Polynomial: Bx = c₀ + c₁·n_D + c₂·n_D² (ICUMSA) | 0 – 95 °Bx |
| **Specific gravity** | SG = (n_D − 1.3330) × k + 1.000 (clinical urine) | 1.000 – 1.070 |
| **%ABV (ethanol)** | ABV = f(n_D, T) calibrated table | 0 – 100 % |
| **Coolant %** | Linear fit per glycol type | −60 – +10 °C FP |

### Step 7: Library Matching

The on-device library contains 60 compounds with their (n_D, V_D, dn/dT) fingerprints. A **k-NN classifier (k=3)** in (n_D, V_D) space returns the 3 nearest matches and a confidence score:

```
confidence = 1 − (d_nearest / d_threshold)
```

If `confidence > 0.85`, the compound name is displayed; otherwise, "Unknown — n_D=1.4231, V_D=52.3" is shown.

### Step 8: Display, Log, Stream

- **OLED** shows n_D, V_D, identified compound, Brix/SG/ABV (depending on Mode)
- **SD card** logs a CSV row: timestamp, T_prism, T_ambient, n_D, n_F, n_C, V_D, Brix, SG, compound, confidence
- **BLE/Wi-Fi** (via ESP32-C3) pushes a JSON result packet to connected clients

---

## Measurement Modes

The MODE button cycles through 5 display modes:

| Mode | Label | Primary Output | Notes |
|------|-------|----------------|-------|
| RI | "RI" | n_D, V_D, dispersion | Raw refractive index + identification |
| BRIX | "BRIX" | °Brix, n_D | Sugar content (ICUMSA polynomial) |
| SG | "SG" | Specific gravity, n_D | Clinical urine / serum |
| COOL | "COOL" | Freeze point, % glycol | Automotive coolant |
| ALC | "ALC" | %ABV, n_D | Ethanol in water (0–100%) |

All 5 derived quantities are computed every measurement; the MODE button only changes which is prominently displayed on the OLED.

---

## Compound Library (60 entries, stored in flash)

| # | Compound | n_D (589nm, 20°C) | V_D | dn/dT (×10⁻⁴/°C) | Category |
|---|----------|-------------------|-----|--------------------|----------|
| 1 | Distilled water | 1.3330 | 55.8 | −0.8 | Reference |
| 2 | Ethanol 100% | 1.3611 | 59.0 | −4.0 | Solvent |
| 3 | Methanol | 1.3284 | 57.6 | −4.0 | Solvent |
| 4 | Acetone | 1.3588 | 54.6 | −4.9 | Solvent |
| 5 | Isopropanol (IPA) | 1.3776 | 54.6 | −3.7 | Solvent |
| 6 | Toluene | 1.4961 | 30.6 | −5.4 | Solvent |
| 7 | Hexane | 1.3750 | 56.8 | −5.4 | Solvent |
| 8 | Dichloromethane | 1.4244 | 40.1 | −5.8 | Solvent |
| 9 | Ethyl acetate | 1.3723 | 53.8 | −4.7 | Solvent |
| 10 | Glycerol | 1.4735 | 46.9 | −2.2 | Polyol |
| 11 | Propylene glycol | 1.4324 | 47.9 | −3.6 | Polyol |
| 12 | Ethylene glycol | 1.4318 | 49.6 | −2.6 | Coolant |
| 13 | Olive oil | 1.4677 | 47.2 | −3.8 | Oil |
| 14 | Sunflower oil | 1.4657 | 47.1 | −3.8 | Oil |
| 15 | Castor oil | 1.4778 | 45.4 | −4.0 | Oil |
| 16 | Coconut oil | 1.4483 | 48.3 | −3.8 | Oil |
| 17 | Mineral oil | 1.4667 | 46.0 | −3.5 | Oil |
| 18 | Silicone oil (100cSt) | 1.4035 | 58.6 | −3.5 | Oil |
| 19 | Honey (18% MC) | 1.4900 | 50.0 | −3.5 | Food |
| 20 | Maple syrup (66°Bx) | 1.4580 | 49.0 | −3.2 | Food |
| 21 | 10% NaCl solution | 1.3509 | 55.5 | −1.6 | Solution |
| 22 | 20% NaCl solution | 1.3686 | 55.0 | −1.8 | Solution |
| 23 | Saturated NaCl | 1.3780 | 54.0 | −2.0 | Solution |
| 24 | 5% glucose | 1.3402 | 55.5 | −1.4 | Solution |
| 25 | 20% glucose | 1.3635 | 55.0 | −2.0 | Solution |
| 26 | 40% glucose | 1.3900 | 54.5 | −2.8 | Solution |
| 27 | 60% sucrose | 1.4490 | 49.0 | −3.3 | Solution |
| 28 | 40% sucrose (Brix 40) | 1.3997 | 53.0 | −2.6 | Solution |
| 29 | Cane juice (15°Bx) | 1.3550 | 55.0 | −1.6 | Beverage |
| 30 | Apple juice (12°Bx) | 1.3505 | 55.2 | −1.5 | Beverage |
| 31 | Orange juice (11°Bx) | 1.3490 | 55.3 | −1.5 | Beverage |
| 32 | Red wine (13% ABV) | 1.3448 | 55.5 | −1.4 | Beverage |
| 33 | Beer (5% ABV) | 1.3380 | 55.6 | −1.2 | Beverage |
| 34 | Coffee (brewed) | 1.3345 | 55.7 | −0.9 | Beverage |
| 35 | Milk (whole) | 1.3460 | 55.4 | −1.5 | Dairy |
| 36 | Skim milk | 1.3443 | 55.5 | −1.3 | Dairy |
| 37 | Cream (35% fat) | 1.4080 | 52.0 | −2.5 | Dairy |
| 38 | Urine (normal, SG 1.020) | 1.3355 | 55.6 | −1.0 | Clinical |
| 39 | Urine (dehydrated, SG 1.030) | 1.3380 | 55.5 | −1.2 | Clinical |
| 40 | Serum (normal) | 1.3450 | 55.2 | −1.3 | Clinical |
| 41 | Saline 0.9% | 1.3345 | 55.7 | −0.9 | Clinical |
| 42 | DMSO | 1.4770 | 47.0 | −4.4 | Solvent |
| 43 | DMF | 1.4305 | 49.2 | −4.3 | Solvent |
| 44 | Acetonitrile | 1.3441 | 56.0 | −4.5 | Solvent |
| 45 | THF | 1.4070 | 51.8 | −5.1 | Solvent |
| 46 | Chloroform | 1.4459 | 41.0 | −5.9 | Solvent |
| 47 | Carbon tetrachloride | 1.4601 | 36.4 | −5.8 | Solvent |
| 48 | Benzene | 1.5011 | 30.2 | −5.5 | Solvent |
| 49 | Turpentine | 1.4690 | 44.0 | −4.0 | Solvent |
| 50 | Linseed oil | 1.4780 | 45.0 | −3.9 | Oil |
| 51 | Sesame oil | 1.4650 | 47.3 | −3.8 | Oil |
| 52 | Peanut oil | 1.4660 | 47.1 | −3.8 | Oil |
| 53 | Brake fluid DOT 4 (new) | 1.4460 | 48.0 | −3.5 | Automotive |
| 54 | Brake fluid DOT 4 (3% H₂O) | 1.4360 | 49.0 | −3.0 | Automotive |
| 55 | Battery electrolyte (full) | 1.4030 | 52.0 | −3.0 | Automotive |
| 56 | Battery electrolyte (50%) | 1.3750 | 54.0 | −2.5 | Automotive |
| 57 | Coolant 50% EG | 1.3820 | 53.0 | −2.8 | Automotive |
| 58 | Coolant 50% PG | 1.3840 | 52.5 | −3.0 | Automotive |
| 59 | Essential oil (lavender) | 1.4580 | 49.5 | −3.8 | Phama |
| 60 | Essential oil (peppermint) | 1.4600 | 49.0 | −3.8 | Phama |

> Library is user-editable via the BLE/Wi-Fi API — add custom compounds with known (n_D, V_D) values.

---

## BLE GATT Service (ESP32-C3)

```
Service UUID: 0xFFC0 (RefractoBead)
  ├── Char 0xFFC1: Measurement Command (write) — uint8 (1=measure, 2=cal_water, 3=cal_oil)
  ├── Char 0xFFC2: RI Results (read/notify) — 32 bytes
  │     {n_D_f32, n_F_f32, n_C_f32, V_D_f32, T_prism_f32}
  ├── Char 0xFFC3: Derived Results (read/notify) — 20 bytes
  │     {brix_f32, sg_f32, abv_f32, fp_f32, compound_id_u8}
  ├── Char 0xFFC4: Compound Match (read/notify) — 48 bytes
  │     {name[16], n_D_f32, V_D_f32, confidence_f32, rank_u8} × 3
  ├── Char 0xFFC5: Raw CCD Waveform (read) — 512 bytes (256× uint8, current wavelength)
  ├── Char 0xFFC6: Device Status (read/notify) — uint8 (0=idle, 1=measuring, 2=streaming, 3=error)
  ├── Char 0xFFC7: Battery Level (read) — uint8 (%)
  └── Char 0xFFC8: Library Entry (read/write) — 32 bytes
        {id_u8, name[16], n_D_f32, V_D_f32, dn_dT_f32}
```

BLE advertising packet (31 bytes):
```
[Flags] [Complete 16-bit UUID: FFC0] [Mfr-specific: status(1), battery%(1), last_nD × 10000 (2)]
```

---

## Wi-Fi REST API (ESP32-C3)

When Wi-Fi is enabled (hold MODE button during boot), the ESP32-C3 hosts a tiny HTTP server:

```
GET  /api/status           → JSON: {status, battery, last_measurement}
POST /api/measure          → JSON: {mode: "ri"|"brix"|"sg"|"cool"|"alc"}
GET  /api/results          → JSON: {n_D, n_F, n_C, V_D, brix, sg, abv, fp, compound, confidence}
GET  /api/compound/matches → JSON: [{name, n_D, V_D, confidence}, ...]
GET  /api/library          → JSON: [{id, name, n_D, V_D, dn_dT}, ...]
POST /api/library          → JSON: {name, n_D, V_D, dn_dT}  (add custom entry)
GET  /api/waveform?wl=589  → Binary: 256 × uint8 (raw CCD pixels)
GET  /api/log?n=100        → JSON: [{timestamp, n_D, ...}, ...] (last N SD log entries)
POST /api/calibrate        → JSON: {standard: "water"|"oil_1.515"|"oil_1.700", ...}
```

---

## Firmware Architecture

The Refracto Bead uses a **dual-MCU architecture**:

- **STM32G491RET6** — real-time measurement: CCD clocking, ADC sampling, edge detection, RI computation, OLED display, SD logging. Bare-metal with STM32Cube HAL. Runs the critical-angle measurement loop with deterministic timing.
- **ESP32-C3-MINI-1** — connectivity: BLE GATT server, Wi-Fi HTTP REST API, MQTT client. Receives results from the STM32 over UART at 460800 baud and relays to phones/cloud. Can be power-gated (PB2/ESP_EN) to save ~18 mA when offline.

### STM32 Firmware (main controller)

```
firmware/
├── Core/
│   ├── Src/
│   │   ├── main.c                # Entry point, HAL init, state machine
│   │   ├── tsl1402r.c            # Linear CCD driver (CLK gen, SI pulse, ADC DMA readout)
│   │   ├── edge_detect.c         # Boundary detection + sub-pixel refinement
│   │   ├── refract_calc.c        # RI computation, Brix/SG/ABV, dispersion, CORDIC sin
│   │   ├── compound_lib.c        # 60-entry flash library + k-NN matching
│   │   ├── ds18b20.c             # 1-Wire temperature sensor (prism temp)
│   │   ├── bme280.c              # Ambient T/H/P (I2C)
│   │   ├── oled_display.c        # SSD1306 driver (I2C, 128×64)
│   │   ├── sd_logger.c           # microSD CSV logging (SPI + FatFS)
│   │   ├── esp32_link.c          # UART protocol to ESP32-C3
│   │   ├── power_manager.c       # Stop mode, battery monitor, charge status
│   │   └── stm32g4xx_it.c        # Interrupt handlers (ADC DMA, EXTI buttons)
│   └── Inc/
│       ├── tsl1402r.h
│       ├── edge_detect.h
│       ├── refract_calc.h
│       ├── compound_lib.h
│       ├── ds18b20.h
│       ├── bme280.h
│       ├── oled_display.h
│       ├── sd_logger.h
│       ├── esp32_link.h
│       ├── power_manager.h
│       └── stm32g4xx_hal_conf.h
├── Makefile                      # arm-none-eabi-gcc build
└── refracto-bead.ioc             # STM32CubeMX project file
```

### ESP32-C3 Firmware (connectivity)

```
firmware/esp32-c3/
├── main/
│   ├── main.c                    # UART receiver from STM32, BLE/Wi-Fi relay
│   ├── ble_service.c             # GATT server
│   ├── wifi_server.c             # HTTP REST API
│   ├── uart_protocol.c           # Binary frame parser (STM32 → ESP32)
│   └── CMakeLists.txt
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow (STM32)

```c
int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_TIM2_Init();        /* TSL_CLK 1 MHz + SI pulse */
    MX_I2C1_Init();
    MX_SPI2_Init();
    MX_USART1_Init();      /* UART to ESP32-C3 @ 460800 */

    oled_display_init();
    bme280_init();
    ds18b20_init();
    tsl1402r_init();
    sd_logger_init();
    esp32_link_init();
    compound_lib_init();

    oled_display_boot_screen();

    while (1) {
        if (measure_pending) {
            measure_pending = 0;
            run_measurement();
        }
        oled_display_idle_screen();
        power_manager_stop_mode(100);  /* RTC wake every 100 ms for button poll */
    }
}

void run_measurement(void) {
    float t_prism = ds18b20_read();
    float t_amb, hum, pres;
    bme280_read(&t_amb, &hum, &pres);

    oled_display_measuring();

    ri_result_t result = {0};
    result.t_prism = t_prism;
    result.t_ambient = t_amb;

    /* 4-wavelength sweep */
    static const uint8_t leds[4] = {LED_589, LED_525, LED_470, LED_655};
    float n_values[4];
    for (int i = 0; i < 4; i++) {
        led_on(leds[i]);
        HAL_Delay(20);
        tsl1402r_read(ccd_buffer);
        led_off(leds[i]);
        float p_edge = edge_detect_find_boundary(ccd_buffer, 256);
        n_values[i] = refract_calc_ri(p_edge, leds[i], t_prism);
    }

    /* Compute derived quantities */
    refract_calc_derive(n_values, t_prism, &result);
    compound_lib_match(&result);

    /* Display + log + stream */
    oled_display_results(current_mode, &result);
    sd_logger_write(&result);
    esp32_link_send_result(&result);
}
```

---

## Calibration

### Factory Calibration (2-point, per wavelength)

Performed once at assembly using two certified reference liquids:

1. **Distilled water** — n_D = 1.3330 at 20 °C (traceable to NIST)
2. **Refractive index standard oil** — n_D = 1.5150 at 20 °C (Cargille Labs, ±0.0002)

For each wavelength (4 LEDs), measure the edge position for both standards:

```
b[λ] = (1.5150 − 1.3330) / (p_oil − p_water)
a[λ] = 1.3330 − b[λ] × p_water
```

This linear fit is stored in flash. A **3-point calibration** (add n_D = 1.7000 oil) refines to a quadratic for the upper range — recommended if measuring high-index samples (oils, pharma).

### User Calibration

The MEASURE button long-press (>3 s) enters calibration mode. The OLED prompts:

1. "Place WATER, press ●" → measures, stores p_water
2. "Place OIL 1.515, press ●" → measures, stores p_oil
3. "Calibration complete ✓"

Coefficients are written to flash (last 4 KB sector, wear-leveled).

### Pixel-to-Angle Mapping (lens calibration)

The lens converts exit angle θ_exit to pixel position via:

```
p = p_0 + (f / pixel_pitch) × tan(θ_exit − θ_axis)
```

with f = 12 mm and pixel_pitch = 63.5 µm, giving ~189 pixels per radian, or ~1.5 pixels per degree. The 256-pixel array covers ~17° of exit angle, corresponding to RI range ~1.30–1.70 with an SF11 prism (n = 1.785). This is captured implicitly by the 2-point RI calibration.

---

## Mechanical

- **PCB**: 85 × 54 mm (credit-card form factor), 1.6 mm FR4, 4-layer
- **Prism assembly**: SF11 flint glass prism (10 × 10 × 10 mm), mounted on a 12 mm raised platform with the sample well milled into an aluminum top plate
- **Optical path**: LED → diffuser → prism (illuminates underside at all angles) → exit face → lens (f=12mm) → TSL1402R
- **TEC (optional)**: TEC1-04030 (4×3 mm, 0.4 W) peltier element bonded under the prism, with PID control to hold 20.0 °C ± 0.1 °C
- **Enclosure**: 3D-printed snap-fit case with a hinged prism cover (dust protection) and a sample-well opening on top
- **Weight**: 55 g (PCB + battery + prism + enclosure)
- **Dimensions**: 85 × 54 × 18 mm (with prism assembly)

Optical alignment considerations:
- The lens-to-CCD distance must be set to f (12 mm) for sharp focus — use a machined spacer
- The prism exit face must be parallel to the CCD long axis (±1°)
- The diffuser ensures uniform angular illumination (ground glass, 600 grit)
- Light leakage: the optical path is shrouded in a black ABS enclosure tube (light-tight)

---

## LCD UI Screens

### Idle Screen
```
┌────────────────────────┐
│  REFRACTO BEAD         │
│  ■■■■■□□□ 75%          │
│                        │
│  Mode: RI              │
│  Press ● to measure    │
│                        │
│  20.1°C  45% RH        │
└────────────────────────┘
```

### Measuring Screen
```
┌────────────────────────┐
│  MEASURING...          │
│  ▓▓▓▓▓▓▓░░░ 70%       │
│                        │
│  λ: 589 nm  ●●●○       │
│  T: 20.1°C             │
│                        │
│  ■■■■■□□□ 75%          │
└────────────────────────┘
```

### RI Results Screen
```
┌────────────────────────┐
│  REFRACTIVE INDEX      │
│                        │
│  n_D:  1.4657          │
│  V_D:  47.1            │
│  Disp: 0.0099          │
│                        │
│  → Sunflower oil (98%) │
│  T: 20.1°C  Brix: —    │
└────────────────────────┘
```

### Brix Results Screen
```
┌────────────────────────┐
│  BRIX (SUGAR %)        │
│                        │
│  Brix: 42.3 °Bx        │
│  n_D:  1.4042          │
│                        │
│  Sugar solution        │
│  (95% confidence)      │
│                        │
│  T: 20.1°C             │
└────────────────────────┘
```

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | STM32G491RET6 | LQFP-64 | 1 | $4.50 | 170MHz Cortex-M4F, CORDIC, 12-bit ADC |
| 2 | ESP32-C3-MINI-1 | Module | 1 | $2.20 | BLE 5.0 + Wi-Fi 4 |
| 3 | TSL1402R | DIP-8 | 1 | $9.50 | 256×1 linear CCD, 63.5µm pitch |
| 4 | SF11 flint glass prism 10mm | Optical | 1 | $6.00 | n_D=1.785, custom cut |
| 5 | Plano-convex lens f=12mm | Ø6mm | 1 | $1.50 | CCD imaging lens |
| 6 | Ground-glass diffuser | Ø6mm | 1 | $0.50 | 600 grit, for LED |
| 7 | LED 589nm 5mm | T-1¾ | 1 | $0.80 | Kingbright L-934ND1D, 15nm FWHM |
| 8 | LED 525nm 5mm | T-1¾ | 1 | $0.25 | Green, 30nm FWHM |
| 9 | LED 470nm 5mm | T-1¾ | 1 | $0.25 | Blue, 25nm FWHM |
| 10 | LED 655nm 5mm | T-1¾ | 1 | $0.25 | Red, 20nm FWHM |
| 11 | SSD1306 OLED 0.96" 128×64 | Module | 1 | $1.80 | I2C, monochrome |
| 12 | BME280 | LGA-8 | 1 | $2.00 | Ambient T/H/P |
| 13 | DS18B20 | TO-92 | 1 | $1.20 | Prism temperature (±0.1°C) |
| 14 | TEC1-04030 Peltier | 4×3mm | 1 | $1.50 | Optional prism temp control |
| 15 | DRV8833 motor driver | SOIC-16 | 1 | $1.00 | TEC H-bridge driver |
| 16 | microSD socket | SMD | 1 | $0.40 | Push-push, SPI mode |
| 17 | microSD card 8GB | — | 1 | $1.50 | Logging |
| 18 | MCP73831-2-OT | SOT-23-5 | 1 | $0.40 | LiPo charger 500mA |
| 19 | AP2112-3.3 | SOT-223 | 1 | $0.30 | LDO 600mA |
| 20 | LiPo 800mAh | Pouch | 1 | $3.00 | 3.7V, with protection PCB |
| 21 | USB-C 16-pin receptacle | SMD | 1 | $0.35 | Power + data |
| 22 | WS2812B-2020 | 2020 | 1 | $0.15 | Status RGB LED |
| 23 | Tactile switch 6×6mm | SMD | 3 | $0.15 | Measure/Mode/Power |
| 24 | NTC 10k 1% | 0402 | 1 | $0.05 | Battery temperature |
| 25 | Resistors/Caps 0402 | 0402 | ~50 | $0.75 | Pullups, decoupling, dividers |
| 26 | 8 MHz crystal | 3225 | 1 | $0.20 | STM32 HSE |
| 27 | 74LVC1G66 analog switch | SOT-23-5 | 1 | $0.10 | USB D+/D- mux (STM32/ESP32) |
| 28 | PCB 4-layer 85×54mm | Rect | 1 | $2.00 | JLCPCB, black mask |

**Total estimated BOM: ~$41.95** (qty 1, without TEC option: ~$39.45)

---

## Comparison to Benchtop Abbe Refractometers

| Feature | Refracto Bead | Atago NAR-1T | Atago NAR-2T | Bellingham RFM600 |
|---------|---------------|--------------|--------------|-------------------|
| RI range | 1.30–1.70 | 1.30–1.70 | 1.30–1.70 | 1.30–1.70 |
| RI accuracy | ±0.0003 | ±0.0002 | ±0.0002 | ±0.0001 |
| Brix range | 0–95 | 0–95 | 0–95 | 0–95 |
| Brix accuracy | ±0.1 °Bx | ±0.1 °Bx | ±0.1 °Bx | ±0.05 °Bx |
| Dispersion (V_D) | ✓ (4-wavelength) | ✓ (2-wavelength) | ✓ (2-wavelength) | ✓ (2-wavelength) |
| Temperature control | Optional TEC | Built-in water bath | Built-in Peltier | Built-in Peltier |
| Sample volume | 1 drop (0.05 mL) | 0.05 mL | 0.05 mL | 0.05 mL |
| Battery / portable | ✓ (800 mAh LiPo) | ✗ (mains) | ✗ (mains) | ✗ (mains) |
| BLE / Wi-Fi | ✓ | ✗ | ✗ | ✗ (USB only) |
| On-device library | ✓ (60 compounds) | ✗ | ✗ | ✗ |
| Compound ID (k-NN) | ✓ | ✗ | ✗ | ✗ |
| Weight | 55 g | 6 kg | 6 kg | 9 kg |
| **Cost** | **~$42** | **~$3,200** | **~$4,800** | **~$8,500** |

The Refracto Bead brings the gold-standard critical-angle Abbe refractometry method — used in food, pharma, clinical, and automotive labs worldwide — down to **~$42 and pocket size**, with comparable accuracy for the vast majority of field applications, and adds on-device compound identification that no benchtop instrument offers.

---

## Directory Structure

```
refracto-bead/
├── README.md                  # This file
├── schematic/
│   ├── refracto_bead.kicad_sch
│   ├── refracto_bead.kicad_pcb
│   └── refracto_bead.kicad_pro
├── firmware/
│   ├── Core/
│   │   ├── Src/
│   │   │   ├── main.c
│   │   │   ├── tsl1402r.c
│   │   │   ├── edge_detect.c
│   │   │   ├── refract_calc.c
│   │   │   ├── compound_lib.c
│   │   │   ├── ds18b20.c
│   │   │   ├── bme280.c
│   │   │   ├── oled_display.c
│   │   │   ├── sd_logger.c
│   │   │   ├── esp32_link.c
│   │   │   ├── power_manager.c
│   │   │   └── stm32g4xx_it.c
│   │   └── Inc/
│   │       ├── tsl1402r.h
│   │       ├── edge_detect.h
│   │       ├── refract_calc.h
│   │       ├── compound_lib.h
│   │       ├── ds18b20.h
│   │       ├── bme280.h
│   │       ├── oled_display.h
│   │       ├── sd_logger.h
│   │       ├── esp32_link.h
│   │       ├── power_manager.h
│   │       └── stm32g4xx_hal_conf.h
│   ├── esp32-c3/
│   │   ├── main/
│   │   │   ├── main.c
│   │   │   ├── ble_service.c
│   │   │   ├── wifi_server.c
│   │   │   ├── uart_protocol.c
│   │   │   └── CMakeLists.txt
│   │   ├── CMakeLists.txt
│   │   └── sdkconfig.defaults
│   ├── Makefile
│   └── refracto-bead.ioc
├── hardware/
│   ├── BOM.csv
│   └── enclosure/             # 3D-printable case (STL)
├── docs/
│   ├── assembly_guide.md
│   ├── api_reference.md
│   └── measurement_theory.md
└── scripts/
    ├── read_results.py        # BLE reader + plotter
    ├── calibrate.py           # 2-point calibration helper
    └── compound_lookup.py     # Offline compound RI lookup
```

---

## Getting Started

### Building the STM32 Firmware

```bash
# Requires arm-none-eabi-gcc toolchain and STM32Cube HAL
cd firmware
make -j8
# Flash via SWD (ST-Link) or USB DFU:
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
        -c "program build/refracto-bead.elf verify reset exit"
```

### Building the ESP32-C3 Firmware

```bash
# Requires ESP-IDF v5.3+
cd firmware/esp32-c3
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyACM0 flash
```

### Running the Python Companion

```bash
cd scripts
pip install bleak matplotlib numpy
python3 read_results.py --mac AA:BB:CC:DD:EE:FF --mode ri
python3 read_results.py --mac AA:BB:CC:DD:EE:FF --mode brix --export result.json
python3 compound_lookup.py --nd 1.4657 --vd 47.1
```

---

## License

MIT — build it, sell it, improve it.

---

*Invented as device #43 for the SoC Device Inventions collection. Bringing $3,000–$8,500 benchtop Abbe refractometry down to ~$42 and pocket size, with on-device compound identification that no benchtop instrument offers.*