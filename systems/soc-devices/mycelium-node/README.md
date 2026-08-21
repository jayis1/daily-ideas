# Mycelium Node

> Mushroom fruiting chamber environmental controller — multi-zone temperature/humidity/CO₂ sensing, PID-controlled actuators, growth phase scheduling, and WiFi/BLE remote monitoring for home mycology.

## Overview

Mycelium Node is a dedicated environmental controller for mushroom fruiting chambers. It monitors temperature, humidity, CO₂, and light in multiple zones, drives humidifiers, heaters, fans, and grow lights with PID control loops, and schedules growth phases (colonization, pinning, fruiting, harvest) automatically. Data is streamed over MQTT for home automation integration and accessible via BLE for on-the-go checks.

**Key differentiators:**
- **Multi-zone sensing** — separate chamber and substrate temperature/humidity probes for precise microclimate control
- **Photoacoustic CO₂** — SCD41 NDIR sensor detects when CO₂ rises above threshold (mushroom respiration indicator) and triggers fresh air exchange
- **PID climate control** — independent PID loops for temperature, humidity, and CO₂ with anti-windup and derivative filtering
- **Growth phase scheduler** — automatic phase transitions (colonization → pinning → fruiting → harvest) with configurable trigger conditions
- **4 PWM actuator channels** — ultrasonic humidifier, heat pad, exhaust fan, grow light, each with smooth proportional control
- **MQTT + Home Assistant** — native MQTT discovery for integration with Home Assistant, Node-RED, or any MQTT broker
- **BLE dashboard** — check status, adjust setpoints, and trigger manual overrides from your phone
- **DIN-rail mountable** — 3D-printed enclosure snaps onto a standard 35mm DIN rail alongside your other automation gear

## Block Diagram

```
                        ┌────────────────────────────────────────────────────┐
                        │                   ESP32-C6-MINI-1                  │
                        │  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
  WiFi/BLE Ant ────────┤──┤ WiFi 6/  │  │  RISC-V  │  │  512KB Flash  │  │
                        │  │ BLE 5.0  │  │  LPGPWM  │  │  320KB SRAM   │  │
                        │  └──────────┘  └──────────┘  └───────────────┘  │
                        │         │           │              │             │
                        │  ┌──────┴───────────┴──────────────┴───┐       │
                        │  │            Peripheral Bus              │       │
                        │  │  ADC×2 │ I²C │ SPI │ UART │ PWM×6   │       │
                        │  └───┬───────┬─────┬──────┬──────┬───────┘       │
                        └──────┼───────┼─────┼──────┼──────┼──────────────┘
                               │       │     │      │      │
  ┌────────────────────────────┘       │     │      │      │
  │                                     │     │      │      │
  │  ┌──────────────────────────────────▼─────▼──┐  │      │
  │  │            I²C Bus (400 kHz)               │  │      │
  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │  │      │
  │  │  │SHT40 │ │SHT40 │ │SCD41 │ │TSL   │      │  │      │
  │  │  │(0x44)│ │(0x45)│ │(0x62)│ │2591  │      │  │      │
  │  │  │Chamb.│ │Subst.│ │CO₂   │ │Light │      │  │      │
  │  │  └──────┘ └──────┘ └──────┘ └──────┘      │  │      │
  │  └───────────────────────────────────────────┘  │      │
  │                                                  │      │
  │  ┌───────────────────────────────────────────┐   │      │
  │  │  SSD1306 OLED (128×64, I2C 0x3C)         │   │      │
  │  │  + Rotary Encoder (CLK, DT, SW)           │   │      │
  │  └───────────────────────────────────────────┘   │      │
  │                                                  │      │
  │  ┌─────────────────────────────────────────────┐ │      │
  │  │  DS18B20 (x2) — Substrate deep probes      │ │      │
  │  │  1-Wire bus on GPIO                          │ │      │
  │  └─────────────────────────────────────────────┘ │      │
  │                                                  │      │
  │                    ┌─────────────────────────────┘      │
  │                    │                                    │
  │  ┌─────────────────▼───────────────────────────────────▼────┐
  │  │                   PWM Actuator Stage                      │
  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
  │  │  │Humidifier│ │ Heater   │ │   Fan    │ │   Light  │  │
  │  │  │ MOSFET   │ │ MOSFET  │ │  MOSFET  │ │  MOSFET  │  │
  │  │  │ (IRLML)  │ │ (IRLML)  │ │ (IRLML)  │ │ (IRLML)  │  │
  │  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
  │  └───────┼────────────┼────────────┼────────────┼─────────┘
  │          │            │            │            │
  │   ┌──────▼──┐  ┌──────▼──┐  ┌─────▼───┐ ┌─────▼───┐
  │   │Ultrason.│  │Heat Pad │  │Exhaust  │ │Grow LED │
  │   │Mister   │  │5V/2A    │  │Fan 12V  │ │Strip 12V│
  │   └─────────┘  └─────────┘  └─────────┘ └─────────┘
  │
  │  ┌──────────────────────────────────────────────────────┐
  │  │  Power: USB-C 5V → MP1584 buck (3.3V) + LiPo backup│
  │  │  USB-C 5V → TP4056 → LiPo 2000mAh → MT3608 boost  │
  │  │  12V/2A barrel jack → fan & LED power rail          │
  │  └──────────────────────────────────────────────────────┘
```

