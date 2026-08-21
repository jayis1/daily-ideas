# Terra Pin

**A handheld, battery-powered soil microbiome activity probe that measures in-situ CO₂ flux (soil respiration), oxidation-reduction potential (redox / Eh), electrical conductivity, moisture, and temperature — then fuses these into a single Soil Health Index for regenerative agriculture, carbon-farming verification, compost maturity testing, and soil ecology research.**

---

## What It Does

The Terra Pin is a pocket-sized **soil health diagnostic instrument** — push it into the ground, press a button, and 90 seconds later you get a comprehensive living-soil reading on the OLED and logged to SD. Unlike cheap NPK probes or single-parameter moisture sensors, the Terra Pin measures the **biological activity** of soil directly, by quantifying how fast the soil microbial community is respiring CO₂, combined with the electrochemical environment (redox potential and conductivity) that governs nutrient availability.

### Why soil microbiome activity matters

Soil health is fundamentally about **biology**. A soil with great chemistry but dead microbiology is dirt, not soil — it compacts, erodes, holds no water, and grows nutrient-poor crops. Regenerative agriculture, carbon farming, and soil-ecology science all need a fast, affordable way to measure whether soil life is thriving. Professional soil respiration labs (Solvita, MicroBIOMETER) cost $400–$2000 per kit and require sending samples away. The Terra Pin does it in-situ in 90 seconds for a sub-$120 build.

### What it measures

- **Soil CO₂ flux (respiration rate)** — an inline NDIR (non-dispersive infrared) CO₂ sensor (**Sensirion SCD41**) sits in a sealed chamber at the probe tip. When the probe is inserted, the chamber seals against the soil surface. The firmware measures the rate of CO₂ rise over 60 seconds (ppm/min), converts to mg CO₂-C m⁻² h⁻¹ using the chamber volume and temperature/pressure (ideal gas law). This is the gold-standard proxy for microbial metabolic activity — more CO₂ = more microbes = healthier soil.
- **Oxidation-reduction potential (ORP / Eh)** — a platinum ORP electrode + Ag/AgCl reference (Atlas Scientific EZO-ORP) measures the redox potential in mV. Redox governs whether the soil is aerobic (oxidized, +300 to +600 mV — good for roots and nitrification) or anaerobic (reduced, < +100 mV — denitrification, sulfur reduction, root disease). A sudden redox drop after rain is an early warning of waterlogging stress.
- **Electrical conductivity (EC)** — a 2-electrode conductivity probe (Atlas Scientific EZO-EC) measures bulk soil EC in µS/cm. EC integrates salinity, dissolved ions, and nutrient availability. Combined with moisture and temperature, it enables pore-water EC estimation (the actual nutrient solution plants roots see).
- **Soil moisture** — a capacitive moisture sensor (MCB-01-A capacitive probe, immune to corrosion unlike resistive probes) measures volumetric water content (VWC %) via the STM32 ADC + 555-style oscillator frequency output.
- **Soil temperature** — a DS18B20 waterproof probe at the chamber depth measures soil temperature (°C), used for CO₂ flux temperature correction (Q₁₀ model) and EC temperature compensation (25 °C normalization).
- **Atmospheric CO₂ baseline** — a second SCD41 sensor (mounted in the handle, open to air) measures ambient CO₂ so the flux calculation subtracts the atmospheric baseline from the chamber rise rate.

### Soil Health Index (SHI)

The firmware fuses all measurements into a **0–100 Soil Health Index** using a weighted model:

```
SHI = 30·S_resp + 25·S_redox + 20·S_ec + 15·S_moist + 10·S_temp
```

Where each sub-score is normalized to 0–1 against agronomically optimal ranges:

| Parameter | Optimal range | Score |
|-----------|--------------|-------|
| Respiration (mg CO₂-C m⁻² h⁻¹) | 15–60 (high activity, not excessive) | Bell curve peak at 30 |
| Redox (mV) | +300 to +550 (aerobic) | Linear ramp 0→1 from 100→350 mV, penalty >550 (too dry/oxidized) |
| EC (µS/cm) | 100–1500 (nutrient-rich, not saline) | Bell curve peak at 600 |
| Moisture (VWC %) | 25–45% (field capacity band) | Bell curve peak at 35 |
| Temperature (°C) | 15–25 °C (optimal microbial range) | Bell curve peak at 20 |

