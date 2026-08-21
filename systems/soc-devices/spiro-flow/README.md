# Spiro Flow

**A pocket-sized, battery-powered electronic spirometer that measures lung function (FVC, FEV1, PEF, FEF25-75, FEV1/FVC) using a Fleisch pneumotachograph and Sensirion SDP810 differential pressure sensor, with BTPS correction, ATS/ERS 2019 quality grading, ECSC/ERS 1993 predicted-value comparison, and BLE/WiFi relay to a phone app — built around a CH32V203 RISC-V microcontroller paired with an ESP32-C3 wireless bridge.**

---

## What It Does

The Spiro Flow is a **handheld pulmonary function device** — you blow into a disposable mouthpiece, and 8 seconds later you get a complete spirometry report on the OLED and on your phone. Unlike desktop clinical spirometers ($2000–$8000), the Spiro Flow costs under $65 to build and fits in a pocket. It computes all standard spirometry parameters, grades maneuver quality per ATS/ERS 2019 guidelines, compares results to ECSC/ERS 1993 predicted values, and classifies the pattern as normal, obstructive, restrictive, or mixed.

### Why affordable spirometry matters

Spirometry is the most common pulmonary function test, used to diagnose and monitor asthma, COPD, pulmonary fibrosis, and other respiratory diseases. Over 500 million people worldwide have chronic respiratory conditions, yet spirometry access is severely limited in low-resource settings. The WHO estimates that 80% of COPD deaths occur in low- and middle-income countries where spirometers are simply unavailable. A $65 open-source spirometer with clinical-grade computation could transform respiratory care in community clinics, telemedicine, and home monitoring.

### How it works

1. **Fleisch pneumotachograph** — the patient blows through a disposable mouthpiece attached to a barrel containing a fine stainless steel mesh screen (400 mesh). The screen creates a small, linear pressure drop proportional to airflow: ΔP = R × flow.

2. **SDP810 differential pressure sensor** — a Sensirion SDP810-500Pa sensor measures the pressure drop across the screen at 250 Hz with 0.1 Pa resolution. The sensor's two ports connect via silicone tubing to upstream and downstream pressure taps in the pneumotach barrel.

3. **Flow computation** — the CH32V203 reads ΔP and computes flow: `flow (L/s) = ΔP (Pa) / 0.0115 Pa·s/L`. The flow is integrated over time (trapezoidal integration) to obtain expired volume in mL.

4. **BTPS correction** — a Bosch BME280 sensor measures ambient temperature, barometric pressure, and humidity. The firmware applies the standard BTPS (Body Temperature, Pressure, Saturated) correction to convert ambient-volume measurements to body-condition volume: `V_btps = V_amb × (310.15 / T_amb) × (Pb - PH2O) / (Pb - 47)`.

5. **Maneuver detection** — the firmware detects the start of forced expiration when flow exceeds 0.5 L/s, then captures flow and volume for up to 8 seconds. The end of maneuver is detected when flow drops below 0.025 L/s for 0.5 seconds.

6. **Back-extrapolation** — the true time zero of the maneuver is found by back-extrapolating the steepest portion of the volume-time curve to zero volume. The back-extrapolation volume (BEV) is a key quality metric — if the patient hesitated at the start, BEV is large and the maneuver is downgraded.

7. **Parameter computation** — from the corrected flow-volume curve, the firmware computes:
   - **FVC** (Forced Vital Capacity) — total expired volume
   - **FEV1** (Forced Expiratory Volume in 1 second) — volume expired in the first second
   - **FEV1/FVC** ratio — Tiffeneau-Pinelli index, key for obstruction detection
   - **PEF** (Peak Expiratory Flow) — maximum flow rate during expiration
   - **FEF25-75** — mean flow between 25% and 75% of FVC (small airway indicator)
   - **FET** (Forced Expiratory Time) — duration of forced expiration
   - **PIF** (Peak Inspiratory Flow) and **FIVC** (Forced Inspiratory Vital Capacity)