## Specifications

| Parameter | Value |
|-----------|-------|
| **SoC** | ESP32-C6-MINI-1 (RISC-V single-core 160 MHz, WiFi 6, BLE 5.0) |
| **Flash** | 512 KB (internal) + 4 MB external (optional) |
| **SRAM** | 320 KB (internal) + 4 MB PSRAM (external) |
| **Chamber temp range** | -40°C to +125°C (SHT40, ±0.1°C) |
| **Chamber humidity range** | 0–100% RH (SHT40, ±1.8% RH) |
| **Substrate temp range** | -55°C to +125°C (DS18B20, ±0.5°C) |
| **CO₂ range** | 0–40000 ppm (SCD41, ±40 ppm + 5%) |
| **Light range** | 0–88000 lux (TSL2591, 600M:1 dynamic range) |
| **Humidifier output** | 0–100% PWM (5V ultrasonic mister, 300 mL/h) |
| **Heater output** | 0–100% PWM (5V heat pad, 10W max) |
| **Fan output** | 0–100% PWM (12V exhaust fan, 80mm) |
| **Light output** | 0–100% PWM (12V LED strip, 6500K) |
| **Connectivity** | WiFi 6 (2.4 GHz), BLE 5.0, MQTT |
| **Display** | SSD1306 128×64 OLED (I2C) |
| **Input** | Rotary encoder with pushbutton |
| **Power** | USB-C 5V/2A (main) + 12V/2A barrel jack (actuators) |
| **Backup** | LiPo 2000mAh (TP4056 charger, maintains operation during power loss) |
| **Dimensions** | 105 mm × 75 mm × 30 mm (DIN-rail mount case) |
| **Weight** | ~120 g (without batteries) |

## Pin Assignments

### ESP32-C6-MINI-1 (QFN40, 4×4 mm module)

