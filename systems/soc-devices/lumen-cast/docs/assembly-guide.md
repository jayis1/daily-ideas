# Lumen Cast — Assembly Guide

## Overview

The Lumen Cast is a pocket goniophotometer built around the STM32G491RET6 Cortex-M4F microcontroller. This guide covers component sourcing, PCB assembly, mechanical construction, and firmware flashing.

## Tools Required

- Soldering iron (fine tip, 0.4mm) with temperature control
- Hot-air rework station (for QFN/LQFP packages)
- Solder paste and stencil (recommended for QFN parts)
- Digital multimeter
- ST-Link V2 SWD programmer (for STM32G491 flashing)
- USB-C cable
- 3D printer (for ring, arm, cradle, and case)
- M2/M3 fastener kit
- Small bearing puller / press (for ring bearings)

## PCB Assembly

### 1. Main PCB (4-layer, 90×60mm)

**Soldering order (lowest profile first):**

1. **Passives** — resistors, capacitors (0402/0603)
   - I2C pull-ups: 4.7kΩ ×2 on PB6/PB7 (to +3V3_SENS)
   - Battery divider: 100kΩ ×2 on PA3
   - Decoupling: 100nF on each IC VDD
   - 10µF on +3V3 rail, 10µF on VBUS, 10µF on VBAT
   - 100µF on VMOT (TMC2209 motor supply)

2. **Small ICs** (SOT-23 packages)
   - U11: TLV70033 LDO (SOT-23-5)
   - U12: DW01A battery protection (SOT-23-6)
   - U13: FS8205A dual MOSFET (SOT-23-6)

3. **Medium ICs** (SOIC)
   - U6: W25Q128 flash (SOIC-8)
   - U7: DS3231SN RTC (SOIC-16W)

4. **Large ICs** (QFN/LQFP — use hot air or stencil)
   - U1: STM32G491RET6 (LQFP-64) — align pin 1 dot, apply flux
   - U2: ESP32-C3-MINI-1 (module, castellated pads)
   - U3: OPT3001DNPT (USON-6) — very small, use stencil
   - U4: TCS34725 (FN-6) — small, use stencil
   - U9: MCP73831 (DFN-8)
   - U10: TPS63020 (SON-14)

5. **Motor driver module**
   - U8: TMC2209 v1.2 (through-hole or SMD module)

6. **Connectors and mechanical**
   - J1: USB-C receptacle (through-hole tabs + SMD pins)
   - J2: JST-PH battery connector
   - J3: 4-pin JST-XH for NEMA8 stepper motor
   - J4: 6-pin SWD programming header (0.1" pitch)
   - SW1, SW2: Tactile buttons
   - LED1: WS2812B
   - LED2: Status LED
   - SERVO1: 3-pin header for SG90 servo

7. **Inductor**
   - L1: 2.2µH 3A (4×4mm) for TPS63020

### 2. Mechanical Assembly

#### Rotating Ring

The rotating ring is a 3D-printed PLA ring (180mm outer diameter, 160mm inner diameter) that holds the sensor head arm and rotates around the source cradle. It runs on two 6mm inner-diameter bearings (624ZZ or MR104ZZ) pressed into the base frame.

**Bill of mechanical parts:**
- 2× 624ZZ bearings (4×13×5mm)
- 4× M3×8mm screws
- 1× GT2 timing belt (200mm loop) or direct coupling
- 1× NEMA8 stepper motor with 20T GT2 pulley (if belt drive)
- 1× 150mm carbon fiber or aluminum arm rod (3mm diameter)
- 1× SG90 servo (mounted on rotating ring for elevation tilt)

#### Sensor Head

The sensor head is a small 3D-printed enclosure (30×20×15mm) that holds:
- OPT3001DNPT sensor (facing inward, toward source)
- TCS34725 sensor (facing inward, alongside OPT3001)
- SG90 servo (for elevation tilt)

The head mounts on the end of the 150mm arm. A short 4-wire ribbon cable connects the sensors back to the main PCB via the rotating ring. Use a slip ring if continuous 360° rotation is needed (otherwise, limit rotation to 350° to avoid cable wrap).

#### Source Cradle

The source cradle is a simple 3D-printed mount at the center of the ring that holds the LED/lamp under test. It should have:
- Adjustable height (M3 screw mechanism)
- A standard 5mm LED socket or adjustable clip
- Thermal pad if testing high-power LEDs

#### Dark Shroud

A black nylon cloth enclosure (velcro-attached to the base) blocks ambient light during scanning. It should fully cover the ring + source area with a small opening for cables.

### 3. Firmware Flashing

#### STM32G491 (main MCU)

1. Connect ST-Link V2 to SWD header (J4):
   - Pin 1: +3V3
   - Pin 2: SWDIO
   - Pin 3: GND
   - Pin 4: SWCLK
   - Pin 5: NRST

2. Build and flash:
```bash
cd firmware
make
make flash    # uses OpenOCD + ST-Link
```

3. Verify via USB-CDC debug output (USART2 @ 115200)

#### ESP32-C3 (BLE/WiFi bridge)

1. Connect USB-C to the board (provides USB-CDC to ESP32-C3)
2. Build and flash:
```bash
cd firmware/esp32_c3_bridge
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyACM0 flash
```

### 4. Calibration

1. Mount the optional reference lamp (1000 lm calibrated LED module) in the cradle
2. Press and hold MODE button for 3 seconds → enters CALIBRATION mode
3. The device runs a Type A scan and computes the calibration factor
4. The factor is stored in flash and applied to all subsequent scans
5. Verify: a known source should read within ±5% of its rated flux

### 5. First Test

1. Mount an LED in the cradle
2. Close the dark shroud
3. Press SCAN button
4. The device will home the stepper, then sweep the sensor head
5. Results appear on the OLED: flux (lm), peak (cd), beam angle (°)
6. Press SCAN again to return to idle
7. Use the phone app (BLE) to view detailed plots and export .IES files

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OLED blank | Check I2C wiring, 0x3C address, SH1106 init sequence |
| OPT3001 reads 0 | Check I2C address (0x44 with ADDR=GND), verify device ID |
| TCS34725 not found | Check I2C address (0x29), verify ID register = 0x44 |
| Motor doesn't move | Check TMC2209 EN (active low), VMOT power, DIR/STEP wiring |
| Servo jitter | Ensure stable 3.3V supply, add 100µF cap on servo power |
| Flux reading too low | Run calibration with reference lamp; check ambient subtraction |
| Beam angle wrong | Verify scan grid covers full beam; use Near-field mode for narrow beams |
| BLE not visible | Check ESP32-C3 firmware, EN pin high, antenna not blocked |