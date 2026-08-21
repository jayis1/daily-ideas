# Iono Pin — Pocket Ion Mobility Spectrometer (IMS)

**Device #54 in the SoC Device Inventions collection.**

A pocket-sized handheld **ion mobility spectrometer** that separates and identifies trace vapors by ionizing sample molecules with a Nickel-63 (or corona-discharge) source, pulsing ions into a drift tube, and measuring their arrival-time spectrum with a Faraday-plate receiver. On-device firmware computes the **ion mobility spectrum** (0.5–3.5 ms drift window), extracts **reduced mobility** (K₀) peaks, classifies them against a 45-compound library (explosives, illicit drugs, CWAs, VOCs, toxic industrial chemicals) with a k-NN classifier, and streams results over BLE/Wi-Fi — bringing $40k–$200k military/lab IMS analyzers (Smiths IONSCAN, Bruker RAID, Thermo EGIS) down to ~$65 and flashlight size.

> ⚠️ **Safety:** A sealed Ni-63 beta source (≤ 1 µCi / 37 kBq) is *exempt-quantity* radioactive material in most jurisdictions (US 10 CFR 30.71, EU EURATOM 2013/59). It is a sealed source with no external dose at contact distance. A corona-discharge ionizer is provided as a **non-radioactive alternative** for jurisdictions restricting radioactive sources, at the cost of ~2× lower sensitivity. Build and operate only where lawful. See [`docs/safety-notes.md`](docs/safety-notes.md).

---

## What it does

| Capability | Detail |
|---|---|
| Principle | Drift-tube ion mobility spectrometry (DT-IMS), positive-ion mode |
| Drift gas | Air (purified, 2-way valve can route through charcoal or sample) |
| Drift field | 250 V/cm, 8.5 cm drift region, 2125 V total |
| Drift time window | 0.5–3.5 ms (→ mobility 0.5–3.5 cm²/V·s) |
| Repetition rate | 20–40 Hz (configurable), 256-spectrum rolling average |
| Sensitivity | ~10 ppb (Ni-63) / ~25 ppb (corona) for TNT (mass-limited) |
| Resolving power | Rₚ = t_d / w_h ≈ 35 (FWHM 100 µs at 3.5 ms) |
| Library | 45 compounds (K₀-based): explosives, drugs, CWAs, TICs, VOCs |
| Classifier | k-NN (k=5) over 24-D K₀-peak feature vector, on-device |
| Display | SH1106 1.3″ OLED — live mobility spectrum + class + confidence |
| Logging | SD card (CSV per-spectrum + binary waveform), session CSV |
| Comms | BLE (live spectrum + verdict) + Wi-Fi (CSV download, OTA) |
| Power | 18650 Li-ion, TP4056 USB-C charging, ~14 h runtime |

---

## Why

Ion mobility spectrometry is the gold standard for **trace vapor detection** at airport security, military checkpoints, hazmat response, and forensic labs — but instruments cost $40k–$200k and are the size of a shoebox. Iono Pin demonstrates that a complete IMS — ionizer, shutter grid, drift tube, Faraday receiver, 24-bit electrometer, HV supply, full DSP, and classifier — can be built for ~$65 in a flashlight-sized package, with an **open DSP + ML pipeline** that commercial units keep proprietary. It is intended for:

- **Education** — teaching mobility spectrometry, drift physics, and K₀ libraries
- **Citizen science / maker security research** — understanding how sniffers work
- **Field screening research** — low-cost deployment of a recognized technique
- **Open instrument design** — a reproducible, documented alternative to closed systems

---

## How it works (physics, in brief)

1. **Ionization.** Sample vapor enters the ionization region. A Ni-63 beta source (or corona discharge) ionizes the carrier gas, forming **reactant ions** (H⁺(H₂O)ₙ in air, the "RIP" — reactant ion peak). Analyte molecules M with proton affinity higher than water **steal** the proton: M + H⁺(H₂O)ₙ → MH⁺(H₂O)ₙ₋ₘ + mH₂O, forming **product ions**.

2. **Shutter pulse.** A Bradbury-Nielsen shutter grid (two interleaved wire sets biased ±90 V to block ions) is pulsed open for 200 µs, admitting a thin slab of ions into the drift region.

3. **Drift.** Ions travel down the drift tube under a uniform field E = 250 V/cm, colliding with the counter-flowing drift gas. Their **drift velocity** v_d = K·E depends on ion mobility K, which is set by collision cross-section and mass. Light, compact ions (e.g., H⁺(H₂O)₃, K₀ ≈ 2.7) arrive first; heavy, bulky ions (e.g., protonated RDX adduct, K₀ ≈ 1.4) arrive last.