A soil scoring 80+ is thriving; 50–79 is moderate; below 50 needs amendment. The index is a heuristic — not a lab replacement — but it gives farmers, gardeners, composters, and researchers an instant biological-health snapshot they can act on.

### Use Cases

| Application | How Terra Pin Helps |
|------------|---------------------|
| Regenerative agriculture | Track soil biology recovery over seasons of cover-cropping, no-till, or compost application — watch the SHI climb |
| Carbon farming verification | CO₂ flux is a direct proxy for soil organic carbon turnover; monitor plots enrolled in carbon-credit programs |
| Compost maturity | Plunge the probe into a compost windrow; high respiration = still active, low + stable redox = mature and ready to use |
| Irrigation management | Redox drops before visible wilting; detect waterlogging or drought stress in the root zone days before symptoms appear |
| Salinity monitoring | EC + moisture → pore-water salinity; detect salt buildup in greenhouse or irrigated arid-land soils |
| Soil ecology research | In-situ CO₂ flux + redox time-series without lab sampling artifacts; log continuously at a fixed station |
| Fertilizer timing | Redox in the aerobic zone indicates nitrification is active (NH₄⁺ → NO₃⁻); if redox drops, denitrification is stealing your nitrogen |
| Golf course / sports turf | Monitor thatch decomposition and root-zone health across greens without sending plugs to a lab |
| Vineyard terroir | Map soil biological activity across a vineyard block — correlates with terroir-driven wine quality |
| Citizen science | Affordable soil-health testing for community gardens, school programs, and permaculture collectives |
| Wetland monitoring | Redox is the master variable in wetland soils; track Eh to verify hydric soil conditions for delineation |
| Bioremediation | Monitor microbial activity in contaminated soil being bioremediated — rising CO₂ flux = bugs are eating the pollutants |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              TERRA PIN                                            │
│                                                                                   │
│   ┌───────────────────────────────────────────────────┐                          │
│   │           ESP32-S3-WROOM-1                         │                          │
│   │   (Xtensa LX7 dual-core 240 MHz, 512 KB SRAM,     │                          │
│   │    384 KB ROM, WiFi 4, BLE 5, 16 KB RTC SRAM)     │                          │
│   │                                                   │                          │
│   │   ┌─────────────────────────────────────────────┐ │     I2C (shared)         │
│   │   │ flux_task — SCD41 chamber CO₂ rise rate     │◄┼──────────────────────────┤
│   │   │  (1 Hz → 60 s slope → mg C m⁻² h⁻¹)        │ │     ┌──────────────┐     │
│   │   ├─────────────────────────────────────────────┤ │     │ SCD41 #1     │     │
│   │   │ ambient_task — SCD41 #2 atmospheric CO₂     │◄┼─────┤ (chamber)    │     │
│   │   ├─────────────────────────────────────────────┤ │     │ NDIR CO₂     │     │
│   │   │ orp_task — EZO-ORP redox (mV)               │◄├─────┤ └──────────────┘     │
│   │   │  (UART3, Atlas Scientific protocol)         │ │     ┌──────────────┐     │
│   │   ├─────────────────────────────────────────────┤ │     │ SCD41 #2     │     │
│   │   │ ec_task — EZO-EC conductivity (µS/cm)       │◄├─────┤ (ambient)    │     │
│   │   │  (UART4, Atlas Scientific protocol)         │ │     │ NDIR CO₂     │     │
│   │   ├─────────────────────────────────────────────┤ │     └──────────────┘     │
│   │   │ moisture_task — capacitive VWC via freq     │◄├── IRQ (PCNT) ─────────────┤
│   │   │  (MCB-01-A 555 oscillator → PCNT count)     │ │     ┌──────────────┐     │
│   │   ├─────────────────────────────────────────────┤ │     │ MCB-01-A     │     │
│   │   │ temp_task — DS18B20 soil temp (1-Wire)      │◄├── 1-Wire ────────────────┤
│   │   │  (temperature correction Q₁₀, EC comp)     │ │     │ capacitive    │     │
│   │   ├─────────────────────────────────────────────┤ │     │ moisture probe│     │
│   │   │ shi_task — Soil Health Index fusion         │ │     └──────────────┘     │
│   │   │  (weighted sub-scores → 0–100 SHI)         │ │                          │
│   │   ├─────────────────────────────────────────────┤ │                          │
│   │   │ display_task — SH1106 OLED (I2C)            │◄├── I2C ───────────────────┤
│   │   │  (SHI gauge, respiration bar, parameters)   │ │     ┌──────────────┐     │
│   │   ├─────────────────────────────────────────────┤ │     │ SH1106 OLED  │     │
│   │   │ sdlog_task — SD card CSV logger (SPI)       │◄├── SPI ───────────────────┤
│   │   │  (per-reading record + continuous mode)     │ │     │ microSD      │     │
│   │   ├─────────────────────────────────────────────┤ │     └──────────────┘     │
│   │   │ ble_task — BLE GATT soil-health notifications│◄├── BLE 5 ─────────────────┤
│   │   │  (SHI + parameters to phone app)            │ │     │ phone app    │     │
│   │   ├─────────────────────────────────────────────┤ │     └──────────────┘     │
│   │   │ wifi_task — CSV push + OTA (optional)       │ │                          │
│   │   └─────────────────────────────────────────────┘ │                          │
│   │                                                   │                          │
│   │   GPIO: BTN_MEASURE, BTN_MODE, ENC_A, ENC_B      │                          │
│   │   LED_RGB (WS2812B) — SHI color indicator         │                          │
│   └───────────────────────────────────────────────────┘                          │
│                                                                                   │
│   Power: 3.7 V 1800 mAh LiPo → MCP73831 USB-C charger                              │
│          → TPS63020 buck-boost (3.3 V rail)                                       │
│          SCD41 sensors on separate 3.3 V LDO (TLV70033) for clean power           │
│                                                                                   │
│   Mechanical: 18 mm stainless probe shaft, 120 mm chamber tip,                    │
│               PTFE membrane gas-permeable seal, ORP + EC electrodes               │
│               exposed at tip, DS18B20 potted in shaft wall                         │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Schematic Overview

