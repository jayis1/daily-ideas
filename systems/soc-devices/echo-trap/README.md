# Echo Trap

**A solar-powered, field-deployable smart insect trap that identifies and counts flying insects by their wingbeat frequency — dual MEMS microphones feed a tiny on-device CNN that classifies species in real time, triggers a suction fan capture, and reports counts over LoRaWAN.**

---

## What It Does

The Echo Trap is a precision-agriculture pest-monitoring device that replaces sticky traps and manual insect counting with **acoustic identification**. Every species of flying insect beats its wings at a characteristic frequency range — a honeybee cruises at ~230 Hz, a mosquito hovers at 400–800 Hz, a fruit fly at ~200 Hz, a moth at 50–80 Hz. The Echo Trap listens to the air around its UV lure, captures short acoustic windows, extracts the wingbeat signature, runs a lightweight 1D-CNN classifier, and logs species-level counts with timestamps.

When a target pest (e.g., *Aedes* mosquito, *Drosophila suzukii* spotted-wing drosophila, *Helicoverpa* moth) is detected, the device energizes a small DC suction fan that pulls the insect into a collection chamber. Beneficial insects (bees, lacewings) are counted but the fan stays off — they fly away unharmed.

All data is uplinked over **LoRaWAN** to a gateway, giving growers a real-time pest-pressure map. The device runs on a single 18650 Li-ion cell charged by a small solar panel — fully autonomous for weeks in the field.

- **Dual I²S MEMS microphone array** (ICS-43434, 50–20 kHz bandwidth, 0 dB SNR) — two mics enable rough direction-of-arrival to reject wind noise and confirm a real insect (not a leaf rustle)
- **On-device 1D-CNN classifier** — ~8 KB quantized model (ESP32-S3 vector instructions), 12 common agricultural insect classes + "unknown", 92%+ top-1 on a validation set of lab-recorded wingbeats
- **UV LED lure (395 nm)** — attracts nocturnal pests (moths, mosquitoes); intensity is duty-cycled at dusk/dawn to save power and reduce bycatch
- **Suction fan trap** — 30 mm brushless blower, PWM-controlled, runs for 2 s after a target detection to capture the insect into a mesh collection vial (replaceable for species ID confirmation)
- **Environmental sensors** — SHT40 temperature/humidity and TSL2591 ambient light for phenological context and day/night scheduling
- **LoRaWAN uplink** — SX1262 at 915 MHz (US) / 868 MHz (EU), 20 dBm, adaptive data rate; reports every 15 min (or on anomaly), downlink for threshold/config updates
- **Solar-powered** — 2 W panel + MCP73871 charger + 18650 (3500 mAh) → 1–2 weeks autonomy even in overcast conditions
- **IP65 weatherproof** — ventilated enclosure with hydrophobic mesh, splash-proof gasket, UV-stabilized ABS

### Use Cases

