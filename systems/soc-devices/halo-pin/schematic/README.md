# Halo Pin — Schematic

This folder contains the KiCad 8 project files for the Halo Pin pocket
optical particle counter.

## Files

| File | Description |
|------|-------------|
| `halo_pin.kicad_pro` | KiCad project file |
| `halo_pin.kicad_sch` | Schematic (symbol-level netlist) |
| `halo_pin.kicad_pcb` | PCB layout (4-layer, 80×50 mm) |
| `halo_pin.kicad_prl` | Project local settings |

## Schematic Overview

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                          HALO PIN — SCHEMATIC                            │
 │                                                                          │
 │  POWER:                                                                  │
 │  USB-C 5V ─▶ TP4056 ─▶ 18650 3.7V ─▶ MCP1640B ─▶ +5V (blower, laser)    │
 │                                  ─▶ AP2112 ─▶ +3V3D (STM32, ESP32, OLED) │
 │                                  ─▶ LP5907 ─▶ +3V3A (OPT101, analog)    │
 │                                  ─▶ REF3030 ─▶ VREF_3V0 (ADC reference)  │
 │                                                                          │
 │  OPTICAL:                                                                │
 │  NCP500 ─▶ Laser Diode (650nm 5mW) ─▶ scattering chamber                  │
 │     ▲              └─▶ Monitor PD (BPW34) ─▶ ADC2_IN3 (PA6)             │
 │     └─ TIM3_CH1 PWM (PB4)                                               │
 │                                                                          │
 │  OPT101 (photodiode+TIA) ◀─ 90° scattered light ─▶ ADC1_IN1 (PA0) 500ksps │
 │                                                                          │
 │  AIRFLOW:                                                                │
 │  TIM2_CH3 PWM (PB0) ─▶ Blower ─▶ chamber ─▶ exhaust                      │
 │  SDP810 (I2C3) ◀─ differential pressure across flow restrictor           │
 │                                                                          │
 │  AMBIENT:                                                                │
 │  SHT45 (I2C1 @0x44) ─▶ T, RH                                             │
 │  BME280 (I2C1 @0x77) ─▶ Pressure, backup T/RH                            │
 │                                                                          │
 │  STM32G474RET6:                                                          │
 │    ADC1_IN1  (PA0)  ◀─ OPT101 photodiode output                          │
 │    ADC2_IN3  (PA6)  ◀─ Monitor PD (laser power feedback)                │
 │    ADC2_IN4  (PA4)  ◀─ Battery voltage divider                           │
 │    TIM3_CH1  (PB4)  ──▶ NCP500 laser driver SET pin                     │
 │    TIM2_CH3  (PB0)  ──▶ Blower motor PWM                                 │
 │    I2C1      (PA11/PA12) ─▶ SHT45, BME280, SH1106 OLED                   │
 │    I2C3      (PA8/PA9)  ─▶ SDP810 differential pressure                  │
 │    SPI2      (PB13/14/15, PB12=CS) ─▶ MicroSD                            │
 │    USART1    (PA9/PA10) ─▶ ESP32-C3 BLE bridge                           │
 │    GPIO PB5-PB7   ─▶ Rotary encoder (A/B/push)                           │
 │    GPIO PB8       ─▶ Scan button                                         │
 │    GPIO PB9       ─▶ Mode button                                         │
 │    GPIO PB12      ◀─ Reed switch (laser interlock)                       │
 │                                                                          │
 │  ESP32-C3-MINI-1:                                                        │
 │    UART ←─▶ STM32 (USART1)                                               │
 │    BLE 5 GATT server (PM2.5, PM10, histogram, flow, T/RH/P)              │
 │    WiFi 4 (optional: data upload to cloud)                               │
 └──────────────────────────────────────────────────────────────────────────┘
```

## Layer Stack

| Layer | Function |
|-------|----------|
| F.Cu | Signal + components |
| In1.Cu | GND plane (solid) |
| In2.Cu | Power plane (+3V3D, +5V split) |
| B.Cu | Signal + components |

## Design Notes

- **Analog/digital split**: The OPT101 photodiode and its analog trace
  are on a separate analog island powered by LP5907-3.3. The ADC input
  trace (PA0) is kept short (< 20 mm) and shielded by ground pour.
- **Laser safety**: A reed switch on PB12 detects the optical cell cover.
  The firmware refuses to fire the laser if the cover is open.
- **Ground**: Star ground with separate AGND and DGND domains, joined
  at a single point under the STM32.