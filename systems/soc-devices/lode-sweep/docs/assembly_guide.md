# Lode Sweep — Assembly Guide

## Bill of Materials

See [`../hardware/BOM.csv`](../hardware/BOM.csv). Total ~$63.

## Tools required

- Soldering iron (fine tip, 0.4 mm) + flux
- Hot-air station (for QFN/LQFP reflow or touch-up)
- 3D printer (PETG) for the control box and coil former
- Torx / Phillips micro screwdrivers
- Multimeter
- ST-Link v2 programmer (for STM32)
- USB-C cable (for charging + ESP32-C3 flashing)
- Drill press or hand drill (for coil former wire winding)

## Search coil winding

The search coil is the most critical component:

1. **Print the coil former**: a 25 cm diameter PETG spool with a 10 mm deep
   groove for the wire winding.
2. **Wind 100 turns** of 0.5 mm enamelled copper wire tightly in the groove.
   Keep turns neat and evenly spaced.
3. **Measure inductance**: should be ~0.5 mH ±20% and ~2 Ω DC resistance.
4. **Secure the winding** with epoxy resin, filling the groove completely.
   Allow 24 hours to cure.
5. **Attach a 1.2 m shielded twisted pair cable** to the coil terminals.
   Solder one end to the coil leads, the other to a 4-pin connector for the
   control box.
6. **Install a 470 Ω damping resistor** across the coil terminals (inside the
   control box, not on the coil) to critically damp the ring-down.
7. **Waterproof**: wrap the coil in heat-shrink tubing or pot the entire
   assembly in epoxy for waterproofing.

## PCB assembly

The PCB is a 2-layer 120×40 mm rectangular board (JLCPCB custom).

1. **Power section**: solder AP2112 LDO, TP4056, DW02, USB-C connector.
   Verify 3.3 V rail before proceeding.
2. **STM32G474**: reflow or hand-solder the LQFP64. Connect ST-Link
   (SWDIO/SWCLK/3V3/GND) and verify chip ID with OpenOCD.
3. **ESP32-C3 module**: solder the WROOM-02 castellated module.
4. **Boost converter**: MC34063 boost → verify 12 V rail under load.
   Enable via PC15 (STM32 GPIO).
5. **TX driver**: IRFH7440 MOSFET + SMBJ18A TVS diode. **Do not connect
   the coil until the RX chain is verified.**
6. **RX chain**: AC coupling capacitor, AD8226 instrumentation amplifier.
   Keep analog traces short, use the 3V3A ferrite-bead rail.
7. **Sensors**: ICM-42688-P IMU (mounted level on the PCB for tilt reference).
8. **GPS**: NEO-M9N module — antenna patch faces up.
9. **OLED + microSD + headphone jack**: solder last.

## Control box

Print the two-piece PETG control box (`docs/box_top.stl`, `docs/box_bot.stl` —
not included, generate from the dimensions in the README). The box mounts on
a 25 mm aluminum shaft via a UHMW bracket, with the search coil at the bottom.

## Coil cable

Route the 1.2 m shielded cable from the coil through the shaft to the control
box. Connect to the 4-pin PCB header (coil+, coil-, shield, water-detect).

## Flashing

### STM32 (DSP core)
```bash
cd firmware
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake ..
make -j
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program lode-sweep.bin 0x08000000 verify reset exit"
```

### ESP32-C3 (radio/GPS)
```bash
cd firmware/esp32c3
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

## First test

1. Charge the 18650 via USB-C (status LED → green when full).
2. Connect the search coil (do not power without the coil connected).
3. Press the mode button to enter ACTIVE state.
4. Hold the coil level, away from metal objects — the OLED should show
   "---" (no target) and the ground balance should calibrate automatically.
5. Pass a coin under the coil — the OLED should show the target class,
   depth estimate, and confidence. Audio should produce a pitch-coded tone.
6. Open the BLE app (`scripts/live_sweep.py` or a phone terminal) and
   verify live target ID + depth streaming.
7. Sweep an area and verify GPS-tagged survey CSV on the SD card.