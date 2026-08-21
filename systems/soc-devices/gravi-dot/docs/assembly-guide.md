# Gravi Dot — Assembly Guide

## Overview

The Gravi Dot is a 4-layer PCB with a small daughterboard for the gravity sensor. The main PCB (50×50 mm) contains the STM32, ESP32-C3, power management, GPS, and connectors. The sensor daughterboard (15×15 mm) holds the ADXL355 and SCL3300 and is mounted inside a copper thermal mass.

## Parts of the build

1. **Main PCB** — 4-layer, 50×50 mm, ENIG finish
2. **Sensor daughterboard** — 2-layer, 15×15 mm, mounts inside copper block
3. **Copper thermal mass** — 30×30×15 mm copper block, drilled for daughterboard + Peltier
4. **Aluminium enclosure** — 106×55×28 mm, CNC-machined, anodized
5. **Levelling feet** — 3× M3 adjustable thumb-screws on the bottom
6. **Bullseye level** — 25 mm circular spirit level on the top face

## Assembly steps

### Step 1: Main PCB fabrication

Order the 4-layer PCB from PCBWay/JLCPCB with:
- 4 layers (signal / GND / 3V3 / signal)
- 1.6 mm thickness, ENIG finish
- 1 oz copper

### Step 2: SMT assembly

Solder components in order of decreasing size:
1. **Power section** — MCP73831, TPS63020, TPS63031, DW01A, USB-C connector
2. **MCU** — STM32G474RET6 (LQFP64, 0.5 mm pitch — use hot-air or reflow)
3. **Wireless** — ESP32-C3-MINI-1 module (reflow only)
4. **Sensors** — ADXL355 (LCC-14), SCL3300 (SOIC-16), MS5837 (metal can)
5. **GPS** — NEO-M9N module (reflow)
6. **Passives** — 0402/0603 R/C/L, crystals, LEDs
7. **Connectors** — microSD socket, tactile buttons, rotary encoder

### Step 3: Sensor daughterboard

1. Solder ADXL355 + SCL3300 onto the 15×15 mm daughterboard
2. Wire daughterboard to main PCB via 8-pin 0.5 mm FFC (flexible flat cable) — 30 mm length
3. Mount daughterboard inside the copper thermal mass using thermal epoxy
4. Attach Peltier element between copper mass and aluminium enclosure (heat sink side out)
5. Install 4× DS18B20 sensors around the copper block at 90° intervals

### Step 4: Enclosure assembly

1. CNC-machine the aluminium enclosure (106×55×28 mm)
2. Drill holes for: USB-C port, OLED window, buttons, encoder, SD card slot
3. Mount PCB inside enclosure on 3× M2.5 standoffs
4. Install the copper thermal mass assembly with silicone vibration isolators
5. Attach the bullseye level to the top face
6. Install 3× adjustable levelling feet on the bottom

### Step 5: Firmware flashing

1. Flash STM32G474 via SWD (ST-Link):
   ```bash
   cd firmware && mkdir build && cd build
   cmake -DCMAKE_TOOLCHAIN_FILE=../cmake/gcc-arm-none-eabi.cmake ..
   make -j8
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
           -c "program gravi_dot.elf verify reset exit"
   ```

2. Flash ESP32-C3 via USB:
   ```bash
   cd firmware/esp32c3
   idf.py set-target esp32c3
   idf.py build flash monitor
   ```

### Step 6: Calibration

Before first use, the ADXL355 temperature coefficient must be calibrated:
1. Place the Gravi Dot in a temperature-controlled environment
2. Run the calibration mode (MENU → CALIBRATE)
3. The firmware sweeps temperature from 20°C to 45°C in 5°C steps
4. Records the bias at each temperature and fits a linear coefficient
5. The coefficient is stored in flash and applied automatically

## Testing

1. **Power test** — connect USB-C, verify 3.3V and 5.0V rails
2. **Thermal test** — verify copper block stabilizes at 35°C ±0.05°C within 60 s
3. **GPS test** — verify NEO-M9N gets a 3D fix (OLED shows "READY")
4. **Sensor test** — press STATION, verify a reading appears on OLED
5. **SD test** — verify `survey_*.csv` is created on the SD card
6. **BLE test** — connect with nRF Connect, verify station notifications
7. **Field test** — take a base reading, walk 10 m, take a station reading, return to base

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| OLED blank | I2C address wrong (0x3C vs 0x3D) | Check SH1106 variant, adjust `SH1106_ADDR` |
| No GPS fix | Antenna blocked or indoor | Go outside, wait 30 s for cold start |
| Thermal unstable | Peltier wiring reversed | Swap Peltier A/B wires |
| Readings noisy | Ground vibration | Survey on solid ground, calm conditions |
| SD card errors | Card not FAT32 | Format card as FAT32 on computer |
| BLE not visible | ESP32-C3 not flashed | Reflash ESP32-C3 firmware |