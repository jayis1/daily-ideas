# Pulse Hound

**A handheld, battery-powered RF signal hunter that sweeps 1 MHz to 8 GHz, displays a real-time spectrum waterfall on an OLED, gives geiger-counter-style audio feedback that intensifies near the source, and uses a motorized directional antenna to compute bearing — for finding hidden cameras, wiretaps, RF interference sources, and unauthorized transmitters.**

---

## What It Does

The Pulse Hound is a pocket-sized TSCM (Technical Surveillance Counter-Measures) and RF engineering tool. It continuously samples a wideband logarithmic RF detector, renders a scrolling spectrum waterfall on a 128×64 OLED, and emits audio clicks whose rate is proportional to signal strength — letting you *hear* when you're getting closer to a transmitter. A small stepper motor rotates a directional antenna through 360°, and the on-device firmware computes the bearing to the strongest signal source by finding the peak RSSI azimuth.

This replaces $5,000+ professional bug sweepers (like the REI Orion or CSCO BugHunter) with a sub-$80 build that fits in a jacket pocket. A security professional, hotel guest, or RF engineer can walk a room and visually + audibly locate any RF-emitting device: hidden cameras, GPS trackers, wireless microphones, BLE beacons, Zigbee, WiFi, cellular modems, or even malfunctioning electronics leaking EMI.

- **Wideband RF detection** — Analog Devices **AD8318** logarithmic detector, 1 MHz to 8 GHz, 70 dB dynamic range (−65 to +5 dBm), ~50 ns response time. Detects virtually any intentional or unintentional RF emitter.
- **16-point sweep mode** — firmware sweeps the AD8318 at up to 500 Hz, building a rolling spectrum histogram; the OLED shows a 64-row waterfall of the last ~8 seconds
- **Motorized direction finding** — a 28BYJ-48 stepper with ULN2003 driver rotates a 2.4 GHz patch antenna (or wideband Yagi) through 360° in 5.625° steps (64 steps); the bearing to the peak RSSI is displayed as a compass arrow
- **Geiger-counter audio** — an LM386-driven speaker clicks at a rate proportional to RSSI; as you walk toward the source the clicks accelerate, giving intuitive analog feedback without looking at the screen
- **Signal classification** — the firmware analyzes the temporal pattern of the detected signal (continuous, bursty, pulsed, periodic) and labels it: "WiFi/BLE", "Cellular", "Analog Bug", "Unknown Pulsed", "Continuous Wave"
- **BLE streaming** — live RSSI + spectrum + bearing data streamed over BLE to a companion phone app for logging and mapping
- **SD card logging** — every sweep is timestamped and logged to a micro-SD card for post-analysis (FAT32, SPI mode)
- **OLED display** — 0.96" SSD1306 (128×64, I2C): waterfall + digital RSSI (dBm) + bearing compass + classification label + battery %
- **USB-C charging** — TP4056 LiPo charger, 1000 mAh battery, ~6 h continuous hunting
- **Three modes**: SWEEP (waterfall + audio), DF (direction finding with rotating antenna), MONITOR (fixed-frequency monitoring with peak hold)

### Use Cases

