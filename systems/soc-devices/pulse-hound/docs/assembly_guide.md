# Pulse Hound — Assembly Guide

## Overview

This guide walks through assembling the Pulse Hound RF Signal Hunter from a bare PCB and components. Estimated time: 3–4 hours with basic soldering skills.

## Tools Required

- Soldering iron (fine tip, 0.4 mm) with leaded or lead-free solder
- Hot-air rework station (for the AD8318 LFCSP-24 package)
- Tweezers (fine-tip, anti-magnetic)
- Magnifying loupe or microscope (10× minimum — the AD8318 has 0.5 mm pitch)
- Multimeter
- 3D printer (for enclosure) or order from a service
- #0 and #1 Phillips screwdrivers
- hobby knife / flush cutters

## PCB Fabrication

Order the 4-layer PCB (50 × 40 mm) from PCBWay, JLCPCB, or similar. Specs:

- **4 layers**: L1 = signal, L2 = GND (solid plane), L3 = PWR (3.3 V), L4 = signal
- **Thickness**: 1.6 mm (for SMA connector mechanical stability)
- **Surface finish**: ENIG (gold) — required for the AD8318 LFCSP package
- **Copper weight**: 1 oz (35 µm) all layers
- **Minimum trace/space**: 6/6 mil (0.15/0.15 mm)
- **Controlled impedance**: 50 Ω microstrip on L1 for the SMA→AD8318 RF path (use a 0.25 mm trace width over the L2 ground plane with 0.2 mm dielectric prepreg)

## Component Placement Order

Solder in this order (smallest to largest, temperature-sensitive last):

### 1. Passive Components (R, C)

1. **R1, R2** (10 kΩ 0.1%, 0603): ADS1115 voltage-divider reference resistors — these set the ADC accuracy, use precision parts
2. **R3** (1 kΩ, 0603): audio RC filter resistor
3. **R4** (10 kΩ, 0603): I²C pull-up resistors (×4, on SDA, SCL lines)
4. **R5** (20 kΩ, 0603): battery voltage divider (×2)
5. **R6** (100 Ω, 0603): LM386 gain-setting resistor
6. **C1** (1 nF C0G, 0402): AD8318 RF input coupling capacitor — **this must be C0G/NP0 dielectric** for low RF loss; place as close to the AD8318 RFIN pin as possible
7. **C2** (10 nF X7R, 0603): AD8318 CLPF loop filter capacitor
8. **C3** (100 nF X7R, 0603): bypass capacitors (×8, one per active IC)
9. **C4** (10 µF X5R, 0805): power rail decoupling (×3: 3.3V, 5V stepper, battery)
10. **C5** (1 µF X5R, 0603): audio RC + TP4056 timing capacitor

### 2. Small ICs (SOIC / MSOP / SOT-23)

11. **U7** (MCP1700-3302, SOT-23-3): 3.3 V LDO — pin 1=GND, pin 2=VOUT(3.3V), pin 3=VIN(battery)
12. **U6** (TP4056, SOP-8): Li-ion charger — orient per silkscreen, tab connects to GND
13. **U4** (LM386, SOIC-8): audio amplifier — pin 1=gain, pin 3=input, pin 5=output, pin 6=VCC, pin 8=gain
14. **U5** (MAX17048, TSSOP-8): fuel gauge — careful with orientation, pin 1=VDD, pin 8=ALRT
15. **U8** (ULN2003, SOIC-16): stepper driver — outputs on pins 11–14, inputs on pins 1–4
16. **Q1** (AO3401, SOT-23): P-channel MOSFET for stepper power-gate (×2)
17. **Q2** (AO3400A, SOT-23): N-channel MOSFET for LED driver
18. **LED1, LED2** (0805): green and red status LEDs

### 3. AD8318 RF Detector (LFCSP-24)

⚠️ **This is the hardest part.** The AD8318 is a 24-pin LFCSP (4 × 4 mm) with 0.5 mm pitch and an exposed pad underneath.

19. Apply solder paste to the footprint (use a stencil or carefully dispense)
20. Place the AD8318 with tweezers — align pin 1 (denoted by a dot on the package) with the silkscreen dot
21. Hot-air reflow at 260 °C for 30 s — the exposed pad must be soldered for thermal and electrical ground
22. Verify with multimeter: continuity from RFIN through C1 to the AD8318 pin; no shorts between VPOS and GND

### 4. ADS1115 ADC (MSOP-10)

23. **U3** (ADS1115, MSOP-10): 16-bit I²C ADC — 0.5 mm pitch, use hot-air or careful iron work
24. Pin 1=VDD, pin 2=AIN0(RSSI), pin 3=AIN1(TEMP), pin 4=GND, pin 5=SCL, pin 6=SDA, pin 7=ADDR, pin 8=ALRT

### 5. ESP32-S3-WROOM-1 Module