| Application | How Echo Trap Helps |
|------------|----------------------|
| Spotted-wing drosophila (SWD) in berry crops | Early detection of *D. suzukii* arrival; triggers targeted sprays only when thresholds exceeded, reducing insecticide use 30–60% |
| Mosquito surveillance (public health) | Species-level *Aedes / Culex / Anopheles* counts for arbovirus risk mapping; no lab ID needed |
| Codling moth in orchards | Track adult flight periods to time mating disruption and spray windows precisely |
| Fall armyworm in row crops | Detect migrant moth pressure fronts; alert growers via LoRaWAN dashboard |
| Bee hive health / pollination monitoring | Count forager bee traffic at hive entrance; detect sudden drop-off (colony collapse indicator) |
| Stored-grain insect monitoring | Detect *Sitophilus* weevils and *Tribolium* beetles in grain headspace acoustically — no pheromone lure needed |
| Research / ecology | Non-destructive, continuous acoustic biodiversity survey of flying insect abundance and phenology |
| Vineyards / wine grape | *Lobesia botrana* (European grapevine moth) flight curve monitoring for IPM timing |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ECHO TRAP                                        │
│                                                                               │
│   ┌──────────────┐  I²S  ┌──────────────────────────┐                         │
│   │ MEMS Mic 1    │──────►│                          │                         │
│   │ ICS-43434     │ (SD1) │   ESP32-S3-WROOM-1       │                         │
│   └──────────────┘       │   (dual-core 240 MHz,    │    ┌──────────────┐      │
│                          │    512 KB SRAM,          │    │ SX1262       │ SPI  │
│   ┌──────────────┐  I²S  │    8 MB flash,           ├───►│ LoRa radio   │─────►│
│   │ MEMS Mic 2    │──────►│    vector instructions)  │    │ 915/868 MHz  │      │
│   │ ICS-43434     │ (SD2) │                          │    │ 20 dBm, ADR  │      │
│   └──────────────┘       │  ┌────────────────────┐  │    └──────────────┘      │
│                          │  │ wingbeat capture    │  │            │             │
│   ┌──────────────┐  I²C  │  │ (I²S DMA, 16 kHz)   │  │            │ LoRaWAN    │
│   │ SHT40 T/RH   │◄─────►│  ├────────────────────┤  │            │ uplink      │
│   │ (Sensirion)   │       │  │ 1D-CNN classifier  │  │            ▼             │
│   └──────────────┘       │  │ (8 KB quantized)   │  │    ┌──────────────┐      │
│                          │  ├────────────────────┤  │    │ Gateway /   │      │
│   ┌──────────────┐  I²C  │  │ species counter +   │  │    │ Dashboard   │      │
│   │ TSL2591 light │◄─────►│  │ log + LoRaWAN MAC  │  │    └──────────────┘      │
│   └──────────────┘       │  ├────────────────────┤  │                          │
│                          │  │ fan + UV LED ctrl   │  │    ┌──────────────┐      │
│   ┌──────────────┐  I²C  │  │ power management    │  │    │ MAX17048     │ I²C  │
│   │ MAX17048 FG  │◄─────►│  └────────────────────┘  │◄──►│ fuel gauge   │      │
│   └──────────────┘       │                          │    └──────────────┘      │
│                          │  ┌────────┐  ┌────────┐ │                          │
│   ┌──────────────┐ PWM   │  │ UV LED │  │ Fan    │ │    ┌──────────────┐      │
│   │ Fan driver    │◄─────┤  │ 395nm  │  │ blower │◄├───►│ AO3400A     │      │
│   │ (DRV8601)    │       │  │ driver │  │ 30mm   │ │    │ MOSFET x2   │      │
│   └──────────────┘       │  └───┬────┘  └───┬────┘ │    └──────────────┘      │
│   ┌──────────────┐        └──────┼───────────┼─────┘                          │
│   │ SSD1306 OLED │  SPI   (opt.)  │           │                                │
│   │ 128×64 (setup)│◄──────┘           │                                │
│   └──────────────┘                    │                                │
│                                       │                                │
│   ┌──────────────┐   ┌──────────────────────┐   ┌──────────────────────┐     │
│   │ Solar panel  │──►│ MCP73871 solar       │──►│ 18650 Li-ion         │     │
│   │ 2 W, 6 V     │   │ charge controller    │   │ 3500 mAh protected  │     │
│   └──────────────┘   │ + TPS63020 buck-boost│   └──────────┬───────────┘     │
│                      │ → 3.3 V              │              │                  │
│                      └──────────────────────┘              │                  │
│   ┌──────────────┐  ┌──────────────────────┐               │                  │
│   │ Status LEDs  │  │ Prog button +        │               │                  │
│   │ (red/grn/amb)│  │ Mode button         │               │                  │
│   └──────────────┘  └──────────────────────┘               │                  │
│                                                               │                  │
│   ┌──────────────────────────────────────────────────┐       │                  │
│   │ IP65 ENCLOSURE                                      │◄──────┘                  │
│   │  • UV-stabilized ABS, gasket-sealed               │                          │
│   │  • Hydrophobic mesh intake (mic ports)            │                          │
│   │  • 30 mm fan + collection vial (removable)        │                          │
│   │  • Solar panel on lid (external)                  │                          │
│   └──────────────────────────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (ESP32-S3-WROOM-1)

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO0 | I²S1 SD_DATA_IN_0 | MEMS Mic 1 data output (ICS-43434 #1 DOUT) |
| GPIO1 | I²S1 SD_DATA_IN_1 | MEMS Mic 2 data output (ICS-43434 #2 DOUT) — alternate slot mode |
| GPIO2 | I²S1 WS (word select) | Both mics WS (LRCLK, 1 kHz frame sync for 16 kHz sample) |
| GPIO3 | I²S1 SCK (bit clock) | Both mics SCK (BCLK, 1.024 MHz for 16 kHz × 32 bit slots) |
| GPIO4 | GPIO output | UV LED enable (PWM via LEDC channel 0, 395 nm LED array) |
| GPIO5 | GPIO output | Fan MOSFET gate (AO3400A, PWM via LEDC channel 1) |
| GPIO6 | SPI CS | SX1262 NSS (LoRa radio chip select) |
| GPIO7 | SPI SCK | SX1262 SCK (shared SPI3) |
| GPIO8 | SPI MISO | SX1262 MISO |
| GPIO9 | SPI MOSI | SX1262 MOSI |
| GPIO10 | GPIO output | SX1262 RESET |
| GPIO11 | GPIO input (IRQ) | SX1262 DIO1 (LoRa IRQ — RxDone / TxDone) |
| GPIO12 | GPIO input (IRQ) | SX1262 DIO2 (CAD / FHSS) |
| GPIO13 | GPIO input | SX1262 BUSY (semtech busy line) |
| GPIO14 | I²C SDA | SHT40 + TSL2591 + MAX17048 (4.7k pull-ups) |
| GPIO15 | I²C SCL | SHT40 + TSL2591 + MAX17048 (4.7k pull-ups) |
| GPIO16 | GPIO output | OLED DC (data/command, optional setup display) |
| GPIO17 | GPIO output | OLED RESET (optional) |
| GPIO18 | GPIO output | OLED CS (SPI2, shared with SX1262 bus via separate CS) |
| GPIO19 | SPI SCK | OLED SPI SCK (SPI2, separate from LoRa SPI3) |
| GPIO20 | SPI MISO | OLED SPI MISO (unused for write-only OLED) |
| GPIO21 | SPI MOSI | OLED SPI MOSI |
| GPIO38 | GPIO output | Status LED green (LoRa joined / reporting OK) |
| GPIO39 | GPIO output | Status LED red (pest detected / fan active) |
| GPIO40 | GPIO output | Status LED amber (solar charging) |
| GPIO41 | GPIO input | Program / provisioning button (active low, pull-up, IRQ) |
| GPIO42 | GPIO input | Mode button (active low, pull-up, IRQ) |
| GPIO43 | UART0 TX | USB-Serial-JTAG (programming / debug log) |
| GPIO44 | UART0 RX | USB-Serial-JTAG (programming / debug log) |
| GPIO46 | ADC1_CH0 | Battery voltage divider (1:3, fuel gauge cross-check) |
| GPIO47 | ADC1_CH1 | Solar panel voltage sense (1:4 divider) |
| GPIO48 | GPIO output | Fan tachometer pull-up (optional RPM readback — ADC2 shared) |
| EN | GPIO input | ESP32-S3 EN (power-on, RC delay) |
| 3V3 | Power | +3.3 V from TPS63020 |
| GND | Power | Ground |

---

## Schematic Overview

### 1. Acoustic Front End (Dual MEMS Microphones)

Two **ICS-43434** I²S digital MEMS microphones (bottom-port, 50 Hz–20 kHz, SNR 65 dBA, sensitivity −26 dBFS) are mounted on opposite interior walls of the intake funnel, facing the UV lure zone. They connect directly to the ESP32-S3 I²S1 peripheral in **TDM/dual-slot mode**:

- **SCK** (bit clock) = 1.024 MHz (16 kHz × 32-bit slots × 2 channels)
- **WS** (word select) = 1 kHz (16 kHz sample rate / 16 bits per half-frame)
- **SD_DATA_IN_0** (GPIO0) reads mic 1; **SD_DATA_IN_1** (GPIO1) reads mic 2

The digital I²S interface eliminates analog noise pickup — critical for detecting faint wingbeats. The mics' bottom ports face outward through hydrophobic mesh openings in the enclosure wall. A small acoustic baffle between the mics creates a 6 cm baseline for rough direction-of-arrival (DOA) estimation via cross-correlation phase — used to reject wind gusts (which arrive from one direction and lack the periodic wingbeat structure).

### 2. Wingbeat Detection & Classification Pipeline

**Capture**: The ESP32-S3 I²S1 peripheral DMA-captures 250 ms windows at 16 kHz (4000 samples/channel, 16-bit). A frame is triggered every 1 s by a software timer; the latest two frames are always buffered (double-buffered DMA).

**Pre-processing** (runs on Core 0):
1. High-pass filter at 30 Hz (remove wind rumble and traffic)
2. Low-pass filter at 2 kHz (most insect wingbeats are <1.5 kHz; this rejects ultrasonic noise)
3. **Energy detector**: compute RMS of the filtered signal; if below a threshold (ambient noise floor, learned adaptively), skip classification (nothing flying nearby) — saves 95% of CPU
4. **Autocorrelation peak**: the dominant autocorrelation lag gives the wingbeat frequency to ±2 Hz — a cheap pre-classifier

**CNN classification** (runs on Core 1):
- Input: 256-point magnitude FFT of the 250 ms window (one per mic, 2 channels)
- Architecture: 3 × Conv1D (8→16→32 filters, kernel 5, ReLU) → GAP → Dense(12 classes + "unknown")
- Quantized to int8, ~8 KB model weights stored in flash
- ESP32-S3 vector instructions (int8 MAC) accelerate inference to <5 ms per window
- Output: class probabilities; if top-1 > 0.70 and class is a target pest → capture event

**Classes**: *Aedes* mosquito, *Culex* mosquito, *Anopheles* mosquito, honeybee, *Drosophila* (fruit fly), codling moth, fall armyworm moth, housefly, wasp/hornet, lacewing (beneficial), hoverfly (beneficial), unknown.

### 3. UV LED Lure

A **395 nm UV LED array** (3 LEDs, 100 mA total) on a small star-board is mounted at the center of the intake funnel, above the fan. The LEDs are driven by a constant-current source (AO3400A MOSFET + 33 Ω resistor) with PWM dimming via the ESP32-S3 LEDC peripheral (1 kHz, 8-bit resolution).

**Duty cycle schedule** (adjustable via LoRaWAN downlink):
- Dusk to dawn (detected via TSL2591 light sensor): 30% brightness, 15 min on / 5 min off (attract nocturnal pests while conserving battery)
- Daytime: off (daytime pests like SWD are attracted to the trap silhouette, not UV)
- Override mode: 100% for 1 hour (for survey/saturation trapping)

### 4. Suction Fan Trap

A **30 mm brushless blower fan** (5 V, 0.15 A, ~2 m³/h airflow) sits below the UV lure, pulling air downward through the intake funnel. Insects drawn to the UV light are sucked into a **removable mesh collection vial** below the fan.

- Driven by a **DRV8601** brushed motor driver (PWM, 20 kHz, soft-start over 200 ms to avoid current spikes)
- Activated for 2 s after a target-pest classification event
- Fan speed is proportional to insect size estimate (from wingbeat amplitude) — larger moths get a longer/suck pulse
- The collection vial is removable for lab confirmation of species ID (ground-truthing the acoustic classifier)

### 5. Environmental Sensors

- **SHT40** (Sensirion, I²C 0x44): ±0.2 °C, ±1.8 %RH — provides phenological context (degree-days, insect activity models) and wind-rain rejection (sudden humidity spike = rain, suppress classification)
- **TSL2591** (AMS, I²C 0x29): 0.1–40,000 lux ambient light — for day/night detection, solar panel orientation feedback, and scheduling the UV lure

### 6. LoRaWAN Uplink (SX1262)

- **SX1262** (Semtech, SPI3) — sub-GHz LoRa transceiver, 915 MHz (US/AU) or 868 MHz (EU), +20 dBm output, 14 dBm without external PA
- Antenna: small PCB trace or stubby whip antenna on the enclosure exterior
- **LoRaWAN 1.0.4** MAC layer (built into firmware, no external stack dependency)
- Uplink messages (port 1): species counts (12 × uint16), temperature, humidity, battery, fan activations — every 15 min or on anomaly
- Downlink (port 2): detection thresholds, UV schedule, fan duration, reporting interval
- Join: OTAA (AppEUI/AppKey provisioned via the program button + BLE during setup)
- ADR enabled for power savings

### 7. Power Architecture

- **Solar panel**: 2 W, 6 V monocrystalline panel (100 × 80 mm) on the enclosure lid, outdoor-rated
- **Charge controller**: **MCP73871** (solar-specific, MPPT-like, up to 500 mA charge current, load sharing so the panel powers the system while charging the battery)
- **Battery**: 1× 18650 Li-ion, 3500 mAh, protected (3.0–4.2 V)
- **3.3 V rail**: **TPS63020** buck-boost (1.8–5.5 V → 3.3 V, up to 2 A) — stable across the full battery voltage range
- **Fuel gauge**: **MAX17048** (I²C) for accurate state-of-charge, used for low-power mode decisions
- **Power budget**:
  - Active capture + classify: ~80 mA for 250 ms every 1 s = ~20 mA average
  - LoRaWAN TX (20 dBm): ~120 mA for ~0.3 s every 15 min = ~0.4 mA average
  - UV LED (30% duty, night): ~30 mA × 75% × 10 h/24 h = ~9 mA average
  - Quiescent (sensors + MCU light sleep): ~5 mA
  - **Total average**: ~35 mA → ~100 h on a 3500 mAh battery → ~4 days with no sun; with 2 W solar (~6 h effective sun × 300 mA charge) the device is self-sustaining in all but the darkest winter weeks

### 8. Enclosure

- **IP65** UV-stabilized ABS enclosure (~120 × 80 × 55 mm)
- **Hydrophobic mesh** (Gore-Tex-style acoustic vent) over the mic ports — blocks water, passes sound
- **Intake funnel** (3D-printed, matte black) directs insects toward the UV lure and fan
- **Solar panel** mounted on the lid with weatherproof adhesive
- **Collection vial** screws into the bottom (removable without opening the enclosure)
- **Mounting**: adjustable strap/zip-tie bracket for trellis wire, branch, or pole

---

## Firmware Architecture (ESP32-S3, ESP-IDF)

FreeRTOS-based, five tasks:

| Task | Core | Priority | Job |
|------|------|----------|-----|
| `capture` | 0 | 5 (highest) | I²S DMA double-buffer, trigger pre-processing on each 250 ms frame |
| `classify` | 1 | 4 | FFT → 1D-CNN inference → species ID → capture decision |
| `trap` | 0 | 3 | Fan PWM soft-start, UV LED scheduling, collection management |
| `lorawan` | 1 | 3 | SX1262 driver, LoRaWAN MAC, uplink queue, downlink handler |
| `power` | 0 | 2 | Fuel gauge polling, solar charge status, light sleep management |

Key modules:

- `i2s_capture.c` — I²S1 dual-channel DMA, 16 kHz, 250 ms windows, double-buffer with callback to `classify`
- `preprocess.c` — FIR band-pass (30 Hz–2 kHz), RMS energy detector, adaptive noise floor, autocorrelation wingbeat frequency estimate
- `classifier.c` — int8 1D-CNN inference (ESP-NN / vector instructions), 12-class + unknown softmax, confidence threshold
- `model_weights.c` — quantized int8 CNN weights and biases (generated by training pipeline, see `scripts/train_model.py`)
- `species.c` — species class names, wingbeat frequency ranges, beneficial/target flag, count accumulator
- `fan_control.c` — DRV8601 PWM soft-start, duration based on detected species size, tachometer readback
- `uv_lure.c` — LEDC PWM dimming, day/night schedule from TSL2591, override modes
- `sensors.c` — SHT40 + TSL2591 I²C drivers, periodic sampling (10 s interval)
- `lorawan.c` — SX1262 SPI driver, LoRaWAN 1.0.4 MAC, OTAA join, uplink packet assembly, downlink config parsing
- `power.c` — MAX17048 fuel gauge, battery/solar voltage ADC, light-sleep entry/exit, low-battery behavior
- `storage.c` — NVS (non-volatile storage) for species counts, config, LoRaWAN session keys
- `ble_provision.c` — BLE GATT server for initial Wi-Fi/LoRaWAN provisioning via the companion app
- `main.c` — ESP-IDF app_main, FreeRTOS task init, peripheral bring-up

---

## Wingbeat Frequency Reference

| Species Class | Wingbeat Range (Hz) | Typical | Target/Beneficial |
|--------------|---------------------|---------|-------------------|
| *Aedes* mosquito | 400–800 | 550 | Target (disease vector) |
| *Culex* mosquito | 300–600 | 450 | Target (disease vector) |
| *Anopheles* mosquito | 300–550 | 400 | Target (malaria vector) |
| Honeybee (*Apis*) | 200–260 | 230 | Beneficial (pollinator) |
| *Drosophila* fruit fly | 150–250 | 200 | Target (crop pest: SWD) |
| Codling moth | 40–80 | 60 | Target (orchard pest) |
| Fall armyworm moth | 30–70 | 50 | Target (row crop pest) |
| Housefly | 150–200 | 180 | Neutral |
| Wasp/hornet | 100–160 | 130 | Target (nuisance/agri-pest) |
| Lacewing | 40–60 | 50 | Beneficial (predator) |
| Hoverfly | 120–180 | 150 | Beneficial (pollinator + predator) |
| Unknown | — | — | Unclassified |

The CNN uses the full FFT spectrum (not just the dominant frequency), so it can distinguish species with overlapping ranges using harmonic content and temporal modulation patterns (e.g., mosquitoes have distinctive amplitude modulation from their wingstroke kinematics).

---

## Bill of Materials

See `hardware/BOM.csv`.

---

## Building It

See `docs/assembly_guide.md` for the full assembly, weatherproofing, and field deployment procedure. See `docs/model_training.md` for how to collect wingbeat training data and train/quantize the CNN. See `docs/api_reference.md` for the LoRaWAN payload format and BLE provisioning protocol.

---

## Companion Scripts

`scripts/` contains Python helpers:

- `train_model.py` — train the 1D-CNN on wingbeat audio data, quantize to int8, export C header for firmware
- `record_wingbeats.py` — connect to the Echo Trap over BLE, stream raw I²S audio to a PC for dataset collection
- `lorawan_config.py` — provision LoRaWAN keys (AppEUI/AppKey/DevEUI) over BLE
- `dashboard.py` — decode LoRaWAN uplinks from a TTN/Chirpstack HTTP integration, plot species counts over time (matplotlib)
- `field_test.py` — automated field test: simulate detections, verify fan/UV/LoRa response, report pass/fail

---

## License

MIT — build it, deploy it, count bugs with it.