| Pin | Function | Connection |
|-----|----------|------------|
| GPIO0 | STRAP / BOOT | Pull-up 10K (boot button) |
| GPIO1 | UART0_TX | Debug console TX |
| GPIO2 | UART0_RX | Debug console RX |
| GPIO3 | I2C_SDA | I2C bus (SHT40×2, SCD41, TSL2591, SSD1306) |
| GPIO4 | I2C_SCL | I2C bus clock |
| GPIO5 | PWM_CH0 | Humidifier MOSFET gate |
| GPIO6 | PWM_CH1 | Heater MOSFET gate |
| GPIO7 | PWM_CH2 | Fan MOSFET gate |
| GPIO8 | PWM_CH3 | Grow light MOSFET gate |
| GPIO9 | ONE_WIRE | DS18B20 data bus (external pull-up 4.7K) |
| GPIO10 | ROT_ENC_A | Rotary encoder phase A |
| GPIO11 | ROT_ENC_B | Rotary encoder phase B |
| GPIO12 | ROT_ENC_SW | Rotary encoder pushbutton |
| GPIO13 | BUZZER | Piezo buzzer (active, 3.3V) |
| GPIO14 | RELAY_CTRL | Safety relay control (active high) |
| GPIO15 | SCD41_RESET | SCD41 reset (active low) |
| GPIO16 | DS18B20_PWR | DS18B20 parasitic power enable (MOSFET gate) |
| GPIO17 | LED_STATUS | Status LED (WS2812B data) |
| GPIO18 | ADC_CH0 | LiPo voltage divider (1/2) |
| GPIO19 | ADC_CH1 | 12V rail voltage divider (1/4) |
| GPIO20 | USB_D+ | USB-C data (optional, for firmware updates) |
| GPIO21 | USB_D- | USB-C data |
| GPIO22 | SPI_CS_FLASH | External flash CS (optional) |
| GPIO23 | SPI_CLK | External flash clock |
| GPIO24 | SPI_MOSI | External flash MOSI |
| GPIO25 | SPI_MISO | External flash MISO |
| GPIO26 | WIFI_ANT | WiFi/BLE antenna (on-module PCB trace) |
| GPIO27 | LDO_EN | 3.3V LDO enable (power gating for I2C bus) |
| GPIO28 | BUZZER_EN | Buzzer power enable (MOSFET gate) |

## Power Architecture

```
  USB-C (5V, 2A)                          12V Barrel Jack (2A)
       │                                         │
       ▼                                         │
  ┌─────────────┐                               │
  │ TP4056      │                               │
  │ LiPo Charger│                               │
  │ (CC/CV)     │                               │
  └──────┬──────┘                               │
         │                                      │
    LiPo 2000mAh                                │
    (3.7V nom.)                                 │
         │                                      │
         ├── MT3608 Boost → 5V (actuator rail)  │
         │                                      │
         ▼                                      │
  ┌─────────────┐                               │
  │ ME6211      │                               │
  │ LDO 3.3V    │                               │
  │ (Iq = 5µA)  │                               │
  └──────┬──────┘                               │
         │                                      │
         ├── ESP32-C6 (always on)               │
         ├── I2C sensors (power-gated via LDO)  │
         ├── DS18B20 (power-gated)              │
         ├── SSD1306 OLED                       │
         └── Buzzer (power-gated)               │
                                                │
  Actuator Power Rails:                         │
  ┌─────────────────────────────────────────────┘
  │
  ├── 5V Rail (USB/MT3608) → Humidifier, Heater
  └── 12V Rail (barrel jack) → Fan, Grow Light

  Voltage Monitoring:
    GPIO18 (ADC) ← LiPo voltage divider (R1=R2=100K)
    GPIO19 (ADC) ← 12V rail voltage divider (R1=300K, R2=100K)
```

### Energy Budget (typical fruiting phase)

| Phase | Duration | Current | Power |
|-------|----------|---------|-------|
| Deep sleep (between cycles) | 270 s | 30 µA | 0.1 mW |
| Sensor wake + I²C reads | 2 s | 25 mA | 82.5 mW |
| CO₂ measurement (SCD41) | 5 s | 19 mA | 62.7 mW |
| OLED update | 0.5 s | 12 mA | 39.6 mW |
| PID compute + actuator adjust | 0.2 s | 30 mA | 99 mW |
| WiFi MQTT publish | 0.5 s | 180 mA | 594 mW |
| **Average (5-min cycle)** | | **~6 mA** | **~20 mW** |

