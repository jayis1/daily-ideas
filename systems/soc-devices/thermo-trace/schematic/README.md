# Schematic — Thermo Trace

This folder contains the KiCad project files for the Thermo Trace pocket DSC.

## Files

| File | Description |
|------|-------------|
| `thermo_trace.kicad_pro` | KiCad project file |
| `thermo_trace.kicad_sch` | Schematic (symbolic netlist) |
| `thermo_trace.kicad_pcb` | PCB layout (placeholder) |
| `thermo_trace.kicad_prl` | Project local settings |

## Schematic Overview

```
                    ┌─────────────────────────────────────────┐
                    │           STM32G491RET6                  │
                    │         (170 MHz Cortex-M4F)             │
                    │                                          │
   PT1000 sample ──▶│  ADS122U04  │  PID₁ → TIM1 PWM₁ → FET₁  │──▶ Heater₁
   PT1000 ref    ──▶│  (SPI,      │  PID₂ → TIM8 PWM₂ → FET₂  │──▶ Heater₂
   I_sense       ──▶│   24-bit)   │                           │
   V_supply      ──▶│             │  Heat flow = P₁ - P₂       │
                    │             │  Peak detect → ΔH           │
                    │             │  Library k-NN match         │
                    └──┬────┬──────┬────┬──────┬───────────────┘
                       │SPI │I2C   │SPI │UART  │GPIO
                       ▼    ▼      ▼    ▼      ▼
                    ┌─────┐┌────┐┌────┐┌─────┐┌──────┐
                    │OLED ││ SD ││ESP ││Safe ││Buttons│
                    │SH110││card││C3  ││ty   ││×3    │
                    │6    ││    ││BLE ││cmp  ││      │
                    └─────┘└────┘└────┘└─────┘└──────┘
```

## Key Subcircuits

### 1. ADS122U04 24-bit ADC + PT1000 RTD Interface

```
  IDAC (250µA) ──┬── AIN0 ── PT1000 (sample) ── AIN1 ──┐
                 │                                       │
                 └── AIN2 ── PT1000 (ref)    ── AIN3 ──┘

  The ADS122U04 provides:
  - 24-bit resolution
  - Programmable IDAC for RTD excitation (250µA)
  - Internal Vref = 2.048V
  - PGA with gain 1-128
  - 4-channel input MUX
```

### 2. Heater Drive Circuit (per channel)

```
  5V ── Fuse 250°C ── 0.5Ω sense R ── Drain
                                          │
                              MOSFET gate │
                              (IRLZ44N)   │
                                          │
                                         GND

  PWM from TIM1 (10 kHz) → gate driver → MOSFET
  Duty cycle 0-85% max (safety clamp in firmware)
```

### 3. Safety Comparator (TLV3201)

```
  Pan temp thermistor ──┬── TLV3201+ input
                        │
  320°C threshold ref ──┘── TLV3201- input
                               │
                        Output ── PB8 (EXTI)
                               │
                        When output LOW: heater enable GPIO forced LOW
```

### 4. Power Supply

```
  USB-C 5V ── TP4056 ── 18650 LiPo (3.7V)
                      │
                      ├── BQ25883 boost → 5V (heaters, max 0.5W each)
                      │
                      └── AP2112 LDO → 3.3V (MCU, ADC, OLED, ESP32-C3)
```

## Notes

- The PCB layout is a placeholder. A real layout would need careful
  thermal isolation between the DSC heater cells and the PCB/electronics.
- The heater cells should be mounted on a ceramic (Al₂O₃) spacer with
  an air gap to the PCB.
- The ADS122U04 analog inputs should be routed away from the PWM heater
  traces to minimize noise coupling.
- The 5V heater rail should be on a separate plane from the 3.3V logic
  rail, with star-ground topology.