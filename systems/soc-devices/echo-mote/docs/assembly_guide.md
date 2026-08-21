# Echo Mote — Assembly Guide

## Overview

This guide walks you through assembling the Echo Mote room acoustic analyzer from components to a working device.

## Tools Required

- Soldering iron with fine tip (0.5 mm)
- Solder wire (0.5 mm, 60/40 or lead-free)
- Flux pen
- Tweezers (ESD-safe, fine tip)
- Magnifying lens or microscope
- Multimeter
- USB-C cable
- Computer with ESP-IDF v5.3+ installed

## PCB Specifications

- **Size**: 85 × 54 mm
- **Layers**: 4 (Signal/Ground/Power/Signal)
- **Thickness**: 1.6 mm FR4
- **Finish**: ENIG (recommended for fine-pitch components)
- **Solder mask**: Matte black (or any color)
- **Silkscreen**: White

## Assembly Order

### Step 1: SMD Passive Components (0402)

Start with the smallest components first. Place and solder:

1. **I²C pull-ups**: 4.7 kΩ on SDA (GPIO15) and SCL (GPIO16) lines
2. **USB CC pull-downs**: 5.1 kΩ on CC1 and CC2 lines
3. **Decoupling capacitors**: 100 nF on each VDD pin (ESP32-S3, BME280, ICS-43434, MAX98357A)
4. **Bulk decoupling**: 10 µF ceramic near ESP32-S3 VDD
5. **Battery voltage divider**: 100 kΩ + 100 kΩ on VBAT_SENSE line
6. **MCP73831 PROG resistor**: 2 kΩ to GND (sets 500 mA charge current)
7. **NTC bias resistor**: 10 kΩ in series with NTC to VDD

**Tip**: Use a stencil for solder paste if you have one. Otherwise, apply flux and solder one pad, position the component with tweezers, reflow the solder, then solder the other pad.

### Step 2: Small SMD ICs

1. **MCP73831** (SOT-23-5) — LiPo charger
   - Pin 1 (STAT): faces toward ESP32-S3
   - Check orientation marker (dot on pin 1)

2. **AP2112-3.3** (SOT-223) — LDO
   - Tab is pin 2 (GND), faces down
   - Align with silkscreen outline

3. **WS2812B-2020** — Status LED
   - Mark on pin 1 (DIN)
   - Very small — use microscope

### Step 3: MEMS Microphones (ICS-43434)

**Critical**: These are the most important components for acoustic accuracy.

1. **Left mic (U2)** — position at top-left, aligned with acoustic port hole
2. **Right mic (U3)** — position 40 mm to the right of U2
3. Orientation: align the port hole (small circular opening) with the PCB acoustic port
4. The MEMS port must be centered over the PCB hole for unobstructed sound entry
5. Solder carefully — do not get flux or solder in the acoustic port

**Tip**: Solder one corner pad, check alignment under magnification, then solder remaining pads.

### Step 4: MAX98357A Amplifier (QFN-16)

1. Apply solder paste to all pads
2. Position the QFN package carefully — pin 1 dot aligns with silkscreen
3. Reflow with hot air or reflow oven
4. Inspect for solder bridges under microscope
5. Clean flux residue from under the package

### Step 5: BME280 Sensor (LGA-8)

1. Apply solder paste to pads
2. The LGA package has no visible pins — align by package outline
3. The pin-1 marker (beveled corner or dot) should match silkscreen
4. Reflow and inspect for tombstoning

### Step 6: ESP32-S3-WROOM-1 Module

1. This is the largest and most expensive component — take your time
2. Apply solder paste to the module footprint pads
3. Position the module — align the pin-1 marker with silkscreen
4. The module has castellated edge pads — ensure all are properly soldered
5. Reflow with hot air or reflow oven
6. Inspect all edge pads for proper wetting
7. **Do not apply pressure** to the module during reflow (the metal shield can deform)

### Step 7: USB-C Connector

1. Apply solder paste to SMD pads
2. Position the connector flush with the PCB edge
3. The through-hole mounting tabs provide mechanical strength — solder these after the SMD pads
4. Check that the port is aligned with the enclosure cutout

### Step 8: LCD Module (ST7789V)

The LCD module is a pre-assembled unit with a flex cable:

1. Solder the 8-pin header (supplied with the module) to the PCB
2. The LCD sits on top of the speaker area — use 4× M2 standoffs (6 mm)
3. Connect via the pre-soldered flat flex cable
4. The backlight pin (GPIO14) is PWM-controllable for dimming

### Step 9: Speaker

1. Place the 28 mm speaker in the center cutout
2. The speaker frame has mounting tabs — secure with 4× M1.6 screws or adhesive
3. Connect the speaker wires to the MAX98357A output pads (SPK+ and SPK-)
4. Ensure the speaker cone faces upward (toward the LCD)
5. Add a thin bead of hot glue around the speaker frame for acoustic sealing

### Step 10: Battery

1. Connect the 800 mAh Lipo pouch battery to the battery pads
   - Red wire → VBAT+
   - Black wire → GND
2. Secure the battery with double-sided tape to the bottom of the PCB
3. The battery sits in the pocket area between the component side and the bottom

### Step 11: Buttons

1. Solder the 3 tactile switches on the right edge
2. Orientation: the actuator (button top) should face outward
3. Check continuity with a multimeter — buttons should read open (no connection) when not pressed

## Post-Assembly Checks

1. **Visual inspection**: Check all solder joints under magnification
2. **Continuity test**: Verify no shorts between VDD and GND
3. **Current test**: Apply 5 V via USB-C and measure current draw — should be < 50 mA at idle (no LCD)
4. **Voltage test**: Measure 3.3 V rail — should be 3.25–3.35 V

## First Boot

1. Connect USB-C to a computer
2. Flash firmware (see Getting Started in README.md)
3. The LCD should show "ECHO MOTE" after boot
4. Press MODE to cycle through measurement modes
5. Press MEASURE to start your first acoustic measurement

## Acoustic Calibration

After assembly, calibrate the speaker output:

1. Place the Echo Mote and a reference SPL meter 1 m apart in a quiet room
2. Hold MEASURE for 3 seconds (enters calibration mode)
3. The device plays a 1 kHz tone at maximum volume
4. Use the USB-C console: `cal spm <measured_dB>`
5. The offset is stored in NVS and applied to all future measurements

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No LCD display | SPI wiring wrong | Check GPIO9-14 connections |
| No sound from speaker | AMP_SD stuck low | Check GPIO20, try `gpio_set_level(20, 1)` |
| Mic levels very low | Acoustic port blocked | Check MEMS port alignment, clean flux |
| Wi-Fi won't connect | Antenna area blocked | Keep PCB area near ESP32 antenna clear of copper |
| Battery not charging | MCP73831 not enabled | Check PROG resistor (2 kΩ), USB 5V present |
| RT60 seems wrong | Room too quiet or noisy | Ensure speaker volume is ~75 dB SPL at 1 m |

## Enclosure (Optional)

A 3D-printed snap-fit enclosure is available in `hardware/enclosure/`:

- Print in PETG or PLA
- Two-part design: top (LCD window + speaker grille) and bottom (battery compartment)
- Acoustic port slots on top edge for microphones
- USB-C cutout on top edge
- Rubber feet inserts on bottom

---

*Echo Mote Assembly Guide — SoC Device Inventions*