With USB power, continuous operation is trivial. LiPo backup provides ~3 hours of operation during power loss (reduced MQTT frequency).

## Sensors Detail

### SHT40-AD1B-B (Chamber, I2C 0x44)

- **Location**: Inside the fruiting chamber, above substrate level
- **Purpose**: Chamber air temperature and humidity — the primary feedback for PID control
- **Accuracy**: ±0.1°C temperature, ±1.8% RH humidity
- **Range**: -40°C to +125°C, 0–100% RH
- **Power**: 0.4 mA (active), 0.1 µA (sleep)
- **Feature**: On-chip heater for dew-point compensation (important for high-humidity environments)

### SHT40-AD1B-B (Substrate, I2C 0x45)

- **Location**: At substrate level, inside the grow bag/block
- **Purpose**: Substrate temperature and local humidity — critical for spawn run and fruiting
- **Feature**: Alternate I2C address (0x45) on the same bus
- **Protection**: PTFE membrane filter (allows humidity, blocks water droplets)

### SCD41 (CO₂, I2C 0x62)

- **Location**: Inside chamber, at canopy level
- **Purpose**: CO₂ monitoring — mushroom respiration produces CO₂; levels above 1000 ppm trigger fresh air exchange
- **Technology**: Photoacoustic NDIR (smaller, lower power than traditional NDIR)
- **Accuracy**: ±40 ppm + 5% of reading
- **Range**: 0–40000 ppm
- **Self-calibration**: Automatic baseline correction (ABC) enabled, assumes lowest CO₂ ≈ 400 ppm over 8-day window
- **Power**: 19 mA (periodic mode, 1 measurement per 5 min)

### TSL2591 (Light, I2C 0x29)

- **Location**: Inside chamber, facing grow area
- **Purpose**: Ambient light monitoring — mushrooms need specific light cycles (12/12 for pinning)
- **Dynamic range**: 600M:1 (infrared + visible channels)
- **Integration**: Reports lux, triggers grow light adjustment

### DS18B20 × 2 (Substrate Deep Probes, 1-Wire)

- **Location**: Embedded in substrate at 3 cm and 7 cm depth
- **Purpose**: Core substrate temperature — prevents overheating during colonization
- **Resolution**: 12-bit (0.0625°C steps)
- **Parasitic power**: Enabled (power-gated via MOSFET on GPIO16)
- **Bus**: 1-Wire on GPIO9 with 4.7K external pull-up

## Actuator Detail

### Ultrasonic Humidifier (PWM on GPIO5)

- **Device**: 5V ultrasonic mist maker disc (20 mm, 1.6 MHz, 300 mL/h)
- **Driver**: IRLML6344 N-channel MOSFET (Vgs_th = 1V, logic-level)
- **PWM Frequency**: 25 kHz (above audible range, smooth mist control)
- **Control**: PID loop targets chamber humidity setpoint (typically 90–95% RH for fruiting)
- **Protection**: 5-minute max continuous runtime, then 30-second cooldown (prevents disc degradation)

### Heat Pad (PWM on GPIO6)

- **Device**: 5V silicone heat pad (10W, 50×50 mm)
- **Driver**: IRLML6344 N-channel MOSFET
- **PWM Frequency**: 1 Hz (slow thermal response, no need for high frequency)
- **Control**: PID loop targets chamber temperature setpoint (typically 20–25°C depending on species)
- **Safety**: Hardware thermal cutoff at 40°C via relay (GPIO14), software limit at 35°C

### Exhaust Fan (PWM on GPIO7)

- **Device**: 12V 80mm PC fan (Noctua-style, ~1500 RPM)
- **Driver**: IRLML6344 MOSFET (gate via 12V-to-3.3V level shifter for 12V fan)
- **PWM Frequency**: 25 kHz (4-wire PWM fan standard)
- **Control**: PID loop targets CO₂ setpoint (typically < 1000 ppm during fruiting)
- **Also serves**: Humidity reduction when RH exceeds setpoint by > 5%

