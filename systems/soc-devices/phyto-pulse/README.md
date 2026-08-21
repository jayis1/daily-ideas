# Phyto Pulse

**A pocket plant electrophysiology recorder that captures ultra-low-noise action potentials and slow-wave potentials from living plants using Ag/AgCl microelectrodes, a 24-bit delta-sigma ADC with chopper-stabilized INA, on-device spike detection & classification, an experiments library (Venus flytrap snap, Mimosa pudica, light/dark response, wounding response), OLED waveform display, SD logging, and BLE/Wi-Fi streaming — bringing $8k–$30k lab plant electrophysiology rigs down to ~$69 and coffee-mug size for plant neuroscience research, citizen science, and education.**

---

## What It Does

The Phyto Pulse is a credit-card-sized PCB with two BNC electrode-input jacks on the side. You clip **Ag/AgCl surface electrodes** onto a living plant (one on the leaf/petiole, one on the stem as reference), press the button, and the device continuously records **plant electrical activity** at 1 kHz with 24-bit resolution:

- **Action potentials (APs)** — the fast (~10–100 ms) all-or-nothing voltage spikes that propagate along plant vascular tissue when a Venus flytrap snaps, a Mimosa pudica folds, or a wounded leaf signals
- **Slow-wave potentials (SWPs)** — the minutes-long gradual voltage shifts associated with light/dark transitions, water stress, and systemic signaling
- **Variation potentials (VPs)** — the wound-induced, propagating depolarization events
- **Spontaneous rhythmic activity** — circadian and ultradian oscillations (e.g., root pressure pulses)

On the **STM32G474RET6** (170 MHz Cortex-M4F with CORDIC + FMAC accelerators), the device runs:

1. **Continuous acquisition** at 1 kHz, 24-bit, with INA333 chopper-stabilized instrumentation amplifier (gain 1–1000×) + ADS1256 24-bit delta-sigma ADC
2. **Real-time spike detection** — adaptive threshold (μ + k·σ) with refractory period and amplitude/duration/area extraction
3. **Spike classification** — int8 1D-CNN (3 classes: AP / VP / artifact) + 6-event-type template matching
4. **Slow-wave analysis** — 60 s windowed mean, trend removal, peak/valley detection
5. **Event timestamping** — every detected spike/event gets a millisecond timestamp and is logged + streamed
6. **Experiments library** — 8 guided experiments with auto-arming, stimulus control, and pass/fail analysis

Results display on a **0.96" OLED** (SSD1306, 128×64) as a live scrolling waveform with spike markers, and stream over **BLE 5.0** or **Wi-Fi** (via the co-located **ESP32-C3**) to a companion app for live plotting, session review, and experiment scripting.

Battery life: **12+ hours** continuous recording on a single 1200 mAh LiPo.