8. **Quality grading** — each maneuver is graded A–F per ATS/ERS 2019 acceptability criteria, based on back-extrapolation volume, forced expiratory time, and curve smoothness (absence of cough artifacts).

9. **Predicted values** — ECSC/ERS 1993 reference equations compute predicted FEV1 and FVC from age, height, sex, and ethnicity. Results are shown as percent predicted, with the lower limit of normal (LLN) for FEV1/FVC.

10. **Diagnostic classification** — the pattern is classified as:
    - **Normal** — FEV1/FVC ≥ LLN and FVC ≥ 80% predicted
    - **Obstructive** — FEV1/FVC < LLN and FVC ≥ 80% predicted (e.g., asthma, COPD)
    - **Restrictive** — FEV1/FVC ≥ LLN and FVC < 80% predicted (e.g., fibrosis)
    - **Mixed** — FEV1/FVC < LLN and FVC < 80% predicted

11. **Wireless relay** — results are sent via UART to an ESP32-C3 module, which relays them over BLE to a phone app or over WiFi to a cloud EHR system. The ESP32-C3 also provides NTP time synchronization.

### Use Cases

| Application | How Spiro Flow Helps |
|------------|---------------------|
| COPD screening | Detect airflow obstruction in primary care, community clinics, pharmacies |
| Asthma monitoring | Track FEV1 and PEF over time at home; detect exacerbations early |
| Telemedicine | Patient performs spirometry at home; results sent to clinician via BLE/WiFi |
| Occupational health | Screen workers in dusty/fume environments for respiratory decline |
| Clinical trials | Low-cost endpoint measurement for respiratory drug trials |
| Global health | Affordable spirometry for LMICs where desktop units are unaffordable |
| Pulmonary rehab | Monitor FVC/FEV1 improvements during rehabilitation programs |
| Pre-operative assessment | Screen for respiratory risk before surgery |
| Sports science | Track athlete pulmonary function at altitude or during training |
| Public health surveillance | Population-level respiratory health monitoring during pandemics |
| Education | Teach spirometry technique and interpretation in medical/nursing schools |
| Research | Low-cost spirometry for field studies and epidemiological research |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              SPIRO FLOW                                           │
│                                                                                   │
│   ┌───────────────────────────────────────────────────┐                          │
│   │         CH32V203RBT6 (RISC-V RV32IMAC @ 144 MHz)   │                          │
│   │         128 KB flash, 64 KB SRAM, LQFP64           │                          │
│   │                                                   │                          │
│   │  ┌──────────────────────────────────────────────┐ │   I2C1 (PB6/PB7)          │
│   │  │ sensor ISR (250 Hz)                          │◄┼──────────────────────┐   │
│   │  │  SDP810 ΔP → flow = ΔP/R → ∫flow dt = vol   │ │                      │   │
│   │  ├──────────────────────────────────────────────┤ │   ┌──────────────┐  │   │
│   │  │ maneuver_fsm — blast detect → capture → end  │ │   │ SDP810       │  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ ±500Pa       │  │   │
│   │  │ spirometry_task                              │◄┼───│ diff press    │  │   │
│   │  │  BTPS, BEV, FVC, FEV1, PEF, FEF25-75, FET   │ │   │ I2C 0x21     │  │   │
│   │  │  predicted (ECSC/ERS), grade (ATS/ERS), DX   │ │   └──────────────┘  │   │
│   │  ├──────────────────────────────────────────────┤ │                      │   │
│   │  │ display_task — SH1106 flow-vol loop + results│◄┼───┌──────────────┐  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ BME280       │  │   │
│   │  │ flashlog_task — W25Q128 session storage      │ │   │ temp/pres/RH │  │   │
│   │  ├──────────────────────────────────────────────┤ │   │ I2C 0x76     │  │   │
│   │  │ ble_bridge_task — UART → ESP32-C3            │ │   └──────────────┘  │   │
│   │  ├──────────────────────────────────────────────┤ │                      │   │
│   │  │ buzzer_task — coaching tones (TIM3 PWM)      │ │   ┌──────────────┐  │   │
│   │  └──────────────────────────────────────────────┘ │   │ SH1106 OLED  │  │   │
│   │                                                   │◄───│ 128×64 I2C   │  │   │
│   └──────────┬──────────────┬──────────────┬──────────┘   └──────────────┘  │   │
│              │ USART1       │ SPI2         │ TIM3                            │   │
│              │ 115200       │              │ PWM                             │   │
│              ▼              ▼              ▼                                 │   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │   │
│   │ ESP32-C3     │  │ W25Q128      │  │ Piezo Buzzer │                       │   │
│   │ MINI-1       │  │ 16MB flash   │  │ coaching     │                       │   │
│   │ BLE5 + WiFi4 │  │ 512 sessions │  │ tones        │                       │   │
│   └──────┬───────┘  └──────────────┘  └──────────────┘                       │   │
│          │ BLE/WiFi                                                              │   │
│          ▼                                                                       │   │
│   ┌──────────────┐                                                               │   │
│   │ Phone App /  │                                                               │   │
│   │ Cloud EHR    │                                                               │   │
│   └──────────────┘                                                               │   │
│                                                                                   │
│   Pneumotach:  Mouthpiece → Fleisch screen → ΔP → SDP810 → flow → volume         │
│   Power:       LiPo 1800mAh → DW01A/FS8205A → TPS63020 3.3V → TLV70033 (sensors)│
│   Charging:    USB-C → MCP73831 → LiPo                                           │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignments (CH32V203RBT6 LQFP64)

