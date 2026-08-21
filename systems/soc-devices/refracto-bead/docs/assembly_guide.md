# Refracto Bead — Assembly Guide

## Overview

This guide walks you through assembling the Refracto Bead pocket digital Abbe refractometer from components to a working device.

## Tools Required

- Soldering iron with fine tip (0.5 mm)
- Solder wire (0.5 mm, 60/40 or lead-free)
- Flux pen
- Tweezers (ESD-safe, fine tip)
- Magnifying lens or microscope
- Multimeter
- ST-Link V2 (or compatible SWD programmer)
- USB-C cable
- Computer with:
  - arm-none-eabi-gcc toolchain
  - STM32Cube HAL libraries
  - ESP-IDF v5.3+

## PCB Specifications

- **Size**: 85 × 54 mm (credit-card form factor)
- **Layers**: 4 (Signal / GND / 3V3 / Signal)
- **Thickness**: 1.6 mm FR4
- **Finish**: ENIG (recommended for the CCD DIP socket and fine-pitch LQFP)
- **Solder mask**: Matte black
- **Silkscreen**: White

## Assembly Order

### Step 1: SMD Passive Components (0402)

Start with the smallest components:

1. **I²C pull-ups**: 4.7 kΩ on SDA (PB1) and SCL (PB0) lines
2. **USB CC pull-downs**: 5.1 kΩ on CC1 and CC2 lines
3. **Decoupling capacitors**: 100 nF on each VDD pin (STM32, ESP32-C3, BME280, TSL1402R)
4. **Bulk decoupling**: 10 µF ceramic near STM32 VDD, 4.7 µF near ESP32-C3
5. **Battery voltage divider**: 100 kΩ + 100 kΩ on VBAT_SENSE (PB13)
6. **MCP73831 PROG resistor**: 2 kΩ to GND (500 mA charge current)
7. **1-Wire pullup**: 4.7 kΩ on DS18B20_DATA (PB11)
8. **LED base resistors**: 1 kΩ on each NPN base (Q1–Q4)
9. **LED emitter resistors**: 100 Ω on each NPN emitter (constant-current approx 26 mA)
10. **NTC bias resistor**: 10 kΩ in series with NTC to VDD

### Step 2: Small SMD ICs

1. **MCP73831** (SOT-23-5) — LiPo charger
2. **AP2112-3.3** (SOT-223) — LDO
3. **MMBT2222A** (SOT-23) × 4 — LED NPN drivers
4. **74LVC1G66** (SOT-23-5) — USB D+/D- analog mux

### Step 3: STM32G491RET6 (LQFP-64)

1. Apply solder paste to the footprint
2. Align pin 1 indicator with silkscreen dot
3. Reflow with hot air or reflow oven
4. Inspect all 64 pins under microscope for bridges
5. Clean flux residue

### Step 4: ESP32-C3-MINI-1 Module

1. Apply solder paste to the castellated pad footprint
2. Position the module — align pin 1 with silkscreen
3. Reflow — ensure all castellated pads are properly wetted
4. **Keep the antenna area clear** of copper on all layers

### Step 5: TSL1402R CCD (DIP-8)

1. Insert the TSL1402R into the DIP-8 socket (or solder directly)
2. Orientation: pin 1 (AO) faces toward the STM32
3. The CCD sensor window must face toward the prism/lens assembly
4. This is the most critical optical alignment component

### Step 6: BME280 Sensor (LGA-8)

1. Apply solder paste to pads
2. Align by package outline (beveled corner = pin 1)
3. Reflow and inspect for tombstoning

### Step 7: DS18B20 (TO-92)

1. Insert through-hole, bend leads to position sensor flat against prism body
2. Solder on bottom side
3. **Bond the sensor to the prism aluminum baseplate** with thermal epoxy

### Step 8: DRV8833 + TEC1-04030 (Optional)

1. Solder the DRV8833 (SOIC-16)
2. Bond the TEC1-04030 peltier to the underside of the prism baseplate
3. Wire TEC+ and TEC- to the DRV8833 output pads

### Step 9: USB-C Connector

1. Apply solder paste to SMD pads
2. Position flush with PCB edge
3. Solder through-hole mounting tabs for mechanical strength

### Step 10: OLED Display

1. Solder the 4-pin I²C header (VCC, GND, SCL, SDA) + RES pin
2. Mount OLED with double-sided foam tape (provides vibration isolation)
3. Connect via the pre-soldered header

### Step 11: LEDs (4 wavelengths)

1. Insert the 4 LEDs through their holes on the optical bench side
2. **Orientation**: anode (long lead) toward the NPN collector pad
3. Solder and trim leads
4. Position LEDs to illuminate the diffuser uniformly

