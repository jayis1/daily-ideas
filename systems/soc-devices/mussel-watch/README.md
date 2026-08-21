# Mussel Watch

**A submersible biomonitoring sensor that clips onto a living bivalve mollusc (mussel or oyster), measures its valve-gape angle with a linear Hall-effect sensor and a magnet, and combines that with water temperature, dissolved oxygen, and depth — then uplinks everything over LoRa for biological early-warning water-quality monitoring. When the shell clams shut, something is wrong.**

---

## What It Does

The Mussel Watch is a low-power aquatic biosensor that exploits a remarkable biological fact: **bivalve molluscs (mussels, oysters, clams) keep their shells open to filter-feed when water conditions are good, and snap shut when they detect pollutants, sudden temperature spikes, or low dissolved oxygen.** By continuously measuring the gape angle of a sentinel mussel, the device turns a living organism into a real-time water-quality sensor — one that responds to a broader range of stressors (heavy metals, pesticides, pharmaceuticals, toxins, hypoxia) than any single chemical sensor could.

The device attaches a **linear Hall-effect sensor** to one valve of the mussel and a tiny **neodymium magnet** to the other. As the mussel opens and closes, the magnetic field at the sensor changes proportionally to the gape angle. The firmware converts the Hall voltage to a calibrated angle in degrees (0° = closed, ~15° = wide open), then runs anomaly detection on the gape time-series: sustained closure events, rapid closure rate, and deviation from the individual's circadian gape rhythm all trigger alerts.

Combined sensors provide context:

- **DS18B20** waterproof probe → water temperature (°C)
- **Atlas Scientific ENV-DO** dissolved oxygen probe → DO (mg/L & %sat)
- **MS5837-02BA** submersible pressure sensor → water depth (m) and barometric compensation
- **BME280** (in the above-water electronics pod) → barometric pressure for depth correction

The **nRF52840** SoC handles sensing, computation, and BLE (for on-site phone configuration), while a **Semtech SX1262** LoRa radio provides kilometre-range uplink to a gateway. A solar panel + LiPo battery enables months of unattended deployment in rivers, lakes, aquaculture pens, and wastewater discharge zones.

- **Biological gape sensing** — Texas Instruments **DRV5053** ratiometric linear Hall sensor (±90 mV range, 18 mV/mT sensitivity) on one valve, 2×2 mm N52 neodymium magnet on the opposing valve; 12-bit ADS1115 ADC digitizes the Hall voltage at 4 Hz
- **Gape-angle calibration** — on-device two-point calibration (closed + fully-open); magnet-sensor distance is computed via inverse-cube law and linearized to 0–15° with ±0.5° accuracy
- **Anomaly detection** — rolling 24-hour baseline of gape angle; closure event = gape drops below 2° for >30 s; stress alert = ≥3 closure events per hour or sustained closure >10 min; circadian rhythm deviation flagged when the normal feeding window gape is absent
- **Water-quality context** — DS18B20 water temp (±0.1 °C), Atlas DO probe (±0.1 mg/L, galvanic), MS5837 depth (±2 cm, 0–30 m), BME280 barometric (±1 hPa)
- **LoRaWAN uplink** — SX1262 at 868/915 MHz, SF7–SF12 adaptive data rate; 15-min telemetry by default, immediate alert on anomaly detection; AES-128 encrypted
- **BLE configuration** — nRF52840 BLE 5 for phone-based setup: calibration, deployment ID, alert thresholds, sampling interval
- **Solar + LiPo** — 2 W 5×5 cm marine-rated solar panel, MCP73871 charge controller, 2000 mAh LiPo; ~40-day autonomy without sun (15-min interval)
- **Marine-grade enclosure** — IP68 potting for the sensor head, above-water electronics pod with cable gland to submersible sensor; titanium Hall sensor mount for corrosion resistance
- **Multi-mussel expansion** — up to 4 gape-sensor heads on one node via I²C multiplexer (TCA9548A); each mussel gets its own DRV5053 + ADS1115 channel

### Why bivalves?

Bivalves are nature's canaries in the coal mine for water quality:

| Stressor | Mussel response | Chemical sensor alternative |
|----------|----------------|---------------------------|
| Heavy metals (Cu, Zn, Pb, Cd) | Valve closure within minutes | ICP-MS lab analysis ($50+/sample) |
| Pesticides / herbicides | Closure + reduced gape rhythm | GC-MS lab analysis ($80+/sample) |
| Hypoxia (low O₂) | Gradual closure over 10–30 min | DO probe (included, but narrow range) |
| pH shock | Rapid closure | pH probe (single parameter) |
| Ammonia / nitrite spike | Closure | Multiple ion-selective electrodes |
| Toxic algal bloom toxins | Closure + coughing (valve micro-movements) | Toxin lab test (days) |
| Thermal pollution | Closure above species threshold | Temperature sensor (included) |
| Pharmaceutical residues | Subtle rhythm disruption | LC-MS/MS ($200+/sample) |

A single Mussel Watch node detects all of the above simultaneously — biologically integrated, real-time, and continuous. This is the principle behind the EU's *Mussel Monitor* and biomonitoring programs worldwide, now miniaturized into a sub-$90 SoC device.

### Use Cases

| Application | How Mussel Watch Helps |
|-----------|----------------------|
| Aquaculture farm monitoring | Early warning of water-quality events before they kill the stock; mussels are the farmed crop *and* the sensor |
| Wastewater discharge compliance | Deploy upstream and downstream of outfall; closure events flag non-compliant discharges in real time |
| Drinking water intake protection | Sentinel array at intake; alert if mussels close (possible contamination) |
| River / lake ecological monitoring | Long-term gape rhythm = ecosystem health indicator; LoRa uplink = no site visits needed |
| Marine protected areas | Underwater deployment with depth sensor; solar surface buoy for power |
| Research / citizen science | Affordable biomonitor for university ecology labs; BLE config + SD log for field studies |
| Industrial spill detection | Detect unplanned chemical discharges into waterways before they spread |
| Hurricane / flood water quality | Reusable, low-cost, deployable pre-storm |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              MUSSEL WATCH NODE                                    │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────┐           │
│   │        nRF52840 (QFAA, Raytac MDBT50Q module)                     │           │
│   │   (ARM Cortex-M4F 64 MHz, 1 MB flash, 256 KB RAM, BLE 5)         │           │
│   │                                                                  │           │
│   │   ┌──────────────────────────────────────────┐                   │           │
│   │   │ Gape sensing task (4 Hz)                 │◄──────┐           │           │
│   │   │ (ADS1115 sample → Hall mV → angle)       │       │           │           │
│   │   ├──────────────────────────────────────────┤       │           │           │
│   │   │ Anomaly detection (closure events,       │       │           │           │
│   │   │  rhythm deviation, stress scoring)       │       │           │           │
│   │   ├──────────────────────────────────────────┤       │           │           │
│   │   │ Water-quality context                    │       │           │           │
│   │   │ (DS18B20 temp, DO probe, MS5837 depth)    │       │           │           │
│   │   ├──────────────────────────────────────────┤       │           │           │
│   │   │ LoRa uplink (SX1262 SPI)                  │       │           │           │
│   │   │ (15-min telemetry + immediate alerts)    │───────┼──────────┼──► SX1262  │
│   │   ├──────────────────────────────────────────┤       │           │  LoRa      │
│   │   │ BLE config (nRF radio, SoftDevice)        │       │           │  868/915   │
│   │   ├──────────────────────────────────────────┤       │           │  MHz       │
│   │   │ SD card logger (FAT32, SPI)               │       │           │            │
│   │   ├──────────────────────────────────────────┤       │           │            │
│   │   │ Power management (solar + LiPo)          │       │           │            │
│   │   └──────────────────────────────────────────┘       │           │            │
│   │                                  │                   │           │            │
│   └──────────────────────────────────┼───────────────────┘           │            │
│   │           I²C                    │ SPI               │            │            │
│   │           │                      │                   │            │            │
│   │   ┌───────▼──────────┐  ┌─────────▼──┐  ┌────────────▼────┐  ┌────▼─────────┐  │
│   │   │ TCA9548A mux     │  │ microSD    │  │   SX1262       │  │ BME280      │  │
│   │   │ (4-ch gape)      │  │ (FAT32 log)│  │   LoRa radio   │  │ barometric  │  │
│   │   └───────┬──────────┘  └────────────┘  └────────────────┘  │ (air pod)  │  │
│   │           │                                              └─────────────┘  │
│   │   ┌───────▼──────────────────────────────────────┐                           │
│   │   │  Ch0: ADS1115 + DRV5053 #1 (Mussel A)       │                           │
│   │   │  Ch1: ADS1115 + DRV5053 #2 (Mussel B)       │                           │
│   │   │  Ch2: ADS1115 + DRV5053 #3 (Mussel C)       │                           │
│   │   │  Ch3: ADS1115 + DRV5053 #4 (Mussel D)       │                           │
│   │   └────────────────────────────────────────────┘                           │
│   │                                                                            │
│   │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│   │   │ DS18B20      │   │ Atlas DO     │   │ MS5837-02BA  │                   │
│   │   │ water temp   │   │ galvanic O₂  │   │ depth+temp    │                   │
│   │   │ (1-Wire)     │   │ (I²C EZO)    │   │ (I²C)        │                   │
│   │   └──────────────┘   └──────────────┘   └──────────────┘                   │
│   │                                                                            │
│   │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│   │   │ MCP73871     │   │ 2 W solar    │   │ 2000 mAh     │                   │
│   │   │ charge ctrl  │◄──┤ panel (IP67) │   │ LiPo        │                   │
│   │   └──────┬───────┘   └──────────────┘   └──────┬───────┘                   │
│   │          │ nRF SAADC (battery V)              │                           │
│   └──────────┼────────────────────────────────────┘                           │
│   │          │                                                                │
│   │     BLE   │              LoRa (SX1262)                                      │
│   │          ▼                 ▼                                               │
│   │   ┌──────────────┐   ┌──────────────────┐                                 │
│   │   │ Phone        │   │ Gateway / TTN    │                                 │
│   │   │ (config app) │   │ (cloud dashboard)│                                │
│   │   └──────────────┘   └──────────────────┘                                 │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐  ┌─────────────────────────────────────────┐
│   SUBMERSIBLE SENSOR HEAD   │  │     ABOVE-WATER ELECTRONICS POD          │
│   (IP68 potted, titanium)   │  │     (IP67, floats / pole-mounted)        │
│                             │  │                                           │
│  DRV5053 Hall ─── magnet     │  │  nRF52840  │ SX1262  │ SD card           │
│  (valve A)      (valve B)    │  │  BME280    │ MCP73871│ BLE antenna       │
│                             │  │  LiPo      │ solar panel connector        │
│  ADS1115 ADC (I²C)          │  │                                           │
│  DS18B20 temp probe         │  │  ← 4-conductor cable to sensor head →    │
│  MS5837 depth+temp          │  │     (I²C + 1-Wire + VCC + GND)            │
│  Atlas DO probe             │  └─────────────────────────────────────────┘
│                             │
│  ─── mussel shell ───        │
└─────────────────────────────┘
```

---

## Hardware Design

### SoC: nRF52840

| Parameter | Value |
|-----------|-------|
| Core | ARM Cortex-M4F @ 64 MHz |
| Flash | 1 MB |
| RAM | 256 KB |
| Radio | BLE 5 + IEEE 802.15.4 |
| ADC | 12-bit SAADC (8 channels) |
| GPIO | 31 usable |
| Supply | 1.7–3.6 V |
| Sleep current | 1.5 µA (System OFF) |
| Module | Raytac MDBT50Q-1M (pre-certified) |

The nRF52840 is chosen for its ultra-low sleep current (critical for solar deployment), integrated BLE 5 for on-site phone configuration, and abundant GPIO/I²C/SPI peripherals. The Raytac MDBT50Q module provides pre-certified BLE + FCC/CE, avoiding antenna design headaches.

### Secondary radio: Semtech SX1262

The SX1262 is a sub-GHz LoRa transceiver (150–960 MHz, up to +22 dBm) used for long-range uplink. It communicates over SPI and handles LoRa modulation, frequency hopping, and AES encryption. Range: 2–15 km line-of-sight, 200–800 m in water-adjacent environments.

### Gape Sensor Principle

```
           magnet (N52, 2×2×1 mm)
           glued to valve B
                │
                ▼  ─── magnetic field ───
               ╲╲╲╲╲
              ╱╱╱╱╱╱
             ╱╱╱╱╱╱
            ─────────── valve B (mobile)
           │           │
           │   open    │ ← gape angle θ (0–15°)
           │           │
            ─────────── valve A (fixed, sensor)
                ▲
           DRV5053 Hall sensor
           glued to valve A
