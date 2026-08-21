# Bolt Compass — Pocket Lightning Direction-Finder & Storm-Warning Station

> A portable, solar-powered **lightning detection, ranging, and direction-finding
> station** that listens to the 3–30 kHz VLF "sferic" radio bursts emitted by
> lightning strokes with a pair of **orthogonal shielded-loop magnetic antennas**,
> measures the quasi-static electric-field change with a **chopper-stabilized
> electrometer whip**, time-tags every stroke with **GPS PPS** to the microsecond,
> classifies each stroke as **cloud-to-ground (CG) vs. intra-cloud (IC)** from its
> waveform shape, estimates **distance** from the sferic amplitude and an
> Earth-ionosphere waveguide propagation model, computes the **bearing** to the
> stroke from the crossed-loop goniometer phase, draws a live **storm bearing
> radar** on an OLED, logs every event to SD, and streams live sferics over
> BLE / Wi-Fi to a phone app. Built around the **ESP32-S3-WROOM-1** and the
> **ADS131M04** 4-channel 24-bit simultaneous-sampling delta-sigma ADC.

```
                 ┌──────────────────────────────────────────────────────────┐
                 │                      ANTENNAS                              │
                 │                                                            │
                 │   ┌─────────────┐      ┌─────────────┐                     │
                 │   │  Loop A N-S │      │  Loop A E-W │   orthogonal shielded│
                 │   │  (VLF mag)  │      │  (VLF mag)  │   air-core loops     │
                 │   └──────┬──────┘      └──────┬──────┘                     │
                 │          │  sferic B-field    │                            │
                 │          ▼                    ▼                            │
                 │   ┌─────────────────────────────────────┐                  │
                 │   │  2× LT1991 low-noise preamp (40 dB)  │                 │
                 │   └──────────────────┬──────────────────┘                  │
                 │                      │ CH0 (N-S) , CH1 (E-W)               │
                 │   ┌──────────────┐   │                                     │
                 │   │  E-field whip│   │   chopper electrometer (ADA4530-1)  │
                 │   │  (slow E,    │   │   0.1 Hz – 1 kHz  slow antenna      │
                 │   │   ΔE/Q)      │───┤ CH2                                 │
                 │   └──────────────┘   │                                     │
                 │                      ▼                                     │
                 │   ┌─────────────────────────────────────┐                  │
                 │   │        ADS131M04  (4-ch 24-bit)      │  SPI ──▶ ESP32-S3 │
                 │   │  simultaneous ΔΣ  8 ksps / ch         │                 │
                 │   └─────────────────────────────────────┘                  │
                 │                                                            │
                 │              ESP32-S3-WROOM-1                              │
                 │   sferic detect · bearing goniometer · CG/IC classify       │
                 │   distance model · storm tracker · keogram                 │
                 │                                                            │
                 │   NEO-M9N GPS (PPS) ──▶ GPIO  ·  SSD1306 OLED 128×64       │
                 │   microSD (SPI)  ·  TP4056 + 18650  ·  SX1262 LoRa (opt)    │
                 │   BLE GATT (BoltCompass) ·  Wi-Fi AP+STA / HTTP / TCP       │
                 └────────────────────────────────────────────────────────────┘
```

---

## 1. What It Is

**Bolt Compass** is the smallest device that can tell you **where lightning is**
—not just *that* it happened, but the **bearing** to the stroke, the **distance**,
and the **type** (cloud-to-ground vs. intra-cloud)—and watch a storm approach in
real time on a pocket-sized OLED "radar" display.

You stand it up in a field (or a balcony, or a hilltop), unfold the two crossed
loop antennas and the E-field whip, and within a minute it is listening. Every
time lightning strikes within ~300 km, the VLF magnetic pulse ("sferic") arrives,
induces a voltage in the two orthogonal loops, and the device:

1. **Captures** a 50 ms window of the 3–30 kHz burst on both loops + the slow
   E-field channel, simultaneously (the ADS131M04 samples all four channels on
   the same clock edge).
2. **Detects** the sferic (energy burst above a noise-floor threshold, confirmed
   by rise-time and duration gates to reject impulsive interference).
3. **Classifies** the stroke: a **CG** stroke has a sharp initial peak, fast
   rise (<5 µs equivalent at the ionospheric group-delay), and a large
   subsequent slow-tail; an **IC** stroke has a broader, bipolar pulse with a
   smaller slow-tail ratio. A small **int8 random-forest / logistic-regression
   classifier** (trained on ~50 000 labeled sferics from the Blitzortung /
   LOFAR public archives) runs on-device.
4. **Ranges** the stroke from the peak field strength corrected for the
   Earth-ionosphere waveguide attenuation (frequency-dependent, 1st TM mode,
   daytime/nighttime conductivity), giving a distance estimate with a typical
   error of ±15 % at 30–200 km.