| Section | Key Parts | Notes |
|---------|-----------|-------|
| MCU core | ESP32-S3-WROOM-1 (U1), 40 MHz XTAL | Dual-core 240 MHz, WiFi 4 + BLE 5, 8 MB flash in module |
| CO₂ — chamber | Sensirion SCD41 (U2), I2C | NDIR true CO₂, 400–5000 ppm, ±40 ppm, 1.8–3.3 V |
| CO₂ — ambient | Sensirion SCD41 (U3), I2C | Second sensor in handle, same I2C bus (alt address via mux) |
| I2C mux | TCA9548A (U4) | SCD41 sensors share address 0x62; mux selects chamber or ambient |
| ORP | Atlas Scientific EZO-ORP (U5), UART | Platinum electrode + Ag/AgCl ref, ±2000 mV range |
| EC | Atlas Scientific EZO-EC (U6), UART | K=1.0 probe, 0.07–500 mS/cm, automatic temp comp |
| Moisture | MCB-01-A capacitive probe → PCNT | 555 oscillator, freq ∝ VWC, 10 Hz–10 kHz range |
| Temperature | DS18B20 (U7), 1-Wire | Waterproof TO-92 potted in probe shaft, ±0.5 °C |
| Display | SH1106 1.3" OLED (U8), I2C | 128×64, SHI gauge + parameter readout |
| Storage | microSD socket (J2), SPI | FAT32 CSV logging, one file per session |
| Power | MCP73831 (U9) + TPS63020 (U10) + TLV70033 (U11) | USB-C charging, 3.3 V main + 3.3 V sensor LDO |
| RGB LED | WS2812B (LED1) | Green (SHI > 70), Yellow (50–70), Red (< 50) |
| User input | 2 tactile buttons + EC11 rotary encoder | MEASURE, MODE, menu navigation |
| Battery protection | DW01A (U12) + FS8205A (U13) | Overcharge / overdischarge / short-circuit |

---

## Pin Assignments (ESP32-S3-WROOM-1)