```

As the mussel opens, the magnet moves away from the Hall sensor. The DRV5053 produces a ratiometric voltage proportional to the magnetic flux density B, which falls off approximately as 1/r³ for a dipole. The ADS1115 samples this at 16-bit resolution (gain PGA = ±2.048 V), and the firmware converts:

1. Raw ADC counts → Hall voltage V_H (mV)
2. V_H → magnetic flux B (mT) using DRV5053 sensitivity (18 mV/mT at Vcc=3.3V)
3. B → magnet-sensor distance r (mm) via B = Br × (V_mag / (4π × r³)) inverse model
4. r → gape angle θ via the geometric relationship r = r₀ + L × sin(θ), where r₀ is the closed distance and L is the lever arm

Two-point calibration (closed + fully-open) eliminates the need to know Br, V_mag, or L precisely — the firmware just linearly interpolates between the two calibration endpoints.

### Pin Assignments

| Pin | nRF GPIO | Function | Direction | Notes |
|-----|----------|----------|-----------|-------|
| J1  | P0.03    | I²C SDA  | Bidir     | TCA9548A, ADS1115×4, MS5837, Atlas DO, BME280 |
| J2  | P0.04    | I²C SCL  | Output    | 4.7k pull-ups to 3.3V |
| J3  | P0.28    | SPI MISO | Input     | SX1262 + SD card (shared bus with CS) |
| J4  | P0.29    | SPI MOSI | Output    | SX1262 + SD card |
| J5  | P0.30    | SPI SCK  | Output    | SX1262 + SD card |
| J6  | P0.31    | SX1262 CS| Output    | LoRa radio CS (active low) |
| J7  | P0.26    | SD CS    | Output    | SD card CS (active low) |
| J8  | P0.24    | SX1262 DIO1 | Input  | LoRa IRQ (RX done / TX done) |
| J9  | P0.25    | SX1262 NRST | Output | LoRa reset |
| J10 | P0.02    | 1-Wire  | Bidir     | DS18B20 water temp (4.7k pull-up) |
| J11 | P0.05    | SAADC   | Input     | Battery voltage (÷2 divider) |
| J12 | P0.06    | SAADC   | Input     | Solar panel voltage (÷2 divider) |
| J13 | P0.07    | GPIO    | Output    | SX1262 TCXO enable (3.3V TCXO) |
| J14 | P0.08    | GPIO    | Output    | Sensor head power enable (load switch) |
| J15 | P0.09    | GPIO    | Input     | Mode button (config/calibrate) |
| J16 | P0.10    | GPIO    | Output    | Status LED (blue) |
| J17 | P0.11    | GPIO    | Output    | Status LED (red, alert) |
| J18 | P0.12    | GPIO    | Output    | TCA9548A reset (active low) |
| J19 | P0.15    | GPIO    | Output    | SD card power (load switch) |
| J20 | P0.16    | GPIO    | Output    | Atlas DO probe power (load switch) |

### Power Architecture

```
                    ┌─────────────┐
                    │ 2 W solar   │
                    │ panel (6 V) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ MCP73871    │     ┌──────────────┐
                    │ charge ctrl │─────┤ 2000 mAh     │
                    │ (Li-ion)    │     │ LiPo 3.7V    │
                    └──────┬──────┘     └──────┬───────┘
                           │                   │
                           ├─── VBUS (5V)      │
                           │                   │
                    ┌──────▼───────────────────▼──┐
                    │    3.3V LDO (TPL9102)      │
                    │    (200 mA, 1 µA Iq)       │
                    └──────────┬────────────────┘
                               │ 3.3V
                    ┌──────────┼──────────────────────┐
                    │          │                       │
               nRF52840   SX1262 (3.3V)          All sensors
               (3.3V)     SD card (3.3V)          (3.3V / 5V DO)