| Application | How Pulse Hound Helps |
|------------|----------------------|
| Hotel / Airbnb bug sweeping | Walk the room, sweep for hidden cameras, GPS trackers, and wireless mics in 60 seconds — audio feedback means you don't need to stare at the screen |
| TSCM / counter-surveillance | Professional sweep tool at 1/50th the cost of commercial bug hunters; SD log provides audit trail |
| RF interference hunting | Track down sources of WiFi/cellular/Zigbee interference — the motorized DF bearing points you to the source |
| EMC pre-compliance | Quick "sniffer" tool to locate EMI leaks on prototypes before formal lab testing |
| Amateur radio foxhunting | Direction finding for transmitter hunts; 64-step bearing with ±5° accuracy |
| Corporate security | Sweep meeting rooms for unauthorized recording devices before sensitive discussions |
| IoT device debugging | Confirm a device is actually transmitting, see its duty cycle and signal strength in real time |
| Paranormal / RF curiosity | Detect and map RF activity in your environment — you'll be surprised how much is around you |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              PULSE HOUND                                       │
│                                                                               │
│   ┌──────────────────────────────────────────────────────────┐               │
│   │        ESP32-S3-WROOM-1                                   │               │
│   │   (Xtensa LX7 dual-core 240 MHz,                         │               │
│   │    512 KB SRAM, 8 MB flash,                              │               │
│   │    WiFi 4 + BLE 5)                                       │               │
│   │                                                          │               │
│   │   ┌──────────────────────────────────────┐               │               │
│   │   │ RF sweep task (Core 1)                │               │               │
│   │   │ (ADC sample → RSSI → waterfall buf)  │◄──────────────┼─── AD8318     │
│   │   ├──────────────────────────────────────┤               │    RF det     │
│   │   │ direction finding task               │               │  (1 MHz–8 GHz)│
│   │   │ (stepper rotate → peak RSSI → bearing)│◄──────┐      │    │          │
│   │   ├──────────────────────────────────────┤       │      │    │ ADS1115  │
│   │   │ signal classifier (temporal pattern) │       │      │    ▼          │
│   │   ├──────────────────────────────────────┤       │      │  16-bit ADC   │
│   │   │ BLE streaming + SD logger             │       │      └───────────   │
│   │   ├──────────────────────────────────────┤       │                     │
│   │   │ audio PWM (geiger clicks)             │       │      ┌───────────   │
│   │   ├──────────────────────────────────────┤       │      │ 28BYJ-48     │
│   │   │ OLED display + UI / buttons            │       ├─────►│ stepper     │
│   │   └──────────────────────────────────────┘       │      │ (ULN2003)    │
│   │                                                  │      └──────┬─────  │
│   │   ┌────────────┐  ┌────────────┐                 │             │        │
│   │   │ WiFi/BLE   │  │ SPI flash  │                 │      ┌──────┴─────   │
│   │   │ (internal)  │  │ (internal) │                 │      │ Directional  │
│   │   └─────┬──────┘  └────────────┘                 │      │ antenna      │
│   │         │                                        │      │ (patch/Yagi)│
│   └─────────┼────────────────────────────────────────┘      └──────────────┘
│   │         │ BLE                                               │
│   │         ▼                                                   │
│   │   ┌──────────────┐   ┌──────────────┐    ┌──────────────┐  │
│   │   │ Phone / PC   │   │ SD card      │ SPI│ SSD1306 OLED │  │
│   │   │ companion    │   │ (FAT32 log)  │    │ 128×64 I2C   │  │
│   │   └──────────────┘   └──────────────┘    └──────────────┘  │
│   │                                                            │
│   │   ┌──────────────┐   ┌──────────────┐    ┌──────────────┐  │
│   │   │ LM386 audio  │   │ Speaker      │    │ Buttons ×3   │  │
│   │   │ amp + PWM    │──►│ (8 Ω, 29 mm) │    │ MODE/SCAN/DF │  │
│   │   └──────────────┘   └──────────────┘    └──────────────┘  │
│   │                                                            │
│   │   ┌──────────────┐   ┌──────────────┐    ┌──────────────┐  │
│   │   │ TP4056       │   │ 1000 mAh     │    │ MAX17048     │  │
│   │   │ USB-C charger │──►│ LiPo 3.7V    │──►│ fuel gauge   │  │
│   │   └──────┬───────┘   └──────────────┘    └──────────────┘  │
│   │          │ USB-C                                            │
│   │          ▼                                                  │
│   │   ┌──────────────┐                                          │
│   │   │ Status LEDs │                                          │
│   │   │ (red/grn)   │                                          │
│   │   └──────────────┘                                          │
│   │                                                            │
│   │   ┌──────────────────────────────────────────────────┐    │
│   │   │ HANDHELD ENCLOSURE (3D-printed)                    │◄───┘
│   │   │  • 95 × 55 × 28 mm, PETG/ABS                       │
│   │   │  • OLED window cutout                             │
│   │   │  • SMA connector on top for antenna               │
│   │   │  • USB-C on bottom for charging                    │
│   │   │  • Speaker grille on front                        │
│   │   │  • 3× tactile buttons on front                     │
│   │   │  • Stepper + antenna on rotating top turret       │
│   │   └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works — RF Detection Pipeline

