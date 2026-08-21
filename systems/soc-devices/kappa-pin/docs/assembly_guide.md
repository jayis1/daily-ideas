# Kappa Pin — Assembly Guide

## Overview

This guide walks through building the Kappa Pin pocket thermal conductivity meter, including PCB assembly, probe construction, firmware flashing, and calibration.

## Tools Required

- Soldering iron (fine tip, 0.4mm)
- Solder paste + hot-air reflow station (for SMD)
- Multimeter
- Precision scale (0.01g)
- Digital caliper
- 3D printer (PETG or PLA)
- Crimp tool for JST-XH connector
- ESP-IDF v5.2+ development environment

## 1. PCB Fabrication

Order the 2-layer PCB from JLCPCB or similar:
- **Gerber files**: Generate from `schematic/kappa-pin.kicad_pro`
- **Dimensions**: 28 × 80 mm
- **Layer count**: 2 (signal + ground plane)
- **Copper weight**: 1 oz
- **Surface finish**: ENIG (for fine-pitch components)
- **Minimum trace**: 6 mil / 0.15 mm

## 2. Component Placement (Top Layer)

### Order of assembly (small to large):

1. **Passives first** (0603 R, C):
   - Decoupling caps: 0.1µF near each IC VCC pin
   - Pull-up resistors: 10kΩ on CS lines, ID resistor divider
   - Voltage divider resistors for heater Vmon

2. **SOIC/TSSOP ICs**:
   - U1: ESP32-S3-WROOM-1 module (hand-solder or reflow)
   - U2: ADS122U04 (TSSOP-16, 0.65mm pitch — use solder paste + reflow)
   - U3: MCP4131 (DIP-8 or SOIC-8)
   - U4: OPA548 (SOIC-8, high-power — ensure good thermal pad)
   - U5: TP4056 (SOIC-8)
   - U6: AP2112K-3.3 (SOT-23-5)

3. **Power components**:
   - Q1: IRFZ44N MOSFET (TO-220, through-hole or SMD variant)
   - R_SENSE: 0.5Ω precision resistor (1% or better)
   - Inductor for TP4056 charge path (if applicable)

4. **Connectors**:
   - J1: JST-XH 5-pin (probe connector)
   - J2: MicroSD push-push socket
   - J3: USB-C 16-pin SMD
   - OLED: FPC connector or direct solder

5. **Mechanical**:
   - Battery holder (18650 single cell)
   - Tactile buttons (3× 6×6mm SMD or THT)

## 3. Probe Construction

### Needle Probe (NP-100) — for soil, granular, polymers

**Materials:**
- 18G stainless hypodermic needle, 100mm × Ø1.2mm
- 36 AWG nichrome wire, 80mm length
- PT1000 4-wire RTD element (thin-film, 2×2mm)
- Thermally conductive epoxy (MG Chemicals 8329TC)
- 5-pin JST-XH connector + 5-conductor PTFE wire (30 AWG)

**Steps:**
1. Cut hypodermic needle to 100mm, deburr ends
2. Thread nichrome heater wire through needle (80mm active length, ~1.0Ω)
3. Position PT1000 RTD at midpoint of heater wire (50mm from tip)
4. Wire 4-wire RTD: 2 excitation + 2 sense leads
5. Fill needle with thermally conductive epoxy (vacuum degas if possible)
6. Cure epoxy per manufacturer spec (typically 24h at 25°C or 2h at 80°C)
7. Solder 5-pin JST-XH connector: pin1=heater+, pin2=heater−, pin3=RTD_exc+, pin4=RTD_sense+, pin5=RTD_sense−
8. Add 0Ω ID resistor between pin5 and GND (needle = 0Ω)

**Verification:**
- Measure heater resistance: should be ~1.0Ω at 25°C
- Measure RTD resistance: should be ~1000Ω at 25°C
- Check 4-wire continuity: all leads should have < 1Ω connection

### Hot-Wire Probe (HW-60) — for liquids

