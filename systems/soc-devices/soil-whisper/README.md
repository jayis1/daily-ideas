# Soil Whisper

> Solar-powered agricultural soil intelligence probe — multi-depth moisture, NPK ion-selective electrodes, pH, temperature, and LoRaWAN uplink for precision farming.

## Overview

Soil Whisper is a rugged, solar-powered soil probe designed for precision agriculture. It inserts into the ground like a stake and continuously monitors soil health at multiple depths, broadcasting data over LoRaWAN to a gateway for cloud analytics. Farmers get real-time soil intelligence without wiring, WiFi, or manual sampling.

**Key differentiators:**
- **Multi-depth sensing** — 3 depth tiers (10 cm, 20 cm, 40 cm) with independent capacitive moisture probes
- **NPK ion-selective electrodes** — direct measurement of Nitrogen (as NO₃⁻), Phosphorus (as H₂PO₄⁻), and Potassium (as K⁺) concentrations at the root zone
- **pH and temperature** at the primary root zone
- **On-device calibration** — stores per-electrode calibration curves in flash, auto-references with internal buffer
- **LoRaWAN Class A** — ultra-low-power, long-range uplink (up to 15 km rural)
- **Solar + supercapacitor** — runs indefinitely with no battery replacement
- **IP68 stake form factor** — all electronics sealed in a polycarbonate tube, probes exposed at depth markers

## Block Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │                  STM32WL55JC                    │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
  LoRa Antenna ────┤──┤ Sub-GHz   │ │  Cortex- │  │  Flash   │     │
  (868/915 MHz)     │  │ Radio    │  │  M4/M0+  │  │  256 KB  │     │
                    │  └──────────┘  └──────────┘  └──────────┘     │
                    │         │           │              │          │
                    │  ┌──────┴───────────┴──────────────┴───┐     │
                    │  │            Peripheral Bus             │     │
                    │  │  ADC×2 │ SPI │ I²C │ UART │ GPIO     │     │
                    │  └───┬───────┬─────┬──────┬──────┬──────┘     │
                    └──────┼───────┼─────┼──────┼──────┼────────────┘
                           │       │     │      │      │
              ┌────────────┘       │     │      │      │
              │                    │     │      │      │
    ┌─────────▼────────┐  ┌───────▼──┐  │      │      │
    │ MUX (CD74HC4067) │  │  ADS1115 │  │      │      │
    │ 16-ch Analog     │  │  16-bit  │  │      │      │
    │ Multiplexer       │  │  ADC     │  │      │      │
    └──┬──┬──┬──┬──┬──┘  └────┬─────┘  │      │      │
       │  │  │  │  │             │        │      │      │
    ┌──▼──▼──▼──▼──▼──▼─────────▼──┐    │      │      │
    │  NPK ISE Probes (x3)         │    │      │      │
    │  NO₃⁻ · H₂PO₄⁻ · K⁺        │    │      │      │      │
    │  + pH Glass Electrode         │    │      │      │      │
    │  + Reference Electrode        │    │      │      │      │
    └───────────────────────────────┘    │      │      │      │
                                         │      │      │      │
    ┌────────────────────────────────────▼──┐   │      │      │
    │ Capacitive Moisture x3 (10/20/40 cm)  │   │      │      │
    │ (555 oscillator → freq proportional)  │   │      │      │
    └────────────────────────────────────────┘   │      │      │
                                                  │      │      │
    ┌─────────────────────────────────────────────▼──┐   │      │
    │ DS18B20 (x3) — Temperature at each depth      │   │      │
    └────────────────────────────────────────────────┘   │      │
                                                          │      │
    ┌─────────────────────────────────────────────────────▼──┐   │
    │ SHT40 — Ambient Humidity (above ground)               │   │
    └────────────────────────────────────────────────────────┘   │
                                                                  │
    ┌─────────────────────────────────────────────────────────────▼──┐
    │ Power: Solar (6V 2W) → BQ25570 → Supercap (10F) + LDO 3.3V │
    └────────────────────────────────────────────────────────────────┘
