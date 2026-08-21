# Volt Scribe — Assembly & Calibration Guide

## Overview

This guide covers PCB assembly, initial testing, and calibration of the Volt Scribe portable electrochemical workstation.

## PCB Assembly

### Tools Required

- Soldering iron (temperature-controlled, ≤350°C for lead-free)
- Solder (0.5 mm, Sn96.5/Ag3.0/Cu0.5 or Sn63/Pb37)
- Flux pen
- Tweezers (ESD-safe, fine tip)
- Multimeter
- Hot air rework station (for QFN/LFCSP packages)
- Magnification (stereo microscope recommended)

### Assembly Order

Assemble in this order to facilitate testing at each stage:

#### Stage 1: Power Supply
1. **U9** — TPS63020 buck-boost (VQFN-12) — 3.3V main rail
2. **U10** — MCP73871 LiPo charger (MSOP-10)
3. **U11** — TPS61041 boost converter — +5V analog rail
4. **U12** — LM27761 inverting charge pump — -5V analog rail
5. **U7** — REF3030 voltage reference (SOT-23-3) — 2.048V reference
6. All power passives (inductors, capacitors, resistors)
7. **Test**: Verify 3.3V, +5V, -5V, and 2.048V rails with multimeter

#### Stage 2: Digital Core
1. **U1** — STM32G491RET6 (LQFP-64)
2. **Y1** — 8 MHz crystal + load capacitors (C5, C6 = 22 pF)
3. **Y2** — 32.768 kHz RTC crystal
4. Decoupling capacitors (C1–C4, C7–C8)
5. **Test**: Connect ST-Link, verify MCU is detected via SWD

#### Stage 3: Analog Front-End
1. **U3** — AD8606ARDZ dual op-amp (control amplifier + RE buffer)
2. **U4** — OPA196ID TIA op-amp
3. **U6** — ADG1606BCPZ analog switch (TIA range select)
4. **R2–R8** — TIA feedback resistors (100 MΩ to 100 Ω, 0.1% thin film)
5. **C10–C15** — TIA compensation capacitors
6. **R1** — CE current-limiting resistor (100 Ω)
7. **C15** — EIS AC coupling capacitor (10 µF)
8. **Test**: Power up analog rails, verify op-amp bias points

#### Stage 4: ADC & Reference
1. **U5** — ADS1115IDGSR (VSSOP-10) — 16-bit current ADC
2. **Test**: Read ADS1115 ID register over I2C

#### Stage 5: Communication & Display
1. **U2** — ESP32-C3-MINI-1 module
2. **U8** — SSD1306 OLED display module
3. **J1** — USB-C receptacle
4. **J3** — MicroSD card slot
5. **Test**: Verify OLED displays splash screen

#### Stage 6: Connectors & Controls
1. **J2** — 3.5 mm TRS jack (CE/RE/WE electrodes)
2. **SW1** — Rotary encoder (PEC11)
3. **SW2, SW3** — Tactile buttons
4. **BT1** — LiPo battery connector

### Soldering Notes

- The **100 MΩ feedback resistor (R2)** requires special handling — use PTFE-insulated wiring if not on PCB, and guard ring around the pad.
- The **AD8606** and **OPA196** are sensitive to contamination — clean flux thoroughly after soldering.
- The **STM32G491RET6** LQFP-64 has 0.5 mm pitch — use flux and drag-solder technique.
- The **ADG1606BCPZ** LFCSP-24 package requires hot air rework.

## Calibration

### 1. Voltage Reference Calibration

Connect a calibrated 6½-digit DMM to the REF3030 output:
- Expected: 2.048V ±2 mV
- If out of spec, check VDDA filtering

### 2. DAC Setpoint Calibration

Use the CLI to set known voltages:
```
VS> set potential_start 0.000
VS> mode amperometric
VS> set potential 0.000
```
Measure at the CE output with DMM. Adjust DAC calibration constants in firmware.

### 3. TIA Current Calibration

For each of the 7 ranges:
1. Connect a precision resistor (1% or better) between WE and CE
2. Apply a known voltage
3. Measure the reported current
4. Calculate calibration factor: `cal_factor = I_expected / I_measured`
5. Store in flash

| Range | R_f | Test Resistor | Test Voltage | Expected Current |
|-------|-----|---------------|--------------|-----------------|
| 1 nA | 100 MΩ | 100 MΩ | 0.1 V | 1 nA |
| 10 nA | 10 MΩ | 10 MΩ | 0.1 V | 10 nA |
| 100 nA | 1 MΩ | 1 MΩ | 0.1 V | 100 nA |
| 1 µA | 100 kΩ | 100 kΩ | 0.1 V | 1 µA |
| 10 µA | 10 kΩ | 10 kΩ | 0.1 V | 10 µA |
| 100 µA | 1 kΩ | 1 kΩ | 0.1 V | 100 µA |
| 10 mA | 100 Ω | 100 Ω | 0.1 V | 1 mA |

### 4. Electrochemical Cell Test

Use a known standard:
- **Ferrocyanide/Ferricyanide** (K₃Fe(CN)₆ / K₄Fe(CN)₆) in 0.1 M KCl
- Expected: reversible one-electron couple, E₀ ≈ +0.36 V vs. Ag/AgCl
- ΔE_p should be ~59 mV at 25°C for a reversible system

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No current reading | TIA range too high | Auto-range or switch to more sensitive range |
| Noisy baseline | Poor reference electrode | Check RE connection, add RE stabilizing capacitor |
| Oscillating signal | TIA instability | Increase compensation capacitor, reduce bandwidth |
| Wrong potential | DAC calibration error | Re-calibrate DAC setpoint |
| SD card not detected | SPI wiring issue | Check SD card CS, clock, and power |
| BLE not connecting | ESP32-C3 firmware | Flash ESP32-C3 with BLE relay firmware |

## Safety

- The CE electrode can source/sink up to ±10 mA at ±5V compliance — sufficient to cause tingling or skin irritation
- Never connect electrodes to the human body without proper safety isolation
- Always disconnect the cell before adjusting wiring
- The LiPo battery must not be short-circuited, punctured, or charged above 4.2V