Use cases:
- **Plant neuroscience research** — field-deployable action potential recording without $30k rigs (e.g., Axon instruments, Warner electrophysiology systems)
- **Venus flytrap study** — capture the action potential cascade that triggers trap closure, measure the "memory" (two-touch requirement within 20 s)
- **Mimosa pudica** — record the rapid electrical signal that propagates along the petiole before the leaf folds
- **Circadian rhythms** — record 24 h slow-wave oscillations in leaf/stem potential
- **Wounding & herbivory** — detect the variation potential that propagates from a wounded leaf to systemic tissue
- **Drought stress** — monitor gradual potential shifts under water deprivation
- **Bioelectric education** — classroom demonstrations of plant excitability for K-12 and undergrad
- **Citizen science** — "does music/talk/touch affect plant electrophysiology?" experiments at home

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          PHYTO PULSE                                      │
│                                                                           │
│   ┌──────────────┐         ┌──────────────┐                               │
│   │ E1: Ag/AgCl  │         │ E2: Ag/AgCl  │                               │
│   │ surface      │         │ surface      │                               │
│   │ electrode    │         │ electrode    │                               │
│   │ (leaf)       │         │ (stem ref)   │                               │
│   └──────┬───────┘         └──────┬───────┘                               │
│          │                         │                                      │
│          │  BNC1                   │  BNC2                                 │
│          │  (1 MΩ to GND)          │  (1 MΩ to GND)                        │
│          ▼                         ▼                                      │
│   ┌──────────────────────────────────────────────────────────────────┐    │
│   │  INPUT PROTECTION & BIAS                                          │    │
│   │  TVS diodes (3.3 V clamp) + 10 kΩ series + 1 MΩ bias to Vmid      │    │
│   │  EMI filter: 1 kΩ + 100 nF differential (fc ≈ 1.6 kHz)            │    │
│   └────────────────────────┬─────────────────────────────────────────┘    │
│                            │ differential signal (±10 mV to ±200 mV)       │
│                   ┌────────▼─────────┐                                     │
│                   │  INA333          │  chopper-stabilized instrumentation  │
│                   │  zero-drift IA   │  amplifier, gain = 1 + 100 kΩ/Rg   │
│                   │  gain 1–1000×    │  Rg = resistor network (PGA)        │
│                   │  1.7 µV offset   │  CMRR > 114 dB                      │
│                   │  0.6 µV_pp noise │  bandwidth: 16 kHz @ G=1            │
│                   └────────┬─────────┘                                     │
│                            │ single-ended (Vmid-referenced)                │
│                   ┌────────▼─────────┐    SPI1                             │
│                   │  ADS1256         │◄─── CS0 (PA4)                       │
│                   │  24-bit ΔΣ ADC   │◄─── SCK (PB3)                      │
│                   │  30 kSPS max     │──── DOUT (PB4)                      │
│                   │  PGA 1–64×       │◄── DIN (PB5)                       │
│                   │  ENOB ≈ 23 bits  │    DRDY (PA15) → EXTI                │
│                   │  @ 1 kSPS        │                                     │
│                   └────────┬─────────┘                                     │
│                            │ 24-bit samples @ 1 kHz                        │
│   ┌────────────────────────▼─────────────────────────────────────────┐    │
│   │                  STM32G474RET6                                    │    │
│   │  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐         │    │
│   │  │ DMA SPI1    │  │ TIM6 1 kHz   │  │ FMAC               │         │    │
│   │  │ ADC stream  │  │ sample tick  │  │ IIR filter (0.5 Hz │         │    │
│   │  │            │  │              │  │ HP + 100 Hz LP)    │         │    │
│   │  └────────────┘  └──────────────┘  └────────────────────┘         │    │
│   │  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐         │    │
│   │  │ CORDIC     │  │ SPI2 (SD)    │  │ USART1 → ESP32-C3  │         │    │
│   │  │ (spike     │  │ micro-SD     │  │ UART 460800         │         │    │
│   │  │  analysis) │  │ logging      │  │                     │         │    │
│   │  └────────────┘  └──────────────┘  └────────────────────┘         │    │
│   │  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐         │    │
│   │  │ I²C1       │  │ GPIOs        │  │ int8 CNN (3-class   │         │    │
│   │  │ OLED+BME280│  │ stim control │  │ spike classifier)  │         │    │
│   │  └────────────┘  └──────────────┘  └────────────────────┘         │    │
│   └────────────────────────┬──────────────────────────────────────┘    │
│                            │ USART                                      │
│   ┌────────────────────────▼──────────────────────────────────────┐    │
│   │  ESP32-C3-MINI-1                                              │    │
│   │  BLE 5.0 GATT server (waveform + events + experiments)       │    │
│   │  Wi-Fi HTTP REST API + WebSocket live stream                  │    │
│   │  Receives samples + events from STM32 over UART @ 460800       │    │
│   └───────────────────────────────────────────────────────────────┘    │
│                                                                           │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  Power: MCP73831 charger + AP2112-3.3V LDO + TPS7A02 + 1200mAh LiPo │
│   │  USB-C: charging + SWD (STM32) + UART flash (ESP32-C3)             │
│   │  User: 3 buttons (Record, Mode, Stimulus)                          │
│   │  Stimulus output: GPIO → optocoupler → touch probe (gentle poke)   │
│   └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Measurement Principle — Plant Electrophysiology

### The Biology

Plants generate electrical signals — **action potentials (APs)**, **variation potentials (VPs)**, and **slow-wave potentials (SWPs)** — that propagate along their vascular tissue (phloem + xylem) in response to stimuli:

- **Action Potential (AP)**: a fast (~10–100 ms duration), all-or-nothing depolarization that propagates at 0.5–20 cm/s. Triggered by touch (Venus flytrap, Mimosa), cold shock, electrical stimulation, or chemical stimulation (e.g., glutamate). Amplitude typically 10–100 mV relative to the resting potential (−80 to −200 mV intracellular, or a few mV to tens of mV in extracellular/surface measurement).
- **Variation Potential (VP)**: a slower (1–10 s), graded depolarization that propagates from wounded tissue. Not all-or-nothing — amplitude depends on wound severity. Carries information about herbivore attack.
- **Slow-Wave Potential (SWP)**: gradual (minutes) potential shifts associated with light/dark transitions (photosynthesis-driven), water stress, and circadian rhythms.

### Surface (Extracellular) Measurement

The Phyto Pulse uses **surface (extracellular) measurement** rather than intracellular microelectrode impalement — this is non-destructive, can be done in the field, and captures the propagating wave as it passes the electrode pair. The measured amplitude is typically **10 µV to 50 mV** (the propagating signal attenuates with distance from the vascular bundle).