| GPIO | Function | Direction | Notes |
|------|----------|-----------|-------|
| GPIO0  | BOOT_STRAP          | I/O  | Pull-up on board; 0 = download mode |
| GPIO1  | UART3_TX → EZO-ORP  | TX   | Atlas ORP probe, 9600 baud |
| GPIO2  | UART3_RX ← EZO-ORP  | RX   | Atlas ORP probe |
| GPIO4  | UART4_TX → EZO-EC   | TX   | Atlas EC probe, 9600 baud |
| GPIO5  | UART4_RX ← EZO-EC   | RX   | Atlas EC probe |
| GPIO6  | I2C_SCL (shared)    | OD   | SCD41 ×2 (via TCA9548A), SH1106 OLED, TCA9548A mux |
| GPIO7  | I2C_SDA (shared)    | OD   | 400 kHz, 4.7 kΩ pull-ups |
| GPIO8  | SPI_SD_CS           | OUT  | microSD card select |
| GPIO9  | SPI_MISO            | IN   | SD card MISO (HSPI) |
| GPIO10 | SPI_MOSI            | OUT  | SD card MOSI |
| GPIO11 | SPI_SCK             | OUT  | SD card SCK |
| GPIO12 | ONEWIRE (DS18B20)   | OD   | 4.7 kΩ pull-up, parasitic power off |
| GPIO13 | MOISTURE_FREQ       | IN   | PCNT input — capacitive probe oscillator |
| GPIO14 | BTN_MEASURE         | IN   | Pull-up, active-low, debounced in SW |
| GPIO15 | BTN_MODE            | IN   | Pull-up, active-low |
| GPIO16 | ENC_A               | IN   | Rotary encoder quadrature A |
| GPIO17 | ENC_B               | IN   | Rotary encoder quadrature B |
| GPIO18 | ENC_BTN             | IN   | Rotary encoder push |
| GPIO19 | WS2812_DATA         | OUT  | RMT channel 0, 800 kHz |
| GPIO20 | LED_STATUS          | OUT  | Simple green LED for activity |
| GPIO21 | CHARGER_STAT        | IN   | MCP73831 STAT pin (charging/done) |
| GPIO22 | BATT_DIV            | IN   | ADC1_CH1 — battery voltage divider (2:1) |
| GPIO3  | SCD41_RESET         | OUT  | Reset both SCD41 sensors (shared line) |
| GPIO46 | BOOT_LED            | OUT  | On-board LED (dev module) |

---

## Power Architecture

```
USB-C 5V ──► MCP73831 (LiPo charger, 4.2V, 500mA)
                │
                ▼
        LiPo 3.7V 1800 mAh ──► DW01A/FS8205A protection
                │
                ├──► TPS63020 buck-boost ──► 3.3V (main rail: MCU, OLED, SD, sensors)
                │                             Imax = 2A, efficiency ~90%
                │
                └──► TLV70033 LDO ──► 3.3V_SENSORS (SCD41 ×2 only)
                                      Low-noise LDO for NDIR measurement stability

Battery monitoring: GPIO22 (ADC1_CH1) reads 2:1 voltage divider
  Full: 4.2V → 2.1V → ADC ~2610 (12-bit, 3.3V ref)
  Empty: 3.0V → 1.5V → ADC ~1860
```

**Power budget:**

| Component | Current (active) | Current (idle) | Duty | Avg (mA) |
|-----------|-----------------|----------------|------|----------|
| ESP32-S3 (CPU active) | 80 mA | 5 mA (light sleep) | 30% | 27.5 |
| SCD41 ×2 (continuous) | 40 mA | 5 mA (idle) | 50% | 22.5 |
| SH1106 OLED | 12 mA | 0.1 mA | 20% | 2.5 |
| SD card (write) | 70 mA | 0.3 mA | 1% | 1.0 |
| EZO-ORP + EZO-EC | 6 mA | 0.4 mA | 10% | 1.0 |
| WS2812B | 20 mA | 0 mA | 5% | 1.0 |
| TPS63020 quiescent | — | 0.05 mA | 100% | 0.05 |
| **Total** | | | | **~56 mA** |

Battery life: 1800 mAh / 56 mA ≈ **32 hours** (continuous logging mode).
In point-measurement mode (sleep between readings): **> 5 days**.

---

## Mechanical Design