**Materials:**
- 25µm platinum-tungsten wire, 60mm length
- PTFE fork support frame (3D printed)
- 5-pin JST-XH connector

**Steps:**
1. 3D print PTFE fork frame with two prongs 60mm apart
2. Solder Pt-W wire across prongs (taut, no sag)
3. Wire as combined heater+sensor: heater current = sense current
4. Measure wire resistance (~30Ω at 25°C) and record
5. Add 10kΩ ID resistor for probe detection
6. Waterproof all solder joints with epoxy

### Surface Probe (SP-40) — for flat materials

**Materials:**
- Kapton flexible heater, 40×6mm, ~15Ω
- PT1000 RTD (thin-film)
- Foam backing pad
- 5-pin JST-XH connector

**Steps:**
1. Bond Kapton heater to contact face
2. Mount PT1000 RTD centered on heater
3. Attach foam backing for spring-loaded contact
4. Wire 5-pin connector with 22kΩ ID resistor

## 4. Firmware Flashing

```bash
# Install ESP-IDF v5.2+
# https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32s3/get-started/

cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
# or on Windows: idf.py -p COM3 flash monitor
```

First boot will:
- Initialize all peripherals
- Detect connected probe
- Start BLE advertising as "KappaPin"
- Start Wi-Fi AP "KappaPin-XXXX" (open)

## 5. 3D-Printed Enclosure

**STL files**: print in PETG for temperature resistance.

- **Body**: Ø28mm × 120mm tube, wall 1.5mm
- **Cap**: threaded end cap with USB-C cutout
- **Probe holder**: side clip for probe storage
- **Button extensions**: 3× tactile button plunger extensions

Print settings:
- Layer height: 0.2mm
- Infill: 30% gyroid
- Wall count: 3
- Material: PETG (for thermal stability near heater)

## 6. Initial Calibration

### Step 1: Probe resistance calibration
1. Connect needle probe
2. Power on device
3. Using a precision multimeter, measure heater wire resistance at 25°C
4. Update via BLE command or menu → set heater R

### Step 2: RTD calibration (ice point)
1. Prepare ice-water bath (0°C, well-stirred)
2. Immerse probe tip
3. Wait 2 minutes for equilibrium
4. Read displayed temperature — should be 0.00 ±0.05°C
5. If offset > 0.1°C, adjust R₀ in flash config

### Step 3: Thermal conductivity calibration (glycerin)
1. Prepare pure glycerin (USP grade) in a beaker, 25°C water bath
2. Connect hot-wire probe (HW-60)
3. Select material: "Liquid"
4. Press MEASURE
5. Wait for measurement to complete (~30 seconds)
6. Read λ — should be 0.292 W/m·K ±5%
7. Calibration factor: CF = 0.292 / λ_measured
8. Store via BLE: `calibrate.py --factor CF`

### Step 4: Verification
Test against known materials:
- Distilled water: λ = 0.598 W/m·K at 20°C
- Dry sand: λ = 0.15–0.25 W/m·K
- Styrofoam: λ = 0.033 W/m·K

## 7. Operation

1. Insert probe into material (full immersion for liquids, insert 80mm for soil)
2. Wait for thermal equilibrium (device displays "wait...")
3. Press MEASURE button
4. Wait for measurement cycle (~1–2 minutes depending on material)
5. Read λ, α, ρcₚ on OLED
6. Data is auto-logged to SD card
7. View live data on phone via BLE or Wi-Fi web UI

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| No probe detected | Connector loose | Check JST-XH connection |
| λ too high | Poor contact, convection | Use thermal grease; reduce ΔT |
| λ too low | Probe not fully inserted | Ensure full active length in material |
| Noisy readings | EMI, ground loops | Use shielded probe cable; star ground |
| Heater overcurrent | Short in probe | Check heater resistance; replace probe |
| BLE not connecting | NimBLE stack issue | Restart device; check `idf.py monitor` |
| SD card error | Format issue | Format as FAT32, 32KB cluster |