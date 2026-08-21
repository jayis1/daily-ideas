# Scribe Nib — Assembly Guide

## Overview

The Scribe Nib is a 12×18mm PCB that clips onto any pen. Assembly requires
surface-mount soldering equipment (0402 passives, QFN ICs) and a few specialty
steps for the clip mechanism and battery.

## Tools Required

- Soldering iron with fine tip (≤0.3mm) or reflow oven
- Solder paste (type 4 or finer for 0402 components)
- Tweezers (ESD-safe, fine tip)
- Hot air rework station (for rework only)
- Multimeter
- Magnification (microscope or 10× loupe)
- USB-C cable for testing
- ESP-IDF development environment for firmware flash

## Assembly Steps

### 1. PCB Fabrication

Order the PCB from JLCPCB or similar with these specs:
- **Size**: 12mm × 18mm
- **Layers**: 4 (2 signal + 1 ground + 1 power)
- **Thickness**: 1.0mm (thin for clip form factor)
- **Surface finish**: ENIG (for fine-pitch components)
- **Solder mask**: Black (both sides)
- **Silkscreen**: White
- **Edge**: V-scored panel for assembly, then snap apart

### 2. SMD Component Placement

Place components in this order (smallest to largest):

1. **Passives (0402)**: All resistors, capacitors, and inductors
   - R1, R2: 4.7kΩ I²C pull-ups (SDA, SCL)
   - C1-C8: 100nF decoupling capacitors (one per IC VDD pin)
   - C9, C10: 10µF bulk capacitors (VBAT, VDD)
   - R3: 2kΩ MCP73831 PROG resistor (sets charge current to 500mA)
   - L1: 10µH inductor (not used in this design — all DC)

2. **Si2302 MOSFET** (SOT-23): Motor driver
   - Gate → GPIO42, Source → GND, Drain → Motor (-)

3. **ME6211 LDO** (SOT-23-5): 3.3V regulation
   - Pin 1: VBAT, Pin 2: GND, Pin 3: EN (tie to VBAT), Pin 4: VOUT (3.3V)

4. **MCP73831 Charger** (SOT-23-5): LiPo charging
   - Pin 1: VUSB, Pin 2: STAT → GPIO12, Pin 3: VBAT
   - Pin 4: PROG → R3 → GND, Pin 5: GND

5. **QMC5883L Magnetometer** (LGA-16): 3×3mm
   - SDA → GPIO7, SCL → GPIO8, DRDY → GPIO10
   - Address pin tied to GND for 0x0D

6. **ICM-42688-P IMU** (LGA-14): 2.5×3mm
   - **Critical**: Position at the center of the PCB (pen contact point)
   - SCLK → GPIO4, SDI → GPIO5, SDO → GPIO0, CS → GPIO6
   - INT1 → GPIO3

7. **WS2812B-2020 LED** (2×2mm): Status indicator
   - DIN → GPIO13

8. **Vibration Motor** (4mm coin): Haptic feedback
   - Solder pads to PCB edge, wire to MOSFET drain

9. **USB-C Receptacle** (16-pin SMD): Right-angle
   - Position at top edge of clip
   - VBUs → MCP73831 VDD, D+/D- → ESP32-S3 GPIO18/19
   - GND → common ground

10. **ESP32-S3-MINI-1** (Module): Main SoC
    - **Last component** placed (largest, most pins)
    - Align module with pin 1 marker
    - Reflow at 240°C peak

11. **SSD1306 OLED** (flex tail): 64×32 display
    - Flex cable soldered to pads at bottom of PCB
    - SDA → GPIO7, SCL → GPIO8, RST → GPIO9
    - Address: 0x3C

### 3. Battery Attachment

- Use 80mAh LiPo pouch (3.7V)
- Attach to back of PCB with double-sided tape
- Solder + and - leads to VBAT and GND pads
- **Important**: Do not short battery leads during soldering!
- Apply conformal coating over battery and leads

### 4. Spring Steel Clip

- Bond 0.3mm spring steel strip to back of PCB with epoxy
- Steel provides spring force to grip the pen
- PCB+steel assembly forms the clip body
- Leave a small gap (1mm) between steel and battery for flex

### 5. Silicone Sleeve (Optional)

- 3D-print a PETG mold, cast silicone (shore 40A)
- Sleeve slides over entire assembly for protection
- Cutouts for USB-C port and OLED window
- File: `hardware/enclosure/clip_sleeve.step`

## Testing

### Power Test

1. Connect USB-C cable (no battery yet)
2. Measure VDD (3.3V) at test point
3. Verify charge status LED behavior
4. Measure quiescent current (< 50µA expected)

### Battery Test

1. Disconnect USB
2. Attach battery (polarity critical!)
3. Verify device boots (OLED shows "SbN")
4. Check battery voltage at VBAT test point (3.7V nominal)

### IMU Test

1. Flash firmware via USB-C
2. Monitor serial output at 115200 baud
3. Move the clip and verify IMU data appears in logs
4. Test pen-up/pen-down by tapping on table

### BLE Test

1. Put device in pairing mode (hold BOOT during reset)
2. Search for "ScribeNib-XXXX" from phone/laptop
3. Pair as BLE keyboard
4. Write on paper and verify characters appear on screen

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No power, no LED | USB-C not connected or battery dead | Check USB voltage, charge battery |
| IMU reads all zeros | SPI wiring wrong or CS stuck low | Check GPIO4-6 connections, verify CS pull-up |
| BLE not discoverable | Firmware not flashed or BT not init'd | Re-flash firmware, check BT config |
| Characters all wrong | Calibration needed or IMU drift | Run calibration, check gravity baseline |
| Motor doesn't vibrate | MOSFET gate not driven or motor bad | Check GPIO42 output, test motor directly |
| OLED blank | I²C issue or reset not toggled | Check GPIO7/8/9, add pull-ups |

## Safety Notes

- **Battery safety**: Never short-circuit or puncture the LiPo battery
- **Charge monitoring**: First charge should be supervised (check for swelling/heat)
- **ESD**: The IMU and ESP32-S3 are ESD-sensitive — use grounded wrist strap
- **Heat**: Do not exceed 260°C soldering temperature on the IMU