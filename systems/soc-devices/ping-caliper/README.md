# Ping Caliper

**A handheld ultrasonic thickness gauge and flaw detector — high-voltage pulser, time-gain-compensated receiver, on-device A-scan envelope/RF capture, multiple-echo through-coating measurement, and BLE/Wi-Fi streaming to a phone app.**

---

## What It Does

The Ping Caliper is a pocket-sized **non-destructive testing (NDT)** instrument that uses a piezoelectric ultrasonic transducer to measure the **wall thickness** of metal pipes, tanks, hulls, and pressure vessels — and to find **internal flaws** (cracks, voids, inclusions, delamination) — all without cutting, drilling, or even removing paint.

You couple the probe to a surface with a drop of gel and press the trigger. The Ping Caliper fires a short, high-voltage electrical spike into the transducer, which emits an ultrasonic pulse (1–10 MHz) into the material. The pulse reflects off the far wall (and any flaws in between) and returns as an echo. The device amplifies the return with **time-gain compensation** (gain rises with depth to offset material attenuation), detects the echo envelope, digitizes it, and computes:

- **Wall thickness** = (sound velocity × time-of-flight) / 2
- **Flaw depth & equivalent size** — from echoes appearing *before* the back-wall
- **Through-coating thickness** — using echo-to-echo mode, which ignores the paint/plastic layer by measuring the spacing between successive back-wall echoes (so you don't have to scrape coatings off)

It then draws a live **A-scan** (amplitude vs. depth) on its OLED, logs the reading with a timestamp to a MicroSD card, and streams the A-scan over **BLE** to a companion phone app for archiving, mapping, and reporting.

- **5 MHz–5 Msps envelope digitizer** — STM32G474's 12-bit ADC captures the detected video envelope for sub-micron-equivalent timing resolution
- **Time-gain compensation (TGC)** — AD8331 ultrasound VGA with a DAC-driven gain ramp that rises with depth (programmable curve, 0–55 dB over the listening window)
- **Negative-spike HV pulser** — up to −200 V, 50–200 ns width, driven by the STM32 high-resolution timer (HRTIM, 184 ps resolution) for precise, jitter-free triggering
- **Built-in material database** — 60+ alloys and materials with their longitudinal wave velocities (steel 5920, aluminum 6320, copper 4760, titanium 6100, cast iron 4600, glass 5640, acrylic 2730 m/s…)
- **Three measurement modes** — pulse-echo thickness, echo-to-echo through-coating, and flaw-detection with a movable gate
- **Calibration suite** — zero-probe (delay-line) calibration, velocity calibration against a known reference block, and gain calibration
- **BLE + Wi-Fi** — live A-scan streaming, measurement logging, OTA firmware updates, and CSV/PDF report export via the phone app
- **12-hour battery** — single 18650 Li-ion; USB-C charging; the HV boost converter only draws current during the brief pulse, so average power is tiny
- **Rugged** — IP54, rubber-overmolded enclosure, probe-cable strain relief

### Use Cases

| Application | How Ping Caliper Helps |
|-------------|------------------------|
| Pipe & pressure-vessel inspection | Measure remaining wall thickness to detect corrosion/erosion before failure; meet API 570 / inspection codes |
| Ship & boat hulls | Find wastage and pitting on steel hulls and ballast tanks without dry-docking |
| Storage tanks | Survey floor and shell wall thickness for API 653 compliance |
| Oil & gas pipelines | Detect wall loss, laminations, and hydrogen blistering from the outside |
| Aerospace | Spot-thickness checks on aircraft skins, corrosion in lap joints, composite delamination |
| Manufacturing QA | Verify part thickness on the shop floor without contact; find inclusions in castings/forgings |
| Coated structures | Echo-to-echo mode measures metal thickness through paint/rubber without removal |
| Weld inspection | Detect porosity, lack-of-fusion, and cracks in weldments with the flaw-detection gate |
| Castings | Find shrinkage cavities and inclusions in iron/aluminum castings |
| Automotive | Brake-disc and cylinder-wall thickness; spot-check sheet metal |
| Foundries | Measure cast-wall thickness to verify mold fill |
| Museums/conservation | Non-invasive metal-thickness survey of artifacts, armor, cannons |
| Home/plumbing | Verify water-pipe wall thickness, detect hidden corrosion |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              PING CALIPER                                 │
│                                                                           │
│   ┌─────────────┐        ┌──────────────────────────┐                     │
│   │ Ultrasonic  │  coax  │   HV PULSER               │                     │
│   │ Transducer  │◄──────►│  LMG1210 driver          │   STM32 HRTIM        │
│   │ 1–10 MHz    │  LEMO  │  → HV GaN FET            │◄──(184 ps timer)──  │
│   │ dual/delay  │  BNC   │  boost → −30…−200 V       │   pulse width/prf    │
│   └─────┬───────┘        └──────────┬───────────────┘                     │
│         │                          │                                     │
│         │   ┌──────────────────────┴──────────────┐                      │
│         │   │ MD0100 T/R switch + BAT54S limiter  │                      │
│         │   └──────────┬──────────────────────────┘                      │
│         │              │ return echo (~µV–mV)                            │
│         │   ┌──────────▼──────────────┐      STM32 DAC1 ── gain ramp     │
│         │   │ AD8331 TGC VGA           │◄──────────────────────────────   │
│         │   │ LNA + VGA 7–55 dB,100MHz │                                  │
│         │   └──────┬─────────┬─────────┘                                 │
│         │          │ RF out  │ RF out                                    │
│         │          │         │                                            │
│   ┌─────▼────┐  ┌──▼──────┐ ┌▼───────────────┐                           │
│   │ Schottky │  │ STM32   │ │ STM32 G474     │                            │
│   │ envelope │  │ ADC2   │ │  RET6          │                            │
│   │ detector │  │ (RF,   │ │                │                            │
│   │ (video)  │  │ ≤2MHz  │ │ ┌────────────┐ │                            │
│   └────┬─────┘  │ probes)│ │ │ thickness  │ │                            │
│        │        └────────┘ │ │  calc      │ │                            │
│   ┌────▼────┐         ┌────┘ │ flaw detect│ │                            │
│   │ STM32   │         │      │ A-scan buf  │ │                            │
│   │ ADC1    │─────────┘      │ materials   │ │                            │
│   │ 5 Msps  │                │ calibration │ │                            │
│   │ envelope│                └──────┬─────┘ │                            │
│   └─────────┘                       │       │                            │
│                              ┌──────▼─────┐ │                            │
│   ┌──────────┐  SPI  ┌───────┴────────────┴─┘   ┌────────────┐          │
│   │ SSD1306  │◄──────┤   STM32G474RET6          │  MicroSD    │  SPI     │
│   │ 128×64   │       │   170 MHz M4F, FMAC,     │  logging   │◄─────────┤
│   │ OLED     │       │   CORDIC, HRTIM, 2× DAC  │            │          │
│   │ A-scan   │       │   5 Msps ADC ×2          └────────────┘          │
│   └──────────┘       └──────┬───────────────────────┬───────┘          │
│                              │ UART (921600)         │ I²C                │
│                       ┌──────▼──────────┐    ┌──────▼──────┐            │
│                       │ ESP32-C3         │    │ MAX17048    │            │
│                       │ BLE 5 + Wi-Fi    │    │ fuel gauge  │            │
│                       │ phone app comms   │    │ (battery %) │            │
│                       │ OTA update        │    └─────────────┘            │
│                       └────────┬─────────┘                              │
│                                │ BLE/Wi-Fi                               │
│                                ▼                                         │
│                          ┌──────────────┐                                │
│                          │ Phone App    │                                │
│                          │ A-scan, log, │                                │
│                          │ report PDF   │                                │
│                          └──────────────┘                                │
│                                                                           │
│   ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│   │ Rotary enc  │  │ Trigger  │  │ USB-C    │  │ Power               │    │
│   │ + 3 buttons │  │ button   │  │ charge  │  │ 18650 Li-ion        │    │
│   │ (menu nav)  │  │ (measure)│  │ MCP73831│  │ → TPS63020 → 3.3 V  │    │
│   └─────────────┘  └──────────┘  └──────────┘  │ LM5022 boost → HV   │    │
│                                                │ TP4056 charge       │    │
│                                                └────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (STM32G474RET6, LQFP64)

| Pin | Function | Connected To |
|-----|----------|-------------|
| PA0 | DAC1_OUT1 | AD8331 VGA gain-control input (TGC ramp, DMA-driven) |
| PA1 | DAC1_OUT2 | HV boost voltage setpoint (controls LM5022 FB via divider) |
| PA2 | ADC1_IN3 | Envelope/video signal from Schottky detector (5 Msps, DMA) |
| PA3 | ADC2_IN4 | RF signal from AD8331 output (≤2 MHz probes, A-scan RF) |
| PA4 | ADC1_IN17 | Battery voltage divider (1:3, fuel-gauge cross-check) |
| PA5 | GPIO output | HV boost enable (LM5022 EN) |
| PA6 | GPIO output | MD0100 T/R switch control (transmit/receive select) |
| PA7 | GPIO output | LMG1210 driver enable / pulser inhibit |
| PA8 | HRTIM_CHA1 | LMG1210 IN+ — negative-spike pulse trigger (sub-ns) |
| PA9 | HRTIM_CHA2 | PRF trigger / sync (configurable rep rate) |
| PA10 | GPIO input | Trigger button (active low, pull-up, interrupt) |
| PA11 | GPIO input | Rotary encoder A (interrupt) |
| PA12 | GPIO input | Rotary encoder B |
| PA13 | GPIO input | SWDIO (debug) |
| PA14 | GPIO input | SWCLK (debug) |
| PA15 | GPIO output | OLED DC (data/command) |
| PB0 | GPIO output | OLED RESET |
| PB1 | GPIO output | OLED CS (SPI) |
| PB2 | SPI1 SCK | OLED (SSD1306) + MicroSD (shared, with CS) |
| PB3 | SPI1 MISO | MicroSD MISO |
| PB4 | SPI1 MOSI | OLED + MicroSD MOSI |
| PB5 | GPIO output | MicroSD CS |
| PB6 | GPIO output | Status LED (white — ready/measuring) |
| PB7 | GPIO output | Status LED (red — flaw/battery-low) |
| PB8 | GPIO output | Status LED (green — BLE link) |
| PB9 | GPIO output | Analog-front-end power gate (VDDA rail enable) |
| PB10 | I²C1 SCL | MAX17048 fuel gauge (4.7k pull-up) |
| PB11 | I²C1 SDA | MAX17048 fuel gauge (4.7k pull-up) |
| PB12 | USART3_TX | ESP32-C3 UART RX (921600 baud, DMA) |
| PB13 | USART3_RX | ESP32-C3 UART TX |
| PB14 | GPIO input | Menu button (active low) |
| PB15 | GPIO input | Mode button (active low) |
| PC0 | ADC1_IN6 | HV monitor (boost output voltage sense, 1:100 divider) |
| PC1 | GPIO output | Beeper (PWM) — key-click & alarm |
| PC2 | GPIO output | Probe-present detect (coupling test — sense probe capacitance) |
| PC3 | GPIO input | Tamper / case-open detect (reed switch) |
| PC4 | GPIO output | ESP32-C3 boot-enable (reset + boot control) |
| PC5 | GPIO output | ESP32-C3 RESET |
| PC6 | GPIO output | ESP32-C3 GPIO0 (boot mode select) |
| PC8 | GPIO output | MicroSD power gate |
| PC9 | GPIO input | USB-C VBUS detect |
| PC10 | GPIO output | Charge status LED (TP4056 → charging) |
| PC11 | GPIO input | TP4056 CHRG status (open drain) |
| PC12 | GPIO input | TP4056 STDBY status (open drain) |
| PC13 | GPIO output | TC4420 pulser driver inhibit (safety) |
| PC14 | GPIO input | Probe ID pin (pull on probe connector selects default velocity) |
| PC15 | GPIO output | Calibration-output / trigger sync (BNC on case for scope) |
| VDD | Power | +3.3 V from TPS63020 |
| VDDA | Power | +3.3 V filtered (VDDA rail, gated by PB9) |
| VSS | Power | GND |

### ESP32-C3 (module) Pin Assignment

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO2 | UART0 RX | STM32 USART3 TX |
| GPIO3 | UART0 TX | STM32 USART3 RX |
| GPIO8 | I²C SDA | (reserved — shared with MAX17048 optional) |
| GPIO9 | I²C SCL | (reserved) |
| GPIO4 | GPIO output | BLE link LED (to STM32 PB8 sense) |
| EN | GPIO input | STM32 PC4 (boot-enable) |
| RST | GPIO input | STM32 PC5 |
| GPIO5 | GPIO input | STM32 PC6 (boot mode) |

---

## Schematic Overview

### 1. HV Pulser (negative-spike transmitter)

The transmit path produces a fast, high-voltage negative spike to shock-excite the piezo:

- **STM32 HRTIM_CHA1** (PA8) → **LMG1210** half-bridge GaN driver (2 A peak, 200 ps propagation) → drives the gate of an **SCT2H12NZ** (650 V, 12 A GaN HEMT) — or a cheaper **IRF830** (500 V N-MOSFET) for ≤150 V operation.
- The GaN FET pulls the transducer node from a charged HV rail down to near ground, creating a **−V_HV spike** (the transducer is AC-coupled / pulse-transformer coupled, so it sees a sharp unipolar or bipolar pulse).
- **HV rail**: **LM5022** boost converter generates −30 V to −200 V (set by STM32 DAC2 controlling the FB divider). A small reservoir cap (47 nF, 250 V) holds the rail during the brief pulse. Average current is tiny (PRF × cap energy), so a single 18650 lasts a full day.
- **Pulse width**: 50–200 ns, set by the HRTIM (184 ps granularity). Pulse repetition frequency (PRF): 10 Hz (battery-saver) to 1 kHz (live A-scan).
- **Pulser inhibit** (PC13 + PA7): hardware safety gate so the HV can only fire when armed and the probe is coupled.

### 2. T/R Switch & Receiver Protection

- **MD0100**: monolithic high-voltage transmit/receive switch (±100 V, 0.5 Ω on-resistance, 50 MHz). During transmit it isolates the receiver; during receive it passes the echo to the preamp. Controlled by PA6.
- **Diode limiter**: a pair of anti-parallel **BAT54S** Schottky clamps across the receiver input, plus a series 50 Ω, protects the AD8331 LNA from residual HV leakage.
- **ESD**: TVS diode (SMAJ15A) at the probe connector.

### 3. TGC Receiver (AD8331)

- **AD8331**: ultrasonic VGA integrating a low-noise preamp (LNA, 1 V/nV input-referred noise, programmable gain 7.6/17.6/22.6 dB via LNA gain pins) and a VGA (gain 0–55 dB linear-in-dB, controlled by a 0–1 V control voltage, 100 MHz bandwidth).
- **Gain control**: STM32 **DAC1_OUT1** (PA0) outputs a **TGC ramp** generated by DMA from a lookup table — gain starts low (near-surface echoes are strong) and rises with time (deep echoes are attenuated). The ramp shape is programmable (linear, exponential, or a custom curve). Ramps restart on each transmit pulse, synchronized by a timer.
- **LNA gain pins** set by GPIOs (low/mid/high gain range selection per probe).
- Output (typically 0.5–2 Vpp on a 1.65 V bias, AC-coupled) feeds two paths:
  - **Envelope detector**: BAT54/HSMS-2852 Schottky diode + RC low-pass (time constant ~1/τ matched to the probe bandwidth) → video envelope. Biased to ~0.6 V reference. → STM32 ADC1 (PA2, 5 Msps).
  - **RF direct**: AC-coupled through a 50 Ω driver → STM32 ADC2 (PA3) for ≤2 MHz probes; or to an optional external high-speed ADC header (J3) for >2 MHz RF digitization.

### 4. Digitization (STM32G474 ADC)

- **ADC1 (PA2)** — envelope/video at up to 5 Msps, DMA into a ring buffer triggered synchronously with the transmit pulse (timer-triggered DMA, so every shot is captured at the same phase). 12-bit → up to 72 dB dynamic range in the envelope domain.
- **ADC2 (PA3)** — RF for ≤2 MHz probes (or the optional external ADC for >2 MHz). Sampled simultaneously.
- Both ADCs triggered by the same HRTIM master timer that fires the pulse — deterministic, jitter-free timing for accurate time-of-flight.
- Capture window: configurable 2 µs–500 µs (corresponds to ~0.5 mm–150 mm in steel).

### 5. OLED Display (SSD1306 128×64, SPI)

- Live **A-scan**: amplitude (envelope or RF) vs. depth, with a depth-axis in mm (scaled by material velocity), a movable **gate** (for flaw detection), and the back-wall echo marker.
- Big numeric **thickness readout** (mm/inch), material name, battery %, mode.
- Menus for material selection, gain, PRF, gate position/width, calibration.

### 6. Power

- **Battery**: 1× 18650 Li-ion, 2600–3500 mAh (protected cell).
- **Charger**: **MCP73831** (USB-C, 500 mA) or **TP4056** with USB-C. Charging status to STM32 (PC11/PC12).
- **3.3 V rail**: **TPS63020** buck-boost (1.8–5.5 V → 3.3 V, up to 2 A) — keeps the system alive across the full 3.0–4.2 V battery range.
- **HV rail**: **LM5022** boost → −30 V to −200 V, programmable via STM32 DAC2; enabled only when armed (PA5).
- **VDDA**: separate filtered analog rail, gated by PB9 (MOSFET) to keep the front end cold between shots and reduce power in idle.
- **Fuel gauge**: **MAX17048** (I²C) for accurate state-of-charge.
- **Typical battery life**: ~12 h continuous measuring, ~30+ h standby (the HV and analog rail are gated off between shots).

---

## Firmware Architecture (STM32G474)

FreeRTOS-based, four tasks:

| Task | Priority | Job |
|------|----------|-----|
| `acquire` | 5 (highest) | HRTIM pulse → ADC DMA capture → hand off to `process` |
| `process` | 4 | Envelope peak-pick, time-of-flight, thickness, flaw gate, A-scan render buffer |
| `ui` | 3 | OLED redraw, rotary-encoder/button handling, menus, calibration flow |
| `comm` | 2 | UART protocol with ESP32-C3 (commands, A-scan streaming, settings) |

Key modules:

- `pulser.c` — HRTIM configuration for the HV trigger (width, PRF, master/slave sync with ADC).
- `tgc.c` — DMA-driven DAC ramp generation; programmable TGC curve.
- `receiver.c` — ADC1 (envelope) + ADC2 (RF) DMA capture, double-buffer.
- `thickness.c` — time-of-flight from first back-wall echo; echo-to-echo for through-coating; velocity compensation.
- `flaw.c` — gate placement, peak detection above threshold, equivalent flaw sizing (DGS-style).
- `materials.c` — 60+ material velocity database (flash-stored, editable).
- `calibration.c` — zero-probe (delay-line) and velocity calibration against a reference block.
- `display.c` — SSD1306 driver + A-scan renderer + menu system + font.
- `sd_log.c` — FatFs-based measurement & A-scan logging.
- `uart_proto.c` — framed binary protocol to ESP32-C3.
- `power.c` — rail gating, fuel gauge, charge status, low-battery handling.
- `main.c` — FreeRTOS task init, system clock (170 MHz), peripheral bring-up.

### ESP32-C3 Firmware

- `uart_comm.c` — framed protocol with STM32 (same as Spectra Charm pattern).
- `ble_ndt.c` — BLE GATT: measurement notify, A-scan characteristic (chunked), command write, settings.
- `wifi_api.c` — OTA firmware update, CSV export, optional cloud logging.
- `oled_ui.c` — (optional) if a second small OLED is on the comms module.
- `main.c` — ESP-IDF app_main, BLE stack, Wi-Fi STA/AP.

---

## Measurement Theory

### Pulse-echo thickness

```
         ┌─── pulse in ───→
   ─────── surface   │                back wall
   │     │   ◄──── echo ──│
   probe │               │
   ══════════════════════════  material, thickness d, velocity v

   d = (v × Δt) / 2
```

`Δt` = round-trip time from the transmit pulse to the first back-wall echo.

- Steel (5920 m/s): 1 mm wall → Δt = 338 ns; 10 mm → 3.38 µs.
- Aluminum (6320 m/s): 1 mm → 316 ns.
- The 5 Msps envelope ADC gives ~200 ns sample period → ~0.3 mm resolution in steel, refined by parabolic interpolation around the echo peak to ~0.01 mm.

### Echo-to-echo (through-coating) mode

When the surface has paint/rubber/plastic of unknown thickness, the first two back-wall echoes (B1, B2) of the **metal** are spaced by exactly one round-trip in the metal — independent of the coating. Measuring Δt = B2 − B1 yields the true metal thickness regardless of coating.

### Flaw detection

A movable **gate** is placed between the surface and back-wall echoes. Any echo peak inside the gate exceeding a threshold is flagged as a flaw. The equivalent reflector size is estimated using a simplified DGS (distance–gain–size) curve stored in flash.

---

## Bill of Materials

See `hardware/BOM.csv`.

---

## Building It

See `docs/assembly_guide.md` for the full assembly, alignment, and safety procedure. See `docs/probe_guide.md` for transducer selection and coupling, and `docs/api_reference.md` for the BLE/UART protocol used by the phone app and scripts.

---

## Companion Scripts

`scripts/` contains Python helpers:

- `read_ascan.py` — connect over BLE, capture and plot a live A-scan (matplotlib).
- `calibrate.py` — guided zero-probe and velocity calibration via BLE.
- `material_db.py` — view/edit the on-device material velocity database.
- `log_download.py` — pull measurement & A-scan logs from the SD card over BLE.
- `report.py` — render an inspection PDF (readings table + A-scan thumbnails).

---

## License

MIT — build it, sell it, inspect with it.