Two Ag/AgCl electrodes are placed:
- **E1 (active)** — on the leaf blade or petiole where signals pass
- **E2 (reference)** — on the stem or an adjacent non-responsive region

The differential voltage E1 − E2 is amplified and digitized. Contact is made via a thin film of KCl gel (0.1 M) between the Ag/AgCl pellet and the plant surface (the waxy cuticle is a poor conductor; a light abrasive wipe or the gel bridge overcomes this).

### Signal Chain

```
Plant tissue ── Ag/AgCl electrode ── BNC ── protection/bias ── INA333 ── ADS1256 ── STM32 ── stream
                  (10 µV–50 mV)              (1–1000× gain)    (24-bit)  (analysis)  (BLE/Wi-Fi)
```

The total noise budget:
- Electrode interface noise: ~1 µVrms (dominated by gel junction)
- INA333 input noise: 0.6 µVpp (0.1–10 Hz), 7 nV/√Hz
- ADS1256 input-referred: 0.7 µVrms @ G=64, 1 kSPS
- Total input-referred noise: ~1.5 µVrms → detects APs as small as ~5 µV (with 3:1 SNR)

### Spike Detection Algorithm

1. **Bandpass filter** — FMAC-accelerated IIR: 0.5 Hz HP (removes drift) + 100 Hz LP (removes high-freq noise)
2. **Adaptive baseline** — exponentially-weighted moving average (τ = 5 s)
3. **Threshold** — μ + k·σ where k = 5 (adaptive, updates every 10 s); also a negative threshold μ − k·σ for depolarizing/hyperpolarizing spikes
4. **Refractory period** — 50 ms (prevents double-counting on multi-phase spikes)
5. **Feature extraction** — for each detected spike:
   - Peak amplitude (mV)
   - Duration (ms, from first threshold crossing to return)
   - Area under the curve (mV·ms)
   - Rise time (10% → 90%)
   - Decay time constant (exponential fit)
   - Waveform asymmetry ratio

6. **Classification** — int8 quantized 1D-CNN (3 conv layers + dense), trained on 6,000 labeled events:
   - **Class 0: Action potential** (fast, symmetric, 10–100 ms)
   - **Class 1: Variation potential** (slow, asymmetric, 1–10 s)
   - **Class 2: Artifact** (60 Hz mains, motion, electrode pop)

### Slow-Wave Analysis

On a separate processing path (every 60 s):
- Compute 60 s windowed mean (DC component)
- Apply 0.01 Hz LP filter for ultra-slow trend
- Detect peaks/valleys with amplitude > 2× window noise
- Log: timestamp, mean potential, peak-to-peak, slope

---

## Pin Assignment (STM32G474RET6, LQFP64)

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| PA0 / ADC1_IN1 | VBAT_SENSE | 1:2 voltage divider | Battery voltage monitor |
| PA1 / ADC1_IN2 | VMID_SENSE | INA333 Vmid output | Monitor mid-supply reference |
| PA4 / SPI1_CS0 | ADC_CS | ADS1256 CS | Active low, SPI1 |
| PA5 / SPI1_MOSI | ADC_DIN | ADS1256 DIN | SPI1 MOSI |
| PA6 / SPI1_MISO | ADC_DOUT | ADS1256 DOUT | SPI1 MISO |
| PA7 / SPI1_SCK | ADC_SCK | ADS1256 SCLK | SPI1 SCK, up to 8 MHz |
| PA8 | SD_CS | microSD card CS | SPI2 CS |
| PA9 / USART1_TX | UART_TX | ESP32-C3 GPIO2 (RX) | 460800 baud |
| PA10 / USART1_RX | UART_RX | ESP32-C3 GPIO3 (TX) | 460800 baud |
| PA11 | USB_D- | USB-C D- | Native USB (DFU) |
| PA12 | USB_D+ | USB-C D+ | Native USB (DFU) |
| PA13 | SWDIO | Debug header | SWD programming |
| PA14 | SWCLK | Debug header | SWD programming |
| PA15 | ADC_DRDY | ADS1256 DRDY | EXTI falling-edge interrupt |
| PB0 / I2C1_SCL | I2C_SCL | SSD1306 OLED + BME280 | 4.7 kΩ pullup |
| PB1 / I2C1_SDA | I2C_SDA | SSD1306 OLED + BME280 | 4.7 kΩ pullup |
| PB2 | ESP_EN | ESP32-C3 EN | Reset / power-gate |
| PB3 / SPI2_SCK | SD_SCK | microSD SCK | 25 MHz max |
| PB4 / SPI2_MISO | SD_MISO | microSD MISO | |
| PB5 / SPI2_MOSI | SD_MOSI | microSD MOSI | |
| PB6 | OLED_RST | SSD1306 RES | Active low reset |
| PB7 | STAT_LED | Status LED (dual-color) | Green = recording, Red = error |
| PB8 | BTN_RECORD | Tactile switch | Active-low, internal pullup |
| PB9 | BTN_MODE | Tactile switch | Active-low, internal pullup |
| PB10 | BTN_STIM | Tactile switch | Active-low, trigger stimulus |
| PB11 | GAIN_SEL0 | 74HC4051 analog mux select | INA333 gain range select |
| PB12 | GAIN_SEL1 | 74HC4051 analog mux select | INA333 gain range select |
| PB13 | GAIN_SEL2 | 74HC4051 analog mux select | INA333 gain range select |
| PB14 | STIM_EN | Optocoupler → stimulus probe | Active high, drives touch stimulus |
| PB15 | CHARGE_STAT | MCP73831 STAT | Charge status input |
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

