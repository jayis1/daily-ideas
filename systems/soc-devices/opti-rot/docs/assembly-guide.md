# Opti Rot — Assembly Guide

This guide walks through assembling the Opti Rot pocket digital polarimeter, from PCB population to optical bench alignment.

## PCB Assembly

### Tools Required

- Soldering iron (fine tip) or hot-air rework station
- Solder paste + stencil (recommended for SMD)
- Tweezers (fine, anti-magnetic)
- Multimeter
- magnifier / microscope (10×)
- KiCad (for viewing schematic/PCB)

### Step 1: Power Section

1. Solder **TP4056** (U3, SOP-8) — USB-C charge controller.
2. Solder **USB-C connector** (J1) — use plenty of flux; the SMT pads are fine-pitch.
3. Solder **AP2112-3.3** (U4, SOT-23-5) — digital 3.3V LDO.
4. Solder **LP5907MFX-3.3** (U5, SOT-23-5) — ultra-low-noise analog 3.3V LDO.
5. Solder **ADP7118ARDZ-5.0** (U6, SOIC-8) — 5V LDO for stepper + LEDs.
6. Solder all power capacitors: C2 (10µF), C3 (1µF), C4 (2.2µF), C6 (4.7µF), C8 (10µF).
7. Insert 18650 battery. Verify: 3.7V at BAT+, 5.0V at ADP7118 output, 3.3V at AP2112, 3.3V at LP5907.

### Step 2: Main MCU

1. Solder **STM32G491RET6** (U1, LQFP-64, 0.5mm pitch) — align pin 1, tack two corners, then drag-solder remaining pins. Use flux generously. Check for bridges with multimeter continuity.
2. Solder decoupling: C1 (100nF near each VDD pin), C7 (1µF near ESP32-C3).
3. Solder **ESP32-C3-MINI-1** (U2) — pre-built module, castellated edges.
4. Solder R9 (10kΩ) for ESP32-C3 EN pullup.

### Step 3: Sensors & Display

1. Solder **TSL257** (U7, SOIC-8) — photodiode. Place near optical bench connector. Power from LP5907 analog 3.3V.
2. Solder **DS18B20** (U8, SOT-23) — temperature sensor. Mount near sample tube chamber. C9 (100nF) across VDD/GND. R1 (4.7kΩ) pullup on 1-Wire data.
3. Solder **SSD1306 OLED** (U9) — I2C module with pre-soldered header. Connect via 4-pin jumper wire or direct SMD.
4. Solder **microSD socket** (J2) — push-push type.

### Step 4: Stepper & LEDs

1. Solder **ULN2003A** (U10, SOIC-16) — stepper driver.
2. Wire **28BYJ-48** stepper (M1) via 5-pin header to ULN2003 outputs.
3. Solder **589nm LED** (D1) with R6 (150Ω) current limit.
4. Solder **520nm LED** (D2) with R7 (150Ω).
5. Solder **405nm LED** (D3) with R8 (100Ω).
6. Solder **RGB LED** (D4, 5050 SMD) with current limit resistors.
7. Solder three **tactile buttons** (SW1/SW2/SW3) with 10kΩ pullups (R10).

### Step 5: Voltage Divider

1. Solder R4 (100kΩ) and R5 (47kΩ) for battery voltage divider. Connect midpoint to PA3 (ADC).

## Optical Bench Assembly

The optical bench is a separate 3D-printed assembly that mounts to the PCB enclosure.

### Parts

- 2× linear polarizing film discs (25mm diameter) — Edmund Optics #32-694 or equivalent
- 1× aspheric collimator lens (25mm, f=20mm) — Edmund Optics #66-048 or equivalent
- 1× borosilicate sample tube (100mm path, 10mm OD, 8mm ID) — standard polarimetry tube
- 3D-printed optical bench (black PLA, file in `/docs/stl/`)
- 28BYJ-48 stepper with analyzer disc coupling

### Assembly

1. **LED mount**: Install the 3 LEDs at the input end of the optical bench, angled to converge on the collimator lens. The 589nm LED is primary (center); 520nm and 405nm are offset by ~15-20°.

2. **Collimator lens**: Press-fit the aspheric lens into the 3D-printed lens holder, 20mm from the LEDs. The lens converts the diverging LED output into a parallel beam (~20mm diameter).

3. **Polarizer**: Mount the first polarizing film disc immediately after the collimator. This is fixed (does not rotate). Align its axis to 0° (reference).

4. **Sample tube holder**: The 100mm borosilicate tube slides into a holder in the center of the bench. The tube must be removable for filling and cleaning. Use PTFE ferrules for a light-tight seal.

5. **Analyzer + stepper**: Mount the second polarizing film disc on the 28BYJ-48 stepper shaft using a 3D-printed coupling. The stepper rotates the analyzer through ±90° (2048 half-steps of the 4096/rev total). Position the stepper so the analyzer disc is ~5mm from the photodiode.

6. **Photodiode**: Mount the TSL257 at the output end, facing the analyzer. Ensure light-tight enclosure around the photodiode to reject ambient light.

7. **Light baffles**: Install internal baffles (3D-printed rings) between each optical element to prevent stray light from reaching the photodiode without passing through the polarizer-sample-analyzer chain.

8. **Enclosure**: Cover the optical bench with a black, light-tight lid. Any ambient light leakage will degrade measurement accuracy.

### Alignment Check

1. Power on with empty sample tube.
2. Set 589nm LED on (via CAL button → Config mode, or BLE app).
3. Rotate stepper through full range. The photodiode reading should vary sinusoidally with a clear minimum (Malus's law). If no variation is seen, check polarizer alignment.
4. The minimum reading should be <5% of maximum (high extinction ratio). If not, clean the polarizing films and check for stress birefringence in the sample tube.

## Calibration

### Step 1: Auto-Zero

1. Insert an empty, clean sample tube (filled with distilled water or air).
2. Press CAL button. The device measures the null angle at all 3 wavelengths and stores as reference.

### Step 2: Sucrose Verification (Optional)

1. Prepare a 26.000 g/100mL sucrose solution (26g sucrose dissolved in water, diluted to 100mL at 20°C).
2. Fill the sample tube. Press MEAS.
3. The reading should be +34.6° (at 589nm, 20°C, 100mm path).
4. If the reading differs, adjust the path length parameter in Config mode or check temperature.

### Step 3: Temperature Calibration

1. The DS18B20 reads the sample chamber temperature. For precise work, compare against a calibrated thermometer.
2. Offset can be adjusted in Config mode if needed (DS18B20 is typically ±0.5°C).

## Flashing Firmware

1. Connect ST-Link v2 to SWD pins (SWDIO, SWCLK, GND, 3.3V) on the debug header.
2. Build: `cd firmware && mkdir build && cd build && cmake .. && make`
3. Flash: `openocd -f interface/stlink.cfg -f target/stm32g4x.cfg -c "program opti_rot.bin reset exit 0x08000000"`
4. The OLED should display the splash screen within 2 seconds.

## ESP32-C3 Companion Firmware

The ESP32-C3 companion firmware (in `firmware/companion/`) is built with ESP-IDF:
```bash
cd firmware/companion
idf.py build flash
```
This sets up the BLE GATT server and Wi-Fi softAP that relay commands to/from the STM32.