### Grow Light (PWM on GPIO8)

- **Device**: 12V LED strip, 6500K daylight, 5W/ft
- **Driver**: IRLML6344 MOSFET (same as fan, level-shifted)
- **PWM Frequency**: 1 kHz (flicker-free)
- **Control**: Schedule-based (configurable photoperiod per growth phase)
  - Colonization: OFF or very dim (10%)
  - Pinning: 12h on / 12h off, 50% intensity
  - Fruiting: 12h on / 12h off, 70% intensity
  - Harvest: OFF

## Firmware Architecture

```
┌──────────────────────────────────────────────────┐
│               Application Layer                    │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Growth   │  │   Web UI /   │  │   BLE      │ │
│  │ Scheduler │  │   MQTT       │  │  Dashboard │ │
│  └──────────┘  └──────────────┘  └────────────┘ │
├──────────────────────────────────────────────────┤
│              Control Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Temp    │  │  Humid   │  │  CO₂ / FAE   │   │
│  │  PID     │  │  PID     │  │  PID          │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
├──────────────────────────────────────────────────┤
│              Sensor Managers                       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │SHT40 │ │SHT40 │ │SCD41 │ │TSL   │ │DS18B20│ │
│  │Chamb │ │Subst │ │CO₂   │ │2591  │ │(x2)  │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
├──────────────────────────────────────────────────┤
│              HAL / Drivers                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ I²C  │ │ 1-Wire│ │ PWM  │ │ OLED │ │ WiFi │ │
│  │ Bus  │ │  Bus  │ │ Timer│ │ Disp │ │ Stack│ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
├──────────────────────────────────────────────────┤
│              Power Manager                         │
│  ┌──────────────────────────────────────────────┐│
│  │  RTC Wake │ LDO Gate │ LiPo Monitor │ Sleep  ││
│  └──────────────────────────────────────────────┘│
├──────────────────────────────────────────────────┤
│           ESP32-C6 Hardware                        │
└──────────────────────────────────────────────────┘
```

### Growth Phase Scheduler

The device manages four growth phases with configurable parameters:

| Phase | Temp Setpoint | RH Setpoint | CO₂ Max | Light | Duration |
|-------|--------------|-------------|---------|-------|----------|
| **Colonization** | 24–26°C | 80–85% | 5000 ppm | OFF or 10% | 14–21 days |
| **Pinning** | 18–22°C | 90–95% | 1000 ppm | 50% (12/12) | 5–10 days |
| **Fruiting** | 18–24°C | 85–95% | 1000 ppm | 70% (12/12) | 7–14 days |
| **Harvest** | 18–22°C | 70–80% | Ambient | OFF | 1–2 days |

Phase transitions can be triggered by:
- **Timer**: After N days in current phase
- **Manual**: User presses encoder button for 3 seconds
- **Condition**: Substrate temp drops below threshold (cold shock for pinning)

### PID Control

Three independent PID controllers run at 1 Hz:

```
output(t) = Kp × e(t) + Ki × Σe(t) × dt + Kd × (e(t) - e(t-1)) / dt

Where:
  e(t) = setpoint - measurement
  Kp, Ki, Kd = tunable gains (defaults per phase)
  
Anti-windup: Integral term clamped to [0, 100%]
Derivative filter: EMA with α = 0.1
Output clamped: [0%, 100%] for humidifier/heater, [0%, 80%] for fan (safety)
```

**Default PID gains (Fruiting phase):**

| Controller | Kp | Ki | Kd | Output |
|-----------|-----|-----|-----|--------|
| Humidity | 2.0 | 0.1 | 0.5 | Humidifier PWM |
| Temperature | 1.5 | 0.05 | 0.3 | Heater PWM |
| CO₂ | 3.0 | 0.2 | 0.0 | Fan PWM |

