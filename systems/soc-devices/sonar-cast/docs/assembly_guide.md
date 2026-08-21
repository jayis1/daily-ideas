# Sonar Cast — Assembly Guide

## Bill of Materials

See [`../hardware/BOM.csv`](../hardware/BOM.csv). Total ~$72.

## Tools required

- Soldering iron (fine tip, 0.4 mm) + flux
- Hot-air station (for QFN/LQFP reflow or touch-up)
- 3D printer (PETG) for the enclosure
- Torx / Phillips micro screwdrivers
- Multimeter
- ST-Link v2 programmer (for STM32)
- USB-C cable (for charging + ESP32-C3 flashing)

## PCB assembly

The PCB is a 2-layer Ø62 mm circular board (JLCPCB custom).

1. **Power section**: solder AP2112 LDO, TP4056, DW02, USB-C connector.
   Verify 3.3 V rail before proceeding.
2. **STM32G474**: reflow or hand-solder the LQFP64. Connect ST-Link
   (SWDIO/SWCLK/3V3/GND) and verify chip ID with OpenOCD.
3. **ESP32-C3 module**: solder the WROOM-02 castellated module.
4. **HV section**: MC34063 boost → verify 12 V rail. Solder 4× IRFH7440
   H-bridge MOSFETs. **Do not power the piezo until T/R switch + AD8331
   are in place.**
5. **Analog front end**: AD8331 VGA, ADS7945 ADC, T/R switch (BAT54S pairs).
   Keep analog traces short, use the 3V3A ferrite-bead rail.
6. **Sensors**: ICM-42688-P, MS5837-30BA, DS18B20 (mount DS18B20 on the
   bottom face, epoxy-sealed so it contacts water).
7. **GPS**: NEO-M9N module — antenna patch faces up (above waterline).
8. **OLED + microSD + WS2812**: solder last.

## Enclosure

Print the two-piece PETG puck (`docs/puck_top.stl`, `docs/puck_bot.stl` —
not included, generate from the dimensions in the README). Install the
AS568-018 O-ring in the bottom groove. Cement the piezo transducer to the
bottom face with marine epoxy. Add the closed-cell foam buoyancy ring
around the top dome.

## Waterproofing test

Before electronics install: seal the empty enclosure, submerge to 1 m
for 30 min, verify no leaks (dry tissue inside).

## Flashing

### STM32 (DSP core)
```bash
cd firmware
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake ..
make -j
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program sonar-cast.bin 0x08000000 verify reset exit"
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
2. Place the puck in water (water-detect probes trigger ACTIVE state).
3. Open the BLE app (`scripts/live_echogram.py` or a phone terminal)
   and verify echogram + depth readings.
4. Cast from shore and verify GPS-tagged bathymetry CSV on the SD card.