# Terra Pin — Assembly Guide

## Overview

This guide walks through the assembly of the Terra Pin soil microbiome activity probe — a handheld device with a PCB inside a 3D-printed handle, connected to a stainless-steel probe shaft containing the sensor electrodes and CO₂ chamber.

## Tools Required

- Soldering iron (fine tip, 0.4 mm)
- Solder (0.5 mm, 60/40 or lead-free)
- Flux pen
- Tweezers (fine, anti-magnetic)
- Hot-air rework station (for QFN/DFN packages)
- Multimeter
- Heat-shrink tubing (3 mm, 5 mm)
- Epoxy potting compound (for waterproofing probe tip)
- 3D printer (for handle enclosure)
- M2 and M3 taps + hardware

## PCB Assembly

### Step 1: Order PCB and components

- Order the 4-layer PCB (60×25 mm) from PCBWay/JLCPCB using the KiCad gerber files
- Order all components per `hardware/BOM.csv`
- Note: the SCD41 #1 (chamber) is mounted on the **probe tip PCB**, not the main handle PCB

### Step 2: Solder power section

1. **U9 (MCP73831)** — USB-C LiPo charger. DFN-8 package, use hot-air rework with flux paste
2. **U12/U13 (DW01A + FS8205A)** — battery protection. SOT-23-6, hand-solderable
3. **U10 (TPS63020)** — 3.3 V buck-boost. SON-14, use hot-air + solder paste stencil
4. **U11 (TLV70033)** — sensor LDO. SOT-23-5, hand-solder
5. Add all decoupling capacitors (100 nF on each IC, 10 µF on power rails)
6. Add 4.7 kΩ I2C pull-ups, 4.7 kΩ 1-Wire pull-up, 10 kΩ boot strap
7. Add battery voltage divider (2× 100 kΩ 0603)

### Step 3: Solder MCU section

1. **U1 (ESP32-S3-WROOM-1)** — pre-assembled module, hand-solder with generous flux
2. Add 40 MHz crystal (if not using module's internal oscillator)
3. Add USB-C connector **J1** with flux and hot-air
4. Add status LED **LED2** (green 0603)

### Step 4: Solder sensor interfaces

1. **U4 (TCA9548A)** — I2C multiplexer. TSSOP-24, use solder paste + hot-air
2. **U2 (SCD41 ambient)** — DFN-6, very small. Use solder paste stencil + hot-air at 250 °C
   - Add 10 µF decoupling cap on VDD
3. **U7 (DS18B20)** — TO-92, through-hole, easy hand-solder
4. **U8 (SH1106 OLED)** — pre-assembled OLED module, solder with header pins or direct wire

### Step 5: UART sensor connectors

1. Wire **U5 (EZO-ORP)** and **U6 (EZO-EC)** via 4-pin JST-PH connectors
   - These are Atlas Scientific breakout boards, mounted in the probe shaft
   - Pinout: VCC, GND, RX, TX

### Step 6: SD card and user interface

1. **J2 (microSD socket)** — Hirose DM3D, SMD, use solder paste + hot-air
2. **SW1, SW2** — tactile switches, through-hole, easy solder
3. **ENC1 (EC11)** — rotary encoder, through-hole, solder from bottom
4. **LED1 (WS2812B)** — 5050 SMD, hand-solder with flux

### Step 7: Probe tip PCB

The probe tip has a separate small PCB (15×15 mm) containing:
- **U3 (SCD41 #1 chamber)** — same DFN-6 assembly as above
- ORP electrode connector
- EC electrode connector
- Capacitive moisture sensing traces (copper pours on both sides)
- DS18B20 (mounted in shaft wall, wired to main PCB)

Connect the probe tip PCB to the main PCB via a 6-wire ribbon cable:
- 3.3 V, GND, I2C SCL, I2C SDA (for SCD41)
- ORP probe wires (2)
- EC probe wires (2)

## Mechanical Assembly

### Step 1: 3D-print the handle

Print the handle enclosure in PLA or PETG (STL files in `hardware/`):
- Two halves that snap together with M2 screws
- Cutout for OLED (28×28 mm window)
- Cutouts for USB-C port, SD card slot, buttons, encoder
- Battery cavity (60×25×6 mm)

### Step 2: Assemble probe shaft

1. Cut 316 stainless tube to 150 mm length, 18 mm OD, 16 mm ID
2. Drill 3 mm holes at 50 mm, 80 mm, 110 mm from tip for:
   - ORP electrode port (50 mm)
   - EC electrode port (80 mm)
   - DS18B20 mounting (110 mm)
3. Insert ORP and EC electrodes through side ports, seal with epoxy
4. Pot DS18B20 in shaft wall with epoxy (waterproof)
5. Mount SCD41 #1 PCB at the top of the chamber section
6. Install PTFE membrane disc at the bottom opening
   - Use a retaining ring or epoxy to hold the membrane
   - Ensure the membrane is gas-permeable but water-repellent

### Step 3: Mount capacitive moisture plates

The MCB-01-A probe can be replaced by two large copper pours on the
probe tip PCB, separated from soil by soldermask. Alternatively, use
the off-the-shelf MCB-01-A module and mount it on the outside of the
shaft with the sensing face contacting soil.

### Step 4: Final assembly

1. Insert main PCB into handle
2. Connect battery (JST-PH)
3. Route ribbon cable from probe tip PCB through shaft to main PCB
4. Screw handle halves together
5. Insert microSD card
6. Press-fit the probe shaft into the handle

## Waterproofing

- All electronics in the probe tip must be potted in epoxy
- The PTFE membrane is the only gas-path to the SCD41 chamber
- Use marine-grade epoxy for the DS18B20 and electrode ports
- The handle is not waterproof — do not submerge above the shaft joint
- For field use, apply silicone sealant at the shaft-handle junction

## First Power-On

1. Charge battery via USB-C for 2 hours (LED shows charging status)
2. Insert a microSD card (FAT32 formatted, 8–32 GB)
3. Power on — OLED should show "Terra Pin" splash
4. Press MODE to cycle: Point → Continuous → Calibrate
5. In Calibrate mode, follow on-screen prompts for moisture dry/wet calibration
6. In Point mode, press MEASURE to take first reading

## Firmware Flashing

```bash
cd terra-pin/firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

## Testing

1. **SCD41 test** — breathe near the probe tip; chamber CO₂ should rise
2. **ORP test** — dip in ZoBell's solution (228 mV expected)
3. **EC test** — dip in 1413 µS/cm KCl standard
4. **Moisture test** — dry soil → ~0%, saturated → ~100%
5. **Temperature test** — ice water → ~0 °C, body temp → ~37 °C
6. **BLE test** — use nRF Connect or LightBlue to find "Terra Pin"
7. **SD test** — remove card and verify CSV file on computer