### MQTT Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `mycelium/node/{id}/sensors` | Publish | JSON: chamber/substrate temp, RH, CO₂, light, LiPo voltage |
| `mycelium/node/{id}/status` | Publish | JSON: phase, PID outputs, uptime, next action |
| `mycelium/node/{id}/setpoint` | Subscribe | JSON: target temp, RH, CO₂, light |
| `mycelium/node/{id}/phase` | Subscribe | String: "colonization", "pinning", "fruiting", "harvest" |
| `mycelium/node/{id}/override` | Subscribe | JSON: manual humidifier/fan/light % |
| `mycelium/node/{id}/config` | Subscribe | JSON: PID gains, phase params, WiFi credentials |

### BLE GATT Services

| Service | UUID | Characteristics |
|---------|------|----------------|
| **Environment** | 0x181A | Chamber temp (float), Substrate temp (float), Chamber RH (float), CO₂ (uint16) |
| **Control** | 0x1820 | Humidifier % (uint8), Heater % (uint8), Fan % (uint8), Light % (uint8) |
| **Phase** | 0x1821 | Current phase (uint8), Days in phase (uint8), Auto-advance toggle (bool) |
| **Config** | 0x1822 | PID Kp/Ki/Kd per controller, Phase setpoints, MQTT broker address |

### Sensor Data JSON (MQTT publish every 60 s)

```json
{
  "id": "mycelium-a1b2c3",
  "ts": 1718534400,
  "phase": "fruiting",
  "chamber": {
    "temp_c": 22.3,
    "rh_pct": 91.2,
    "co2_ppm": 856,
    "light_lux": 420
  },
  "substrate": {
    "temp_c": 23.1,
    "rh_pct": 88.7,
    "deep_temp_1_c": 22.8,
    "deep_temp_2_c": 22.5
  },
  "actuators": {
    "humidifier_pct": 45,
    "heater_pct": 12,
    "fan_pct": 30,
    "light_pct": 70
  },
  "power": {
    "lipo_v": 3.92,
    "usb_v": 5.01,
    "rail_12v": 12.1
  },
  "uptime_s": 86400,
  "next_action": "sensor_read in 30s"
}
```

## Assembly Guide

### Tools Required

- Soldering iron (fine tip, temperature controlled)
- Hot air rework station (for ESP32-C6-MINI-1 module)
- Multimeter
- USB-C cable for power/programming
- ST-Link or ESP-Prog (for initial flash)
- KiCad 8+

### Assembly Steps

1. **PCB fabrication** — Order 4-layer PCB (1.6mm, ENIG finish, HASL lead-free) from JLCPCB or similar
2. **SMD soldering** — Place all QFN/SOT/MOSFET packages using solder paste and hot air reflow
3. **ESP32-C6-MINI-1** — Place module last (castellated edges, use solder paste + hot air)
4. **Through-hole** — Install DS18B20 probe connectors, barrel jack, USB-C, piezo buzzer
5. **OLED display** — Solder 4-pin header or use FPC connector
6. **Sensor boards** — Mount SHT40 and SCD41 on separate small PCBs connected via I2C ribbon cable
7. **External probe assembly** — Solder DS18B20 waterproof probes to 3.5mm jack connectors
8. **Enclosure** — 3D-print DIN-rail case (STL files in `hardware/`), insert PCB, snap shut
9. **Firmware flash** — Connect ESP-Prog to SWD/UART header, flash bootloader + application
10. **Commissioning** — Power on, verify sensor readings, calibrate SCD41 (run outside for 10 min for baseline)

### Calibration

