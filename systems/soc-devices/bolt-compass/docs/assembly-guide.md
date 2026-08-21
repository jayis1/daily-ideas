# Bolt Compass — Assembly Guide

## 1. Parts checklist

See [`hardware/BOM.csv`](../hardware/BOM.csv). Before starting, verify you have:

- ESP32-S3-WROOM-1 (N16R8) module
- ADS131M04IPW (TSSOP-20)
- ADA4530-1 (SOIC-8)
- 2× LT1991-3 (MSOP-8) or AD8429
- NEO-M9N GPS module
- SSD1306 0.96" OLED 128×64 I2C
- SX1262 (Ra-01SH) — optional
- TP4056, MCP73871, MAX17048, AMS1117-3.3, TPS60403
- 5 W 6 V solar panel, 18650 3400 mAh
- microSD socket, USB-C receptacle
- Die-cast aluminum enclosure 100×60×25 mm
- AWG24 enameled wire (for loops), copper foil (for shields)
- 30 cm telescopic whip antenna with BNC

## 2. PCB assembly

### 2.1 Order of population

Solder in this order (lowest-profile first):

1. **Resistors, capacitors, ferrite beads** — all 0603/0805 passives.
2. **SOIC-8 / MSOP-8 ICs** — ADA4530-1, 2× LT1991-3, TPS60403.
3. **TSSOP-20** — ADS131M04 (use a fine-tip iron or hot-air; 0.65 mm pitch).
4. **SMD connectors** — USB-C, microSD, JST battery/solar.
5. **ESP32-S3-WROOM-1 module** — castellated edges, hand-solder or reflow.
6. **Through-hole** — 1/4"-20 tripod insert, BNC whip connector, buttons,
   header pins for OLED/GPS/LoRa daughtercards.

### 2.2 Power section

1. Solder TP4056 (USB-C charging) and MCP73871 (solar MPPT).
2. Add AMS1117-3.3 LDO + decoupling.
3. Add MAX17048 fuel gauge (I²C).
4. Add TPS60403 charge pump (generates −2.5 V for loop preamps from +3.3 V).
5. **Test point**: with no battery, apply 5 V to USB-C — check 3.3 V rail
   and ±2.5 V rails. Current should be < 5 mA.

### 2.3 Analog front end

1. Solder ADA4530-1 electrometer. **Critical**: keep the input node
   (whip → 100 kΩ → ADA4530-1 in-) as short as possible; route it on an
   isolated guard ring tied to the in+ reference. Any leakage here ruins
   the slow-E measurement.
2. Solder 2× LT1991-3 loop preamps. Add the ±2.5 V bypass caps close to
   each op-amp.
3. Add the spark-gap (Bourns 2049, 90 V) and TVS diodes at the whip input.
4. **Test point**: inject a 10 mV 10 kHz sine into one loop input — you
   should see ~1 V at the ADS131M04 input (40 dB gain).

### 2.4 ADS131M04

1. Solder the ADS131M04 (TSSOP-20). Add the 1 µF AVDD decoupling and the
   ferrite-bead isolation between the analog and digital 3.3 V.
2. The CLKIN pin is left floating (internal 8.192 MHz oscillator).
3. **Test point**: after firmware flash, the DRDY LED should blink at
   8 kHz (too fast to see — use a logic analyzer).

## 3. Antenna construction

### 3.1 Shielded loops (×2)

Each loop is a 10 cm diameter, 40-turn air-core coil with an
electrostatic shield.

1. Cut a 10 cm OD PVC pipe ring (or 3D-print the form in `docs/`).
2. Wind 40 turns of AWG24 enameled copper wire, tightly packed (~8 mm
   wide winding band).
3. Wrap the outside of the winding in **copper foil tape**, leaving a
   **5 mm gap** so the shield does not form a shorted turn.
4. Solder the copper shield to GND at **one point only** (the gap side).
5. The two loop leads go to a twisted pair → the PCB input.
6. Mount the two loops at **exactly 90°** in the 3D-printed cross bracket
   (`docs/loop-bracket.stl`). One loop plane faces N-S, the other E-W.

> The electrostatic shield is essential — without it, the whip's E-field
> couples capacitively into the loops and corrupts the bearing. The
> shield blocks E-field pickup while passing the magnetic field.

### 3.2 E-field whip

1. Mount the 30 cm telescopic whip on a BNC connector at the top of the
   enclosure.
2. At the whip base: spark-gap (90 V) to GND, then 100 kΩ series, then
   the ADA4530-1 input. Add a 3.3 V TVS across the input.
3. The whip is omnidirectional in the horizontal plane — it does not
   contribute to bearing, only to stroke detection + 180° resolution.

### 3.3 Tripod mounting

1. Press the 1/4"-20 stainless insert into the enclosure base.
2. Mount on a standard camera tripod, elevated ≥1.5 m above ground for
   a clean horizon.
3. **Bond the enclosure to earth ground** via a wire from the tripod to
   a ground rod (critical for safety + noise).

## 4. Firmware flash

1. Connect USB-C to a PC.
2. Build and flash:
   ```bash
   cd firmware
   idf.py set-target esp32s3
   idf.py build
   idf.py -p /dev/ttyACM0 flash monitor
   ```
3. On first boot, the OLED shows "Bolt Compass / listening" and the
   BLE advertises as `BoltCompass`.

## 5. First-light test

1. Take the device outdoors on a day with thunderstorms within 100 km
   (check lightningmaps.org).
2. Set it up on the tripod, loops level, whip vertical.
3. Open the Wi-Fi config page (`192.168.4.1`) or connect via BLE.
4. Watch the OLED radar — strokes should appear as dots within a few
   minutes. CG strokes are solid dots; IC/CC are ring outlines.
5. Cross-check bearing/distance against lightningmaps.org — if
   bearings are systematically rotated, adjust the loop alignment
   (see `calibration-guide.md`).

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| No detections | Loops not connected / shield shorted | Check continuity, shield gap |
| Detections but no bearing | Only one loop working | Swap loops, check preamp |
| Bearing always 0/180/90/270 | One loop dead or 90° off | Re-align cross bracket |
| All noise, no sferics | Gain too low / ADC saturated | Check PGA gain, preamp output |
| Distance always 9999 | ref_field_uv not calibrated | Run calibration (see guide) |
| GPS no fix | Indoor / antenna blocked | Go outdoors, wait 2 min |
| SD mount fail | Card not FAT32 | `mkfs.vfat /dev/sdX` |