4. **Detection.** Ions hit a **Faraday plate** connected to an electrometer-grade TIA. The current (pA–nA) is integrated, converted to voltage, and sampled by a 24-bit ADC at 40 ksps.

5. **Reduced mobility.** Drift time t_d is measured. Reduced mobility is computed:
   K₀ = (L²) / (V·t_d) · (P/760) · (273/T) , where L = drift length, V = drift voltage, P,T = ambient pressure/temperature (from BME280). This **normalizes** drift time across conditions so the **K₀ library is portable**.

6. **Classification.** The spectrum's peaks are detected (derivative + threshold), the K₀ peaks form a feature vector, and a k-NN classifier (k=5) matches it to the 45-compound library, reporting compound + confidence + limit-of-detection estimate.

---

## Block diagram

```
                  ┌───────────────────────────────────────────────────────┐
                  │                    IONO PIN                           │
  Sample vapor ──┼─► Membrane inlet ──► Ionization region ──► Bradbury-   │
  (drift gas     │   (PDMS 20 µm)      (Ni-63 37 kBq OR      │  Nielsen    │
   counter-flow) │                      corona discharge)   │  shutter     │
                  │                                           │  (200 µs)   │
                  │                                           ▼             │
                  │   Drift tube (8.5 cm, 8× resistor rings, 2125 V total)  │
                  │   field 250 V/cm, drift gas counter-flow ──►            │
                  │                                           │             │
                  │                                           ▼             │
                  │   Faraday plate ──► ADA4530-1 TIA ──► ADS122U04        │
                  │                   (1e11 Ω, 10 pA)    (24-bit, 40 ksps) │
                  │                                           │             │
                  │   HV: EMCO F50CT (5 kV) ──► divider chain (8× 10 MΩ)   │
                  │   Shutter bias: ±90 V from dual rail                   │
                  │   Drift-gas pump: 6 V diaphragm micro-pump             │
                  │                                           │             │
                  │   STM32G474RET6 ◄── SPI/ADC/PIO ◄──────────┘             │
                  │   • drift-time DSP, K₀ computation, k-NN classify      │
                  │   • OLED, SD, buttons, buzzer                          │
                  │   • ESP32-C3-MINI-1 (BLE + Wi-Fi bridge)                │
                  └───────────────────────────────────────────────────────┘
                                     │
                          BLE / Wi-Fi ──► phone app
                          SD card ──► CSV + binary log
```

---

## SoC choice

| Role | Chip | Why |
|---|---|---|
| **DSP SoC** | STM32G474RET6 | Cortex-M4F @ 170 MHz, CORDIC + FMAC math accelerators, 6× ADC (one used at high speed via DMA + timer for 40 ksps), 128 KB flash, 32 KB SRAM, 5 V-tolerant, abundant timers for shutter pulse timing. Drift-time DSP + k-NN fit comfortably. |
| **Bridge SoC** | ESP32-C3-MINI-1 | RISC-V Wi-Fi + BLE 5 in a tiny module; UART to STM32 for streaming spectra/verdicts; OTA + CSV download over Wi-Fi web UI. |

---

## Pin assignments (STM32G474RET6 — LQFP-64)