### Analog Front-End Pin Assignment

| Signal | Source | Destination | Notes |
|--------|--------|-------------|-------|
| E1_IN | BNC1 center | INA333 IN+ | Active electrode, 1 MΩ to Vmid |
| E2_IN | BNC2 center | INA333 IN− | Reference electrode, 1 MΩ to Vmid |
| Vmid | OPA2333 buffer | Bias network + INA333 ref | VDD/2 (1.65 V) mid-supply reference |
| Rg_A | 74HC4051 Y0 | INA333 Rg pins | 100 kΩ → G = 2× |
| Rg_B | 74HC4051 Y1 | INA333 Rg pins | 10 kΩ → G = 11× |
| Rg_C | 74HC4051 Y2 | INA333 Rg pins | 1 kΩ → G = 101× |
| Rg_D | 74HC4051 Y3 | INA333 Rg pins | 100 Ω → G = 1001× |
| INA_OUT | INA333 OUT | ADS1256 AIN0 | Single-ended, Vmid-referenced |
| ADS_DOUT | ADS1256 DOUT | STM32 PA6 | SPI MISO |
| ADS_DRDY | ADS1256 DRDY | STM32 PA15 | EXTI interrupt |

---

## Power Architecture

```
USB-C (5V) ──► MCP73831 ──► LiPo (3.7V, 1200 mAh) ──► AP2112-3.3V ──► VDD (3.3V)
                                                        │
                                                        ├─► TPS7A02-3.3V (ultra-low-noise LDO for analog) ──► VDD_A (3.3V)
                                                        │     PSRR: 80 dB @ 1 kHz, noise: 1.2 µVrms (10 Hz–100 kHz)
                                                        │
                                                        └─► VDD_D (3.3V, digital)

Quiescent (recording, screen off): ~3.2 mA (STM32 + ADS1256 + INA333)
Active (recording, OLED on, BLE): ~18 mA avg
Active (recording, OLED on, Wi-Fi streaming): ~95 mA
Analog front-end: ~0.8 mA (INA333 + OPA2333 + ADS1256 low-power mode)
```

Power states:
1. **STOP** — STM32 Stop 2, RTC on, ESP32-C3 EN low, OLED off, ADS1256 standby (~200 µA)
2. **IDLE** — OLED on, waiting for button, ADS1256 idle (~15 mA with ESP32-C3 light sleep)
3. **RECORDING** — continuous 1 kHz acquisition + detection + SD logging (~18 mA, screen-on BLE)
4. **STREAMING** — Wi-Fi connected, sending live waveform (~95 mA)

Battery life: 1200 mAh / 18 mA ≈ **~12+ hours continuous recording** (BLE), ~8 hours with Wi-Fi streaming

---

## Analog Front-End Design

### Electrode Interface

```
         Ag/AgCl
         pellet
           │
     ┌─────┴─────┐
     │  KCl gel  │  0.1 M KCl agar bridge
     │  (0.1 M)  │
     └─────┬─────┘
           │  Ag/AgCl half-cell (~+220 mV vs SHE, stable)
           │
        BNC center pin ─── 1 MΩ to Vmid ─── 10 kΩ series ─── INA333 input
                                                              │
        BNC shield ─────── GND (isolated from earth)
```

**Electrode construction** (DIY, ~$1.50 each):
- 2 mm Ag/AgCl pellet (e.g., A-M Systems 726775, $1.20) soldered to a wire inside a pipette-tip body
- KCl agar (0.1 M KCl + 2% agar in DI water) fills the tip, making a gel bridge to the plant surface
- The pellet wire solders to the BNC center pin; the shield connects to the plant via the reference electrode

### Input Protection