### AD8318 Logarithmic Detector

The **AD8318** (Analog Devices) is a complete RF detection subsystem in a 24-lead LFCSP package. It takes an RF input (from an antenna through an SMA connector) and outputs an analog voltage proportional to the log of the input power — a **RSSI** (Received Signal Strength Indicator) signal.

- **Frequency range**: 1 MHz to 8 GHz (covers everything from AM broadcast through WiFi/Bluetooth/5G sub-8)
- **Dynamic range**: 70 dB (−65 dBm to +5 dBm) — enough to detect a 1 mW transmitter at 10+ meters
- **Output**: 0.5 V (strong signal, +5 dBm) to 1.8 V (weak signal, −65 dBm); the slope is ~19 mV/dB (inverted — lower voltage = stronger signal)
- **Response time**: 50 ns — fast enough to detect pulsed/bursty signals like WiFi BLE advertisements
- **Temperature compensation**: internal thermistor for drift correction; the ESP32-S3 reads the AD8318's TEMP pin via a second ADC channel

The AD8318's RSSI output goes through an **ADS1115** 16-bit I²C ADC (for better than 0.01 dB resolution) — though in practice the ESP32-S3's internal 12-bit ADC can be used for a simpler build at ~0.05 dB resolution. The ADS1115 also reads the AD8318 TEMP pin for temperature compensation.

### Sweep → Waterfall

1. **Sampling**: Core 1 samples the ADS1115 at 500 Hz (2 ms/sample) in SWEEP mode
2. **RSSI conversion**: raw ADC voltage → dBm via the AD8318 transfer function: `P_dBm = (V_out − V_intercept) / slope`, where `slope ≈ −19 mV/dB` and `V_intercept ≈ 1.8 V` at the calibration temperature
3. **Waterfall buffer**: RSSI samples are decimated into 64 frequency bins (the "frequency" axis here is time-domain — each row represents ~16 ms of RF environment; the waterfall scrolls vertically). Each row maps to a color/intensity level on the OLED
4. **Display**: the 128×64 OLED shows the waterfall on the left 96 columns, and the right 32 columns show digital RSSI (dBm), peak hold, classification label, bearing, and battery %

### Direction Finding (DF Mode)

In DF mode, the firmware commands the 28BYJ-48 stepper to rotate the directional antenna through 360° in 64 steps (5.625° each). At each step, it pauses 200 ms, samples the AD8318 at 100 Hz for 0.5 s, and records the median RSSI. The result is a 64-point RSSI vs. azimuth pattern. The peak RSSI azimuth is the estimated bearing to the source.

The directional antenna (a 2.4 GHz patch or a 6-element Yagi for sub-GHz) has a typical front-to-back ratio of 10–15 dB and a half-power beamwidth of ~50°, giving bearing accuracy of ±5° under good conditions. The firmware performs a parabolic interpolation around the peak to refine to ±2°.

The bearing is displayed as a compass arrow on the OLED and streamed over BLE with the RSSI pattern for phone-app mapping.

### Signal Classification

The firmware analyzes the temporal envelope of the detected signal to classify its likely source:

| Pattern | Classification | Typical Sources |
|---------|---------------|-----------------|
| Continuous, stable RSSI | "CW / Continuous" | Analog wireless mic, AM/FM bug, oscillator leakage |
| Bursty, 10–100 ms on, 1–4 s off | "WiFi / BLE" | WiFi beacon, BLE advertisement, Zigbee |
| Pulsed, 0.5–5 ms on, 20–2000 ms period | "Cellular" | GSM/UMTS/LTE/5G slot burst, GPS tracker |
| Pulsed, 1–10 µs on, 1–100 ms period | "Radar / UWB" | Motion sensor, UWB ranging, radar |
| Slowly varying, 0.1–1 Hz | "Thermal drift" | Not a signal — environmental noise |
| No pattern detected | "Unknown" | Unclassified emitter |

