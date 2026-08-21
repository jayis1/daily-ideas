# Fluor Cast — Assembly Guide

## Overview

This guide walks through assembling a Fluor Cast pocket spectrofluorometer from the KiCad schematics, BOM, and 3D-printed parts.

## Tools Required

- Soldering iron (fine tip, temperature-controlled)
- Solder (0.5mm rosin-core, lead-free or leaded)
- Tweezers (ESD-safe, fine tip)
- Magnifier or microscope (for SMD work)
- Multimeter
- ST-Link V2 programmer (for STM32)
- USB-C cable
- MicroSD card (4–32 GB)
- 3D printer (for enclosure and LED wheel)
- Small Phillips screwdriver
- M2 screws and nuts

## PCB Assembly

### Step 1: Order PCB
- Upload `schematic/fluor-cast.kicad_pcb` Gerbers to JLCPCB (or similar)
- Spec: 4-layer, 1.6mm, ENIG finish, 1oz copper
- Order minimum 5 boards (~$2 each)

### Step 2: Solder Components (in order of decreasing size)
1. **STM32G474RET6** (LQFP-64): Align pin 1, tack-solder corners, drag-solder or reflow
2. **TPS63020** (QFN-14): Apply stencil solder paste, place with tweezers, reflow
3. **MCP73831** (SOT-23-5): Hand solder
4. **ESP32-C3-MINI-1** module: Check orientation, solder castellated edges
5. **Passive components** (0603 resistors, capacitors): Use pick-and-place or tweezers
6. **TSL1402R CCD** (DIP-8): Insert in socket or solder directly
7. **OPT101** (DIP-8): Solder directly (precision alignment)
8. **Connectors**: USB-C, MicroSD socket
9. **Through-hole**: DS18B20 (TO-92), OPA548 (TO-220-7), ULN2003 (DIP-16)

### Step 3: Clean and Inspect
- Clean flux residue with isopropyl alcohol
- Inspect all solder joints under magnification
- Check for bridges on fine-pitch ICs
- Verify continuity with multimeter (power rails)

### Step 4: Power Test
- Connect battery (3.7V LiPo) — **do NOT insert yet**
- Check for short circuits between +3V3 and GND, +5V and GND
- Connect USB-C power (without battery)
- Verify: +3V3 rail reads 3.30V ± 0.05V
- Verify: +5V rail reads 5.0V ± 0.1V

## Mechanical Assembly

### Step 5: 3D Print Parts
Print the following (STL files in `docs/`):
1. **Main enclosure** (top + bottom): PETG or ABS, 0.2mm layer
2. **LED wheel**: Holds 8 LEDs + filters in radial slots
3. **Cuvette holder**: Black PTFE or printed in black PETG
4. **Optical bench**: Internal frame holding CCD, grating, slit

### Step 6: Assemble Optical Path
1. Press-fit reflective grating (600 lines/mm) into optical bench mount
2. Install adjustable slit (0.2mm) between cuvette holder and grating
3. Align TSL1402R CCD in its mount — pixel array facing grating
4. Install long-pass filter (320 nm cut-on) between cuvette and slit
5. Mount OPT101 reference photodiode adjacent to LED wheel

### Step 7: Assemble LED Wheel
1. Insert 8 LEDs into wheel slots (255→525 nm, clockwise)
2. Insert bandpass filters in front of each LED
3. Press-fit wheel onto 28BYJ-48 stepper shaft
4. Mount Hall sensor magnet on wheel edge
5. Mount AH49E Hall sensor on PCB at wheel home position

### Step 8: Final Assembly
1. Insert PCB into bottom enclosure
2. Place optical bench + cuvette holder on top
3. Route LED wheel cables
4. Connect 3.7V LiPo battery
5. Install OLED display in front panel cutout
6. Install MicroSD card
7. Screw top enclosure on (M2 screws)

## Firmware Flashing

### Step 9: Flash STM32
1. Connect ST-Link V2 to SWD header (SWDIO, SWCLK, GND, 3V3)
2. Build firmware:
   ```bash
   cd firmware
   mkdir build && cd build
   cmake ..
   make
   ```
3. Flash:
   ```bash
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
     -c "program fluor_cast.bin reset exit 0x08000000"
   ```

### Step 10: Flash ESP32-C3
1. Connect USB-C cable (ESP32-C3 USB CDC)
2. Flash:
   ```bash
   esptool.py --chip esp32c3 --port /dev/ttyUSB0 --baud 460800 \
     write_flash -z 0x0 firmware/esp32/fluor_cast_bridge.bin
   ```

## Calibration

### Step 11: Initial Calibration
1. Prepare 1 µg/mL quinine sulfate in 0.1 M H₂SO₄
2. Fill a UV quartz cuvette (10mm pathlength)
3. Insert cuvette in holder, close lid
4. Run calibration:
   ```bash
   python3 scripts/calibrate.py --port /dev/ttyUSB0
   ```
5. Verify wavelength calibration (quinine peak at 455 nm)
6. Save calibration to device flash

## Testing

### Step 12: Functional Test
1. Fill cuvette with tap water
2. Press button to start scan
3. Verify: OLED shows "EEM Scanning"
4. Wait ~25 seconds
5. Verify: OLED shows result (should match "Tap water" baseline)
6. Check SD card for log file
7. Test BLE connection from phone

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| No power | Battery not connected / reverse polarity | Check battery connector polarity |
| STM32 not programming | SWD wiring / clock config | Verify ST-Link wiring, check 3V3 |
| CCD reads all zeros | CCD not initialized / bad wiring | Check SI, CLK, AO pin connections |
| LED wheel doesn't move | Stepper wiring / ULN2003 | Check coil wiring (A+/B+/A-/B-) |
| No fluorescence signal | Optical misalignment / LED dead | Check LED current, align cuvette |
| SD card error | Card not formatted / bad socket | Format as FAT32, check socket solder |
| BLE not connecting | ESP32 firmware / UART wiring | Flash ESP32, check UART bridge |
| UV LEDs not lighting | Interlock switch | Close lid (reed interlock) |

## Safety

- **UV-C LEDs (255/280 nm)**: Never look at UV LED output directly. The enclosure lid blocks UV when closed. An interlock switch disables all LEDs when the lid is open.
- **LiPo battery**: Use only protected 3.7V cells. Do not short-circuit, puncture, or charge above 4.2V.
- **Chemicals**: Quinine sulfate, ethidium bromide, and pesticides are hazardous. Use appropriate PPE and dispose of properly.