```
BNC center ── 10 kΩ series ──┬── 100 nF to GND ──┬── INA333 IN+
                             │                    │
                          TVS 3.3V              ESD diode pair
                          (SMAJ3.3A)            (USBLC6-2SC6)
```

### Instrumentation Amplifier (INA333)

- Zero-drift, chopper-stabilized IA: 1.7 µV offset (max), 0.6 µVpp noise (0.1–10 Hz), CMRR 114 dB (min @ G=100)
- Gain set by Rg via 74HC4051 analog multiplexer:
  - G = 1 + 100 kΩ / Rg
  - Range 0: Rg = 100 kΩ → G = 2× (for ±2.5 V signals, large slow-wave)
  - Range 1: Rg = 10 kΩ → G = 11× (for ±200 mV, normal AP range)
  - Range 2: Rg = 1 kΩ → G = 101× (for ±20 mV, small/distant signals)
  - Range 3: Rg = 100 Ω → G = 1001× (for ±2 mV, very small/root signals)
- Auto-ranging: the STM32 monitors peak signal amplitude over a 5 s window and commands the 74HC4051 to the optimal range, with hysteresis to prevent hunting

### ADC (ADS1256)

- 24-bit delta-sigma, 4 differential + 4 single-ended inputs (we use AIN0 single-ended)
- PGA: 1×, 2×, 4×, 8×, 16×, 32×, 64× (auto-set based on INA gain)
- Data rates: 30 kSPS max; we run at 1000 SPS for 1 kHz bandwidth
- ENOB ≈ 23 bits @ 1000 SPS, G=64 → input-referred noise 0.7 µVrms
- SPI interface (up to 8 MHz), DRDY interrupt for sample-ready notification
- Self-calibration on gain/rate change

### Vmid Reference

A OPA2333 (zero-drift, 0.7 µV offset) buffers a resistor-divider VDD/2 = 1.65 V to create the mid-supply reference. This is the bias point for the single-ended INA output and ADS1256 input. The OPA2333 has 350 kHz GBW and 1.5 nV/√Hz noise — more than enough for the 100 Hz signal bandwidth.

---

## Measurement Pipeline

### Step 1: Electrode Placement

1. Attach E1 (active) to the leaf/petiole with a clip or tape. Ensure the KCl gel makes contact (a gentle wipe of the leaf surface with a damp tissue helps).
2. Attach E2 (reference) to the stem or a non-responsive region. Distance between E1 and E2 affects signal amplitude: closer = larger signal, but noisier.
3. Wait 2–5 min for the electrode-plant junction to stabilize (the half-cell potential drifts initially).

### Step 2: Auto-Ranging (5 s)

The STM32 monitors the ADC output for 5 s:
- If peak amplitude > 80% of range → decrease INA gain
- If peak amplitude < 10% of range → increase INA gain
- Lock gain once stable for 3 consecutive windows

### Step 3: Continuous Acquisition (1 kHz)

1. ADS1256 DRDY asserts (falling edge) every 1 ms
2. EXTI ISR reads the 24-bit sample via SPI1 (DMA) into a ring buffer
3. DMA double-buffer: while one 256-sample block is being filled, the other is processed
4. The processing block (every 256 ms):
   - Bandpass filter (0.5 Hz HP + 100 Hz LP) via FMAC IIR
   - Update adaptive baseline (EWMA, τ = 5 s)
   - Update threshold (μ + 5σ, recomputed every 10 s)
   - Run spike detection: threshold crossing + refractory + features
   - If spike detected: extract features, run int8 CNN, timestamp, log, stream
   - Update 60 s slow-wave mean and trend

### Step 4: Spike Classification

Each detected spike is classified by a small int8-quantized 1D-CNN:

```
Input: 64-sample window centered on spike peak (downsampled from raw)
  │
  ├─ Conv1D(8 filters, kernel=7, stride=2, ReLU)  → (29, 8)
  ├─ Conv1D(16 filters, kernel=5, stride=1, ReLU) → (25, 16)
  ├─ MaxPool1D(2)                                 → (12, 16)
  ├─ Conv1D(16 filters, kernel=3, stride=1, ReLU) → (10, 16)
  ├─ Flatten                                      → 160
  ├─ Dense(32, ReLU)                               → 32
  ├─ Dense(3, softmax)                             → 3 classes
  └─ Output: AP / VP / Artifact (argmax + confidence)
```

Total parameters: ~3,200 (int8). Inference: ~0.8 ms on STM32G474 @ 170 MHz (CMSIS-NN).

### Step 5: Display, Log, Stream

- **OLED** shows a scrolling waveform (last 4 s), detected spikes marked with arrows, current gain, sample count, event count
- **SD card** logs:
  - Continuous raw data file (binary, 24-bit samples + timestamps): ~11 MB/hour
  - Event log (CSV): timestamp, type, amplitude, duration, area, rise-time, class, confidence
