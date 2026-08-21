# Gossamer Spin — Assembly Guide

## Bill of Materials

See [`../hardware/BOM.csv`](../hardware/BOM.csv). Total ~$68.

## Tools required

- Soldering iron (fine tip, 0.4 mm) + flux
- Hot-air station (for LQFP/QFN reflow)
- 3D printer (PETG) for chamber and control box
- Torx / Phillips micro screwdrivers
- Multimeter
- HV multimeter or HV probe (for testing 30 kV output)
- ST-Link v2 programmer (for STM32)
- USB-C cable (for charging + ESP32-C3 flashing)
- Wire winding jig (for flyback transformer secondary)

## ⚠️ Safety warning

**This device generates up to 30 kV.** While the current is limited to
~33 µA, the stored energy in the CW multiplier can deliver a painful
shock. Always:

1. Disconnect the battery before working on the PCB.
2. Short the HV output to ground after any test (use an insulated HV
   probe with a 100 MΩ resistor).
3. Wait 5 seconds after power-off for the bleeder to discharge.
4. Never touch the needle or collector while HV is active.
5. Test the safety cutoffs (door, tilt, comparator) before first use.

## Flyback transformer winding

The flyback transformer is the most critical custom component:

1. **Core**: EE25 ferrite core (PC44 material, available from DigiKey).
2. **Bobbin**: EE25 vertical bobbin.
3. **Primary**: 15 turns of 0.3 mm enamelled copper wire on the inner
   section. Wind tightly and evenly.
4. **Insulation**: 3 layers of Mylar tape (0.05 mm) over the primary.
5. **Secondary**: 1200 turns of 0.05 mm enamelled copper wire. Wind in
   neat layers, with Mylar tape between every 200 turns. This is the
   most tedious part — expect ~2 hours of winding.
6. **Core gap**: add 0.1 mm paper gap between core halves for DCM
   operation. Secure with tape.
7. **Test**: primary inductance should be ~50 µH, secondary ~300 mH.
   Insulation test: 1 kV between primary and secondary for 1 minute.

## HV section assembly (Cockcroft-Walton multiplier)

The 10-stage CW multiplier is built on a separate small PCB or
point-to-point on a perfboard:

1. **Layout**: 20× 1N4007 diodes and 20× 1 nF 3 kV ceramic capacitors
   arranged in a ladder. Keep stages physically separated to prevent
   arcing — minimum 2 mm between adjacent stages.
2. **Potting**: after testing, pot the entire CW assembly in epoxy
   resin to prevent corona discharge and arcing at high humidity.
3. **Output**: connect the HV output to a silicone-insulated 30 kV wire
   going to the needle mount.
4. **Divider**: solder the 900 MΩ + 900 kΩ divider across the output,
   with the sense point going to the ADS122U04 via a shielded wire.

## PCB assembly (control board)

The PCB is a 2-layer 80×40 mm board (JLCPCB custom).

1. **Power section**: solder AP2112 LDO, TP4056, DW02, USB-C connector.
   Verify 3.3 V rail before proceeding.
2. **STM32G474**: reflow or hand-solder the LQFP64. Connect ST-Link
   (SWDIO/SWCLK/3V3/GND) and verify chip ID with OpenOCD.
3. **ESP32-C3 module**: solder the WROOM-02 castellated module.
4. **Flyback driver**: IRFH7440 MOSFET + gate driver. Connect the
   flyback transformer primary. **Do not connect the CW multiplier
   yet.**
5. **ADS122U04**: SPI3 ADC for jet current + HV voltage. Keep analog
   traces short, on the 3V3A ferrite-bead rail.
6. **ADA4530-1 TIA**: electrometer op-amp. Use a guard ring around the
   input pin (IN-) on the PCB to prevent leakage currents. Clean the
   PCB thoroughly with IPA after soldering — flux residue can cause
   nanoamp-level leakage.
7. **Stepper drivers**: 2× A4988 modules + NEMA8 motors.
8. **Sensors**: BME280, SSD1306 OLED, microSD socket.
9. **Safety sensors**: reed switch, tilt sensor, TLV3201 comparator.

## Chamber assembly

1. **Print the chamber**: 110×60×50 mm PETG, 1.5 mm walls, with a
   hinged lid and gasket groove. Print at 100% infill for solvent
   resistance.