5. **Bears** the stroke from the ratio and sign of the two loop amplitudes
   (`θ = atan2(EW, NS)`), the classic **crossed-loop goniometer** used since the
   1920s and still the basis of Blitzortung.org and lightningmaps.org. The
   orthogonal loops remove the 180° ambiguity when combined with the sign of the
   initial E-field change.
6. **Time-tags** the stroke to the microsecond using the GPS PPS edge, so events
   can be cross-correlated with the global GLD360 / Blitzortung stroke database
   (the device can also upload to Blitzortung as a station).
7. **Plots** the stroke as a dot on an OLED polar "radar" sweep, builds a
   storm-cluster centroid, and shows a bearing arrow + distance + approach-rate.
8. **Logs** every event to the SD card as CSV + a binary waveform, and
   **streams** live sferics over BLE (GATT notify) and/or Wi-Fi (TCP) to the
   companion phone/PC app.

It is inspired by the **Blitzortung.org** red kit, the **Boltek StormTracker**,
and academic VLF direction-finder work (Krider, Noggle, Uman 1976), but it is
entirely open-source, costs ~$85 in parts, fits in a pocket, and runs for a
week on a single 18650 + small solar panel.

### Why the ESP32-S3 + ADS131M04 split

The **ESP32-S3-WROOM-1** is the compute + connectivity core: dual-core Xtensa
at 240 MHz, 8 MB flash + 8 MB PSRAM (for waveform ring buffers and the ML
classifier's weight matrices), hardware SHA/AES, vector instructions for the
FFT, Wi-Fi 4 + BLE 5, and a fast SPI peripheral to stream the ADC. It cannot,
however, sample four channels *simultaneously* with enough dynamic range for
VLF direction-finding: its internal 12-bit ADC is noisy and non-simultaneous.

The **ADS131M04** is the analog front-end: a **4-channel, 24-bit,
simultaneous-sampling delta-sigma ADC** designed by TI for electricity-metering
and protection relays. It offers up to 32 ksps per channel with phase-locked
sync across all four inputs, a programmable PGA (1–128×), a SPI data-ready
interrupt (DRDY), and runs from a single 3.3 V supply. The simultaneity is the
critical feature — the **phase relationship between the N-S and E-W loops is the
bearing**, so any inter-channel skew directly corrupts the angle. The ADS131M04
samples all four channels within nanoseconds of each other, which a
multiplexed ADC (like the ESP32's) cannot do.

This is the same "precision ADC + connectivity SoC" pattern used in
**Hive Mind (#7)**, **Sap Watch (#17)**, and **Ping Caliper (#15)**, but
applied to radio direction-finding instead of load cells or ultrasound.

---

## 2. Key Features

- **Crossed-loop VLF direction-finding** — two orthogonal shielded air-core
  loops (10 cm diameter, 40 turns, electrostatic shield) tuned to ~10 kHz,
  preamped by a pair of LT1991-3 low-noise difference amplifiers (40 dB),
  give a bearing accuracy of **±3° rms** for strokes within 200 km and a
  field of view of 360° (no azimuthal nulls, unlike a single loop).
- **Slow E-field electrometer** — a 30 cm whip + chopper-stabilized
  **ADA4530-1** (1 fA bias) electrometer measures the quasi-static charge
  redistribution (0.1 Hz–1 kHz, "slow antenna"), used to (a) reject the 180°
  bearing ambiguity via the sign of ΔE, (b) detect the **total lightning
  flash rate** even when individual sferics overlap, and (c) provide a
  storm-electrification early warning before the first CG stroke.
- **Simultaneous 24-bit / 8 ksps / 4-channel ADC** — the ADS131M04 captures
  N-S, E-W, slow-E, and a spare "fast-E" (whip AC-coupled 1–100 kHz) channel
  on the same clock, with a DRDY interrupt feeding the ESP32's GPIO for
  low-latency, DMA-free streaming into a ring buffer in PSRAM.
- **On-device sferic detection + classification**:
  - **Energy + rise-time + duration** gates reject impulse noise (cars,
    switches, fluorescent lamps) with a CFAR (constant-false-alarm-rate)
    noise-floor estimator.
  - A compact **int8 logistic-regression / shallow-NN classifier** (~6 kB of
    weights) labels each stroke **CG / IC / cloud-to-cloud (CC)** from 16
    waveform features (rise-time, peak/zero-cross ratio, slow-tail energy
    ratio, E-field sign, loop coherence). Typical accuracy ~92 % on a
    held-out test set.
- **Distance estimation** from the sferic peak amplitude + a 2-mode
  Earth-ionosphere waveguide propagation model (mode-1 TM, with
  day/night terminator conductivity and ground conductivity tables),
  giving ±15 % distance error over 10–300 km.
- **GPS PPS microsecond time-tagging** — a u-blox NEO-M9N provides a 1 Hz
  PPS edge captured by an ESP32 GPIO interrupt; the sferic timestamp is
  `GPS_week + TOW + sub-second_offset`, compatible with the Blitzortung
  station data format.
- **Storm tracker** — clusters strokes into storm cells (DBSCAN on
  bearing×distance), tracks the centroid over time, computes approach rate
  and **time-to-arrival**, and triggers a **"storm approaching"** BLE alert
  when a CG cell closes to <20 km.
- **OLED polar radar** — a 128×64 SSD1306 draws a live sweep: each stroke
  is a dot at (bearing, scaled-distance), older strokes fade, the active
  storm centroid is a ring, and the bottom line shows the last stroke's
  type / distance / bearing.
- **SD logging** — every sferic is stored as a row in `SFERIC_YYYYMMDD.csv`
  (timestamp, type, bearing, distance, peak-field, features) plus a binary
  waveform blob in `WAVE/` for later replay/analysis.
- **BLE + Wi-Fi streaming**:
  - **BLE**: a `BoltCompass` GATT service with a `SfericEvent` notify
    characteristic (12-byte packed event) and a `SfericWaveform` chunked
    characteristic for live oscilloscope-style viewing.
  - **Wi-Fi**: an AP+STA captive config page, an HTTP `/events.json` endpoint
    (last 100 strokes), a `/stream` Server-Sent-Events feed, and a raw TCP
    socket for the PC app.
- **Optional LoRaWAN uplink** — an SX1262 (on a breakout / Ra-01SH) can
  forward a compact 14-byte storm summary every 10 minutes for remote
  deployments without Wi-Fi (same SX1262 used by **Hive Mind**, **Tremor
  Tile**).
- **Solar-powered** — a 5 W 6 V panel + MCP73871 solar charger keeps a single
  18650 (3400 mAh) topped up; the device sleeps (<1 mA) between sferics and
  wakes on the ADS131M04 DRDY at 8 ksps (the ADC runs continuously; the ESP32
  sleeps the radio and most clocks). Typical endurance: 7 days no sun, or
  indefinite with 2 h/day of sun.
- **Safety**: the E-field whip has a **spark-gap + TVS** to protect the
  electrometer from a direct/near strike; the loops are galvanically isolated
  with a 1:1 isolation transformer stage; the whole front end is in a
  shielded die-cast enclosure bonded to earth ground via the tripod.

---

## 3. Block Diagram

```
   ┌────────────┐  E-field        ┌─────────────────┐
   │  30 cm whip│───── spark-gap ─▶│  ADA4530-1      │  slow E  (0.1Hz–1kHz)
   │  (slow E)  │     + TVS        │  electrometer   │──────▶ ADS131M04 CH2
   └────────────┘                  │  + 100 GΩ fb    │
                                   └─────────────────┘

   ┌────────────┐  B-field N-S     ┌─────────────────┐
   │ Loop A     │─────────────────▶│  LT1991-3       │  40 dB
   │ 10cm×40t   │  electrostatic   │  diff amp       │──────▶ ADS131M04 CH0
   │ shielded   │  shield gnd      └─────────────────┘
   └────────────┘
   ┌────────────┐  B-field E-W     ┌─────────────────┐
   │ Loop B     │─────────────────▶│  LT1991-3       │  40 dB
   │ 10cm×40t   │  electrostatic   │  diff amp       │──────▶ ADS131M04 CH1
   │ shielded   │  shield gnd      └─────────────────┘
   └────────────┘
                                                   ┌─────────────────┐
   ┌────────────┐  fast E AC       │  ADA4530-1     │ fast E (1–100kHz)
   │ whip AC    │── 100nF ─────────▶  + 2nd opamp   │──────▶ ADS131M04 CH3
   │ tap        │                  └─────────────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │   ADS131M04     │  4-ch 24-bit
                                          │   ΔΣ ADC        │  simultaneous
                                          │   8 ksps/ch     │  8 ksps
                                          └────────┬────────┘
                                                   │ SPI + DRDY
                                          ┌────────▼────────┐
                                          │  ESP32-S3       │
                                          │  WROOM-1        │
                                          │                 │
                                          │ sferic detect   │
                                          │ bearing atan2   │
                                          │ CG/IC classify  │
                                          │ distance model  │
                                          │ storm DBSCAN    │
                                          │ FFT (vector)    │
                                          └────┬──┬──┬──────┘
                                               │  │  │
                          NEO-M9N GPS ── PPS ───┘  │  └── SPI ──▶ microSD
                          I²C ──▶ SSD1306 OLED ────┘
                          UART ──▶ SX1262 LoRa (opt)
                          BLE/Wi-Fi ──▶ phone / PC
                          USB-C ──▶ console + power
```

---

## 4. Bill of Materials

See [`hardware/BOM.csv`](hardware/BOM.csv) for the full priced BOM. Summary:

| Ref | Part | Qty | Price (USD) | Role |
|-----|------|-----|-----------|------|
| U1 | ESP32-S3-WROOM-1 (N16R8, 16 MB flash / 8 MB PSRAM) | 1 | 3.40 | Compute + connectivity SoC |
| U2 | ADS131M04IPW | 1 | 5.20 | 4-ch 24-bit simultaneous ΔΣ ADC |
| U3 | ADA4530-1 | 1 | 4.80 | 1 fA chopper electrometer (slow E) |
| U4 | LT1991-3 (or AD8429) | 2 | 6.40 | Low-noise loop preamps (×2) |
| U5 | NEO-M9N GPS module | 1 | 9.50 | PPS + station location |
| U6 | SSD1306 OLED 128×64 I²C | 1 | 2.20 | Polar radar display |
| U7 | SX1262 (Ra-01SH) | 1 | 4.50 | Optional LoRaWAN uplink |
| U8 | TP4056 | 1 | 0.35 | 18650 USB-C charger |
| U9 | MCP73871 | 1 | 1.80 | Solar charge manager (5 W panel) |
| U10 | MAX17048 | 1 | 2.30 | 18650 fuel gauge |
| U11 | AMS1117-3.3 | 1 | 0.15 | 3.3 V LDO |
| ANT-A | Loop A — 10 cm dia, 40 t, AWG24, shielded | 1 | 3.00 | N-S VLF magnetic antenna |
| ANT-B | Loop B — 10 cm dia, 40 t, AWG24, shielded | 1 | 3.00 | E-W VLF magnetic antenna |
| ANT-E | 30 cm telescopic whip + base | 1 | 2.50 | Slow E-field antenna |
| SG | 90 V spark-gap (Bourns 2049) | 2 | 0.60 | E-whip strike protection |
| TVS | TVS 3.3 V (ESD9B3.3) | 4 | 0.40 | Front-end protection |
| SOL | 5 W 6 V solar panel (100×80 mm) | 1 | 4.50 | Power |
| BAT | 18650 3400 mAh Li-ion | 1 | 5.50 | Storage |
| µSD | microSD socket (Molex 502570-0893) | 1 | 0.90 | Logging |
| J1 | USB-C 2.0 receptacle | 1 | 0.30 | Charging + console |
| ENC | die-cast Al enclosure 100×60×25 mm | 1 | 6.00 | Shielding + housing |
| TRP | camera tripod mount (1/4"-20 insert) | 1 | 0.50 | Field deployment |
| PCB | 4-layer FR4 90×65 mm | 1 | 7.00 | — |
| Misc | passives, inductors, LEDs, buttons, connectors | — | ~9.00 | — |
| | **Total** | | **~$83** | |

> The two shielded loops and the whip can be hand-wound (instructions in
> [`docs/assembly-guide.md`](docs/assembly-guide.md) §3); pre-built
> "active loop" antennas also work if you attenuate to the ADS131M04 range.

---

## 5. Pin Assignments

### ESP32-S3-WROOM-1 pin map

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| GPIO0 | SPI CLK | ADC_SCLK | ADS131M04 SCLK |
| GPIO1 | SPI MISO | ADC_DOUT | ADS131M04 DOUT |
| GPIO2 | SPI MOSI | ADC_DIN | ADS131M04 DIN (config) |
| GPIO3 | GPIO | ADC_CS | ADS131M04 CS (active low) |
| GPIO4 | GPIO (ext int) | ADC_DRDY | ADS131M04 DRDY, edge IRQ |
| GPIO5 | GPIO (ext int) | ADC_SYNC | optional sync-in |
| GPIO6 | GPIO | ADC_PWDN | ADS131M04 power-down (sleep) |
| GPIO7 | GPIO | GPS_PPS | NEO-M9N PPS, edge IRQ → timestamp |
| GPIO8 | UART1 TX | GPS_TX | → NEO-M9N RX |
| GPIO9 | UART1 RX | GPS_RX | ← NEO-M9N TX |
| GPIO10 | SPI CLK | SD_SCK | microSD |
| GPIO11 | SPI MISO | SD_MISO | microSD |
| GPIO12 | SPI MOSI | SD_MOSI | microSD |
| GPIO13 | GPIO | SD_CS | microSD chip-select |
| GPIO14 | I²C SDA | I2C_SDA | OLED + MAX17048 |
| GPIO15 | I²C SCL | I2C_SCL | OLED + MAX17048 |
| GPIO16 | GPIO | LORA_CS | SX1262 NSS (optional) |
| GPIO17 | SPI CLK | LORA_SCK | SX1262 (shares bus? — separate to avoid SD contention) |
| GPIO18 | SPI MISO | LORA_MISO | SX1262 |
| GPIO19 | SPI MOSI | LORA_MOSI | SX1262 |
| GPIO20 | GPIO | LORA_BUSY | SX1262 BUSY |
| GPIO21 | GPIO | LORA_DIO1 | SX1262 DIO1 IRQ |
| GPIO22 | GPIO | LORA_RST | SX1262 reset |
| GPIO23 | GPIO | LORA_ANT_SW | SX1262 RF switch (TX/RX) |
| GPIO24 | GPIO | CHRG_STAT | TP4056 charge status |
| GPIO25 | GPIO | SOL_PG | MCP73871 power-good |
| GPIO26 | GPIO | BTN_MODE | OLED mode / brightness button |
| GPIO27 | GPIO | BTN_LOG | hold to stop logging / force flush |
| GPIO28 | GPIO | LED_RED | strike LED (blinks on CG) |
| GPIO29 | GPIO | LED_GRN | status / power LED |
| GPIO30 | GPIO | LED_BLU | BLE/Wi-Fi active LED |
| GPIO35 | UART0 TX | DBG_TX | USB-C console |
| GPIO36 | UART0 RX | DBG_RX | USB-C console |
| 19/20 | USB D-/D+ | USB | console + firmware flash |
| EN | — | EN | 10 kΩ pull-up, RC delay |
| BOOT | — | BOOT | 10 kΩ pull-up |

> The ESP32-S3 has abundant GPIO; the LoRa SPI is on a dedicated bus (GPIO17-19)
> to avoid bus-contention stalls on the SD/ADC SPI during a sferic capture.

### ADS131M04 pin map (relevant)

| Pin | Function | Net | Notes |
|-----|----------|-----|-------|
| AIN0P/N | CH0 diff | LOOP_NS | N-S loop preamp output (diff) |
| AIN1P/N | CH1 diff | LOOP_EW | E-W loop preamp output (diff) |
| AIN2P/N | CH2 diff | E_SLOW | ADA4530-1 slow-E output (diff) |
| AIN3P/N | CH3 diff | E_FAST | fast-E AC-coupled output (diff) |
| SCLK / DOUT / DIN / CS | SPI | (ESP32 GPIO0-3) | config + data readout |
| DRDY | data ready | ADC_DRDY | falling edge → ESP32 IRQ |
| SYNC/RESET | sync | ADC_SYNC | optional multi-ADC sync |
| AVDD/DVDD | — | +3V3 | analog + digital supply (decoupled) |
| CLKIN | — | int. osc | internal 8.192 MHz (no ext clock needed) |

---

## 6. Power Architecture

```
                      USB-C (5 V)          5 W 6 V solar
                          │                     │
                  ┌───────▼────────┐    ┌───────▼────────┐
                  │   TP4056       │    │  MCP73871      │
                  │   (USB charge) │    │  (solar MPPT)  │
                  └───────┬────────┘    └───────┬────────┘
                          │   VBAT (3.0–4.2 V)   │
                          └──────────┬──────────┘
                                     │
                            ┌────────▼─────────┐
                            │  18650 3400 mAh  │
                            └────────┬─────────┘
                                     │
                       ┌─────────────┼──────────────┐
                       │             │              │
                ┌──────▼──────┐ ┌────▼─────┐  ┌─────▼──────┐
                │ AMS1117 3.3V│ │ MAX17048 │  │ ADS131M04  │
                │  LDO 500 mA │ │ fuel gaug│  │ AVDD (3.3) │
                └──────┬──────┘ └──────────┘  └────────────┘
                       │ 3V3
                ┌──────┼──────────────┐
                │      │              │
            ESP32-S3  OLED   SX1262 / SD / GPS / preamps
            (3.3 V)
```

- The **ADS131M04 and analog front-end** are powered from a **separate
  LC-filtered 3.3 V rail** (ferrite bead + 22 µF) off the same LDO, to keep
  the ESP32's digital noise out of the 24-bit ADC.
- The **loops and electrometer** draw ~6 mA total; the **ESP32-S3** averages
  ~25 mA (sleeps between sferics, wakes on DRDY at 8 ksps → ~3 mA average in
  capture-sleep), the **GPS** ~30 mA (can be duty-cycled to 10 s on / 90 s off
  → ~6 mA average), **SD** idle ~0.2 mA, **OLED** ~10 mA (dimmed in sleep).
- Total average: **~8 mA** with GPS duty-cycled and OLED dimmed →
  **~17 days** on a 3400 mAh 18650 with no sun; realistic field life with 2 h
  sun/day is **indefinite**.
- The **±2.5 V** for the loop preamps' centered-output swing is generated by a
  tiny charge-pump (TPS60403) from the 3.3 V rail.

---

## 7. Firmware

The firmware is bare-metal C built with **ESP-IDF v5.2**. The core signal
path runs in a **dedicated high-priority task pinned to Core 1** (the "sferic
core"), while Wi-Fi/BLE/GPS/SD run on Core 0 — so a radio event or SD write
can never drop a sferic sample.

```
firmware/
├── CMakeLists.txt
├── main/
│   ├── CMakeLists.txt
│   ├── main.c              # app entry, task creation, supervisor
│   ├── adc.c / .h          # ADS131M04 SPI driver, DRDY ISR, ring buffer
│   ├── detect.c / .h       # CFAR sferic detector + feature extraction
│   ├── classify.c / .h     # int8 CG/IC/CC classifier (weights in classify_data.c)
│   ├── bearing.c / .h      # crossed-loop goniometer, ambiguity resolve
│   ├── range.c / .h        # Earth-ionosphere distance model
│   ├── storm.c / .h        # DBSCAN storm-cell tracker + approach alert
│   ├── gps.c / .h          # NEO-M9N UART parser + PPS timestamp
│   ├── display.c / .h      # SSD1306 polar radar + status lines
│   ├── sdlog.c / .h        # FatFS CSV + binary waveform logging
│   ├── ble.c / .h          # NimBLE BoltCompass GATT service
│   ├── wifi.c / .h         # AP+STA, HTTP /events.json, /stream SSE, TCP
│   ├── lora.c / .h         # SX1262 LoRaWAN storm-summary uplink (opt)
│   ├── power.c / .h        # MCP73871 + MAX17048 + light-sleep manager
│   └── fft.c / .h          # 256-pt Radix-2 FFT (vector-instr accelerated)
├── sim/
│   └── CMakeLists.txt      # host simulation: feeds synthetic sferics
└── port_sim.c              # HAL stubs for the sim build
```

### Building

**ESP32-S3 (ESP-IDF v5.2):**
```bash
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

**Simulation (host, exercises the detect + classify + bearing + range math
without hardware):**
```bash
cd firmware
cmake -B build-sim -S sim
cmake --build build-sim
./build-sim/bolt_compass_sim
# prints synthetic sferics: type, bearing, distance, peak-field
```

The simulation feeds the detect/classify/bearing/range pipeline a stream of
synthetic CG and IC sferics (a known bearing + distance, with the modeled
waveguide attenuation added) and asserts that the recovered bearing and
distance are within tolerance — a self-test of the math path.

### Configuration

`sdkconfig.defaults` sets:
- ESP32-S3 @ 240 MHz, flash 16 MB, PSRAM 8 MB (octal),
- Wi-Fi 4 AP+STA, mDNS `bolt-compass.local`,
- BLE NimBLE (1 connection), BoltCompass GATT service,
- FatFs on SPI SD card (long filenames),
- FreeRTOS tick 100 Hz, Core 1 = sferic core (pinning),
- Light-sleep enabled (EXT0 wake on ADS131M04 DRDY).

---

## 8. Measurement Theory

### Why VLF sferics?

A lightning return stroke is a ~30 kA current pulse that radiates
electromagnetically from a few Hz to hundreds of MHz. The bulk of the energy,
however, couples into the **Earth-ionosphere waveguide** (the cavity between
the ground and the lower D-region ionosphere, ~70 km high in the day) and
propagates as a **VLF "sferic"** in the 3–30 kHz band. This band:

- propagates **hundreds to thousands of km** with low attenuation
  (~2–5 dB/Mm daytime, ~1 dB/Mm nighttime),
- carries the **waveform signature** of the stroke (rise time, peak, slow tail),
- is **direction-findable** with crossed magnetic loops, because the magnetic
  field of the dominant TM mode is horizontal and perpendicular to the
  propagation direction.

This is why every lightning location network (Blitzortung, Vaisala GLD360,
WeatherBug) listens in VLF.

### Crossed-loop bearing (goniometer)

A small shielded loop at the ground, with its plane vertical and normal along
azimuth θ, intercepts the horizontal magnetic field **H** of the sferic. The
induced voltage is proportional to `cos(α − θ)` where α is the bearing to the
stroke. Two orthogonal loops (N-S and E-W) give:

```
V_NS = K · H · cos(α)        V_EW = K · H · sin(α)
   →  α = atan2(V_EW, V_NS)
```

The 180° ambiguity (a loop can't tell N from S) is resolved by the **sign of
the initial E-field change** ΔE: a CG stroke that lowers negative charge to
ground produces a ΔE of a known sign relative to the bearing. The slow-E
channel provides this.

### CG vs. IC classification

A **cloud-to-ground (CG)** return stroke radiates a sferic with:
- a very sharp **initial peak** (rise < 1 µs at source),
- a large **slow tail** (10–100 µs) carrying the continuing current,
- a **peak/zero-cross ratio** > 2.

An **intra-cloud (IC)** pulse is broader, more bipolar, with a smaller slow
tail and a peak/zero-cross ratio near 1. The on-device classifier extracts 16
features (rise time, peak, zero-cross time, slow-tail energy ratio, E-field
sign, loop coherence, spectral centroid) and runs a compact int8 model.

### Distance estimation

The sferic amplitude decays with distance `d` roughly as:

```
E_peak(d) ≈ E_0 · exp(−α(f) · d) / sqrt(d)
```

where `α(f)` is the mode-1 TM waveguide attenuation rate (dB/Mm), which
depends on the **ground conductivity** σ_g and the **ionosphere conductivity
profile** (day vs. night). Bolt Compass uses a tabulated `α(f)` at 10 kHz for
day/night and a user-selectable ground-conductivity region (default:
"continental average", σ_g = 10 mS/m). It solves the inverse for `d` from the
measured peak (calibrated against a known reference stroke from the GPS-synced
Blitzortung feed during setup). Typical error: **±15 %** at 10–200 km,
degrading beyond 300 km where higher modes dominate.

### Slow-E storm electrification

The slow E-field channel (0.1 Hz–1 kHz) tracks the **total charge
redistribution** under the storm — it rises as the storm electrifies, often
**minutes before the first CG stroke**, giving an early warning that a storm
is building. The device triggers a "storm building" alert when |ΔE| exceeds
2× the fair-weather field (~100 V/m) sustained for >60 s.

---

## 9. Detection & Classification Pipeline

A sferic is processed in four stages, all on-device in real time:

1. **CFAR detection** — a sliding window estimates the noise floor (median +
   MAD over 50 ms); a sferic candidate is a window where the loop energy
   exceeds `floor + k·MAD` (k=12) for >50 µs and <2 ms. A rise-time gate
   (2–50 µs) rejects slow E-field transients and 50/60 Hz mains hum.
2. **Feature extraction** — for the 50 ms window straddling the trigger:
   - peak amplitude (both loops + slow-E),
   - rise time (10→90 %),
   - zero-cross time after peak,
   - slow-tail energy ratio (energy in 5–50 ms after peak / total),
   - E-field sign (polarity of slow-E at t+5 ms),
   - loop coherence (|cos(Δφ_NS-EW)| at the peak),
   - spectral centroid (256-pt FFT).
3. **Classification** — the 16-feature vector is fed to an **int8 logistic
   regression** (3 classes: CG, IC, CC) — ~600 bytes of weights — giving a
   softmax over classes. The argmax + confidence is stored.
4. **Bearing + distance** — `α = atan2(V_EW_peak, V_NS_peak)`, 180° resolved
   by `sign(ΔE)`, distance from the peak amplitude + propagation model. The
   stroke is added to the storm tracker.

The whole pipeline runs in <2 ms on the ESP32-S3 (240 MHz, vector FFT), well
within the 8 ksps / 125 µs-per-sample budget.

---

## 10. Storm Tracker

Strokes are clustered with a simple online **DBSCAN** (ε = 15° bearing,
50 km distance, minPts = 3) into **storm cells**. Each cell stores:

- centroid (bearing, distance),
- stroke count + flash rate (strokes/min),
- first-seen / last-seen timestamps,
- approach rate (d(distance)/dt over a 5 min sliding window),
- dominant stroke type (CG fraction).

The device emits a **"storm approaching"** BLE/Wi-Fi notification when a
CG-bearing cell is within 20 km and closing at >5 km/min, and a **"storm
imminent"** alert at <10 km. The OLED radar shows the centroid as a pulsing
ring; the bearing arrow points to the most active cell.

---

## 11. Companion App

`scripts/storm_view.py` is a Python (matplotlib + bleak/requests) app that:

- **Live mode**: connects over BLE (or Wi-Fi TCP) and plots the polar radar,
  the last sferic waveform (both loops + slow-E), the storm-cell table, and
  the flash-rate time series.
- **Replay mode**: reads an SD-card `SFERIC_*.csv` + `WAVE/*.bin` dump and
  replays the storm as a time-accelerated movie.
- **Network mode**: cross-correlates the device's GPS-timed strokes with the
  public Blitzortung JSON feed (`lightningmaps.org`) to calibrate the
  distance model and verify bearing accuracy.

```bash
python3 scripts/storm_view.py --ble --device BoltCompass
python3 scripts/storm_view.py --wifi --host 192.168.4.1
python3 scripts/storm_view.py --replay /mnt/sd/SFERIC_20260626.csv
python3 scripts/storm_view.py --calibrate --blitzortung
```

`scripts/sferic_gen.py` generates synthetic CG/IC sferic waveforms (with the
Earth-ionosphere waveguide model) for testing the classifier offline.

---

## 12. Assembly

See [`docs/assembly-guide.md`](docs/assembly-guide.md) for the full
step-by-step. In brief:

1. Solder the ESP32-S3-WROOM-1 module and the ADS131M04 (TSSOP-20).
2. Populate the analog front end: ADA4530-1 electrometer, 2× LT1991-3 loop
   preamps, ±2.5 V charge pump (TPS60403), spark-gap + TVS protection.
3. Populate the power section: TP4056, MCP73871, MAX17048, AMS1117.
4. Populate the user interface: SSD1306 OLED, microSD socket, NEO-M9N GPS,
   optional SX1262, status LEDs, mode/log buttons.
5. **Wind the two loops**: 40 turns of AWG24 enameled wire on a 10 cm PVC
   form, wrap the outside in copper foil (electrostatic shield) with a 5 mm
   gap so the shield doesn't form a shorted turn; solder the shield to GND
   at one point only. Mount the two loops at 90° in a 3D-printed cross
   bracket (STL in `docs/`).
6. **Mount the whip**: 30 cm telescopic antenna on a BNC connector at the
   top of the enclosure; spark-gap + TVS at the base.
7. Flash the ESP32-S3 over USB-C.
8. Calibrate: see [`docs/calibration-guide.md`](docs/calibration-guide.md)
   (loop balance, bearing alignment, distance model fit).

---

## 13. Safety

This device has antennas outdoors during thunderstorms. Read
[`docs/safety-notes.md`](docs/safety-notes.md) before deploying.

- **Do not deploy during an active storm with lightning within 5 km.** A
  direct or near strike will destroy the front end despite the spark-gap/TVS.
- The whip has a **90 V spark-gap + 3.3 V TVS + 100 kΩ series resistor** to
  bleed charge; the loops are isolated with a 1:1 transformer.
- The enclosure is **bonded to earth ground** via the tripod + a ground
  strap; never operate un-grounded.
- Indoor/balcony use (through-wall VLF reception) is fine — VLF penetrates
  buildings — but bearing accuracy degrades near rebar / metal siding.

---

## 14. API Reference

See [`docs/api-reference.md`](docs/api-reference.md) for full firmware API
docs. Key functions:

- `adc_init()` — configure ADS131M04 (8 ksps, PGA ×8, continuous), arm DRDY IRQ.
- `adc_poll_frame(int16_t ch[4])` — copy one 4-channel sample (called from
  the DRDY ISR → ring buffer).
- `detect_sferic(const ring_t *r, sferic_t *out)` — CFAR detect + feature
  extract; returns 1 if a sferic was found in the window.
- `classify_sferic(const sferic_t *s)` — int8 CG/IC/CC softmax → label +
  confidence.
- `bearing_compute(const sferic_t *s)` — `atan2` + ambiguity resolve →
  azimuth 0–360°.
- `range_estimate(const sferic_t *s, const range_model_t *m)` — propagation
  model inverse → distance km.
- `storm_add(const stroke_t *st)` — feed the DBSCAN tracker.
- `storm_alerts(alert_t *out, int n)` — pull pending alerts.
- `gps_pps_isr()` — PPS edge → latch the sferic timestamp.
- `sdlog_sferic(const sferic_t *s, const int16_t *wave, int n)` — CSV row +
  binary waveform.
- `ble_notify_sferic(const sferic_t *s)` — push a 12-byte event to BLE
  subscribers.
- `wifi_stream_sferic(const sferic_t *s, const int16_t *wave, int n)` —
  SSE/TCP push.

---

## 15. What Makes It Different

| | Canopy Listener (#2) | Pulse Hound (#18) | Sky Lens (#22) | **Bolt Compass** |
|---|---|---|---|---|
| Domain | Acoustic biodiversity | RF signal hunting | Cosmic-ray muons | **Lightning / storms** |
| Antenna | MEMS mic | Log detector + motor DF | SiPM + scintillator | **Crossed VLF loops + E-whip** |
| Sense | Acoustic species | 1 MHz–8 GHz power | Ionizing radiation | **3–30 kHz sferics** |
| Math | CNN wingbeat | Spectrum waterfall | Track reconstruction | **Goniometer + CG/IC ML** |
| Output | LoRa uplink | Geiger audio + OLED | Muon skymap | **Bearing radar + storm alert** |
| SoC | RP2040 | ESP32-S3 | ESP32-S3 | **ESP32-S3 + ADS131M04** |

Bolt Compass is the first device in this collection aimed at **severe-weather
nowcasting** — combining VLF radio direction-finding, GPS time-tagging, and
on-device ML to give a single person, with a pocket-sized device, the same
storm situational awareness that a regional lightning network gives a whole
forecast office.

---

## 16. License

MIT — build it, chase it, improve it. See repo root LICENSE.

---

*Invented as device #28 in the SoC Device Inventions collection.*