```

**Power budget (15-min interval, 4 Hz gape sampling):**

| State | Current | Duration / cycle | Energy / cycle |
|-------|---------|-----------------|----------------|
| Active sensing (4 s) | 8 mA | 4 s | 32 mAs |
| LoRa TX (1 s, +14 dBm) | 25 mA | 1 s | 25 mAs |
| SD write (10 ms) | 12 mA | 10 ms | 0.12 mAs |
| Sleep (between samples) | 15 µA | 896 s | 13.4 mAs |
| **Total / 15-min cycle** | | | **70.5 mAs** |

Daily consumption: 70.5 × 96 = 6768 mAs = **~1.88 mAh/day**

2000 mAh LiPo → **~1063 days** (no solar) — solar tops up during the day, enabling perpetual operation.

### Sensor Summary

| Sensor | Interface | Parameter | Range | Accuracy |
|--------|-----------|-----------|-------|----------|
| DRV5053 + ADS1115 ×4 | I²C (via TCA9548A) | Gape angle | 0–15° | ±0.5° |
| DS18B20 (waterproof) | 1-Wire | Water temp | −10 to +85 °C | ±0.1 °C |
| Atlas Scientific DO | I²C (EZO) | Dissolved O₂ | 0–20 mg/L | ±0.1 mg/L |
| MS5837-02BA | I²C | Depth + temp | 0–30 m, −5 to +65 °C | ±2 cm, ±0.5 °C |
| BME280 | I²C | Barometric pressure | 300–1100 hPa | ±1 hPa |
| SAADC (internal) | ADC | Battery voltage | 0–4.2 V (÷2) | ±0.05 V |
| SAADC (internal) | ADC | Solar voltage | 0–6 V (÷2) | ±0.05 V |

---

## Firmware

The firmware is written in portable C targeting the nRF5 SDK / nRF Connect SDK. It uses a cooperative super-loop scheduler (no RTOS dependency for portability) with the nRF SoftDevice for BLE.

### Source files

| File | Purpose |
|------|---------|
| `config.h` | Pin assignments, I²C addresses, constants |
| `main.c` | Application entry, scheduler loop, state machine |
| `gape_sensor.c/.h` | ADS1115 + DRV5053 driver, angle conversion, calibration |
| `water_quality.c/.h` | DS18B20, MS5837, Atlas DO, BME280 drivers |
| `anomaly.c/.h` | Closure-event detection, rhythm analysis, stress scoring |
| `lora_uplink.c/.h` | SX1262 driver, LoRaWAN packet format, AES-128 |
| `ble_config.c/.h` | BLE GATT service for phone configuration |
| `logger.c/.h` | SD card FAT32 logging |
| `power.c/.h` | Battery/solar monitoring, sleep management |
| `CMakeLists.txt` | Build system (nRF Connect SDK + sim stub) |

### Build

```bash
# Production (nRF Connect SDK / Zephyr)
west build -b nrf52840dk_nrf52840 firmware
west flash