```
    ┌─────────────────────────────────────────────┐
    │  Handle (PCB + battery + OLED + buttons)    │
    │  ┌─────────┐  ┌──────┐  ┌──────┐           │
    │  │ SH1106  │  │MEAS  │  │ MODE │           │
    │  │ OLED    │  │ btn  │  │ btn  │           │
    │  └─────────┘  └──────┘  └──────┘           │
    │  ┌──────────────────────────────────┐      │
    │  │  1800 mAh LiPo battery            │      │
    │  └──────────────────────────────────┘      │
    │  ┌──────────┐  USB-C charge port           │
    │  │ EC11 enc │                              │
    │  └──────────┘                              │
    └───────────────────┬───────────────────────┘
                        │  18 mm SS tube (shaft)
                        │  150 mm long
                        │
    ┌───────────────────┴───────────────────────┐
    │  Chamber tip (PTFE membrane, 120 mm)       │
    │  ┌──────────────────────────────────┐      │
    │  │  SCD41 #1 (chamber CO₂)          │      │
    │  │  DS18B20 (soil temp)             │      │
    │  │  ORP electrode (Pt + Ag/AgCl)    │      │
    │  │  EC electrode (2-pin graphite)   │      │
    │  │  MCB-01-A moisture plates        │      │
    │  └──────────────────────────────────┘      │
    │  PTFE membrane at bottom — gas permeable,  │
    │  water repellant; seals against soil when  │
    │  pressed in.                                │
    └─────────────────────────────────────────────┘
```

The probe tip is a 120 mm long stainless-steel tube with a **PTFE membrane** (Gore-Tex-like) at the bottom. When pressed into soil, the membrane seals against the soil surface — soil CO₂ diffuses through the membrane into the chamber but liquid water is blocked. The SCD41 inside the chamber measures the CO₂ rise rate. The ORP and EC electrodes are exposed through side ports in the shaft wall, contacting the soil directly. The DS18B20 is potted in epoxy in the shaft wall. The capacitive moisture plates are two copper traces on the inner PCB, separated from soil by a thin soldermask layer (capacitive sensing through the PCB).

---

## Firmware Overview

The firmware is written in C using the **ESP-IDF v5.2** framework with FreeRTOS. Each sensor has its own task:

| Task | Priority | Stack | Rate | Function |
|------|----------|-------|------|----------|
| `flux_task` | 5 (high) | 4096 | 1 Hz → 60 s slope | SCD41 chamber CO₂ rise rate → respiration |
| `ambient_task` | 3 | 3072 | 0.1 Hz | SCD41 ambient CO₂ baseline |
| `orp_task` | 4 | 3072 | 0.2 Hz | EZO-ORP UART read → redox mV |
| `ec_task` | 4 | 3072 | 0.2 Hz | EZO-EC UART read → conductivity µS/cm |
| `moisture_task` | 3 | 2048 | 1 Hz | PCNT frequency → VWC % |
| `temp_task` | 3 | 2048 | 0.5 Hz | DS18B20 1-Wire → soil temp °C |
| `shi_task` | 6 (highest) | 4096 | event-driven | Fuse all parameters → SHI 0–100 |
| `display_task` | 2 | 3072 | 10 Hz | SH1106 OLED UI |
| `sdlog_task` | 2 | 4096 | event-driven | FAT32 CSV logging |
| `ble_task` | 3 | 4096 | event-driven | BLE GATT notifications |
| `button_task` | 3 | 2048 | 100 Hz (debounce) | Button + encoder polling |

### Measurement sequence (point mode)

1. Operator pushes probe into soil, presses **MEASURE**.
2. `flux_task` starts: SCD41 #1 begins single-shot periodic measurement (5 s interval).
3. `orp_task`, `ec_task`, `moisture_task`, `temp_task` read immediately.
4. After 60 seconds, `flux_task` computes CO₂ slope (ppm/min) via linear regression.
5. `shi_task` fuses all readings → SHI.
6. `display_task` shows results on OLED; `sdlog_task` writes CSV; `ble_task` notifies phone.
7. System returns to idle (sensors sleep).

### Continuous mode

Press **MODE** to toggle continuous mode: all sensors read at their natural rate, SHI updates every 60 s, and data is logged to SD every reading. For long-term station deployment (e.g., field research), the probe stays inserted and the solar option (see hardware/BOM.csv) extends operation indefinitely.

---

## SD Card Log Format

