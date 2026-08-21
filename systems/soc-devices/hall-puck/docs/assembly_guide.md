# Hall Puck — Assembly Guide

## Overview

This guide walks through building the Hall Puck pocket Hall effect & Van der Pauw semiconductor characterization system, including PCB assembly, sample holder construction, magnet rotation mechanism, and firmware flashing.

## Tools Required

- Soldering iron (fine tip, 0.4mm)
- Solder paste + hot-air reflow station (for SMD)
- Multimeter
- Digital caliper
- 3D printer (PETG or PLA)
- Crimp tool for connectors
- ARM GCC toolchain (`arm-none-eabi-gcc`)
- ESP-IDF v5.2+ (for ESP32-C3 companion)
- ST-Link V2 programmer (for STM32G474)
- USB-TTL adapter (for ESP32-C3 flashing)

## 1. PCB Fabrication

Order the 4-layer PCB from JLCPCB or similar:
- **Gerber files**: Generate from `schematic/hall-puck.kicad_pro`
- **Dimensions**: 72mm diameter (circular puck shape)
- **Layer count**: 4 (2 signal + 2 ground/power planes)
- **Copper weight**: 1 oz
- **Surface finish**: ENIG (for fine-pitch components)
- **Minimum trace**: 5 mil / 0.125 mm
- **Impedance**: No special requirements (no high-speed signals)

## 2. Component Placement

### Order of assembly (small to large):

1. **Passives first** (0603 R, C):
   - Decoupling caps: 0.1µF near each IC VCC pin
   - Pull-up resistors: 10kΩ on CS lines, DS18B20 1-wire
   - Precision resistors: 0.1% for Howland current pump (critical!)

2. **SOIC/TSSOP ICs**:
   - U1: STM32G474RET6 (LQFP-64, 0.5mm pitch — use solder paste + reflow)
   - U2: ESP32-C3-MINI-1 (module, hand-solder)
   - U3: ADS122U04 (TSSOP-16, 0.65mm pitch)
   - U4: INA333 (MSOP-8, 0.65mm pitch)
   - U5, U6: ADG714 (TSSOP-16, 0.65mm pitch)
   - U7: OPA2188 (SOIC-8)
   - U8: ULN2003A (SOIC-16)
   - U9: DRV5053 (SOT-23)
   - U10: AP2112K-3.3 (SOT-23-5)
   - U11: TP4056 (SOIC-8)

3. **Connectors**:
   - J4: 4-pin pogo pin receptacles (sample holder)
   - J2: MicroSD push-push socket
   - J3: USB-C 16-pin SMD
   - OLED: FPC connector or direct solder

4. **Mechanical**:
   - M1: 28BYJ-48 stepper motor (mounted on underside, magnet arm)
   - Battery holder (18650 single cell)
   - Tactile buttons (3× 6×6mm)

## 3. Sample Holder Construction

The sample holder is the most critical mechanical component:

### Pogo Pin Assembly
1. Install 4× P75-B2 pogo pin receptacles on the PCB at the sample position
2. Insert pogo pins (P75-B2, 0.68mm tip, 100g spring force)
3. Ensure pins are perpendicular to PCB surface
4. Contact spacing: 10mm default (adjustable rails for 5–20mm)

### Sample Platform
1. Place a thin copper-clad PCB shim under the sample area (thermal platform)
2. Optional: attach polyimide film heater (10Ω) to underside of platform
3. Ensure pogo pins protrude 1–2mm above platform surface

### Sample Mounting
1. Place semiconductor sample (5–20mm square) on platform
2. Pogo pins contact the sample periphery (corners or edges)
3. Sample must be clean — use isopropyl alcohol to remove oxides
4. For thin films: ensure the film side faces the pogo pins
5. For wafers: ensure the doped layer faces the pogo pins

## 4. Magnet Rotation Mechanism

The N52 neodymium magnet (Ø10mm × 5mm) is mounted on a rotating arm below the sample platform:

1. **Motor mount**: 3D-printed bracket for 28BYJ-48 stepper on PCB underside
2. **Magnet arm**: 3D-printed arm (40mm length) that holds the N52 magnet
3. **Magnet position**: Magnet sits 2–3mm below the sample (through PCB cutout)
4. **Rotation range**: 0° (B+ position) ↔ 180° (B- position) ↔ 90° (parked)
5. **DRV5053 sensor**: Mounted on PCB near magnet arm to detect orientation

### Assembly steps:
1. Solder ULN2003A driver IC
2. Mount 28BYJ-48 stepper with 3D-printed bracket
3. Attach magnet arm to stepper shaft
4. Glue N52 magnet into arm pocket (epoxy)
5. Mount DRV5053 sensor near arm path
6. Calibrate 180° rotation: step until DRV5053 reads B+, mark position

## 5. Firmware Flashing

### STM32G474 (main SoC)
```bash
cd firmware
make
# Connect ST-Link V2 to SWD pins (SWDIO, SWCLK, GND, 3V3)
make flash
```

### ESP32-C3 (companion)
```bash
cd firmware/esp32-c3
idf.py set-target esp32c3
idf.py build
# Connect USB-TTL to ESP32-C3 UART pins
idf.py -p /dev/ttyUSB1 flash
```

## 6. Calibration

### B-field calibration (required once):
1. Obtain a reference sample with known Hall coefficient (e.g., n-Si, R_H = -860 cm³/C)
2. Place reference sample on holder
3. Run measurement via BLE: send CMD_CALIBRATE
4. Device measures V_H and computes B = V_H × d / (I × R_H_known)
5. B-field stored in flash automatically

### Current source calibration (recommended):
1. Connect a precision 1kΩ resistor (0.1%) across contacts 1 and 2
2. Force 1mA current (CMD_SET_CURRENT, 1.0)
3. Measure voltage with external DMM across contacts 3 and 4
4. Verify: V = I × R = 1mA × 1kΩ = 1V
5. Adjust if needed via calibration factor in flash

### Voltage offset calibration:
1. Run measurement with no sample (contacts open)
2. Device performs auto-zero (short V+ to V-)
3. Offset stored in flash

## 7. 3D-Printed Enclosure

The enclosure is a puck-shaped cylinder (Ø72mm × 28mm):

- **Top half**: OLED window cutout, 3 button holes, USB-C cutout
- **Bottom half**: Stepper motor mount, battery compartment, sample access opening
- **Material**: PETG (heat resistant, durable)
- **Print settings**: 0.2mm layer height, 30% infill, 4 perimeters

STL files should be generated from the 3D model (not included in this repo — design to match component placement).

## 8. Testing

1. Power on via USB-C or 18650 battery
2. OLED displays "Hall Puck — Ready"
3. BLE advertises as "HallPuck"
4. Wi-Fi AP "HallPuck" visible
5. Place a known sample (e.g., n-Si wafer) on holder
6. Press MEASURE button
7. Device runs: contact check → Van der Pauw → Hall (B+) → Hall (B-) → results
8. OLED displays carrier type, concentration, mobility, resistivity
9. Verify results match expected values for the reference sample