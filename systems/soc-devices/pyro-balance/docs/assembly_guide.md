# Pyro Balance — Assembly Guide

## Overview

Pyro Balance is a pocket thermogravimetric analyzer (TGA). This guide walks through mechanical assembly, wiring, calibration, and first run.

> ⚠️ **Safety warning.** The furnace reaches 600 °C. The device has triple-redundant safety (thermal fuse, hardware comparator, software limit + watchdog + interlock), but you must still follow the assembly steps carefully. Never bypass the thermal fuse or interlock.

## Mechanical Assembly

### Parts needed (see `hardware/BOM.csv`)

- Custom PCB (4-layer, 70×110 mm)
- 3D-printed PETG enclosure (coffee-mug sized, ~Ø70 × 110 mm)
- Alumina tube + crucibles + hang-down rod
- Nichrome coil + ceramic fiber insulation

### Steps

1. **PCB population.** Solder all SMD passives first (0603 resistors/caps), then the STM32G474, ESP32-C3 module, HX711, ADS122U04, BME280, OLED, SD socket, USB-C + TP4056, MP1584 + MT3608, MOSFETs, TLV3201, buttons, buzzer, LED. Use flux and hot-air for the QFPs.

2. **Furnace assembly.** Wind ~6 Ω of 30 AWG nichrome wire around the alumina tube (evenly spaced). Secure with ceramic cement. Insert the PT1000 RTD probe so its tip is centered beside the crucible position. Wrap the tube in ceramic fiber insulation, leaving the top opening for the crucible.

3. **Balance assembly.** Mount the 5 g foil-strain load cell vertically on the balance bay floor. Attach the thin alumina hang-down rod to the load cell's sensing end, threading it down through the ceramic insulation block into the furnace tube, so the crucible hangs centered in the furnace hot zone. Keep the balance bay thermally isolated with the fiber insulation block; the bay must stay below 55 °C.

4. **Thermal fuse.** Mount the 250 °C thermal fuse in series with the 12 V furnace rail, physically on the balance bay wall (where it senses balance-bay temperature). If the bay exceeds 250 °C the fuse blows and cuts furnace power permanently.

5. **Safety sensors.** Mount the TLV3201 comparator's thermistor on the furnace tube exterior. Mount the reed interlock switch so it is closed only when the lid is on.

6. **Enclosure.** Place the PCB in the bottom of the PETG enclosure. Mount the OLED on the lid. Drill ventilation slots for the cooling fan. Add a small fan (5 V) on the balance bay for active cooling after runs.

7. **Purge (optional).** If using N₂ purge, connect the micro diaphragm pump inlet to your N₂ source (with regulator), outlet through the SFM3300 flow sensor to the furnace tube inlet. Wire the pump and solenoid valve to the PCB.

## Wiring

Follow the pin table in `README.md`. Key connections:

- HX711 SCK → PA1, DOUT → PA2, RATE → PA3
- ADS122U04 I²C → PB10/PB11 (I²C2)
- BME280 I²C → PB8/PB9 (I²C1)
- Furnace MOSFET gate → PA5 (TIM/HRTIM PWM)
- Heater enable relay → PA8
- TLV3201 output → PA11
- Thermal fuse sense → PA15
- Interlock → PC13
- SD SPI → PB3/PB4/PB5, CS → PB6
- OLED SPI → shared PB3/PB5, CS → PB7, DC → PB1
- UART to ESP32-C3 → PA9/PA10
- Buttons → PB13/PB14/PB15

## Power

- 2× 18650 in series (7.4 V) or USB-C 5 V via TP4056 (charging only; running from USB alone limits furnace power — use battery for full heating rate).
- MP1584 buck → 5 V logic rail.
- MT3608 boost → 12 V furnace rail (through thermal fuse).

## Calibration

1. **Mass.** With no crucible, run MENU until "TARE" shows, hold MENU 2 s → offset stored. Place a 5 g reference weight, hold MENU → scale factor stored. Repeat 2× for stability.
2. **Temperature.** Ice-water bath (0 °C) on the RTD probe — note ADC reading. Boiling water (100 °C, adjust for altitude) — note reading. Two-point linear fit stored in `flash_store`. For higher accuracy, add an indium melt point (156.6 °C): place a small indium chip in a crucible, ramp through 150–160 °C, the plateau is the melting point; correct any offset.
3. **Furnace lag.** Run an empty crucible at 10 °C/min and compare the furnace RTD temperature to a second independent thermocouple at the crucible position. Store the offset in `g_cfg.furnace_lag_c`.
4. **Buoyancy blank.** Run an empty crucible through your method (full ramp). Save the resulting mass-vs-temperature curve. In analysis, subtract this "blank" curve from sample runs to remove buoyancy/flow effects (standard TGA practice). `scripts/analyze_tga.py` supports this.

## First Run

1. Insert a 18650 pack or connect USB-C. The OLED shows "Pyro Balance v1.0 / Ready. Insert sample."
2. Place 5–20 mg of sample in an alumina crucible. Hang it on the balance rod. Close the lid (interlock must be closed).
3. Press START. The furnace ramps, the OLED plots the TG curve live, SD logs CSV, and BLE streams to a phone.
4. The run ends at the final temperature + hold. Cooling fan runs until < 60 °C.
5. Results (steps, residual %) display on OLED and are saved to SD.

## Maintenance

- Replace alumina crucibles (single use for some samples).
- Clean the hang-down rod with IPA if sample spills.
- Check the thermal fuse continuity annually.
- Recalibrate mass if the device is dropped or the load cell is disturbed.