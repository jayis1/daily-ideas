# Sap Watch — Assembly & Installation Guide

## Overview

This guide covers PCB assembly, enclosure preparation, probe installation on a tree, and field deployment.

## 1. PCB Assembly

### Required tools
- Soldering iron (fine tip, 0.4 mm) or hot-air rework station
- Solder paste + stencil (recommended for QFN STM32WL55JC)
- Magnification (10× loupe or microscope for QFN-48)
- Multimeter
- SWD programmer (ST-Link V2 or J-Link)
- 18650 Li-ion cell (user-supplied, protected)

### Assembly order

1. **STM32WL55JC (U1, QFN-48)** — solder first. Use solder paste + stencil for the 0.5 mm pitch QFN. If hand-soldering, use flux generously and drag-solder with 0.3 mm solder, then clean with flux remover. Verify no bridges under magnification.

2. **Passives (R, C, L)** — place all 0805/0603 resistors and capacitors. Pay special attention to the four 10 kΩ 0.1 % 25 ppm reference resistors (R1–R4) — these set the thermistor measurement accuracy. Do not substitute with cheaper 1 % parts.

3. **Power management** — TPS63020 (U3, TSSOP-16), MCP73831 (U4, SOT-23-5), MAX17048 (U5, SOT-23-8). The TPS63020 inductor (L1, 2.2 µH) must be rated for ≥2 A saturation current.

4. **Analog front-end** — ADS122U04 (U2, TSSOP-16), INA180 (U8, SOT-23-5), AO3400A (Q1, SOT-23), FDN5618P (Q3, SOT-23-3).

5. **Sensors** — SHT45 (U6, DFN-4), TSL2591 (U7), DS18B20 (U9, TO-92 — through-hole, solder last).

6. **External flash** (optional) — W25Q16JV (U10, SOIC-8). Only needed if you want the full 24 h local log buffer.

7. **Connectors** — U.FL antenna connector (J1), PG7 cable gland (J2), SWD Tag-Connect footprint (J4), USB-C (J3, optional).

8. **Crystal** — 32.768 kHz LSE crystal (CRY1, 3215 SMD). Critical for RTC timing accuracy during deep sleep.

9. **LEDs and buttons** — 3× status LEDs (D1 green, D2 red, D3 amber), 2× tactile switches (S1 program, S2 mode).

10. **Battery holder** — 18650 SMD holder (BAT1). Ensure correct polarity orientation.

### Post-assembly checks

- Power the board from a bench supply at 3.7 V (simulate battery) before inserting a real 18650
- Check 3.3 V rail: should be stable at 3.30 ±0.03 V
- Check I²C bus: scan addresses — should find 0x44 (SHT45), 0x29 (TSL2591), 0x36 (MAX17048)
- Connect SWD programmer and verify the MCU responds (read chip ID)
- Flash firmware and check debug UART output (115200 baud)

## 2. Probe Assembly

The 3-needle probe is the most critical mechanical component. It must be built carefully — incorrect needle spacing will invalidate the heat-ratio measurement.

### Materials
- 3× stainless-steel hypodermic needles, 30 mm × 1.2 mm OD (18 G)
- 1× PTFE core rod, 28 mm × 0.8 mm OD (heater needle insulator)
- 40 Ω constantan wire (0.08 mm dia, ~2 m needed, wound on PTFE core)
- 2× 10 kΩ NTC thermistor (NCP18XH103F03RB, 0805 SMD)
- Thermal epoxy (two-part, thermally conductive)
- 72 °C thermal fuse (one-shot, cylindrical 6×12 mm)
- 6-conductor shielded cable, 1 m (24 AWG, shielded)

### Needle 1 (upstream thermistor, 5 mm above heater)
1. Insert a NCP18XH103F03RB thermistor to 5 mm from the needle tip
2. Fill the needle with thermal epoxy, ensuring the thermistor is centered
3. Solder 2 wires (30 AWG, PTFE-insulated) to the thermistor pads
4. Cure epoxy per manufacturer instructions (typically 24 h at room temp)