```

## Specifications

| Parameter | Value |
|-----------|-------|
| **SoC** | STM32WL55JC (Dual-core Cortex-M4/M0+, integrated Sub-GHz radio) |
| **Frequency** | 868 MHz (EU) / 915 MHz (US) |
| **Range** | Up to 15 km (rural, line-of-sight) |
| **Protocol** | LoRaWAN 1.0.3 Class A |
| **Moisture depths** | 10 cm, 20 cm, 40 cm |
| **Moisture accuracy** | ±3% VWC (capacitive) |
| **NPK range** | NO₃⁻: 1–1000 ppm, H₂PO₄⁻: 0.5–500 ppm, K⁺: 5–2000 ppm |
| **pH range** | 0–14 (±0.1 pH) |
| **Temperature range** | -40°C to +85°C (DS18B20) |
| **Humidity** | 0–100% RH (SHT40, above ground) |
| **Power** | Solar 2W panel + 10F supercapacitor (no battery) |
| **Sample interval** | Configurable: 5 min to 24 hours (default 30 min) |
| **Sleep current** | < 8 µA (deep stop with RTC) |
| **Operating current** | ~15 mA (active sampling), ~120 mA (LoRa TX) |
| **Dimensions** | 50 mm × 600 mm stake (polycarbonate tube) |
| **Ingress protection** | IP68 (submersible) |
| **Weight** | ~280 g |

## Pin Assignments

### STM32WL55JC (UFQFPN48)

| Pin | Function | Connection |
|-----|----------|------------|
| PA0 | ADC1_IN5 | MUX common output (moisture frequency counter) |
| PA1 | ADC1_IN6 | ADS1115 alert/RDY (interrupt) |
| PA2 | USART2_TX | Debug UART TX |
| PA3 | USART2_RX | Debug UART RX |
| PA4 | GPIO_OUT | MUX enable (active low) |
| PA5 | SPI1_SCK | Flash SPI clock |
| PA6 | SPI1_MISO | Flash SPI MISO |
| PA7 | SPI1_MOSI | Flash SPI MOSI |
| PA8 | GPIO_OUT | MUX S0 |
| PA9 | GPIO_OUT | MUX S1 |
| PA10 | GPIO_OUT | MUX S2 |
| PA11 | GPIO_OUT | MUX S3 |
| PA12 | GPIO_OUT | DS18B20 power enable |
| PA13 | SWDIO | Debug |
| PA14 | SWCLK | Debug |
| PA15 | GPIO_OUT | LDO enable (power gating) |
| PB0 | GPIO_OUT | NPK probe power enable |
| PB1 | GPIO_OUT | pH probe power enable |
| PB2 | GPIO_OUT | Status LED (green) |
| PB3 | GPIO_OUT | Status LED (red) |
| PB4 | GPIO_OUT | RFSwitch CTRL1 (RF switch control) |
| PB5 | GPIO_OUT | RFSwitch CTRL2 |
| PB6 | I2C1_SCL | I2C bus — ADS1115, SHT40 |
| PB7 | I2C1_SDA | I2C bus — ADS1115, SHT40 |
| PB8 | GPIO_OUT | LoRa TCXO enable |
| PB9 | GPIO_OUT | RF power amplifier enable |
| PB10 | GPIO_OUT | Solar charger interrupt |
| PB11 | GPIO_IN | VBAT_SENSE (voltage divider) |
| PB12 | GPIO_OUT | RF switch VDD |
| PB13 | SPI2_SCK | Internal flash SPI2 |
| PB14 | SPI2_MISO | Internal flash SPI2 |
| PB15 | SPI2_MOSI | Internal flash SPI2 |
| PC0 | ADC1_IN1 | ADS1115 analog pass-through |
| PC1 | ADC1_IN2 | VBAT voltage divider |
| PC2 | ADC1_IN3 | Thermistor analog (internal temp) |
| PC3 | ADC1_IN4 | Reference voltage check |
| PC6 | TIM3_CH1 | Moisture PWM capture (depth 1) |
| PC7 | TIM3_CH2 | Moisture PWM capture (depth 2) |
| PC8 | TIM3_CH3 | Moisture PWM capture (depth 3) |
| PC13 | GPIO_OUT | DS18B20 data (1-Wire) |
| PH0 | OSC_IN | 32.768 kHz LSE crystal |
| PH1 | OSC_OUT | 32.768 kHz LSE crystal |
| PH3 | BOOT0 | Boot mode (pull low) |

## Power Architecture

```
  Solar Panel (6V, 2W, monocrystalline)
       │
       ▼
  ┌─────────────┐
  │ BQ25570     │  MPPT + buck-boost charger
  │ (Solar PM) │  VOUT: 3.6V (supercap charge)
  └─────┬───────┘
        │
        ├── Supercapacitor 10F, 3.6V (energy buffer)
        │
        ▼
  ┌─────────────┐
  │ TPS7A02     │  Ultra-low-Iq LDO
  │ 3.3V/150mA │  Iq = 25 nA
  └─────┬───────┘
        │
        ├── STM32WL55 (always on, sleep < 8 µA)
        ├── ADS1115 (power-gated via LDO enable)
        ├── SHT40 (power-gated via I2C, auto-shutdown)
        ├── MUX CD74HC4067 (power-gated)
        ├── DS18B20 (power-gated via MOSFET)
        └── NPK/pH probes (power-gated via MOSFET)

  Voltage monitoring:
    PC1 (ADC) ← voltage divider on supercap for charge tracking
    PB10 (IRQ) ← BQ25570 VBAT_OK interrupt