| Pin | GPIO | Function | Direction | Connected To |
|-----|------|----------|-----------|-------------|
| 1 | PA0 | WS2812B data | OUT | WS2812B LED |
| 2 | PA1 | Battery ADC | AN | 2:1 battery divider |
| 3 | PA2 | USART2 TX | OUT | Debug header |
| 4 | PA3 | USART2 RX | IN | Debug header |
| 5 | PA4 | MEASURE button | IN | SW1 (active low) |
| 6 | PA5 | MODE button | IN | SW2 (active low) |
| 7 | PA6 | TIM3 CH1 PWM | OUT | 2N3904 base → buzzer |
| 8 | PA8 | Status LED | OUT | Green LED |
| 9 | PA9 | USART1 TX | OUT | ESP32-C3 GPIO5 (RX) |
| 10 | PA10 | USART1 RX | IN | ESP32-C3 GPIO4 (TX) |
| 11 | PA11 | USB D- | I/O | USB-C connector |
| 12 | PA12 | USB D+ | I/O | USB-C connector |
| 13 | PB0 | Charger status | IN | MCP73831 STAT |
| 14 | PB3 | ESP32-C3 EN | OUT | ESP32-C3 EN |
| 15 | PB4 | ESP32-C3 BOOT | OUT | ESP32-C3 IO9 (pull-up) |
| 16 | PB6 | I2C1 SCL | I/O | SDP810, BME280, SH1106 |
| 17 | PB7 | I2C1 SDA | I/O | SDP810, BME280, SH1106 |
| 18 | PB12 | Flash CS | OUT | W25Q128 CS |
| 19 | PB13 | SPI2 SCK | OUT | W25Q128 SCK |
| 20 | PB14 | SPI2 MISO | IN | W25Q128 DO |
| 21 | PB15 | SPI2 MOSI | OUT | W25Q128 DI |

## I2C Bus Devices

| Device | Address | Function |
|--------|---------|----------|
| SDP810-500Pa | 0x21 | Differential pressure sensor (250 Hz) |
| BME280 | 0x76 | Ambient temperature/pressure/humidity |
| SH1106 OLED | 0x3C | 128×64 monochrome display |

---

## Power Architecture

```
USB-C 5V ──→ MCP73831 ──→ LiPo 3.7V 1800mAh
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
                   CH32V203     SDP810
                   ESP32-C3     BME280
                   SH1106
                   W25Q128
                   WS2812B
```