# Simulation (algorithm test on host)
MUSSEL_WATCH_SIM=1 cmake -B build && cmake --build build
./build/mussel_watch_sim
```

### BLE Configuration Service

| UUID | Characteristic | R/W | Description |
|------|---------------|-----|-------------|
| `0x1901` | deployment_id | R/W | 16-byte ASCII deployment identifier |
| `0x1902` | sample_interval_s | R/W | uint16, sampling interval (30–3600 s) |
| `0x1903` | uplink_interval_s | R/W | uint16, LoRa uplink interval (60–86400 s) |
| `0x1904` | gape_threshold_deg | R/W | float, closure-event threshold (0.5–5°) |
| `0x1905` | closure_duration_s | R/W | uint16, sustained-closure alert (10–600 s) |
| `0x1906` | calibrate_closed | W | Trigger: "set current angle as 0° (closed)" |
| `0x1907` | calibrate_open | W | Trigger: "set current angle as max (open)" |
| `0x1908` | gape_live | R | float[4], live gape angles for all 4 mussels (notify) |
| `0x1909` | water_quality_live | R | struct: temp, DO, depth, battery (notify) |
| `0x190A` | alert_flags | R | uint16, active alert bitmask (notify) |
| `0x190B` | firmware_version | R | ASCII string |

### LoRaWAN Packet Format

```
Byte 0:    Device class (0x01 = Mussel Watch)
Byte 1:    Deployment ID (hash, 1 byte)
Bytes 2-9: Timestamp (Unix epoch, big-endian uint64)
Byte 10:   Flags (bit0=alert, bit1=low_battery, bit2=cal_mode, bit3=multi-head)
Bytes 11-14: Mussel A gape angle (float32, little-endian, degrees)
Bytes 15-18: Mussel B gape angle (or 0xFF if unused)
Bytes 19-22: Mussel C gape angle (or 0xFF if unused)
Bytes 23-26: Mussel D gape angle (or 0xFF if unused)
Byte 27:   Water temp (int8, °C × 2, range -40 to +85)
Bytes 28-29: Dissolved O₂ (uint16, mg/L × 100)
Bytes 30-31: Depth (int16, cm, signed for above/below waterline)
Byte 32:   Battery % (uint8, 0-100)
Byte 33:   Alert code (0=none, 1=closure_event, 2=sustained_closure,
                     3=rhythm_deviation, 4=multi_mussel_event,
                     5=temp_anomaly, 6=DO_anomaly)
