# Visco Shear — Assembly Guide

## Overview

This guide walks through the complete assembly of the Visco Shear pocket rheometer, from PCB fabrication to mechanical assembly and calibration.

## 1. PCB Fabrication

### Specifications
- **Size**: 30 × 80 mm, 4-layer
- **Layer stack**: Signal / GND / PWR / Signal
- **Min trace**: 0.12 mm (5 mil)
- **Min via**: 0.25 mm / 0.15 mm drill
- **Surface finish**: ENIG (recommended for Hall sensor pads)
- **Solder mask**: Black or blue

### Ordering
Upload the Gerber files from `schematic/` to JLCPCB, PCBWay, or OSH Park. 5 boards cost ~$4–8.

## 2. Component Sourcing

All parts are listed in `hardware/BOM.csv`. Key sources:
- **RP2040**: Mouser, Digi-Key (~$1.00)
- **ADS1115**: Digi-Key (~$4.20)
- **TMC2209**: AliExpress (module form, ~$3.50)
- **DRV5053**: Digi-Key (~$1.20 each, need 2)
- **NEMA8 stepper**: AliExpress (~$8.00)
- **Peltier TEC1-12706**: AliExpress (~$3.20)
- **OLED SH1106**: AliExpress (~$3.50)

Total BOM: ~$67

## 3. PCB Assembly

### 3.1 Surface Mount Components
1. Apply solder paste with a stencil
2. Place components (RP2040, ADS1115, ESP32-C3, TMC2209, DRV8833, passives)
3. Reflow in a hot-air oven or with a hot-air gun
4. Inspect under microscope for bridges

### 3.2 Through-Hole / Module Components
1. Solder TMC2209 module (if using breakout board)
2. Solder OLED module (1.3" SH1106 I2C)
3. Solder microSD socket
4. Solder USB-C receptacle
5. Solder buttons, buzzer, LEDs

### 3.3 External Connections
1. Solder NEMA8 stepper motor wires (4 leads: A1, A2, B1, B2)
2. Solder DRV5053 Hall sensors (2×) on the mechanical assembly
3. Solder Peltier TEC1-12706 leads
4. Solder NTC thermistor leads
5. Solder battery JST-PH connector

## 4. Mechanical Assembly

### 4.1 Motor Mount
1. 3D-print the motor mount (STL in `docs/stl/`)
2. Mount NEMA8 stepper with 4× M2×6mm screws
3. Attach rotor magnet (N42 6×3mm disc) to motor shaft with cyanoacrylate

### 4.2 Torsion Spring Assembly
1. Install beryllium copper torsion spring in the spring housing
2. Attach stator magnet (N42 6×3mm disc) to spring arm
3. Mount DRV5053 Hall sensor #1 (torque) on the fixed frame, 2mm from spring arm magnet
4. Mount DRV5053 Hall sensor #2 (reference) on the motor mount, 2mm from rotor magnet

### 4.3 Sample Cup
1. Install PEEK cup (Ø14.5mm ID, 0.5mm wall) in the cup holder
2. Bond Peltier TEC1-12706 to the cup base with thermal epoxy
3. Attach heatsink + 40mm fan to Peltier hot side
4. Insert NTC thermistor into the cup wall (thermal paste)

### 4.4 Spindle
1. Select spindle (CC-13, CP-25, VN-16, or TB-3)
2. Insert spindle into magnetic quick-change coupling
3. Lower spindle into sample cup (ensure 1mm clearance from cup bottom)

### 4.5 Enclosure
1. 3D-print the pen-style enclosure (2 halves)
2. Insert PCB assembly
3. Route wires neatly, secure with tape
4. Snap enclosure halves together, secure with M2 screws

## 5. Firmware Flashing

### 5.1 RP2040
```bash
cd firmware
mkdir build && cd build
cmake ..
make -j4
# Method 1: UF2 (hold BOOTSEL, plug USB)
picotool load visco_shear.uf2
# Method 2: SWD (CMSIS-DAP)
openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg \
  -c "adapter speed 5000; program visco_shear.elf verify reset exit"
```

### 5.2 ESP32-C3
```bash
cd firmware/esp32c3
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB1 flash
```

## 6. Calibration

### 6.1 Torque Sensor Zero
1. Power on the device (no spindle installed, motor stopped)
2. The firmware auto-zeros on startup
3. Verify: OLED shows "T: 25.0°C" (no torque offset)

### 6.2 Silicone Oil Calibration (Single-Point)
1. Install CC-13 spindle
2. Add 2.0 mL silicone oil (100 cSt, NIST-traceable) to the cup
3. Set temperature to 25°C, wait for equilibrium
4. Press START → run single-speed measurement at 10 rpm
5. Expected: η ≈ 96 mPa·s
6. If different, run `scripts/calibrate.py` over BLE:
   ```
   CF = 96.0 / measured_eta
   ```
7. CF is stored in RP2040 flash and applied to all future measurements

### 6.3 Two-Point Calibration (Extended Range)
1. Low-viscosity point: water (η = 0.890 mPa·s at 25°C)
2. High-viscosity point: glycerin (η = 1412 mPa·s at 25°C)
3. Run `scripts/calibrate.py --two-point`:
   ```
   η_corrected = a × η_measured + b
   ```

## 7. Verification

### 7.1 Reference Fluids
Test with known fluids from the reference library:
- Water: should read ~0.9 mPa·s (Newtonian)
- Glycerin: should read ~1400 mPa·s (Newtonian)
- Honey: should read ~10,000 mPa·s (shear-thinning)
- Ketchup: should show yield stress ~15 Pa (Herschel–Bulkley)

### 7.2 Temperature Control
1. Set target to 40°C
2. Verify cup reaches 40 ± 0.1°C within 60 seconds
3. Set target to 10°C
4. Verify cooling to 10 ± 0.1°C (with ambient ≤ 25°C)

## 8. Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| No torque reading | Hall sensor wiring | Check DRV5053 connections |
| Motor doesn't turn | TMC2209 config | Verify enable pin LOW, check motor wiring |
| Erratic torque | Magnetic interference | Keep away from ferromagnetic objects |
| Temperature won't reach | Peltier polarity | Swap PELTIER_DIR, check heatsink fan |
| OLED blank | I2C address | Try 0x3C or 0x3D, check wiring |
| BLE not found | ESP32-C3 firmware | Re-flash ESP32-C3, check UART wiring |

## 9. Maintenance

- Clean sample cup with isopropyl alcohol after each use
- Inspect spindle for damage or corrosion
- Re-calibrate torque zero before each session
- Replace 18650 battery when voltage < 3.3V
- Check Peltier heatsink for dust buildup monthly