### Step 12: Optical Assembly

1. **Mount the SF11 prism** in the 12×12 mm cutout on the top of the PCB
2. Use an aluminum baseplate (custom machined) to hold the prism
3. **Bond the DS18B20** to the baseplate with thermal epoxy
4. **Mount the plano-convex lens** (f=12mm) between the prism exit face and the CCD
   - Use a machined spacer tube (12 mm long, 6 mm inner diameter)
   - The lens focuses the angular light distribution onto the CCD
5. **Mount the ground-glass diffuser** between the LEDs and the prism
6. **Shroud the optical path** with a black ABS tube (light-tight)

### Step 13: microSD Socket

1. Solder the SMD microSD socket
2. The card ejector should face the PCB edge

### Step 14: Buttons & Battery

1. Solder 3 tactile switches (Measure, Mode, Power) on the right edge
2. Connect the 800 mAh LiPo: red → VBAT+, black → GND
3. Secure battery with double-sided tape in the bottom pocket

### Step 15: Crystal

1. Solder the 8 MHz crystal (3225 SMD package) near the STM32
2. Add 12 pF load capacitors on each crystal pin to GND

## Post-Assembly Checks

1. **Visual inspection**: Check all solder joints under magnification
2. **Continuity test**: Verify no shorts between VDD and GND
3. **Power test**: Apply 5 V via USB-C — current should be < 100 mA at idle
4. **Voltage test**: 3.3 V rail should read 3.25–3.35 V
5. **SWD test**: Connect ST-Link and verify the STM32 responds (`openocd -f interface/stlink.cfg -f target/stm32g4x.cfg`)
6. **ESP32 test**: Check that ESP_EN (PB2) high enables the ESP32-C3

## First Boot

1. Flash the STM32 firmware via SWD:
   ```bash
   cd firmware
   make flash
   ```
2. Flash the ESP32-C3 firmware via USB-C:
   ```bash
   cd firmware/esp32-c3
   idf.py set-target esp32c3
   idf.py -p /dev/ttyACM0 flash
   ```
3. The OLED should show "REFRACTO BEAD" after boot
4. Press MODE to cycle through measurement modes (RI, BRIX, SG, COOL, ALC)
5. Press MEASURE to start your first measurement

## Calibration

### First-Time Calibration (Required)

Before first use, calibrate the Refracto Bead with two reference liquids:

1. **Distilled water** (n_D = 1.3330 at 20°C)
2. **RI standard oil** (n_D = 1.5150 at 20°C, Cargille Labs)

Procedure:
1. Clean the prism with lens tissue and isopropyl alcohol
2. Apply 1–2 drops of distilled water to the prism
3. Hold MEASURE for >3 seconds to enter calibration mode
4. The OLED prompts "Place WATER, press MEASURE"
5. Press MEASURE — the device records the water edge position
6. Clean the prism, apply the RI standard oil
7. Press MEASURE again — records the oil edge position
8. "Calibration complete ✓" — coefficients stored in flash

### Verification

After calibration, verify accuracy:
1. Measure distilled water → should read n_D = 1.3330 ± 0.0003
2. Measure a known solution (e.g., 20% sucrose → n_D ≈ 1.3635)
3. If readings are off, repeat calibration

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No OLED display | I²C wiring wrong | Check PB0/PB1 connections, 4.7k pullups |
| CCD reads all zeros | TSL_CLK not running | Check TIM2_CH1 on PA1, 1 MHz PWM |
| CCD reads all max | LEDs not turning on | Check PA3–PA6 and NPN drivers |
| No edge detected | Optical misalignment | Check prism→lens→CCD spacing (12 mm) |
| RI values wrong | Not calibrated | Perform 2-point calibration (water + oil) |
| BLE not found | ESP32 not powered | Check PB2 (ESP_EN) is high |
| Wi-Fi won't connect | No credentials | Store SSID/pass via BLE or USB |
| Battery not charging | MCP73831 issue | Check PROG resistor (2 kΩ), USB 5V present |
| Temperature wrong | DS18B20 not bonded | Thermal-epoxy sensor to prism baseplate |

## Enclosure (Optional)

A 3D-printed snap-fit enclosure is available:

- Print in PETG or PLA (black for light-tightness)
- Two-part design: top (OLED window + prism opening) and bottom (battery compartment)
- The prism opening has a hinged dust cover
- USB-C cutout on the right edge
- Button cutouts on the right edge
- No openings over the optical path (light-tight)

---

*Refracto Bead Assembly Guide — SoC Device Inventions*