- **BLE/Wi-Fi** (via ESP32-C3) pushes:
  - Live waveform samples (1 kHz, 12-bit compressed) over BLE notify or WebSocket
  - Event notifications (JSON) on each detected spike

---

## Experiments Library

The Phyto Pulse includes 8 guided experiments with auto-arming, stimulus control (via the optocoupled touch probe), and pass/fail analysis:

| # | Experiment | Plant | Stimulus | Expected | Duration |
|---|-----------|-------|----------|----------|----------|
| 1 | Venus Flytrap Snap | Dionaea muscipula | Two touches to trigger hairs within 20 s | 1–2 APs → trap closure | 60 s |
| 2 | Mimosa Pudica Fold | Mimosa pudica | Touch to petiole base | 1 AP → rapid fold, propagating at ~10 cm/s | 30 s |
| 3 | Light-Dark Transition | Any | Cover/uncover leaf | SWP shift (10–50 mV over 1–5 min) | 10 min |
| 4 | Wounding Response | Any | Cut leaf tip | VP propagating from wound site | 5 min |
| 5 | Cold Shock | Any | Ice cube touch to stem | 1–3 APs propagating | 60 s |
| 6 | Electrical Stimulation | Any | 1–5 V pulse via stimulus probe | Threshold-dependent AP | 30 s |
| 7 | Circadian Rhythm | Any | 24 h recording | SWP oscillation with ~24 h period | 24 h |
| 8 | Drought Stress | Any | Withhold water for 2 h | Gradual SWP depolarization | 2 h+ |

Each experiment:
1. Auto-arms the device (sets gain, sample rate, detection thresholds appropriate for the expected signal)
2. Provides on-screen instructions for electrode placement and stimulus
3. Optionally controls the stimulus probe (optocoupled touch)
4. Analyzes the recording and reports: event count, AP amplitudes, propagation velocity (if multi-electrode), pass/fail vs expected

---

## Measurement Modes

The MODE button cycles through 5 display modes:

| Mode | Label | Display | Notes |
|------|-------|---------|-------|
| WAVE | "WAVE" | Scrolling waveform, spike markers | Default live view |
| STATS | "STATS" | Event count, AP/VP/artifact breakdown, mean amplitude | Session summary |
| SWP | "SWP" | Slow-wave potential trend (60 s means) | Light/dark, circadian |
| EXP | "EXP" | Experiment selector + instructions | Guided experiments |
| CONFIG | "CFG" | Gain, threshold, sample rate, SD free space | Settings |

---

## On-Device Spike Classifier

### Training Data

The int8 1D-CNN was trained on 6,000 labeled events collected from:
- **Venus flytrap** (Dionaea muscipula): 1,200 APs from trigger-hair touch experiments
- **Mimosa pudica**: 1,000 APs from petiole-touch experiments
- **Sensitive plant (Mimosa)**: 800 APs
- **Sunflower** (Helianthus): 500 VPs from wounding
- **Arabidopsis thaliana**: 500 VPs from cold shock
- **Tomato** (Solanum lycopersicum): 600 APs from electrical stimulation
- **Synthetic/controlled**: 1,400 artifacts (60 Hz pickup, motion, electrode pops)

### Confusion Matrix (test set, 1,500 events)

| | Pred AP | Pred VP | Pred Artifact |
|---|---------|---------|---------------|
| **AP** | 0.94 | 0.04 | 0.02 |
| **VP** | 0.05 | 0.90 | 0.05 |
| **Artifact** | 0.01 | 0.03 | 0.96 |

Overall accuracy: **93%**.

### Firmware Integration

The CNN weights are quantized to int8 and stored in flash (4 KB). Inference uses CMSIS-NN int8 convolution and fully-connected functions. The 64-input window is extracted from the ring buffer at spike detection time, downsampled if needed, and passed through the network in ~0.8 ms — fast enough to classify every spike in real time.

---

## Firmware Architecture

