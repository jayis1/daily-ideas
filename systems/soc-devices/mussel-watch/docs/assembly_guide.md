# Mussel Watch — Assembly Guide

## Overview

The Mussel Watch consists of two physical assemblies connected by a cable:

1. **Submersible sensor head** — clips onto a living mussel, contains the Hall sensor, ADS1115, DS18B20, MS5837, and Atlas DO interface. IP68 potted.
2. **Above-water electronics pod** — contains the nRF52840, SX1262, BME280, SD card, battery, solar charge controller. IP67 sealed.

## Tools Required

- Soldering iron (fine tip, 0.4mm) + lead-free solder
- Heat gun (for SMD rework if needed)
- Multimeter
- KiCad (for viewing the schematic)
- Marine epoxy potting compound (e.g., MG Chemicals 832TC)
- Cyanoacrylate glue + food-safe epoxy (for magnet attachment to shell)
- Titanium clip forming tools (or pre-made clip)
- IP68 cable gland wrench
- Torx screwdrivers (for enclosure)

## Step 1: PCB Assembly

### 1.1 Order the PCB

Fabricate the PCB from the KiCad gerber files. Recommended specs:
- 2-layer, 1.6mm FR4
- HASL or ENIG finish (ENIG preferred for marine environment)
- 1oz copper
- Green or blue soldermask

### 1.2 Solder SMD components (smallest first)

1. **Decoupling capacitors** (C1–C8): 100nF (0805) and 10uF (0805), 4.7uF tantalum
2. **Pull-up resistors** (R1–R8): 4.7k, 100k, 330Ω, 10k (0805)
3. **LEDs** (D2 blue, D3 red): 0805 SMD, orient per footprint markings
4. **DRV5053** (U5): SOT-23, orientation per datasheet dot
5. **ADS1115** (U4): MSOP-10, use solder paste + hot air or fine iron
6. **TCA9548A** (U3): TSSOP-24
7. **SX1262** (U2): QFN-24, requires hot air rework station
8. **MCP73871** (U10): QFN-20
9. **BME280** (U8): LGA package, requires solder paste stencil

### 1.3 Solder through-hole / module components

10. **nRF52840 module** (U1): Raytac MDBT50Q-1M, hand-solder the castellated edges
11. **DS18B20 probe** (U6): waterproof TO-92 probe with 1m cable, solder wires to PCB
12. **MS5837** (U7): SMD, solder to sensor head PCB (separate small board)
13. **Atlas DO EZO** (U9): board-to-board or wire connection
14. **SD card socket** (SD1): SMD, solder with hot air
15. **Schottky diode** (D1): SOD-123
16. **Reed switch** (J1): through-hole or SMD
17. **Tactile button** (SW1): SMD 6mm

### 1.4 Connectors

18. **Solar panel connector** (JST-PH 2-pin)
19. **Battery connector** (JST-PH 2-pin, matched to LiPo)
20. **Cable gland** (M12, IP68) for sensor head cable
21. **SMA connector** for LoRa antenna

## Step 2: Sensor Head Assembly

### 2.1 Titanium clip

Form or purchase a titanium spring clip that grips the mussel shell:
- Two arms: one fixed (Hall sensor side), one riding the mobile valve
- Spring tension: ~0.5N (enough to stay attached, not enough to stress the mussel)
- Non-toxic, non-corroding grade 2 titanium

### 2.2 Mount the Hall sensor

1. Pot the DRV5053 in marine epoxy on the fixed clip arm
2. Position it so the sensing face points toward the opposite valve
3. Route wires through the clip to the sensor head PCB

### 2.3 Attach the magnet

1. Place a 2×2×1mm N52 neodymium magnet on the mobile valve of the mussel
2. Secure with cyanoacrylate, then overcoat with food-safe epoxy
3. The magnet should be directly opposite the Hall sensor when the shell is closed
4. **Important**: do this *gently* — do not stress or harm the mussel

### 2.4 Pot the sensor head

1. Place the ADS1115, TCA9548A (if multi-head), DS18B20, MS5837, and Atlas DO interface in the IP68 enclosure
2. Route the cable to the electronics pod through the cable gland
3. Fill the enclosure with marine epoxy potting compound
4. Allow 24 hours to cure fully
5. Test for water ingress (submerge in water, check for bubbles)

## Step 3: Electronics Pod Assembly

1. Mount the main PCB in the IP67 enclosure
2. Connect the LiPo battery (2000mAh)
3. Connect the solar panel (2W, 5×5cm) to the JST connector
4. Route the LoRa antenna cable out through a gland
5. Route the sensor head cable in through the M12 cable gland
6. Insert a microSD card (8–32GB, FAT32 formatted)
7. Seal the enclosure lid (verify gasket seating)

## Step 4: Power-up Test

1. Verify battery voltage with multimeter (>3.5V)
2. Power on — the blue LED should blink 2× (boot OK)
3. If no calibration is stored, the blue LED blinks 5× (calibration needed)
4. Open the companion app and connect via BLE ("Mussel Watch")

## Step 5: Calibration

See [deployment_guide.md](deployment_guide.md) for full calibration instructions.

## Step 6: Deployment

1. Attach the sensor head clip to the mussel (gently!)
2. Submerge the sensor head to deployment depth
3. Mount the electronics pod above water (pole, buoy, or dock)
4. Ensure the solar panel faces south (northern hemisphere) at ~30° tilt
5. Verify LoRa uplinks appear in the gateway dashboard
6. The device is now operational

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No LED on power-up | Battery dead / wrong polarity | Check battery voltage and connector polarity |
| 5 blinks on boot | No calibration stored | Run two-point calibration via BLE app |
| Gape angle always -1 | Calibration invalid or Hall voltage out of range | Re-calibrate; check DRV5053 wiring |
| No LoRa uplinks | SX1262 not initialized, wrong frequency | Check SPI wiring; verify 868/915 MHz setting for region |
| BLE not visible | SoftDevice not started | Check nRF firmware, verify BLE config |
| Water temp -999 | DS18B20 1-Wire error | Check 4.7k pull-up, probe wiring |
| DO reading -1 | Atlas DO not responding | Check I²C address (0x61), power sequencing |
| Depth -999 | MS5837 error | Check I²C wiring, verify PROM read |
| SD log empty | Card not FAT32 or not seated | Reformat as FAT32, reseat card |