```

Total: **34 bytes payload** (fits single LoRa packet at SF7).

---

## Mechanical Design

### Sensor Head (submersible)

```
            ┌─────────────────────────────┐
            │   IP68 potted sensor head    │
            │                              │
            │  ┌─────────────────────┐    │
            │  │ ADS1115 + DRV5053×4 │    │
            │  │ TCA9548A mux        │    │
            │  └──────────┬──────────┘    │
            │             │ I²C            │
            │  ┌──────────┴──────────┐    │
            │  │ 4-wire cable gland   │────┼──► to electronics pod
            │  └─────────────────────┘    │
            │                              │
            │  Titanium clip mount:        │
            │  ┌───┐         ┌───┐        │
            │  │ H │← magnet  │ │          │
            │  │ a │ (valve B)│ │          │
            │  │ l │         │ │          │
            │  │ s │ (valve A)│ │          │
            │  └───┘         └───┘        │
            │  clip grips mussel shell     │
            └─────────────────────────────┘
```

The sensor head uses a **titanium spring clip** (non-corroding, non-toxic to mussels) that grips the mussel shell. The DRV5053 is potted in marine epoxy on the fixed clip arm; the magnet is glued (cyanoacrylate + epoxy overcoat) to the mobile valve. A 2 m cable connects to the above-water electronics pod.

### Electronics Pod (above water)

- IP67 sealed enclosure (70×50×30 mm)
- Cable gland to sensor head
- BLE antenna (internal, module)
- LoRa antenna (external, 868/915 MHz whip, IP67)
- Solar panel connector on top
- Magnetic reed switch for mode (external magnet activates calibrate mode without opening enclosure)

---

## Calibration

### Two-point gape calibration

1. **Closed point**: Hold the mussel closed (gently), press the mode button or send BLE `calibrate_closed` (0x1906). The firmware records the current Hall voltage as 0°.
2. **Open point**: Wait until the mussel is naturally wide open (typically during feeding, 1–4 hours), then send BLE `calibrate_open` (0x1907). The firmware records the current Hall voltage as the max-open angle.

The firmware linearly maps all subsequent Hall voltages: `angle = (V_H - V_closed) / (V_open - V_closed) × angle_max`.

Calibration values are stored in nRF flash (non-volatile).

---

## Bill of Materials

See `hardware/BOM.csv` for the full bill of materials. Total cost: ~**$87** (single-mussel config).

---

## Repository Structure

```
mussel-watch/
├── README.md              ← you are here
├── schematic/
│   ├── mussel_watch.kicad_pro
│   └── mussel_watch.kicad_sch
├── firmware/
│   ├── CMakeLists.txt
│   ├── config.h
│   ├── main.c
│   ├── gape_sensor.c / .h
│   ├── water_quality.c / .h
│   ├── anomaly.c / .h
│   ├── lora_uplink.c / .h
│   ├── ble_config.c / .h
│   ├── logger.c / .h
│   └── power.c / .h
├── hardware/
│   └── BOM.csv
├── docs/
│   ├── assembly_guide.md
│   ├── deployment_guide.md
│   └── api_reference.md
└── scripts/
    ├── visualize_gape.py
    ├── decode_lora.py
    └── deploy_config.py
```

---

## License

MIT — build it, deploy it, improve it.

---

*Invented as device #19 in the SoC Device Inventions collection.*