1. **SHT40** — Factory calibrated, no user calibration needed. Enable on-chip heater for dew-point compensation in high humidity.
2. **SCD41** — Run automatic baseline correction (ABC) for 8 days in a well-ventilated area. For manual calibration: expose to fresh outdoor air (≈420 ppm CO₂), then send `SCD41_PERFORM_FACTORY_RESET` over I2C.
3. **DS18B20** — Factory calibrated to ±0.5°C. For higher accuracy: ice water bath (0°C) calibration, store offset in NVS.
4. **TSL2591** — Factory calibrated. For grow light calibration: place sensor at canopy height, adjust gain/integration time.

## API Reference

### Serial Debug Interface (115200 baud, 8N1)

```
MYC> status
  PHASE: fruiting (day 5/14)
  CHAMBER: 22.3°C / 91.2% RH
  SUBSTRATE: 23.1°C / 88.7% RH
  CO2: 856 ppm
  LIGHT: 420 lux
  DEEP1: 22.8°C  DEEP2: 22.5°C
  HUM: 45%  HEAT: 12%  FAN: 30%  LIGHT: 70%
  LIPO: 3.92V  USB: 5.01V  12V: 12.1V

MYC> set humidity 93
  Humidity setpoint: 93% RH

MYC> set co2_max 800
  CO2 max setpoint: 800 ppm

MYC> phase pinning
  Phase → pinning
  Setpoints: 20°C, 92% RH, 1000 ppm CO2, 50% light

MYC> pid humidity kp 2.5
  Humidity PID Kp: 2.5

MYC> override humidifier 80
  Humidifier override: 80% (manual, will auto-clear in 10 min)

MYC> calibrate co2 420
  SCD41 forced calibration at 420 ppm... done

MYC> schedule show
  Colonization: 18 days, 25°C, 82% RH, 5000 CO2, 10% light
  Pinning: 7 days, 20°C, 92% RH, 1000 CO2, 50% light
  Fruiting: 14 days, 22°C, 93% RH, 1000 CO2, 70% light
  Harvest: 2 days, 20°C, 75% RH, ambient CO2, OFF light
  Auto-advance: ON

MYC> wifi connect "MySSID" "password123"
  Connecting... connected, IP: 192.168.1.42

MYC> mqtt start
  MQTT connecting to 192.168.1.100:1883... connected

MYC> ota check
  Checking for firmware update... v1.2.0 available (current: v1.1.0)
  Use 'ota apply' to install
```

### MQTT Decoded Payload (Python)

```python
import json
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class MyceliumReading:
    device_id: str
    timestamp: int
    phase: str
    chamber_temp_c: float
    chamber_rh_pct: float
    substrate_temp_c: float
    substrate_rh_pct: float
    deep_temp_1_c: float
    deep_temp_2_c: float
    co2_ppm: int
    light_lux: float
    humidifier_pct: int
    heater_pct: int
    fan_pct: int
    light_pct: int
    lipo_v: float
    usb_v: float
    rail_12v: float

    @classmethod
    def from_mqtt(cls, payload: bytes) -> 'MyceliumReading':
        data = json.loads(payload)
        return cls(
            device_id=data['id'],
            timestamp=data['ts'],
            phase=data['phase'],
            chamber_temp_c=data['chamber']['temp_c'],
            chamber_rh_pct=data['chamber']['rh_pct'],
            substrate_temp_c=data['substrate']['temp_c'],
            substrate_rh_pct=data['substrate']['rh_pct'],
            deep_temp_1_c=data['substrate']['deep_temp_1_c'],
            deep_temp_2_c=data['substrate']['deep_temp_2_c'],
            co2_ppm=data['chamber']['co2_ppm'],
            light_lux=data['chamber']['light_lux'],
            humidifier_pct=data['actuators']['humidifier_pct'],
            heater_pct=data['actuators']['heater_pct'],
            fan_pct=data['actuators']['fan_pct'],
            light_pct=data['actuators']['light_pct'],
            lipo_v=data['power']['lipo_v'],
            usb_v=data['power']['usb_v'],
            rail_12v=data['power']['rail_12v'],
        )

# Home Assistant MQTT Discovery config
HA_DISCOVERY = {
    "dev_cla": "humidity",
    "unit_of_meas": "%",
    "stat_t": "mycelium/node/{id}/sensors",
    "val_tpl": "{{ value_json.chamber.rh_pct }}",
    "uniq_id": "mycelium_{id}_chamber_rh",
    "name": "Mycelium Chamber Humidity",
}
```