```csv
# Terra Pin soil health log
# session,timestamp,co2_chamber,co2_ambient,flux_ppm_min,flux_mgC,orp_mv,ec_us,moisture_vwc,temp_c,shi,shi_resp,shi_redox,shi_ec,shi_moist,shi_temp,lat,lon
0,2026-06-23T14:32:01,847,412,3.2,14.8,+421,687,33.2,19.4,72,0.78,0.82,0.65,0.88,0.91,0.0,0.0
0,2026-06-23T14:34:15,891,415,2.8,12.9,+398,712,34.1,19.6,69,0.71,0.76,0.68,0.91,0.93,0.0,0.0
```

---

## BLE Interface

| UUID | Name | Type | Description |
|------|------|------|-------------|
| 0x0001 | Terra Pin Service | service | Root service |
| 0x0002 | SHI | characteristic (read/notify) | Soil Health Index 0–100 (uint8) |
| 0x0003 | Flux | characteristic (read) | CO₂ flux mg C m⁻² h⁻¹ (float32, LE) |
| 0x0004 | ORP | characteristic (read) | Redox potential mV (int16) |
| 0x0005 | EC | characteristic (read) | Conductivity µS/cm (uint16) |
| 0x0006 | Moisture | characteristic (read) | VWC % (float32, LE) |
| 0x0007 | Temperature | characteristic (read) | Soil temp °C (float32, LE) |
| 0x0008 | Raw CO₂ | characteristic (read) | Chamber + ambient CO₂ ppm (2× uint16) |
| 0x0009 | Mode | characteristic (read/write) | 0=point, 1=continuous, 2=calibrate |

---

## Calibration

### ORP calibration
Atlas Scientific EZO-ORP comes factory-calibrated. Optional field check with ZoBell's solution (228 mV at 25 °C). Send `Cal,228` over UART.

### EC calibration
Atlas Scientific EZO-EC requires 2-point calibration:
- Dry (calibrate 0): `Cal,dry`
- Low point (e.g., 1413 µS/cm KCl standard): `Cal,low,1413`

### Moisture calibration (capacitive probe)
1. Air-dry soil (oven-dried, 0% VWC): press MEASURE in MODE=calibrate → stores `freq_dry`.
2. Saturated soil (standing water, ~100% VWC): press MEASURE → stores `freq_wet`.
3. Firmware linearly maps frequency → VWC between the two endpoints.

### SCD41 field calibration
Sensirion SCD41 is factory-calibrated for CO₂. For long-term accuracy, periodic forced recalibration at 420 ppm (outdoor ambient) using `perform_forced_recalibration(420)`.

---

## Assembly Guide

See [docs/assembly-guide.md](docs/assembly-guide.md) for step-by-step build instructions, PCB assembly notes, probe shaft construction, PTFE membrane installation, and waterproofing details.

## API Reference

See [docs/api-reference.md](docs/api-reference.md) for the full firmware API, sensor driver interfaces, BLE GATT protocol, and Python helper script usage.

---

## BOM Summary

| Category | Parts | Est. Cost |
|----------|-------|-----------|
| MCU + wireless | ESP32-S3-WROOM-1 | $3.50 |
| CO₂ sensors | 2× Sensirion SCD41 | $23.80 |
| I2C mux | TCA9548A | $0.80 |
| ORP | Atlas Scientific EZO-ORP + probe | $42.00 |
| EC | Atlas Scientific EZO-EC + probe | $42.00 |
| Moisture | MCB-01-A capacitive probe | $3.50 |
| Temperature | DS18B20 waterproof | $1.50 |
| Display | SH1106 1.3" OLED | $3.50 |
| Power | MCP73831 + TPS63020 + TLV70033 + DW01A + FS8205A | $5.10 |
| Storage | microSD socket + 8GB card | $2.30 |
| Mechanical | SS tube, PTFE membrane, 3D-printed handle, electrode holders | $8.00 |
| Passives + connectors | R, C, USB-C, buttons, encoder, RGB LED | $4.50 |
| PCB | 4-layer 60×25 mm | $5.00 |
| Battery | 1800 mAh LiPo 602535 | $4.50 |
| **Total** | | **~$120.00** |

Full BOM in [hardware/BOM.csv](hardware/BOM.csv).

---

## License

MIT — build it, sell it, improve it.

---

*Invented by [jayis1](https://github.com/jayis1) — SoC Device Inventions.*