```

### Energy Budget (30-minute cycle)

| Phase | Duration | Current | Charge |
|-------|----------|---------|--------|
| Deep sleep | 29 min 50 s | 8 µA | 14.3 mC |
| Wake + ADC sampling | 5 s | 12 mA | 60 mC |
| NPK/pH stabilization + read | 3 s | 5 mA | 15 mC |
| DS18B20 read (x3) | 1 s | 4 mA | 4 mC |
| SHT40 read | 0.1 s | 0.4 mA | 0.04 mC |
| LoRa TX (SF7, 50 bytes) | 0.5 s | 120 mA | 60 mC |
| **Total per cycle** | | | **~153 mC** |

Supercapacitor energy: 10F × 3.6V² / 2 = 64.8 J = 18,000 mAh·s ≈ far more than 153 mC per cycle. With 2W solar (worst case 0.5W average), the system runs perpetually.

## Sensors Detail

### Capacitive Moisture Probes (x3, depths 10/20/40 cm)

Each probe uses a TLC555 timer in astable mode with a capacitive PCB trace that acts as the sensing element. Soil moisture changes the dielectric constant, shifting the oscillation frequency.

- **Sensing element**: Interdigitated copper traces on 1.6mm FR4, conformal coated
- **Frequency range**: ~20 kHz (dry) to ~50 kHz (wet)
- **Output**: Square wave captured by TIM3 input capture
- **Calibration**: 3-point (air, water, reference soil), stored as polynomial coefficients in flash

### NPK Ion-Selective Electrodes (x3)

- **Nitrate (NO₃⁻)**: PVC membrane ISE, range 1–1000 ppm, sensitivity ~54 mV/decade
- **Phosphate (H₂PO₄⁻)**: PVC membrane ISE, range 0.5–500 ppm, sensitivity ~50 mV/decade
- **Potassium (K⁺)**: Valinomycin-based PVC membrane, range 5–2000 ppm, sensitivity ~56 mV/decade

All three ISEs share a common Ag/AgCl reference electrode. The high-impedance output (~100 MΩ) goes through a TLV8542 dual op-amp instrumentation front-end before the CD74HC4067 MUX and ADS1115 16-bit ADC.

### pH Glass Electrode

- Standard glass pH electrode with Ag/AgCl reference
- Range: 0–14 pH, accuracy ±0.1 pH
- High-impedance buffer: TLV8542 op-amp (gain = 1, input bias < 1 pA)
- Calibration: 2-point (pH 4.0 and 7.0 buffers)

### DS18B20 Temperature Probes (x3)

- One at each moisture depth (10/20/40 cm)
- Parasitic power mode (power-gated via MOSFET on PA12)
- 12-bit resolution (0.0625°C steps)
- 1-Wire bus on PC13

### SHT40 Humidity Sensor (above ground)

- I2C address 0x44
- ±1.8% RH accuracy
- Auto-shutdown after measurement

## Firmware Architecture

```
┌─────────────────────────────────────┐
│           Application Layer          │
│  ┌─────────┐  ┌──────────────────┐  │
│  │LoRaWAN  │  │  Data Aggregation│  │
│  │ Stack   │  │  & Compression   │  │
│  └─────────┘  └──────────────────┘  │
├─────────────────────────────────────┤
│           Sensor Managers            │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │Moist │ │ NPK  │ │pH/   │       │
│  │Driver│ │Driver │ │Temp  │       │
│  └──────┘ └──────┘ └──────┘       │
├─────────────────────────────────────┤
│           HAL / Drivers             │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │ADC   │ │I2C   │ │1-Wire│       │
│  │Timer │ │Bus   │ │Bus   │       │
│  └──────┘ └──────┘ └──────┘       │
├─────────────────────────────────────┤
│           Power Manager             │
│  ┌──────────────────────────────┐   │
│  │ RTC Wake │ LDO Gate │ Sleep  │   │
│  └──────────────────────────────┘   │
├─────────────────────────────────────┤
│        STM32WL55 Hardware           │
└─────────────────────────────────────┘
```

### LoRaWAN Payload Format (21 bytes)

| Byte | Bits | Field | Scale | Unit |
|------|------|-------|-------|------|
| 0 | 8 | Flags | — | — |
| 1–2 | 16 | Moisture 10cm | ×0.01 | %VWC |
| 3–4 | 16 | Moisture 20cm | ×0.01 | %VWC |
| 5–6 | 16 | Moisture 40cm | ×0.01 | %VWC |
| 7–8 | 16 | Temperature 10cm | ×0.01 | °C (offset -40) |
| 9–10 | 16 | Temperature 20cm | ×0.01 | °C |
| 11–12 | 16 | Temperature 40cm | ×0.01 | °C |
| 13–14 | 16 | NO₃⁻ concentration | ×0.1 | ppm |
| 15 | 8 | H₂PO₄⁻ concentration | ×2 | ppm |
| 16–17 | 16 | K⁺ concentration | ×0.1 | ppm |
| 18 | 8 | pH | ×10 | — |
| 19 | 8 | Humidity | ×0.4 | %RH |
| 20 | 8 | Battery voltage | ×0.02 | V |

**Flags byte (0):**
- Bit 7: Moisture valid
- Bit 6: Temperature valid
- Bit 5: NPK valid
- Bit 4: pH valid
- Bit 3: Humidity valid
- Bit 2–0: Reserved

## Assembly Guide

### Tools Required
- Soldering iron (fine tip, temperature controlled)
- Hot air rework station (for QFN packages)
- Multimeter
- Oscilloscope (helpful for verifying 555 oscillators)
- ST-Link v2 programmer
- KiCad 8+

### Assembly Steps

1. **PCB fabrication** — Order 4-layer PCB (1.6mm, ENIG finish) from JLCPCB or similar
2. **SMD soldering** — Place all QFN/SOT packages using solder paste and hot air
3. **Through-hole** — Install DS18B20 probes, electrolytic cap, supercapacitor terminals
4. **Sensor assembly** — Solder capacitive moisture PCBs at depth markers on the stake
5. **ISE installation** — Insert NPK and pH electrodes into waterproof housings at 20 cm depth
6. **Enclosure** — Slide PCB into polycarbonate tube, seal with silicone O-rings
7. **Solar panel** — Mount on top cap, route wires through sealed cable gland
8. **Firmware flash** — Connect ST-Link to SWD pads, flash bootloader + application

### Calibration

1. **Moisture**: Record frequency in air (0% VWC) and in water (100% VWC), update flash calibration table
2. **pH**: Immerse in pH 4.0 and pH 7.0 buffer solutions, record ADC values, store calibration
3. **NPK**: Use standard solutions (100 ppm each), record mV readings, compute Nernst slope

## API Reference

### Serial Debug Interface (115200 baud, 8N1)

```
SOIL> status
  VCAP: 3.42V
  MOIST10: 34.2%  MOIST20: 28.7%  MOIST40: 22.1%
  TEMP10: 18.3C   TEMP20: 16.9C   TEMP40: 15.4C
  NO3: 45.2 ppm    PO4: 12.8 ppm   K: 187.3 ppm
  PH: 6.4          RH: 62%
  LAST_TX: 1420s ago