- **Battery life:** ~15 hours continuous, ~200 maneuvers
- **Charge time:** ~4 hours via USB-C
- **Low-power:** CH32V203 standby (~2µA), ESP32-C3 deep sleep (~5µA)

---

## Firmware

### Build

**CH32V203 (main MCU):**
```bash
cd firmware
make          # requires riscv-none-embed-gcc + WCH CH32V20x HAL
make flash    # requires WCH-LinkE SWD programmer
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
| `main.c` | Super-loop, state machine, maneuver capture |
| `spirometry.c` | FVC/FEV1/PEF/FEF25-75 computation, BTPS, grading |
| `sdp810.c` | SDP810 differential pressure sensor driver |
| `bme280.c` | BME280 ambient sensor with full compensation |
| `sh1106.c` | OLED display driver with flow-volume plotting |
| `ble_bridge.c` | UART binary protocol to ESP32-C3 |
| `flashlog.c` | W25Q128 SPI flash session logging |
| `buzzer.c` | Coaching tone generation (TIM3 PWM) |
| `ws2812.c` | WS2812B RGB LED bit-bang driver |
| `linker.ld` | CH32V203 linker script (128KB flash, 64KB SRAM) |
| `Makefile` | Build system for riscv-none-embed-gcc |
| `esp32_c3_bridge/` | ESP-IDF project for BLE/WiFi bridge |

---

## Python Companion App

```bash
cd scripts
python3 spiro_flow_viewer.py --demo --age 35 --height 178 --sex male
```

Output:
```
  Flow-Volume Loop:
  Flow (L/s) ↑ 9.5
  │      ●
  │  ●       ●
  │             ●
  │                ●
  ...
  └─────────────────────────────────────────────────────────────────────
  └─────────────────────────────────────────────────────────────────────→ Volume (L) 5.5

  SPIRO FLOW — Spirometry Results
  Patient: Demo Patient  |  Age: 35  |  Height: 178cm  |  Sex: M
  Ambient: 22.0°C  |  760 mmHg  |  50% RH  |  BTPS: 1.106
  ------------------------------------------------------------
  Parameter              Measured  Predicted    %Pred
  ------------------------------------------------------------
  FVC (L)                    5.50       5.00     110%
  FEV1 (L)                   3.85       3.75     103%
  FEV1/FVC (%)               70.0       74.9
  PEF (L/s)                  10.5
  FEF25-75 (L/s)              2.6
  FET (s)                     8.0
  ------------------------------------------------------------
  Quality Grade: A (excellent)
  Diagnosis: Normal
  LLN (FEV1/FVC): 66.9%
```

---

## BOM Summary

| Part | Qty | Unit Cost | Source |
|------|-----|-----------|--------|
| CH32V203RBT6 | 1 | $2.20 | Mouser |
| ESP32-C3-MINI-1 | 1 | $2.80 | Mouser |
| SDP810-500Pa | 1 | $18.00 | Digi-Key |
| BME280 | 1 | $5.50 | Digi-Key |
| SH1106 OLED 1.3" | 1 | $3.50 | AliExpress |
| W25Q128 16MB | 1 | $1.20 | Digi-Key |
| TPS63020 | 1 | $3.90 | Digi-Key |
| MCP73831 | 1 | $0.60 | Digi-Key |
| Fleisch pneumotach | 1 | $8.00 | custom |
| LiPo 1800mAh | 1 | $4.50 | BatteryJunction |
| Passives + misc | — | $3.00 | Digi-Key |
| PCB (4-layer) | 1 | $5.00 | PCBWay |
| **Total** | | **~$62** | |

Full BOM: `hardware/BOM.csv`

---

## Medical Disclaimer

The Spiro Flow is an open-source research and educational device. It is **not FDA-approved** or CE-marked. It is not intended for clinical diagnosis. Always use under appropriate medical supervision. The spirometry algorithms are based on published standards (ATS/ERS 2019, ECSC/ERS 1993) but have not been clinically validated against reference devices. Use disposable mouthpieces and bacterial/viral filters for infection control.

---

## License

MIT — build it, sell it, improve it.