| Pin | Net | Function |
|---|---|---|
| PA0 | ADC1_IN1 / TIA_OUT | Electrometer output → 40 ksps ADC (DMA + TIM1 triggered) |
| PA1 | HV_MON | EMCO HV monitor (5 kV → 2.5 V via 2000:1 divider) |
| PA2 | IONIZER_EN | Ni-63 shutter-bias / corona power enable (safety-interlocked) |
| PA3 | SHUTTER_P | Bradbury-Nielsen shutter + rail (±90 V control via opto) |
| PA4 | SHUTTER_N | Shutter − rail control |
| PA5 | PUMP_PWM | Drift-gas micro-pump MOSFET gate (PWM 25 kHz) |
| PA6 | DAC1_OUT | Shutter bias setpoint (±90 V rail servo) |
| PA7 | DAC2_OUT | Faraday guard bias / electrometer bias |
| PA8 | TIM1_CH1 | ADC conversion trigger (40 ksps) |
| PB0 | ADC2_IN | Vbat divider (2:1) |
| PB10 | UART_TX | → ESP32-C3 RX (115200, 921600 streaming) |
| PB11 | UART_RX | ← ESP32-C3 TX |
| PB12 | SPI2_NSS | ADS122U04 CS (aux high-res ADC for Vbat/HV) |
| PB13 | SPI2_SCK | ADS122U04 SCK |
| PB14 | SPI2_MISO | ADS122U04 DOUT |
| PB15 | SPI2_MOSI | ADS122U04 DIN |
| PC6 | OLED_DC | SH1106 D/C |
| PC8 | OLED_RES | SH1106 RES |
| PC9 | OLED_CS | SH1106 CS |
| PC10 | SPI3_SCK | Shared SPI bus (OLED + SD) |
| PC11 | SPI3_MISO | SD MISO |
| PC12 | SPI3_MOSI | SD MOSI / OLED SDA |
| PD2 | SD_CS | MicroSD CS |
| PA9 | UART1_TX | Debug TX (ST-Link) |
| PA10 | UART1_RX | Debug RX |
| PA13/PA14 | SWDIO/SWCLK | ST-Link debug/flash |
| PB6 | BUZZER | Piezo buzzer PWM |
| PC0 | MODE_BTN | Mode button (ADC-ish digital) |
| PC1 | SCAN_BTN | Scan trigger |
| PC2 | CAL_BTN | Calibration (run blank) |
| PC3 | INTERLOCK | Reed switch (lid closed) — interrupts ionizer |
| PC4 | FAULT_IN | TLV3201 HV fault (over-current) |
| PC5 | HV_SHDN | EMCO shutdown (active low) |
| PB3 | LED_R | WS2812B data line (status) |
| PA15 | I2C1_SCL | BME280 SCL |
| PB4 | I2C1_SDA | BME280 SDA (drift-gas T/P compensation) |

### ESP32-C3-MINI-1 (bridge)
| Pin | Net | Function |
|---|---|---|
| GPIO4 | UART_RX | ← STM32 PB10 (TX) |
| GPIO5 | UART_TX | → STM32 PB11 (RX) |
| GPIO2 | BOOT/STATUS | WS2812 status (BLE link) |
| GPIO6 | BOOT_BTN | OTA / pair button |
| EN | RESET | Power-on reset |

---

## Power architecture

```
USB-C 5V ──► TP4056 ──► 18650 (3.7 V, 2600 mAh)
                        │
                        ├─► MCP1640B boost 3.7→5V (pump + analog rail)
                        │     ├─► AP2112K-3.3  (digital 3V3: STM32, ESP32-C3, OLED)
                        │     └─► LP5907-3.3   (ultra-low-noise 3V3: Faraday TIA, ADC VREF)
                        │
                        └─► EMCO F50CT 5→5000V boost (HV drift stack)
                              └─► 8× 10 MΩ resistor ring → 8.5 cm drift tube
                              └─► ±90 V shutter bias (dual rail via charge pump)
                        └─► Micro-pump 6 V (from boost rail, PWM speed)
```

- Triple-redundant HV safety: **reed interlock** (lid must be closed) + **TLV3201 over-current comparator** (HV rail) + **IWDG watchdog** + **250 °C thermal fuse** on HV module.
- Battery life: ~14 h typical (pump + HV dominate; pump duty-cycled).

---

## Bill of materials

See [`hardware/BOM.csv`](hardware/BOM.csv). Cost target ~$65 (excluding 18650, enclosure, Ni-63 source). Summary:

- **SoC + bridge**: STM32G474RET6 ($6.40), ESP32-C3-MINI-1 ($2.70)
- **HV**: EMCO F50CT 5 kV module ($8.50), 8× 10 MΩ HV resistors ($0.80)
- **Ionizer**: Ni-63 37 kBq sealed source ($8.00 — exempt quantity, sealed) **or** corona-discharge needle + driver ($1.20)
- **Shutter**: Bradbury-Nielsen grid (PCB trace, $0.50), ±90 V charge pump ($0.60)
- **Receiver**: Faraday plate (PCB pad), ADA4530-1 TIA ($4.80), REF3030 ($1.80), ADS122U04 ($3.40) (24-bit aux + high-speed path via STM32 ADC)
- **Sample path**: PDMS 20 µm membrane ($0.30), 6 V diaphragm micro-pump ($3.80), 2-way valve ($0.90)
- **Drift tube**: PTFE tube 8.5 cm + stainless rings ($1.50)
- **Power**: TP4056, MCP1640B, AP2112K, LP5907, 18650 holder
- **UI**: SH1106 OLED, 3 buttons, EC11 encoder, buzzer, WS2812B
- **Storage**: MicroSD socket, W25Q128 (optional raw buffer)
- **Misc**: BME280 (P/T for K₀), DS18B20 (drift tube wall T), USB-C, PCB, enclosure