Classification uses a simple feature extractor: the firmware computes the autocorrelation of the RSSI envelope over a 5 s window, finds the dominant period (if any), and matches it against the above taxonomy. This is not foolproof but gives useful hints to the operator.

---

## Pin Assignment (ESP32-S3-WROOM-1)

The ESP32-S3-WROOM-1 module exposes 45 GPIO pins. The following assignments use the ESP-IDF naming.

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO0 | BOOT | Boot strap (pull-up 10 kΩ; to GND = download mode) |
| GPIO1 | I2C SDA | SSD1306 OLED + ADS1115 ADC + MAX17048 fuel gauge (4.7 kΩ pull-ups) |
| GPIO2 | I2C SCL | SSD1306 + ADS1115 + MAX17048 |
| GPIO3 | GPIO input | MODE button (active low, internal pull-up) |
| GPIO4 | GPIO input | SCAN/SENS button (active low, internal pull-up) |
| GPIO5 | GPIO input | DF button (active low, internal pull-up) |
| GPIO6 | GPIO output | Status LED green (power on / sweeping) |
| GPIO7 | GPIO output | Status LED red (strong signal detected / alarm) |
| GPIO8 | GPIO output | LM386 shutdown/enable (high = audio on) |
| GPIO9 | LEDC PWM | Audio output (PWM → RC low-pass → LM386 input) |
| GPIO10 | SPI MOSI | SD card MOSI (SPI mode) |
| GPIO11 | SPI MISO | SD card MISO |
| GPIO12 | SPI SCK | SD card SCK |
| GPIO13 | GPIO output | SD card CS (active low) |
| GPIO14 | GPIO output | Stepper ULN2003 IN1 |
| GPIO15 | GPIO output | Stepper ULN2003 IN2 |
| GPIO16 | GPIO output | Stepper ULN2003 IN3 |
| GPIO17 | GPIO output | Stepper ULN2003 IN4 |
| GPIO18 | GPIO output | Stepper power enable (high-side MOSFET, power-gate stepper when idle) |
| GPIO19 | GPIO input | AD8318 /VRFLAG (clip indicator, optional) |
| GPIO20 | ADC1_CH0 | AD8318 TEMP output (temperature compensation, optional — use ADS1115 instead) |
| GPIO21 | GPIO output | AD8318 PWDN (power-down, active low; power-gate detector between sweeps) |
| GPIO38 | GPIO input | MAX17048 ALRT (low battery interrupt) |
| GPIO39 | GPIO output | TP4056 CHRG status (read charge state) |
| GPIO40 | GPIO output | LDO enable for analog front-end (power-gate ADS1115 + AD8318) |
| GPIO41 | ADC1_CH4 | Battery voltage divider (1:2, optional backup for MAX17048) |
| GPIO42 | GPIO output | Spare (expansion / future use) |
| GPIO43 | UART0 TX | USB-serial debug log (115200 baud, via USB-CDC) |
| GPIO44 | UART0 RX | USB-serial debug input |
| GPIO45 | GPIO output | Spare |
| GPIO46 | GPIO output | Spare |
| USB_DP | USB | USB-C data+ (programming + charging via TP4056 if USB-C VBUS → TP4056) |
| USB_DM | USB | USB-C data− |
| 3V3 | Power | +3.3 V from MCP1700 LDO (battery → 3.3 V) |
| GND | Power | Ground |

### Antenna Path

```
  Directional antenna (2.4 GHz patch or wideband Yagi)
          │
          │  SMA connector (top of enclosure)
          │
     50 Ω coax (10 cm)
          │
     ┌────┴────┐
     │ AD8318  │  RF input (RFIN pin, AC-coupled via 1 nF cap)
     │  log    │
     │  det    │── VOUT (RSSI) ──► ADS1115 AIN0 (16-bit I²C ADC)
     │         │── TEMP        ──► ADS1115 AIN1 (temperature comp)
     │         │── PWDN       ◄── GPIO21 (power-gate)
     │         │── CLPF       ── 10 nF to GND (loop filter cap)
     └─────────┘
```