## Physical Layout

```
  ┌─────────────────────────────────────┐
  │  [USB-C]        [12V DC]            │  ← Top edge: power connectors
  │                                      │
  │  ┌───────────────────┐              │
  │  │  ESP32-C6-MINI-1  │              │
  │  │  (WiFi/BLE ant)   │              │
  │  └───────────────────┘              │
  │                                      │
  │  ┌────┐ ┌────┐ ┌─────┐ ┌─────┐     │
  │  │SHT │ │SHT │ │SCD41│ │TSL  │     │  ← I2C sensors
  │  │0x44│ │0x45│ │0x62 │ │2591 │     │
  │  └────┘ └────┘ └─────┘ └─────┘     │
  │                                      │
  │  ┌───────────────┐  ┌──────────┐   │
  │  │ SSD1306 OLED  │  │  Rotary  │   │
  │  │  128×64       │  │  Encoder │   │
  │  └───────────────┘  └──────────┘   │
  │                                      │
  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐             │
  │  │M1│ │M2│ │M3│ │M4│             │  ← MOSFET drivers
  │  │Hum│Heat│Fan│LED│             │
  │  └──┘ └──┘ └──┘ └──┘             │
  │                                      │
  │  [DS18B20 x2] ─── 3.5mm jacks      │  ← External probe connectors
  │                                      │
  │  [Buzzer] [Relay] [WS2812]         │  ← Status indicators
  │                                      │
  └──────────────────────────────────────┘

  External Connections:
  ┌────────────┐     ┌─────────────────────┐
  │ Ultrasonic │     │    Exhaust Fan       │
  │ Mist Maker │─────│    (12V 80mm)       │
  │ (5V disc)  │     │                     │
  └────────────┘     └─────────────────────┘
  ┌────────────┐     ┌─────────────────────┐
  │ Heat Pad   │     │    Grow Light       │
  │ (5V 10W)   │     │    (12V LED strip)  │
  └────────────┘     └─────────────────────┘
  
  DIN Rail Mount:
  ┌──────────────────────────┐
  │  ┌────────────────────┐  │
  │  │   Mycelium Node    │  │  ← Snaps onto 35mm DIN rail
  │  │   PCB + Enclosure  │  │
  │  └────────────────────┘  │
  │  ══════════════════════   │  ← DIN rail
  └──────────────────────────┘
```

## Species Profiles (Built-in Presets)

| Species | Colonization | Pinning | Fruiting | Notes |
|---------|-------------|---------|----------|-------|
| **Oyster (Pleurotus)** | 24°C, 80% RH, 14d | 18°C, 92% RH, 5d | 20°C, 90% RH, 7d | Aggressive, high CO₂ tolerance |
| **Lion's Mane (Hericium)** | 22°C, 82% RH, 18d | 18°C, 90% RH, 7d | 20°C, 88% RH, 10d | Prefers high O₂, lower humidity |
| **Shiitake (Lentinula)** | 22°C, 78% RH, 21d | 16°C, 90% RH, 7d | 18°C, 85% RH, 14d | Cold shock needed for pinning |
| **Reishi (Ganoderma)** | 26°C, 85% RH, 18d | 22°C, 95% RH, 10d | 24°C, 92% RH, 21d | Antler form at high CO₂ |
| **Chestnut (G. bellinghamensis)** | 22°C, 80% RH, 14d | 18°C, 88% RH, 5d | 20°C, 85% RH, 10d | Fast colonizer, moderate FAE |

## License

MIT — build it, grow it, improve it.