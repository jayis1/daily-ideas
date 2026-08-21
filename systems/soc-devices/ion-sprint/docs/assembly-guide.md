# Assembly Guide — Ion Sprint

## Overview

This guide walks through assembling the Ion Sprint pocket capillary
electrophoresis instrument with contactless conductivity detection
(C4D). The device consists of a main PCB, a C4D detector cell
(off-board), a capillary assembly, and a vial lift mechanism.

## Tools Required

- Soldering iron (fine tip, 0.4 mm)
- Solder paste + hot-air rework station (for QFN/LQFP parts)
- Multimeter
- KiCad (for PCB fabrication)
- 3D printer (for enclosure and C4D cell)
- Tweezers (ESD-safe)
- Magnification (loupe or microscope)

## PCB Assembly

### 1. Power Section
1. Solder U2 (TP4056) — SOIC-8, USB charging
2. Solder U3 (MCP1640B) — SOT-23-5, 3.7→5V boost
3. Solder U5 (AP2112-3.3) — SOT-23-5, digital 3.3V LDO
4. Solder U6 (LP5907-3.3) — SOT-23-5, analog 3.3V LDO
5. Solder U7 (REF3030) — SOT-23-3, 3.0V voltage reference
6. Solder L1, L2 (BLM18PG121 ferrite beads) — 0603
7. Solder C1-C9 (decoupling capacitors)
8. Solder J1 (USB-C receptacle)
9. Solder BT1 (18650 holder, Keystone 1042)

### 2. SoC
1. Apply solder paste to LQFP-64 footprint
2. Place U1 (STM32G474RET6) — align pin 1
3. Reflow with hot air (260°C, 60 s)
4. Inspect for bridges under microscope

### 3. HV Section (Cockcroft-Walton)
**⚠️ HIGH VOLTAGE — up to 30 kV. Read safety notes before proceeding.**

1. Solder U4 (MC34063A) — SO-8, boost oscillator
2. Solder D10-D14 (US1M diodes) — SMA package
3. Solder C20-C23 (1nF 3kV caps) — 1206 package
4. Solder R20 (100MΩ 1%) — 1206 (HV divider top)
5. Solder R21 (10kΩ 1%) — 0603 (HV divider bottom)
6. Solder R22 (1GΩ 5% 3kV) — axial through-hole (bleeder)
7. Solder R23 (100Ω 1%) — 0603 (current sense)
8. Solder U8 (AD8629) — SO-8 (current monitor amp)
9. Solder U9 (TLV3201) — SOT-23-6 (safety comparator)

**HV creepage**: Ensure ≥10 mm clearance between HV traces and
any other net. The PCB should have a 2 mm slot around the CW
multiplier section. Apply conformal coating after assembly and
testing.

### 4. C4D Front End
1. Solder U10 (OPA656) — SO-8, JFET op-amp
2. Solder U11 (BPF 90-110kHz) — SOIC-8, band-pass filter
3. Solder R30, R31 (1MΩ 1%) — 0603, feedback resistors
4. Solder C30 (1nF C0G) — 0603, AC coupling
5. Solder J3 (SMA connectors ×2) — C4D electrode coax

### 5. Memory / Display / BLE
1. Solder U12 (SH1106 OLED) — I2C module (header pins)
2. Solder U13 (ESP32-C3-MINI-1) — castellated module
3. Solder U14 (W25Q128) — SOIC-8, SPI flash
4. Solder J2 (MicroSD socket) — push-push

### 6. Motor Drivers
1. Solder U16 (DRV8833) — HTSSOP-16, stepper driver
2. Solder U17 (DRV8833) — HTSSOP-16, pump driver
3. Solder M1 (NEMA8 stepper) — connector
4. Solder M2 (peristaltic pump) — connector

### 7. Sensors & UI
1. Solder U15 (DS18B20) — TO-92 (BGE temperature)
2. Solder SW1 (EC11 encoder)
3. Solder SW2-SW4 (tactile buttons)
4. Solder SW5 (lid interlock switch)
5. Solder OPT1-OPT2 (TCRT5000 reflective sensors)
6. Solder D1, D2 (LEDs)
7. Solder D3 (WS2812B)

## C4D Detector Cell Assembly

The C4D detector cell is a 3D-printed part that clamps onto the
fused-silica capillary at the detection window.