2. **Drum collector**: mount the NEMA8 stepper with GT2 pulley on the
   chamber floor. Belt-drive the aluminum drum on bearings at the top
   of the chamber.
3. **Slip ring**: mount the gold slip ring on the drum shaft. Connect
   one side to the drum (via the shaft), the other to the TIA input.
4. **Syringe pump**: mount the NEMA8 + leadscrew + linear rail on the
   side of the chamber. The syringe sits horizontally, needle pointing
   into the chamber.
5. **Needle mount**: adjustable sliding mount for the 21G needle, with
   distance markings (8–18 cm from drum). Connect HV silicone wire to
   the needle.
6. **Door interlock**: glue the reed switch to the chamber lid frame,
   and a small magnet to the lid. Test that opening the lid triggers
   the interlock.
7. **Tilt sensor**: mount on the PCB, oriented so the device sits level
   when the chamber is upright.
8. **Vent**: drill a 3 mm hole in the chamber wall, fit with a removable
   solvent filter cap (activated carbon).

## Wiring

1. Connect the 6-pin chamber cable: HV, ground, door interlock, tilt,
   motor power (2 pins for both steppers).
2. Connect the control box to the chamber via the cable.
3. Verify all safety connections before applying power.

## Flashing

### STM32 (control core)
```bash
cd firmware
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake ..
make -j
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program gossamer-spin.bin 0x08000000 verify reset exit"
```

Or use the helper script:
```bash
cd scripts
./flash_stm32.sh
```

### ESP32-C3 (radio relay)
```bash
cd firmware/esp32c3
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

## First test

### 1. Low-voltage test (no HV)
1. **Remove the flyback transformer fuse** (or disconnect the primary).
2. Power on. The OLED should show "IDLE".
3. Verify the STM32 boots, ESP32-C3 connects via BLE.
4. Test the syringe pump (should rotate slowly at 1 mL/h setting).
5. Test the drum collector (should rotate at set RPM).
6. Test the door interlock (open lid → SAFE mode).
7. Test the tilt sensor (tip 30° → SAFE mode).

### 2. HV test (with HV probe only)
1. **Reconnect the flyback transformer.**
2. **Remove the needle** from the chamber (no spinning yet).
3. Connect an HV probe (1000:1) to the CW output.
4. Set target to 5 kV. Enable HV. Verify output reads ~5 kV on the
   probe and on the OLED (via the divider).
5. Ramp to 10, 15, 20, 25, 30 kV. Verify regulation at each step.
6. Short the output with a 100 MΩ insulated probe — verify the current
   reads ~300 nA and the comparator does NOT trip (threshold is 10 µA).
7. Short with a direct wire — verify the TLV3201 comparator trips and
   cuts HV instantly.
8. Disable HV. Wait 5 seconds. Verify output is <60 V with the HV probe.

### 3. First electrospinning run
1. Prepare a PVA solution: 10% w/v PVA (MW 85k) in deionized water,
   heated to 80°C with stirring until dissolved. Cool to room temp.
2. Load 3 mL into a 5 mL syringe. Attach the 21G blunt needle.
3. Install the syringe in the pump. Set the needle-collector distance
   to 15 cm.
4. Wrap aluminum foil around the drum.
5. Select recipe 0 (PVA) on the OLED or via the BLE app.
6. Press start. The device should:
   - Ramp HV to 18 kV
   - Start the syringe pump at 1.0 mL/h
   - Start the drum at 800 RPM
   - Show "STABLE" jet state within ~30 seconds
   - Log to SD card
7. After ~5 minutes, stop and inspect the drum — you should see a
   white nanofiber mat on the foil.
8. Check the SD log CSV for the process data.

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| No HV output | Flyback not oscillating | Check MOSFET gate drive, transformer winding |
| HV too low | CW stage failure | Check each diode/cap with multimeter |
| Jet current always 0 | Needle clogged or too far | Clean needle, reduce distance |
| Jet current erratic | Voltage too high or flow too fast | Reduce voltage by 2 kV or flow by 0.2 mL/h |
| No fibers on drum | Humidity too high or solution wrong | Check RH, verify polymer concentration |
| Beaded fibers | Voltage too low or humidity too high | Increase voltage, reduce RH |
| OLED blank | I2C wiring | Check SCL/SDA connections, 4.7k pull-ups |
| Safety trips immediately | Door/tilt sensor stuck | Check sensor wiring and alignment |