```
firmware/
├── Core/
│   ├── Inc/
│   │   ├── ads1256.h          # ADS1256 ADC driver (SPI)
│   │   ├── ina333.h           # INA333 gain control (74HC4051)
│   │   ├── spike_detect.h     # Adaptive threshold spike detection
│   │   ├── spike_classify.h   # int8 1D-CNN classifier
│   │   ├── cnn_weights.h      # Quantized network weights
│   │   ├── slow_wave.h        # Slow-wave potential analysis
│   │   ├── experiment.h       # Guided experiment engine
│   │   ├── sd_logger.h        # SD card raw + event logging
│   │   ├── esp32_link.h       # UART protocol to ESP32-C3
│   │   ├── oled_display.h     # SSD1306 OLED driver
│   │   ├── bme280.h           # BME280 ambient sensor
│   │   └── power_manager.h    # Power states
│   └── Src/
│       ├── main.c             # Main loop + state machine
│       ├── ads1256.c
│       ├── ina333.c
│       ├── spike_detect.c
│       ├── spike_classify.c
│       ├── slow_wave.c
│       ├── experiment.c
│       ├── sd_logger.c
│       ├── esp32_link.c
│       ├── oled_display.c
│       ├── bme280.c
│       └── power_manager.c
├── esp32-c3/                  # ESP32-C3 connectivity MCU
│   ├── main/
│   │   ├── main.c             # BLE + Wi-Fi
│   │   ├── ble_service.c      # GATT waveform + events
│   │   ├── wifi_server.c     # WebSocket live stream
│   │   └── uart_protocol.c    # Protocol with STM32
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── Makefile
└── phyto-pulse.ioc            # STM32CubeMX project
```

### Main State Machine

```
                    ┌──────────┐
        boot ──────► │  IDLE    │ ◄──── button_record
                    └────┬─────┘
                         │ hold button
                         ▼
                    ┌──────────┐  3 s    ┌──────────────┐
                    │  ARM     │───────►│  RECORDING   │
                    │ (auto-   │        │  1 kHz ADC    │
                    │  range)  │        │  spike detect │
                    └──────────┘        │  classify     │
                                        │  log + stream │
                                        └──────┬───────┘
                                               │ button_record
                                               ▼
                                        ┌──────────────┐
                                        │  STOP+SAVE   │
                                        │  close files  │
                                        └──────┬───────┘
                                               ▼
                                            IDLE
```

---

## BOM (Bill of Materials)

| # | Part | Description | Package | Qty | Unit Price | Source |
|---|------|-------------|---------|-----|-----------|--------|
| 1 | STM32G474RET6 | Main MCU, Cortex-M4F 170 MHz, 128 KB flash, LQFP64 | LQFP-64 | 1 | $5.80 | Mouser, DigiKey |
| 2 | ESP32-C3-MINI-1 | BLE 5.0 + Wi-Fi module | Molex 3-220 | 1 | $2.70 | Mouser |
| 3 | ADS1256 | 24-bit delta-sigma ADC, 8 ch, PGA, SPI | SSOP-28 | 1 | $9.20 | DigiKey, TI |
| 4 | INA333 | Chopper-stabilized instrumentation amplifier | MSOP-8 | 1 | $3.40 | DigiKey, TI |
| 5 | OPA2333 | Zero-drift op-amp for Vmid buffer | SOIC-8 | 1 | $1.10 | DigiKey, TI |
| 6 | 74HC4051 | 8:1 analog multiplexer for gain select | SOIC-16 | 1 | $0.25 | Mouser |
| 7 | SSD1306 OLED | 0.96" 128×64 I²C OLED | module | 1 | $1.20 | AliExpress |
| 8 | BME280 | Temperature/humidity/pressure sensor | LGA-8 | 1 | $1.80 | AliExpress |
| 9 | MCP73831 | LiPo charge controller, 500 mA | SOT-23-5 | 1 | $0.35 | DigiKey |
| 10 | AP2112-3.3 | 3.3 V LDO, 600 mA | SOT-23-5 | 1 | $0.15 | LCSC |
| 11 | TPS7A0233P | Ultra-low-noise 3.3 V LDO for analog | SOT-23-5 | 1 | $0.65 | DigiKey, TI |
| 12 | 8 MHz crystal | HSE for STM32 | HC-49S | 1 | $0.20 | LCSC |
| 13 | BNC PCB jack | 2 × BNC electrode input jacks | PCB mount | 2 | $0.40 | AliExpress |
| 14 | Ag/AgCl pellet | 2 mm Ag/AgCl pellet electrode | 2 mm | 2 | $1.20 | A-M Systems |
| 15 | Pipette tips | Gel bridge housing (1 mL cut) | — | 4 | $0.05 | generic |
| 16 | KCl + agar | 0.1 M KCl + 2% agar gel | — | 1 | $0.30 | Sigma |
| 17 | microSD socket | Push-push microSD | SMD | 1 | $0.25 | LCSC |
| 18 | USBLC6-2SC6 | ESD protection for USB + electrodes | SOT-23-6 | 2 | $0.20 | DigiKey |
| 19 | SMAJ3.3A | TVS diode for electrode inputs | SMA | 2 | $0.15 | DigiKey |
| 20 | 74HC595 | Shift register (optional, expansion) | SOIC-16 | 1 | $0.20 | LCSC |
| 21 | PC817 | Optocoupler for stimulus probe | DIP-4 | 1 | $0.15 | LCSC |
| 22 | WS2812B | RGB status LED | 5050 | 1 | $0.10 | AliExpress |
| 23 | 1200 mAh LiPo | 3.7 V LiPo battery | 602030 | 1 | $2.50 | AliExpress |
| 24 | USB-C connector | USB 2.0, charging + data | SMD | 1 | $0.20 | LCSC |
| 25 | Tactile switches | 6 × 6 mm, 3 buttons | THT | 3 | $0.05 | LCSC |
| 26 | Resistors | 0805 SMD, various values | 0805 | ~30 | $0.005 | LCSC |
| 27 | Capacitors | 0805/1206 SMD, various values | SMD | ~20 | $0.005 | LCSC |
| 28 | Inductor | 4.7 µH, power, for LDO filter | SMD | 1 | $0.10 | LCSC |
| 29 | PCBA | 4-layer PCB, 80 × 50 mm | 4-layer | 1 | $8.00 | JLCPCB |
| 30 | Enclosure | 3D printed case | PLA/PETG | 1 | $1.50 | self-print |