---

## Schematic Overview

### 1. RF Detection Front-End

The **AD8318** (Analog Devices, 24-LFCSP, 4×4 mm) is the heart of the Pulse Hound. It accepts an RF signal at its RFIN pin (AC-coupled through a 1 nF, 50 Ω, 0402 capacitor) and produces an analog voltage on VOUT that is logarithmically proportional to the input RF power.

- **RFIN**: connects to the SMA antenna connector via a 50 Ω microstrip on the PCB (controlled impedance); the AD8318 input impedance is ~500 Ω at low frequencies, dropping to ~50 Ω above 100 MHz — a 50 Ω external shunt resistor (0402) matches the antenna across the band
- **VOUT**: the RSSI output; a 10 nF capacitor on the CLPF pin sets the loop filter bandwidth (settling time ~1 µs for fast sweep)
- **TEMP**: temperature output (10 mV/°C, nominally 0.8 V at 25 °C); read by the ADS1115 for temperature-compensated RSSI correction
- **PWDN**: power-down pin (active low); driven by GPIO21 to power-gate the detector between sweeps, saving ~35 mA

The **ADS1115** (TI, 16-bit delta-sigma, I²C, MSOP-10) reads the AD8318 VOUT and TEMP at up to 860 SPS (programmable gain ±6.144 V, ±0.1875 mV resolution). At 500 SPS, this gives ~0.01 dB RSSI resolution — far better than the AD8318's intrinsic ±1 dB accuracy. The ADS1115 address is 0x48 (GND on ADDR pin).

### 2. Direction Finding Subsystem

A **28BYJ-48** stepper motor (5 V, 4-phase, 1:64 gear reduction, 2048 steps/rev, 5.625° per step) drives a rotating antenna turret on top of the enclosure. The ULN2003 darlington array (on a breakout board) is driven by GPIO14–17 in 8-step half-sequence. GPIO18 enables a high-side P-MOSFET (AO3401) that powers the stepper only during DF mode — the stepper draws ~40 mA when energized, so power-gating is essential for battery life.

The directional antenna mounts on a 3D-printed turret that the stepper rotates. A small mechanical slip-clutch prevents damage if the antenna hits an obstacle. A magnet + reed switch at the 0° position provides a home reference (read via a spare GPIO); on boot the firmware rotates until the reed switch trips to establish the absolute bearing reference.

### 3. Audio Feedback

An **LM386** low-voltage audio amplifier (gain 20, SOIC-8) drives a 29 mm, 8 Ω mylar speaker. The input comes from a PWM signal on GPIO9 (LEDC peripheral, 10 kHz carrier), low-pass filtered through a 1 kΩ + 100 nF RC network (cutoff ~1.6 kHz). The firmware modulates the PWM duty cycle to produce short "click" waveforms at a rate proportional to the current RSSI:

- RSSI < −70 dBm (noise floor): 0.5 clicks/s (background tick)
- RSSI = −50 dBm: 5 clicks/s
- RSSI = −30 dBm: 20 clicks/s (rapid clicking)
- RSSI > −10 dBm: 50 clicks/s (continuous tone — you're right next to it)

GPIO8 (LM386 shutdown) mutes the amp when audio is disabled.

### 4. Display

A **SSD1306** OLED (0.96", 128×64, I²C address 0x3C) shows:
- Left 96 columns: scrolling spectrum waterfall (64 rows × 96 columns; each row = ~16 ms of RF environment, intensity-mapped to 8 grayscale levels via dithering)
- Right 32 columns: digital RSSI (dBm), peak-hold marker, signal classification label, bearing compass (in DF mode), battery %, mode indicator

The display updates at 30 FPS; the waterfall scrolls smoothly. I²C at 400 kHz handles the 1 KB/frame update in ~3 ms.

### 5. Power Architecture

- **Battery**: 1000 mAh LiPo (3.7 V nominal, 4.2 V charged) — compact 402035 size, fits inside the enclosure
- **Charger**: **TP4056** (linear Li-ion charger, 500 mA, USB-C input via VBUS) — simple, robust, with charge/standby status LEDs
- **3.3 V rail**: **MCP1700-3302** LDO (3.3 V, 250 mA, low quiescent current 1.6 µA) — powers the ESP32-S3 and all peripherals
- **Fuel gauge**: **MAX17048** (I²C, 0x36) for accurate state-of-charge; the device enters low-power mode (1 Hz sampling, OLED dimmed) when SoC < 15%
- **USB-C**: provides charging (VBUS → TP4056) and programming (USB_DP/DM → ESP32-S3 USB-serial)
- **Power budget**:
  - Active sweep (AD8318 + ADS1115 + OLED + MCU): ~80 mA → ~12.5 h on 1000 mAh
  - DF mode (+ stepper): ~120 mA → ~8 h
  - Low-power mode (1 Hz, OLED off): ~5 mA → ~200 h standby
  - AD8318 power-gated between sweeps (GPIO21): saves ~35 mA when idle

### 6. SD Card Logging

A micro-SD card slot (SPI mode, GPIO10–13) logs every sweep: timestamp, RSSI, peak frequency (if applicable), classification, bearing, battery %. Uses FAT32 with a simple append-only CSV format. At 500 Hz sampling, the log grows at ~200 KB/min; a 2 GB card holds ~7 days of continuous logging.

### 7. Enclosure

- **3D-printed** PETG or ABS, 95 × 55 × 28 mm
- **OLED window**: cutout on front, 25 × 20 mm
- **SMA connector**: top of enclosure, gold-plated, for antenna attachment
- **Stepper turret**: top of enclosure, rotating platform for antenna (the stepper is inside, the antenna mounts externally)
- **USB-C**: bottom, for charging + programming
- **Speaker grille**: front, 6 mm circular holes
- **Buttons**: 3× tactile buttons on front (MODE, SCAN/SENS, DF)
- **Status LEDs**: 2× (green = power/sweep, red = strong signal alarm) visible through the enclosure wall

---

## Firmware Architecture (ESP32-S3, ESP-IDF / CMake)

FreeRTOS-based with tasks pinned to cores:

| Task | Core | Priority | Job |
|------|------|----------|-----|
| `rf_sweep` | 1 | 5 | Sample ADS1115 at 500 Hz, convert to dBm, push to waterfall buffer |
| `display` | 0 | 3 | Render OLED waterfall + digital readout at 30 FPS |
| `audio` | 0 | 4 | PWM click generation, RSSI-to-click-rate mapping |
| `direction` | 0 | 2 | DF mode: rotate stepper, sample RSSI per azimuth, compute bearing |
| `classifier` | 1 | 2 | Temporal pattern analysis, signal classification |
| `ble_stream` | 0 | 1 | BLE GATT server, stream RSSI + spectrum + bearing to phone |
| `sd_logger` | 1 | 1 | Write sweep data to SD card (FAT32, append-only) |
| `power` | 0 | 1 | Fuel gauge polling, low-power mode, charge status |
| `button` | 0 | 3 | Debounce, mode switching, sensitivity adjust |

Key modules:

- `main.c` — peripheral init, FreeRTOS task creation, mode state machine
- `config.h` — all constants, pin map, I²C addresses, calibration values
- `rf_detector.c` — ADS1115 I²C driver, AD8318 VOUT→dBm conversion, temperature compensation, power-gate control
- `spectrum.c` — waterfall buffer (ring buffer of RSSI rows), decimation, peak-hold
- `direction.c` — 28BYJ-48 stepper driver (ULN2003 half-step sequence), home sensor, 360° RSSI pattern, parabolic peak interpolation, bearing computation
- `classifier.c` — temporal envelope autocorrelation, pattern matching, classification labels
- `audio.c` — LEDC PWM audio, click waveform synthesis, RSSI-to-rate mapping, LM386 shutdown
- `display.c` — SSD1306 I²C driver, waterfall rendering, compass, digital readout, dithering
- `ble_stream.c` — BLE GATT server, custom service (RSSI + spectrum + bearing), notification streaming
- `sd_logger.c` — SPI SD card driver, FAT32 append, CSV format, timestamping
- `power.c` — MAX17048 driver, low-power mode, TP4056 charge status, battery voltage divider

---

## AD8318 RSSI Calibration

The AD8318's output voltage is:

```
V_OUT = V_INTERCEPT + SLOPE × P_dBm

where (typical at 25 °C, 2.4 GHz):
  SLOPE      = −19 mV/dB   (negative: stronger signal → lower voltage)
  V_INTERCEPT = 1.80 V     (the voltage at 0 dBm extrapolated)
```

Solving for power:

```
P_dBm = (V_OUT − V_INTERCEPT) / SLOPE
```

### Temperature Compensation

The AD8318's intercept and slope drift with temperature. The TEMP pin outputs 10 mV/°C (nominally 0.8 V at 25 °C). The firmware applies a correction:

```
ΔV_intercept = −2.2 mV/°C × (T − 25)
V_intercept_comp = V_INTERCEPT + ΔV_intercept
P_dBm = (V_OUT − V_intercept_comp) / SLOPE
```

### Calibration Procedure

1. **No-signal baseline**: with no antenna attached (SMA terminated with 50 Ω), record V_OUT → this is the noise floor reference (typically −75 to −80 dBm equivalent)
2. **Known-signal calibration**: connect a calibrated signal generator at 2.4 GHz, −30 dBm. Record V_OUT. Compute the actual slope and intercept.
3. **Store**: calibration values (slope, intercept, temp_coeff) are stored in NVS (non-volatile storage)

See `docs/calibration_guide.md` for the full procedure.

---

## BLE GATT Interface

### Service: Pulse Hound (UUID `8e7f1a01-...`)

| Characteristic | UUID | Direction | Format |
|----------------|------|-----------|--------|
| RSSI Stream | `8e7f1a02-...` | Notify | int16 dBm × 100 (2 bytes, every 100 ms) |
| Spectrum Frame | `8e7f1a03-...` | Notify | 64 bytes (one waterfall row, 8-bit intensity) |
| Bearing | `8e7f1a04-...` | Notify | uint16 bearing_deg × 10 (2 bytes) |
| Classification | `8e7f1a05-...` | Read/Notify | uint8 enum (0=CW, 1=WiFi/BLE, 2=Cellular, 3=Radar, 4=Unknown) |
| Mode Control | `8e7f1a06-...` | Write | uint8 (0=Sweep, 1=DF, 2=Monitor, 3=PowerSave) |
| Battery | `8e7f1a07-...` | Read/Notify | uint8 % (MAX17048) |
| Log Control | `8e7f1a08-...` | Write | uint8 (0=stop logging, 1=start logging) |

---

## SD Card Log Format

```csv
timestamp_ms,rssi_dbm,peak_rssi_dbm,classification,bearing_deg,battery_pct,mode
0,-78.3,-45.1,0,0,87,0
100,-77.9,-45.1,0,0,87,0
200,-76.5,-45.1,0,0,87,0
...
```

---

## Bill of Materials

See `hardware/BOM.csv`.

---

## Building It

See `docs/assembly_guide.md` for the full assembly, 3D printing, and calibration procedure. See `docs/api_reference.md` for the BLE GATT interface and SD log format. See `docs/hunting_guide.md` for practical RF hunting tips and techniques.

---

## Companion Scripts

`scripts/` contains Python helpers:

- `decode_ble.py` — connect to Pulse Hound over BLE, decode RSSI + spectrum + bearing into human-readable JSON
- `plot_spectrum.py` — plot the live spectrum waterfall on a PC (matplotlib), connect over BLE
- `hunt.py` — interactive CLI for controlling the device over BLE: switch modes, set sensitivity, trigger DF sweep, log to file

---

## License

MIT — build it, sweep rooms with it, hunt signals with it.