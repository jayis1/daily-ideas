# Dent Scope — Assembly Guide

## Overview

Dent Scope is a pocket instrumented indentation tester. This guide walks through mechanical assembly, wiring, calibration, and first test.

> ⚠️ **Safety warning.** The device applies up to 20 N of force via a stepper motor. The mechanical over-travel clutch (25 N slip clutch) and software force limit protect against overload. Always ensure the tip is securely fastened and the reference ring is clean.

## Mechanical Assembly

### Parts needed (see `hardware/BOM.csv`)

- Custom PCB (4-layer, 34×180 mm)
- 3D-printed PETG enclosure (pen-sized, Ø34 × 180 mm)
- 28BYJ-48 geared stepper + M4×0.35 leadscrew
- 20 N sub-miniature load cell + HX711
- AD7746 capacitive sensor + custom parallel-plate PCB
- Spring-loaded reference ring
- Interchangeable indenter tip (Vickers/Berkovich/WC ball)
- 25 N mechanical slip clutch

### Steps

1. **PCB population.** Solder all SMD passives first (0603 resistors/caps), then the STM32G474, ESP32-C3 module, HX711, AD7746, DRV8833, ICM-42688-P, OLED, SD socket, USB-C + TP4056, MP1584, buttons, buzzer, LED. Use flux and hot-air for QFPs.

2. **Stepper assembly.** Mount the 28BYJ-48 stepper in the mid-section of the enclosure. Connect the M4×0.35 leadscrew to the stepper output shaft via a flexible coupler. Install the 25 N slip clutch between the leadscrew and the load cell mount.

3. **Load cell.** Mount the 20 N sub-miniature foil-strain load cell between the leadscrew nut and the indenter shaft. The load cell measures the reaction force as the indenter presses into the sample. Wire the load cell to the HX711 (E+→E+, A+→A+, A-→A-, E-→E-).

4. **Capacitive depth sensor.** The parallel-plate sensor consists of two PCB plates (Ø10 mm) separated by a ~1 mm gap. The fixed plate mounts on the spring-loaded reference ring (which contacts the sample surface). The moving plate mounts on the indenter shaft. As the indenter moves into the sample, the gap changes proportionally. Wire to AD7746 CIN1/CIN2.

5. **Reference ring.** The spring-loaded reference ring sits at the bottom of the device. When placed on a sample, it contacts the surface and provides the reference plane for depth measurement. This is the key innovation: depth is measured relative to the sample surface, eliminating frame compliance.

6. **Indenter tips.** The interchangeable tips thread into a collet at the bottom of the indenter shaft. A reed interlock switch detects tip presence before allowing a test. Tips available:
   - Vickers (136° diamond pyramid) — general metals/ceramics
   - Berkovich (65.27° 3-sided pyramid) — thin films
   - WC ball (1 mm) — soft metals/polymers (Brinell)

7. **Enclosure.** Place the PCB in the upper section of the PETG enclosure. Mount the OLED on the side. The stepper + leadscrew + load cell + sensor stack in the mid-section. The reference ring protrudes from the bottom. Buttons accessible on the side.

8. **Battery.** Insert two 18650 cells in the top compartment. The TP4056 handles USB-C charging.

## Wiring

Follow the pin table in `README.md`. Key connections:

- HX711: SCK → PA1, DOUT → PA2, RATE → PA3
- AD7746: I²C → PB8/PB9 (I²C1)
- DRV8833: IN1-4 → PA4-PA7, EN → PA8
- ICM-42688-P: SPI2 → PB10/PB11, CS → PB12
- DS18B20: 1-wire → PB0
- SD SPI → PB3/PB4/PB5, CS → PB6
- OLED SPI → shared PB3/PB5, CS → PB7, DC → PB1, RST → PC14
- UART to ESP32-C3 → PA9/PA10
- Buttons → PB13/PB14/PB15
- Interlock (tip present) → PC13
- Stall/over-travel → PA11

## Calibration

### 1. Force calibration

1. With no tip installed and no contact, run `scripts/calibrate.py --force-zero`.
   This sets the HX711 offset (tare).
2. Hang a known reference weight (e.g., 5 g = 49.1 mN, or 20 g = 196.2 mN) from the indenter shaft.
3. Run `scripts/calibrate.py --force-scale 49.1` (or your weight in mN).
   This computes the HX711 scale factor (mN per count) and stores it in flash.

### 2. Depth (capacitive) calibration

1. Place the device on a flat surface. The reference ring contacts the surface.
2. Using precision gauge blocks or shims, create known gaps between the reference ring and the indenter shaft tip: 0 µm (contact), 50 µm, 100 µm, 150 µm.
3. At each gap, run `scripts/calibrate.py --depth-point <um>`.
4. The script collects AD7746 raw readings and fits a polynomial (µm = offset + scale×pF + quad×pF²).
5. Store the calibration in flash with `--depth-commit`.

### 3. Tip area function

The Vickers and Berkovich tips have a known area function `A(h_c) = 24.5·h_c²` (ideal geometry). For higher accuracy, calibrate against a fused silica standard (E = 72 GPa, ν = 0.17):
1. Perform 5 indents on fused silica at 5 N peak load.
2. The computed E should be ~72 GPa. If it deviates, adjust the tip area function coefficient.
3. Store corrected area function in flash.

### 4. Temperature

DS18B20 is factory-trimmed to ±0.5 °C. For higher accuracy, do an ice-bath (0 °C) + room temperature two-point calibration.

## First Test

1. Insert a Vickers tip. The reed interlock should detect it (OLED shows "Tip: VICK").
2. Place Dent Scope on a clean, flat metal surface (e.g., aluminum block).
3. Check tilt: the IMU reading should be < 2° (OLED shows "Tilt: X.X deg"). Adjust the device position if needed.
4. Press START. The stepper approaches the surface. When the load cell detects > 50 mN (surface contact), loading begins.
5. The P–h curve streams live on the OLED and via BLE to the phone app.
6. After the hold and unloading, the buzzer sounds and results appear: HV, E (GPa), η, and material match.
7. The stepper retracts. Ready for the next test.

## Maintenance

- **Tip care:** Diamond tips are durable but can chip on hard ceramics. Inspect under magnification regularly. Clean with isopropyl alcohol.
- **Reference ring:** Keep the contact surface clean and flat. Replace if worn.
- **Load cell:** Recalibrate monthly with a reference weight.
- **Capacitive sensor:** Keep plates clean and dry. Moisture affects capacitance.