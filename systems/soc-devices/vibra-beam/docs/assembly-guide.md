# Vibra Beam — Assembly Guide

## Overview

Vibra Beam is a pocket laser Doppler vibrometer in a flashlight-style enclosure (~35 mm dia × 140 mm). The optical bench — laser diode, beamsplitters, quarter-wave plate, photodiodes — is mounted on a small 4-layer PCB inside the front tube; the electronics sit behind it.

## Tools & Skills

- Soldering iron (fine tip) + solder paste/hot-air for SMD
- 3D printer (PETG/PLA) for the enclosure and optic mounts
- M2 screwdriver
- Multimeter
- Optional: USB microscope for inspecting 0603 joints

## PCB Assembly Order

1. **Power first.** Solder the MCP73831, TPS63020, TPS7A4700, MT3601, USB-C, and LiPo battery leads. Verify 3.3 V digital and 3.3 V analog rails with no load, then with the MCU absent.
2. **MCU.** Place the STM32G474RET6 (LQFP-64). Use hot-air or reflow. Check 3.3 V / GND continuity before powering.
3. **ESP32-C3-MINI-1.** Hand-solder the castellated module. Verify it boots and advertises BLE.
4. **Sensors.** ICM-42688-P (QFN-14 — use stencil + reflow), BME280, DS18B20.
5. **OLED, MicroSD, buttons, RGB LED, USB-C.**
6. **Audio.** MAX98357A, speaker, headphone jack.
7. **Analog front end.** Two OPA380 TIAs with 1 MΩ 0.1% feedback resistors and 2.2 pF C0G feedback caps. Keep the photodiode traces short (< 5 mm).
8. **Laser & shutter.** AL8805 driver, laser diode in TO-18, DRV8833, solenoid shutter.
9. **Optics.** Mount the NPBS cube, QWP, PBS cube, fixed reference mirror, and collimator lens. The QWP must be at 45° to the laser polarization. The reference mirror should be λ/20 or better.

## Optical Alignment

1. **Collimation.** Power the laser at 1 mW. Adjust the collimator lens so the beam at 1 m distance is a clean ~3 mm spot.
2. **Beamsplitter cube.** The NPBS splits the beam: reference reflects off the fixed mirror, signal exits the front lens. Both returns recombine at the NPBS.
3. **QWP + PBS.** The QWP in the common path converts linear to circular; after the double-pass the polarization rotates 90°, routing returns to the second NPBS port. The PBS then splits the recombined beam into I and Q (90° apart).
4. **Photodiodes.** Aim each PBS output at a TEMD5010. Verify the DC level is ~1.5 V (mid-rail) on each TIA output.
5. **Target.** Point at a retroreflective tape or any reflective surface ~30 cm away. Tapping the table should produce a visible fringe change on the OLED Lissajous view.

## Enclosure

- Front: lens + optic mount (3D-printed, matte black interior)
- Mid: PCB stack with optics on a sub-board
- Rear: battery + USB-C + buttons + OLED window
- Reed switch glues to the lid; a small magnet in the lid closes it when shut

## Firmware Flash

1. Connect an ST-Link V2 to the SWD header (PA13/PA14).
2. `cd firmware && mkdir build && cd build && cmake .. && make -j`
3. `openocd -f interface/stlink.cfg -f target/stm32g4x.cfg -c "program vibra_beam.elf verify reset exit"`

## Safety Checks Before First Power-On

- [ ] Laser diode current limit set to 1 mW in firmware (default)
- [ ] Shutter solenoid moves freely and closes on power-off
- [ ] Reed interlock cuts laser when lid opens
- [ ] Tilt > 45° disables laser (test by tilting while running)
- [ ] IWDG refreshes in main loop
- [ ] Never look into the beam; use a white card to view the spot

## Calibration

1. **Fringe calibration.** Menu → Calibrate. Point at a static target. The Lissajous (I/Q circle) should be a clean circle; offset adjusts the DC baseline.
2. **Velocity scale.** Drive a known target (e.g., a speaker at 1 kHz, 1 µm peak). Verify the measured velocity equals 2π·f·x = 6.28 mm/s.
3. **IMU compensation.** Hold the device still and verify the velocity reads ~0. Slowly translate the device; the compensation should reject the translation.