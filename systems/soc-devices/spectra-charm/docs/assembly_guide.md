# Spectra Charm — Assembly Guide

## Overview

This guide walks you through assembling a Spectra Charm pocket UV-Vis spectrophotometer from components. The PCB is a 4-layer FR4 board, 85 × 54 mm, 1.6 mm thickness, ENIG finish.

## Tools Required

- Soldering iron with fine tip (0.5 mm or smaller)
- Solder paste + hot air rework station (for QFP and QFN parts)
- Digital multimeter
- USB-C cable
- 10 mm path length PMMA cuvette
- Deionized water for calibration
- Potassium dichromate standard solution (for wavelength verification)

## PCB Specifications

| Parameter | Value |
|-----------|-------|
| Layers | 4 (Signal/Ground/Power/Signal) |
| Thickness | 1.6 mm |
| Copper weight | 1 oz (35 µm) outer, 0.5 oz inner |
| Finish | ENIG (Electroless Nickel Immersion Gold) |
| Minimum trace/space | 0.1/0.1 mm |
| Minimum via | 0.3 mm drill, 0.6 mm pad |
| Impedance | 50 Ω controlled (USB D+/D-) |

## Assembly Steps

### Step 1: Solder Paste Application

1. Order a solder paste stencil (0.1 mm thick stainless steel)
2. Apply lead-free solder paste (SAC305, type 4 for fine-pitch)
3. Inspect paste deposits under magnification — especially the 0.4 mm pitch STM32G491 QFP

### Step 2: Place Components (Bottom Side)

1. Place USB-C receptacle (J1) — this is the only bottom-side component
2. Reflow bottom side first

### Step 3: Place Components (Top Side)

Place components in this order (largest to smallest):

1. **ESP32-C3-MINI-1 module** (U2) — align on pads, reflow
2. **SSD1306 OLED display** (U12) — solder 4-pin header
3. **STM32G491RET6** (U1) — LQFP-64, 0.5 mm pitch, align pin 1 dot
4. **AS7343** (U3) — OLGA-24, careful alignment (no leads to inspect!)
5. **TPS63020** (U9) — VSON-10, center thermal pad needs vias
6. **AL8805** (U11) — SOT-23-6
7. **TP4056** (U7) — SOT-23-6
8. **DW01A** (U8) — SOT-23-6
9. **USBLC6-2** (U13) — SOT-23-6
10. **BQ27441** (U6) — CSP-9 (requires hot air, very small!)
11. **W25Q128** (U4) — SOIC-8
12. **24AA02E48** (U5) — TSSOP-8
13. **MOSFETs** (Q1, Q2) — SOT-23
14. **Hall sensor** (H1) — SOT-23
15. **Inductors** (L1: 2.2 µH, L2: 4.7 µH) — 3×3 mm
16. **Crystals** (Y1: 8 MHz, Y2: 32.768 kHz) — 3225 package
17. **Tactile switches** (SW1, SW2) — 6×6 mm
18. **WS2812B** (D3) — 5050
19. **LEDs** (D1: white, D2: UV 365 nm) — through-hole D1, SMD D2
20. **All passives** (R, C) — 0402 size
21. **LiPo battery connector** (J2) — JST-PH 2-pin

### Step 4: Reflow

1. Use a controlled reflow profile (lead-free: peak 250°C, time above liquidus 60-90s)
2. Inspect all joints under magnification
3. Pay special attention to:
   - STM32G491 QFP — check for bridges
   - AS7343 QFN — X-ray if possible (hidden solder joints)
   - BQ27441 CSP — very small, verify alignment
   - TPS63020 VSON — verify center pad soldered

### Step 5: Clean and Inspect

1. Clean with IPA to remove flux residue
2. Inspect under magnification (10× minimum)
3. Check for solder bridges, cold joints, tombstoned passives

### Step 6: Install Mechanical Parts

1. Press-fit the PTFE integrating diffuser into the cuvette well
2. Mount the broadband white LED (D1) in the light source cavity
3. Mount the UV LED (D2) next to it
4. Insert the PMMA cuvette into the well
5. Align the AS7343 sensor aperture with the diffuser output
6. Install the hall sensor magnet on the cuvette holder

### Step 7: Connect Battery

1. Solder the LiPo cell wires to J2 (observe polarity!)
2. Secure the 402020 LiPo cell with double-sided tape

### Step 8: Initial Power Test

1. Connect USB-C power supply
2. Verify 3.3V rail with multimeter
3. Check current draw — should be < 50 mA idle
4. Verify TP4056 is charging (CHG_STAT LED)

### Step 9: Flash Firmware

1. STM32G491: Use SWD (SWDIO/SWCLK pads) with ST-Link
2. ESP32-C3: Use USB-C or UART bootloader
3. Verify both MCUs are running (status LEDs)

### Step 10: Calibration

1. **Dark calibration**: Close cuvette well (no cuvette), press and hold MODE then SCAN
2. **Blank calibration**: Insert cuvette filled with deionized water, select "Blank" from menu
3. **Wavelength verification**: Measure potassium dichromate standard (peak at 350 nm)
4. **Linearity check**: Measure KMnO4 dilution series (0.1, 0.01, 0.001 M)
5. **Stray light check**: Insert 340 nm cutoff filter, measure residual signal

### Step 11: 3D Print and Assemble Case

1. Print PETG top and bottom case halves
2. Install rubber gasket for IP52 seal
3. Snap-fit case together
4. Verify button operation through case

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No power | Battery protection tripped | Short DW01A CS pin momentarily to reset |
| AS7343 reads zero | SPI wiring wrong | Check solder joints, verify chip select |
| High noise | LDO not clean | Check AP2112 output cap (must be low-ESR ceramic) |
| UV LED won't turn on | Hall sensor tripped | Insert cuvette to clear interlock |
| BLE not connecting | Antenna keepout violated | Check copper pour near ESP32 module |
| Wild absorbance values | No blank reference | Run blank calibration first |

## Safety Warnings

- ⚠️ The UV LED emits 365 nm radiation — never look directly at the LED
- ⚠️ The UV LED is interlocked — it should only activate with cuvette inserted
- ⚠️ Do not disassemble the LiPo battery
- ⚠️ Use only the specified USB-C 5V power supply for charging