SOIL> cal moisture 10 air
  Moisture 10cm air: 21834 Hz → stored

SOIL> cal moisture 10 water
  Moisture 10cm water: 48291 Hz → stored

SOIL> cal ph 4.0
  pH 4.0: ADC=8234 → stored

SOIL> cal ph 7.0
  pH 7.0: ADC=13201 → stored

SOIL> sample now
  Sampling... done
  MOIST10: 31.5%  MOIST20: 26.1%  MOIST40: 19.8%
  ...

SOIL> lora join
  Joining... accepted (DevAddr: 260BFFA1)

SOIL> lora tx
  TX on port 2, 21 bytes... done
```

### LoRaWAN Decoded Payload (Python)

```python
from dataclasses import dataclass

@dataclass
class SoilWhisperPayload:
    moisture_10: float  # % VWC
    moisture_20: float  # % VWC
    moisture_40: float  # % VWC
    temp_10: float       # °C
    temp_20: float       # °C
    temp_40: float       # °C
    no3: float           # ppm
    po4: float           # ppm
    k: float             # ppm
    ph: float            # pH
    humidity: float      # %RH
    vbat: float          # V

    @classmethod
    def decode(cls, data: bytes):
        flags = data[0]
        m10 = int.from_bytes(data[1:3], 'little') * 0.01
        m20 = int.from_bytes(data[3:5], 'little') * 0.01
        m40 = int.from_bytes(data[5:7], 'little') * 0.01
        t10 = int.from_bytes(data[7:9], 'little', signed=True) * 0.01 - 40
        t20 = int.from_bytes(data[9:11], 'little', signed=True) * 0.01 - 40
        t40 = int.from_bytes(data[11:13], 'little', signed=True) * 0.01 - 40
        no3 = int.from_bytes(data[13:15], 'little') * 0.1
        po4 = data[15] * 2.0
        k   = int.from_bytes(data[16:18], 'little') * 0.1
        ph  = data[18] * 0.1
        rh  = data[19] * 0.4
        vbat = data[20] * 0.02
        return cls(m10, m20, m40, t10, t20, t40, no3, po4, k, ph, rh, vbat)
```

## Physical Layout

```
  ┌─────────────────────┐
  │  Solar Panel (6V)   │  ← Top cap, above ground
  ├─────────────────────┤
  │  SHT40 (humidity)   │  ← 2 cm above ground
  ╞═════════════════════╡  ← Ground level
  │                     │
  │  ╔═══╗ Moisture 1  │  ← 10 cm depth
  │  ║   ║ Temp 1      │
  │                     │
  │  ╔═══╗ Moisture 2  │  ← 20 cm depth
  │  ║   ║ Temp 2      │
  │  ║   ║ NPK probes   │
  │  ║   ║ pH electrode │
  │                     │
  │  ╔═══╗ Moisture 3  │  ← 40 cm depth
  │  ║   ║ Temp 3      │
  │                     │
  │  [PCB + Supercap]   │  ← 30-50 cm (center of stake)
  │                     │
  ╘═════════════════════╛

  Polycarbonate tube: Ø 50mm × 600mm
  Probe tabs exposed at depth markers through sealed windows
```

## License

MIT — build it, deploy it, improve it.