### Materials
- 2× copper tube electrodes (2 mm inner diameter, 2 mm wide)
- 3D-printed C4D cell body (PLA or PETG)
- RG-178 micro-coax cable (<5 cm each electrode)
- Fused-silica capillary (50 µm ID, 365 µm OD, 25 cm)

### Steps
1. **Remove polyimide coating** at the detection window (20 cm from
   inlet): burn off ~2 mm of polyimide with a lighter or use a
   hot-air gun at 400°C. Clean with isopropanol.

2. **Mount capillary** in the 3D-printed C4D cell groove. The cell
   has a channel that holds the capillary snugly.

3. **Install electrodes**: slide the two copper tube electrodes over
   the capillary at the detection window, 1 mm apart. The cell body
   has slots that position the electrodes precisely.

4. **Solder coax**: solder the inner conductor of each RG-178 cable
   to the copper electrode. Solder the shield to the cell ground
   (the 3D-printed cell has a copper foil ground plane).

5. **Install guard shield**: the middle section between electrodes
   has a driven shield (connected to PB10). Wrap thin copper foil
   around the middle section and connect to the shield cable.

6. **Connect to PCB**: attach the two SMA connectors (J3) to the
   C4D cell coax cables.

## Vial Lift Mechanism

The vial lift uses a NEMA8 stepper with an M3 lead screw (0.5 mm/rev)
to raise/lower the inlet vial for hydrodynamic injection.

### Assembly
1. Mount NEMA8 stepper vertically in the 3D-printed enclosure
2. Attach M3 lead screw (200 mm) to the stepper shaft via coupler
3. Mount the vial carriage on the lead screw (threaded M3 nut)
4. Install limit switch (PC5) at the bottom position
5. Wire stepper to DRV8833 (U16) output: A+/A-/B+/B-
6. Wire limit switch to PC5 (pull-up)

## BGE Reservoir & Pump

1. Mount the peristaltic pump (M2) in the enclosure
2. Connect inlet to BGE reservoir (5 mL vial)
3. Connect outlet to the capillary inlet vial
4. Wire pump to DRV8833 (U17) output

## Testing

### 1. Power Test
- Install 18650 battery (do NOT install capillary yet)
- Connect USB-C, verify TP4056 charging LED
- Measure: AP2112 = 3.3V, LP5907 = 3.3V, REF3030 = 3.0V

### 2. SoC Test
- Connect ST-Link debugger to SWD header
- Flash firmware via OpenOCD: `make flash`
- Verify OLED shows splash screen

### 3. HV Test (NO CAPILLARY)
- **Ensure lid interlock is closed**
- Set HV setpoint to 5 kV via menu
- Verify ADC3 reads ~5 kV (±0.5 kV)
- Verify ADC2 reads <10 µA (no load)
- Set HV to 0, verify bleeder discharges to 0 kV in <1 s

### 4. C4D Test
- Install capillary with BGE (no sample)
- Start a run at 20 kV
- Verify electropherogram is flat (no peaks)
- Inject a 1 mM KCl sample → verify a peak appears at ~68 s

### 5. Safety Test
- Open lid interlock → verify HV refuses to arm
- Short HV output (carefully!) → verify TLV3201 trips at 250 µA
- Verify bleeder discharges HV in <1 s after run

## Enclosure

3D-print the enclosure (STL files in `hardware/`). The enclosure has:
- Main body (holds PCB, battery, motors)
- Lid (with interlock switch)
- C4D cell mount
- Vial bay (holds inlet/outlet vials)
- BGE reservoir slot

## Calibration

After assembly, calibrate:
1. **HV voltage monitor**: measure actual HV with an external HV
   probe, adjust `HV_VMON_DIVIDER` in config.
2. **HV current monitor**: measure actual current with a multimeter
   in series, adjust `HV_IMON_GAIN`.
3. **C4D sensitivity**: run a series of known concentration standards
   (0.1, 0.5, 1.0, 5.0 mM KCl) and verify linearity.
4. **Ion library migration times**: run a mixed cation/anion standard
   under BGE recipe 0, update `lib[]` migration times in `library.c`.
5. **Response factors**: run standards with internal standard (1 mM
   Ba²⁺), update `response_factors[]` in `quant.c`.