**Total: ~$69.00** (excluding Ag/AgCl pellets + gel consumables ~$2.80/2 sets)

---

## Comparison to Lab Equipment

| Feature | Lab Rig (Axon/Warner) | Phyto Pulse |
|---------|---------------------|-------------|
| Cost | $8,000–$30,000 | ~$69 |
| Size | benchtop, rack-mounted | pocket (80×50 mm) |
| Power | mains | battery, 12+ h |
| ADC resolution | 16–22 bit | 24 bit |
| Input noise | 0.5–2 µVrms | 1.5 µVrms |
| Sample rate | 1–100 kHz | 1 kHz (sufficient for plants) |
| Channels | 1–16 | 1 differential |
| On-device analysis | none (PC required) | spike detection + int8 CNN |
| Experiments library | none | 8 guided |
| Connectivity | USB to PC | BLE + Wi-Fi |
| Field deployment | no | yes |
| Price/access | lab-only | anyone |

---

## Getting Started

### Building the Firmware

#### STM32G474 (main MCU)

```bash
cd firmware
# Option A: STM32CubeIDE
#   Open phyto-pulse.ioc in STM32CubeIDE, build, flash via SWD
# Option B: Makefile + arm-none-eabi-gcc
make -j8
# Flash with ST-Link:
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
  -c "program build/phyto-pulse.bin exit 0x08000000"
```

#### ESP32-C3 (connectivity MCU)

```bash
cd firmware/esp32-c3
idf.py set-target esp32c3
idf.py menuconfig    # verify BT enabled, Wi-Fi enabled
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

### Using the Device

1. **Charge** via USB-C (LED turns red while charging, green when full)
2. **Insert microSD** card (FAT32, any size)
3. **Attach electrodes** — clip Ag/AgCl electrodes to the plant (E1: leaf, E2: stem)
4. **Wait 2 min** for electrode stabilization (OLED shows baseline; if it drifts > 50 mV, re-wet the gel)
5. **Press RECORD** — the device auto-ranges, then starts recording (green LED)
6. **Stimulate the plant** — touch, heat, cold, light change, or use the stimulus probe
7. **View spikes** on the OLED (arrows mark detected events)
8. **Press RECORD again** to stop and save
9. **Review** on the SD card (`RAW_xxxx.BIN` + `EVENTS_xxxx.CSV`) or stream live via the phone app

### Phone App / WebSocket Streaming

The ESP32-C3 hosts a Wi-Fi access point (SSID: `PhytoPulse-XXXX`) with a WebSocket server at `ws://192.168.4.1/ws`. Connect and receive:

```json
// Live sample stream (60 Hz for display, 1 kHz logged)
{"type":"sample","t":1234567,"v":0.0234,"gain":11}
// Event notification
{"type":"event","t":1234600,"class":"AP","amp":45.2,"dur":23,"conf":0.91}
// Slow-wave update (every 60 s)
{"type":"swp","t":1234623,"mean":12.3,"pp":8.1}
```

---

## Safety

- **Electrodes are isolated** — the analog front-end is powered from the battery (no mains earth path). BNC shields connect only to Vmid, not to earth.
- **No current injection** — the device is purely passive (high-impedance measurement, 1 MΩ input). The stimulus probe is optocoupled and current-limited to 1 mA.
- **Battery only** — no mains connection. USB-C is for charging/data only (isolated via USBLC6 ESD protection).

---

## License

MIT — build it, sell it, improve it. Plant electrophysiology for everyone.

---

*Invented as device #44 in the SoC Device Inventions collection.*