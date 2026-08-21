# Taste Bead — Assembly Guide

## Overview

This guide walks you through assembling the Taste Bead pocket electronic tongue. The device consists of:

1. **Main body PCB** (110 × 55 mm): ESP32-S3, AD5941 AFE, ADG715 mux, power, display, SD, buttons
2. **Electrode probe** (120 × 8 mm): 5-metal electrode array in PEEK housing

## Tools Required

- Soldering iron (fine tip, temperature-controlled)
- Solder (0.6mm, 63/37 or lead-free)
- Flux pen
- Tweezers (fine, anti-magnetic)
- Multimeter
- Magnifier or microscope (for 0805 SMD and QFN parts)
- 3D printer (for enclosure and probe body)
- M2.5 / M3 tap and drill bits
- Small lathe or drill press (for PEEK probe body machining)

## Assembly Steps

### Step 1: Main Body PCB — Power Supply

1. **U6 TP4056** (SOIC-8): Solder the Li-ion charger IC first.
2. **USB-C connector**: Solder the USB-C receptacle. Use flux and check for bridges.
3. **U7 AP2112-3.3** (SOT-23-5): Digital 3.3V LDO regulator.
4. **U8 ADP7118-3.3** (DFN-8): Ultra-low-noise analog 3.3V LDO. This powers the AD5941 analog rails. **Critical**: keep this rail separate from digital to minimize noise.
5. **U9 LP5907-1.8** (SOT-23-5): 1.8V LDO for AD5941 digital core.
6. **R1, R2** (1MΩ, 0805): Battery voltage divider (2:1).
7. **18650 battery holder**: Solder the spring-loaded battery holder.
8. **Test**: Insert battery, check voltages: 3.3V digital, 3.3V analog, 1.8V AD5941 core.

### Step 2: Main Body PCB — ESP32-S3 MCU

1. **U1 ESP32-S3-WROOM-1** (module): Solder the module. This is a castellated-edge module — use flux and drag-solder the edges.
2. **Y1** (26 MHz crystal, 3225 package): System crystal with two 22pF caps (C3, C4).
3. **Y2** (32.768 kHz crystal): RTC crystal with two 12pF caps.
4. **Decoupling caps**: Place 100nF caps near each IC's VDD pin.
5. **Test**: Connect USB-C, verify ESP32-S3 is recognized by esptool (`esptool.py chip_id`).

### Step 3: Main Body PCB — AD5941 Analog Front-End

1. **U2 AD5941** (LFCSP-28 / QFN-28): This is the most critical component. Use stencil + reflow soldering, or careful hand soldering with flux. **Keep analog traces short and away from digital signals.**
2. **U3 ADG715** (TSSOP-16): 8:1 analog mux for electrode selection.
3. **Analog decoupling**: Place 1µF and 100nF caps close to AD5941 AVDD pins. Use a star ground for analog.
4. **Analog guard ring**: Route a ground guard ring around the WE/RE/CE analog inputs on the PCB to reduce leakage.
5. **Test**: Power on, verify AD5941 responds to SPI commands (read ID register).

### Step 4: Main Body PCB — Peripherals

1. **U4 BME280** (LGA-8): Environmental sensor. I2C address 0x76.
2. **U5 SSD1306 OLED**: Solder the OLED module (pre-assembled, just solder the 4-pin header).
3. **microSD slot**: Solder the Molex microSD card slot.
4. **3× tactile buttons**: ID, MODE, LIB buttons.
5. **RGB LED**: Common-cathode 0805 RGB LED.
6. **Test**: Verify I2C devices (BME280 + OLED) are detected.

### Step 5: Electrode Probe Construction

1. **PEEK body**: Machine a 120mm × 8mm PEEK rod with 5 holes (1mm diameter, 5mm spacing) at one end. PEEK is chemically inert and mechanically strong.
2. **Insert electrodes**: Insert the 5 metal wires (Au, Pt, Ag/AgCl, GC, Cu) into the holes. Use conductive epoxy (silver epoxy) to bond wires to PCB pads, then seal with epoxy resin.
3. **Platinum counter electrode ring**: Wrap a 3mm Pt wire ring around the probe body, 15mm from the tip.
4. **Ag/AgCl reference electrode**: Insert a separate Ag/AgCl wire (silver wire coated with AgCl via bleaching in 0.1M HCl under 1V bias).
5. **O-ring seals**: Place silicone O-rings at the probe-cable junction for waterproofing.
6. **Probe cable**: Solder a 4-conductor shielded silicone cable (WE, CE, RE, GND + shield) to the PCB connector.
7. **Test**: Check continuity from each electrode to the PCB connector. Check for shorts between electrodes.

### Step 6: 3D Printed Enclosure

1. Print the main body enclosure (PLA or PETG) — a two-piece clamshell with cutouts for OLED, USB-C, buttons, and SD card.
2. Print the probe cap — a silicone or TPU cap that protects the electrode tip when not in use.
3. Assemble with M3 screws.

### Step 7: Firmware Upload

1. Connect USB-C to computer.
2. Flash firmware: `idf.py build && idf.py flash monitor`
3. Verify boot sequence on OLED: splash screen → calibration warning → ready.

### Step 8: Calibration

1. **OPEN calibration**: Remove probe from any liquid. Press ID button in Calibrate mode → "OPEN cal".
2. **SHORT calibration**: Place probe tip in a small metal cup (all electrodes shorted). Press ID button twice → "SHORT cal".
3. **KCl calibration**: Prepare 0.01 M KCl solution (0.7455 g KCl in 1L distilled water). Dip probe. Press ID button three times → "KCl cal".
4. Calibration is stored in NVS flash and persists across reboots.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| AD5941 not responding | Check SPI wiring, 1.8V core supply, reset pin |
| Impedance readings all NaN | Check mux enable, electrode probe cable continuity |
| No BLE connection | Verify ESP32-S3 antenna area is not covered by metal |
| OLED blank | Check I2C wiring, 3.3V supply, SSD1306 address (0x3C) |
| Classification always "uncertain" | Add more library entries, check calibration |
| Battery not charging | Check TP4056, USB-C 5V, battery polarity |