25. **U1** (ESP32-S3-WROOM-1): the main SoC module — pre-certified, castellated edges
26. Apply solder paste to the castellated pad footprint
27. Place carefully, align the alignment corner mark
28. Hot-air reflow at 245 °C for 45 s — ensure all castellated pads wet properly
29. Verify: no shorts on 3V3/GND, USB DP/DM continuity to USB-C connector

### 6. Connectors and Mechanical

30. **J1** (SMA connector): solder the center pin first, then the four mechanical ground tabs
31. **J2** (USB-C 16-pin): use solder paste + hot-air; verify VBUS and GND pins
32. **SD1** (micro-SD slot): SMT push-push, solder the shell ground tabs + signal pins
33. **DS1** (SSD1306 OLED): pre-assembled breakout board, solder via header pins or direct wire
34. **SW1** (×3, tactile buttons): MODE, SCAN, DF — solder all four tabs
35. **SW2** (reed switch): home sensor, position adjacent to the stepper magnet path
36. **SP1** (speaker): solder + and − leads to the PCB pads

### 7. Stepper Motor

37. **M1** (28BYJ-48): connect the 5-pin header to the ULN2003 breakout board
38. Mount the stepper to the 3D-printed turret base using 2× M2 screws
39. Attach the directional antenna to the rotating platform on the stepper shaft
40. Glue the neodymium magnet (MAG1) to the rotating platform at the 0° position, aligned with the reed switch

## 3D-Printed Enclosure

Print these parts in PETG or ABS:

| Part | STL File | Notes |
|------|----------|-------|
| Main body | `enclosure_body.stl` | 95 × 55 × 28 mm, OLED window cutout, USB-C cutout |
| Front cover | `enclosure_front.stl` | Speaker grille, 3× button holes |
| Stepper turret | `turret_base.stl` | Mounts 28BYJ-48, rotates with shaft |
| Antenna mount | `antenna_mount.stl` | Attaches directional antenna to turret |

Print settings: 0.2 mm layer height, 3 perimeters, 30% infill, PETG at 230 °C.

## Assembly

1. Insert the assembled PCB into the main body
2. Mount the OLED (breakout board) behind the front window, secure with double-sided tape
3. Mount the speaker behind the grille, secure with hot-melt adhesive
4. Thread the button caps through the front cover
5. Mount the stepper+turret assembly on top, feed the stepper cable through a strain relief
6. Attach the SMA antenna connector (accessible through the top hole)
7. Connect the LiPo battery (1000 mAh, 3-pin with protection), route the cable to avoid pinching
8. Screw the front cover to the main body with 4× M2.5 screws
9. Attach the directional antenna to the turret mount

## Power-Up Test

1. Charge the battery via USB-C for at least 1 hour (red LED = charging, green = full)
2. Power on by pressing MODE button — green LED should light, OLED should display the waterfall
3. Verify: sweep noise floor reads approximately −75 to −80 dBm (no antenna connected, SMA terminated with 50 Ω)
4. Connect the directional antenna — the waterfall should show activity, audio should click slowly
5. Press SCAN button — audio should toggle on/off
6. Press DF button — stepper should rotate 360°, bearing should appear on OLED
7. Point the antenna at a known WiFi router — RSSI should jump to −40 to −60 dBm, clicks should accelerate

## Calibration

See `docs/calibration_guide.md` for the AD8318 RSSI calibration procedure.

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| OLED blank | I²C wiring wrong | Check SDA/SCL, pull-ups, 3.3V |
| RSSI stuck at −80 dBm | AD8318 not powered | Check PWDN pin (GPIO21 = high), AFE_EN (GPIO40) |
| No audio | LM386 shutdown | Check GPIO8 (high = enabled), speaker wiring |
| Stepper doesn't rotate | ULN2003 wiring | Check GPIO14–17, stepper power (GPIO18), 5V supply |
| BLE not advertising | ESP32-S3 firmware | Verify BLE enabled in sdkconfig, antenna connected |
| SD card not logging | SPI wiring | Check GPIO10–13, CS (GPIO13), card formatted FAT32 |
| Battery drains fast | Stepper always on | Check GPIO18 power-gate, firmware must cut power when idle |

## Disassembly

To replace the battery or service the PCB:

1. Remove 4× M2.5 screws from the front cover
2. Carefully lift the front cover (mind the speaker wires)
3. Disconnect the LiPo battery connector
4. The PCB lifts out of the main body

## Safety Notes

- The AD8318 is sensitive to ESD — use a grounded wrist strap when handling the bare IC
- The 28BYJ-48 stepper can get warm during continuous DF operation — normal, not a hazard
- The LiPo battery has a protection circuit — do not bypass it
- The AD8318 max RF input is +10 dBm (10 mW) — do not connect directly to a transmitter output; always use an attenuator if testing near high-power RF sources
- USB-C provides charging only — programming is also via USB-C (CDC serial)