---

## Firmware

Firmware is bare-metal C on STM32 HAL + CMSIS-DSP, built with `arm-none-eabi-gcc` via Makefile (or CMake). See [`firmware/`](firmware/).

**Modules:**
- `main.c` — top-level state machine (IDLE / PURGE / SAMPLE / CAL / FAULT)
- `hv_supply.c/h` — EMCO HV regulation, 2125 V drift-voltage servo, safety
- `shutter.c/h` — Bradbury-Nielsen 200 µs pulse, repetition rate, drift-tube timing
- `ionizer.c/h` — Ni-63 / corona enable, safety interlock
- `electrometer.c/h` — ADA4530-1 TIA + ADS122U04 + STM32 ADC1 40 ksps DMA capture
- `ims.c/h` — drift-time DSP: baseline subtract, 256-spectrum rolling average, peak detect, K₀ computation
- `library.c/h` — 45-compound K₀ library + k-NN classifier (k=5)
- `pump.c/h` — drift-gas micro-pump PWM + 2-way valve control
- `bme280.c/h`, `ds18b20.c/h` — ambient / drift-tube temperature, pressure (K₀ normalization)
- `display.c/h` — SH1106 OLED driver (live spectrum, K₀ peaks, class, confidence)
- `sd_log.c/h` — CSV + binary session logging
- `ble_bridge.c/h` — UART protocol to ESP32-C3 (live spectrum + verdict frames)
- `safety.c/h` — interlock, watchdog, fault handler
- `buttons.c/h` — debounced mode/scan/cal buttons + encoder
- `startup_stm32g474xx.s`, `stm32g474_ret6.ld` — startup + linker

---

## Reduced-mobility library (excerpt)

| K₀ (cm²/V·s) | Compound | Class |
|---|---|---|
| 2.70 | Reactant ion peak (H⁺(H₂O)₃) | reference |
| 2.45 | Ammonia adduct | reference |
| 1.78 | DMMP (Sarin simulant) | CWA simulant |
| 1.54 | TNT | explosive |
| 1.42 | RDX | explosive |
| 1.34 | PETN | explosive |
| 1.62 | NG (nitroglycerin) | explosive |
| 1.86 | DNT | explosive |
| 1.49 | TATP | explosive |
| 1.35 | HMTD | explosive |
| 1.98 | Cocaine | drug |
| 1.92 | Heroin | drug |
| 1.74 | MDMA | drug |
| 1.56 | Methamphetamine | drug |
| 1.80 | Fentanyl | drug |
| 1.78 | Mustard (HD) | CWA |
| 1.32 | VX | CWA |
| 1.51 | GA (Tabun) | CWA |
| 1.85 | GB (Sarin) | CWA |
| 2.18 | Ammonia | TIC |
| 1.79 | Toluene | VOC |
| 1.65 | Benzene | VOC |
| 1.95 | Acetone | VOC |
| … | (45 total) | … |

Full list in [`firmware/main/library.h`](firmware/main/library.h).

---

## Build & flash

```bash
cd iono-pin/firmware
make              # builds iono_pin.elf / .hex / .bin
make flash        # via openocd + ST-Link
# ESP32-C3 bridge:
cd bridge && idf.py build flash monitor
```

See [`docs/assembly-guide.md`](docs/assembly-guide.md) for full build/assembly/calibration.

---

## Safety, regulatory, and ethical notes

- **Radioactive source:** Ni-63 at ≤ 37 kBq (1 µCi) is a *sealed, exempt-quantity* source in most jurisdictions — no external dose at contact, no contamination risk if the foil is intact. **Check your local regulations** before acquiring or using any radioactive material. The **corona-discharge alternative** avoids radioactive material entirely (at ~2× lower sensitivity) and is recommended for educational/unrestricted use.
- **High voltage:** 2125 V drift + 5 kV supply can give a painful shock. The interlock + bleeder + fuse chain is mandatory. Never operate with the lid open.
- **Toxic samples:** Do **not** introduce actual CWAs, explosives, or illicit drugs. The device is for **simulants** (DMMP for Sarin, DNT for TNT, etc.) and **education/research**. Use only safe reference simulants at trace levels.
- **Ethical use:** This is an open instrument for understanding a widely-deployed security technology. It is not a substitute for certified detectors in safety-critical settings.

---

## License

MIT — build it, study it, improve it. Radioactive material handling is your responsibility.

---

*Invented as device #54 in the SoC Device Inventions collection. New device every 24h.*