### Needle 2 (heater, center)
1. Wind the constantan wire on the PTFE core — measure resistance, target 40 Ω ±5 %
2. Place the thermal fuse in series with the heater coil inside the needle
3. Thread the assembly into the needle, epoxy in place
4. Solder 2 wires: one to the top of the heater, one through the fuse to the bottom

### Needle 3 (downstream thermistor, 10 mm below heater)
1. Identical to Needle 1, but thermistor positioned at 10 mm from tip
2. The asymmetric spacing (5 mm up / 10 mm down) corrects for the known downstream bias of the HRM method

### Spacing verification
Use the included 3D-printed drill guide jig to verify needle spacing:
- Upstream needle tip → heater tip: 5.0 mm ±0.2 mm
- Heater tip → downstream needle tip: 10.0 mm ±0.3 mm
- Needles must be perfectly parallel (within 1° over 20 mm depth)

### Cable assembly
- Solder the 6 probe wires to the shielded cable:
  - Wires 1-2: upstream thermistor (twisted pair)
  - Wires 3-4: heater (twisted pair, heavier gauge — 26 AWG)
  - Wires 5-6: downstream thermistor (twisted pair)
- Connect the cable shield to PCB GND at the enclosure end only

## 3. Enclosure Preparation

1. Drill a 7 mm hole for the PG7 cable gland on one short end of the enclosure
2. Mount the PCB with 4× M2 standoffs (6 mm tall)
3. Route the probe cable through the gland and solder to the PCB probe connector
4. Mount the U.FL antenna connector on the exterior and connect to the PCB U.FL
5. Mount the solar panel on the sun-facing side using the bracket and adhesive
6. Insert the 18650 cell (protected type only — internal PCM required)

## 4. Tree Installation

### Selecting the tree
- Trunk diameter: 8–40 cm DBH (diameter at breast height, 1.3 m)
- Bark thickness: <5 mm (thick bark must be shaved)
- Choose a north-facing or shaded side to avoid direct sun heating the probe

### Drilling probe holes
1. Use the 3D-printed drill guide jig clamped to the trunk at 1.3 m height
2. Drill three 1.0 mm pilot holes at the correct 5/10 mm spacing, 20 mm deep into the sapwood
3. Verify depth with the depth gauge on the drill guide
4. Do not drill deeper than the sapwood depth (check with an increment core first)

### Inserting the probe
1. Apply a small amount of thermal grease to each needle
2. Gently tap the needles into the pilot holes using a small mallet and a needle driver
3. Ensure all three needles are inserted to the 20 mm depth mark
4. Secure the probe cable to the trunk with a cable clip

### Mounting the enclosure
1. Wrap the ratchet strap around the trunk at 1.2 m height
2. Hang the enclosure from the strap bracket
3. Position the solar panel facing south (in the Northern Hemisphere) at ~45° from vertical
4. Route the antenna cable so the whip is above the enclosure, away from the trunk

## 5. Provisioning

1. Hold the PROG button (S1) for 3 seconds — the green LED will blink
2. Connect to the debug UART (115200 baud) with a serial console
3. Follow the menu to enter LoRaWAN credentials (AppEUI, AppKey, DevEUI)
4. The device will attempt to join the LoRaWAN network (OTAA)
5. Green LED solid = joined; red LED = join failed (check gateway coverage)

## 6. Post-installation verification

- Press the MODE button (S2) to trigger an immediate measurement
- The green LED should blink once (measurement successful)
- Check the dashboard for the first uplink (within 15 min)
- Verify sap-flux velocity is in a reasonable range (0–50 cm/h for most trees)
- At predawn the next day, verify the zero-flow calibration is valid (probe_health bit 4 = 1)

## 7. Maintenance

- **Weekly**: Check the dashboard for anomalies. Verify all nodes reporting.
- **Monthly**: Inspect solar panels for debris/leaf cover. Clean with a damp cloth.
- **Seasonally**: Re-run zero-flow calibration (send downlink command 3). Check probe integrity.
- **Annually**: Replace the 18650 cell (Li-ion degrades after ~500 cycles / 2–3 years).
- **Bi-annually**: Inspect the probe needles for corrosion. Replace if needed.