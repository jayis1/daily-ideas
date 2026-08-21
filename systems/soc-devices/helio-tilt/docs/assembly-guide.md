# Assembly Guide — Helio Tilt

## Overview

This guide walks through assembling the Helio Tilt pocket tracking
pyrheliometer and aerosol optical depth meter. The device consists
of a main PCB, a 2-axis tracking head (azimuth turntable + elevation
arm), a collimator tube with filter wheel, and an optical detector
assembly.

## Tools Required

- Soldering iron (fine tip, 0.4 mm)
- Solder paste + hot-air rework station (for QFN/LQFP parts)
- Multimeter
- KiCad (for PCB fabrication)
- 3D printer (for enclosure, tracking head, filter wheel)
- Tweezers (ESD-safe)
- Magnification (loupe or microscope)
- Small Phillips screwdriver set
- Allen key set (M2/M3)

## PCB Assembly

### 1. Power Section
1. Solder U2 (TP4056) — SOIC-8, USB charging
2. Solder U3 (MCP1640B) — SOT-23-5, 3.7→5V boost
3. Solder U4 (AP2112-3.3) — SOT-23-5, digital 3.3V LDO
4. Solder U5 (LP5907-3.3) — SOT-23-5, analog 3.3V LDO
5. Solder L1, L2 (BLM18PG121 ferrite beads) — 0603
6. Solder C1-C8 (decoupling capacitors)
7. Solder J1 (USB-C receptacle)
8. Solder BT1 (18650 holder, Keystone 1042)

### 2. SoC
1. Apply solder paste to LQFP-64 footprint
2. Place U1 (STM32G474RET6) — align pin 1
3. Reflow with hot air (260°C, 60 s)
4. Inspect for bridges under microscope

### 3. GPS Module
1. Solder U7 (NEO-M9N) — castellated module, 16×12.2 mm
2. Position on top face of PCB (antenna up)
3. Keep away from steppers and OLED for best reception

### 4. IMU & Magnetometer
1. Solder U8 (LSM6DSO) — LGA-14, 6-axis IMU
2. Solder U9 (MMC5603NJ) — LGA-12, 3-axis magnetometer
3. Place near center of PCB, away from current-carrying traces

### 5. ADC & Detector
1. Solder U6 (ADS122U04) — TSSOP-16, 24-bit ADC
2. Solder D1 (thermopile detector) — on detector board (off-board)
3. Connect detector to PCB via shielded twisted-pair cable (≤50 mm)

### 6. Stepper Drivers
1. Solder U13 (A4988) — AZ stepper driver module (header pins)
2. Solder U13b (A4988) — EL stepper driver module (header pins)
3. Solder MS1/MS2/MS3 jumpers (PC5, PC6, PC12 → all HIGH for 1/16)

### 7. Memory / Display / BLE
1. Solder U12 (SH1106 OLED) — I2C module (header pins)
2. Solder U10 (ESP32-C3-MINI-1) — castellated module
3. Solder U11 (W25Q128) — SOIC-8, SPI flash
4. Solder J2 (MicroSD socket) — push-push

### 8. UI & Sensors
1. Solder SW1 (EC11 rotary encoder)
2. Solder SW2-SW4 (tactile buttons: Mode, Start/Stop, Calibrate)
3. Solder SW5, SW6 (limit switches for AZ/EL home)
4. Solder SW7 (optical slot sensor for filter wheel home)
5. Solder D2 (green LED), D3 (blue LED), D4 (WS2812B RGB LED)
6. Solder R1, R2 (battery divider 100k×2)

## Mechanical Assembly

### 1. Azimuth Turntable
1. 3D print the azimuth base and turntable housing
2. Mount NEMA8 AZ stepper (M1) vertically in the base
3. Attach the 60:1 worm gear to the stepper shaft
4. Mount the turntable gear ring to the rotating platform
5. Install the AZ home limit switch (SW5) at the 0° position
6. Connect stepper wires to A4988 AZ driver (JST connector)

### 2. Elevation Arm
1. 3D print the elevation arm and bracket
2. Mount NEMA8 EL stepper (M2) on the azimuth turntable
3. Attach the 2:1 timing belt pulleys and GT2 belt
4. Mount the collimator tube on the elevation arm (pivot joint)
5. Install the EL home limit switch (SW6) at the 0° (horizon) position
6. Connect stepper wires to A4988 EL driver (JST connector)

### 3. Collimator Tube & Filter Wheel
1. Assemble the collimator tube: 30 mm aperture, 350 mm focal length
2. Install the 6 interference filters in the 3D-printed filter wheel
   - Position 0: 405 nm (blue-violet)
   - Position 1: 440 nm (blue)
   - Position 2: 675 nm (red)
   - Position 3: 870 nm (near-IR)
   - Position 4: 940 nm (near-IR, water vapor)
   - Position 5: 1640 nm (short-wave IR)
3. Mount the SG90 servo (M3) to rotate the filter wheel
4. Install the optical slot sensor (SW7) at the position 0 slot
5. Mount the thermopile detector (D1) at the focal point of the
   collimator tube, behind the filter wheel

### 4. Enclosure
1. 3D print the main enclosure (base + lid)
2. Mount the PCB in the base with M2 standoffs
3. Route cables to the tracking head through a strain-relief hole
4. Mount the OLED on the front panel (cutout)
5. Mount buttons and encoder on the front panel
6. Attach the tracking head to the top of the enclosure

## Wiring

| From | To | Signal | Notes |
|------|-----|--------|-------|
| PCB J_AZ | M1 (AZ stepper) | 4-wire | JST-XH 4-pin |
| PCB J_EL | M2 (EL stepper) | 4-wire | JST-XH 4-pin |
| PCB J_SERVO | M3 (SG90) | 3-wire | VCC/GND/PWM |
| PCB J_DET | D1 (thermopile) | 2-wire shielded | Twisted pair, ≤50 mm |
| PCB J_HOME_AZ | SW5 | 2-wire | Limit switch |
| PCB J_HOME_EL | SW6 | 2-wire | Limit switch |
| PCB J_HOME_FW | SW7 | 3-wire | Optical slot (VCC/GND/OUT) |

## First Boot

1. Insert a charged 18650 cell
2. Insert a microSD card (FAT32 formatted)
3. Power on — OLED shows "HELIO TILT v1.0"
4. The device enters IDLE state
5. Press Start — device enters GPS_FIX state
6. Wait for GPS fix (LED turns green when fix acquired, ~10-30 s)
7. Device will home steppers, then start tracking the sun
8. The OLED shows DNI bar chart + AOD values
9. After ~10 seconds, the first filter sweep completes and AOD
   values appear

## Calibration

### Magnetometer Calibration
1. From the menu, select "Mag Calibrate"
2. Rotate the device slowly 360° in the horizontal plane
3. Wait ~30 seconds for calibration to complete
4. The hard-iron offsets are stored in RAM (save to flash in production)

### Langley Calibration
1. Choose a clear, stable-aerosol day (morning or evening)
2. From the menu, select "Langley Cal" (or press Calibrate button)
3. The device will track the sun and log V(λ) vs air mass every
   2 minutes for 2-3 hours
4. The OLED shows progress: point count, R², V₀(870)
5. When R² > 0.99 for all wavelengths, calibration is complete
6. The V₀ constants are stored in RAM (save to flash in production)
7. AOD measurements are now accurate to ±0.01

### DNI Verification
1. Compare the DNI reading with a reference pyranometer
2. If the offset is >5%, adjust the thermopile sensitivity constant
   in `stm32g474_conf.h` (THERMOPILE_SENS)
3. Re-flash the firmware