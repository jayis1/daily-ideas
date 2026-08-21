# Levia Forge — Assembly Guide

## Tools Required

- Soldering iron (fine tip) or hot-air rework station
- Solder paste + stencil (for SMT reflow)
- Multimeter
- 3D printer (for array mounts)
- Small Phillips screwdriver
- Tweezers (for SMT placement)
- Flux pen

## Step 1: PCB Fabrication

Order the 4-layer PCB from your preferred fab (JLCPCB, PCBWay, OSH Park).
Use the Gerber files from `schematic/levia-forge-gerbers.zip`.

Specifications:
- 4 layers (Top, GND, 3.3V/10V split, Bottom)
- 1.6mm thickness
- ENIG finish (for the QFN pads)
- 6/6 mil trace/space minimum

## Step 2: SMT Component Assembly

### 2a. Power Supply Section
1. Apply solder paste with stencil
2. Place: TPS61023 (U13), MCP1603T (U14), AP2112K (U15), TP4056 (U16)
3. Place inductors L1 (10µH), L2 (4.7µH)
4. Place bulk capacitors C1-C10 (10µF)
5. Place feedback resistors R73 (1MΩ), R74 (118kΩ)
6. Reflow at 245°C peak
7. **Test**: Connect 7.4V bench supply. Verify:
   - 3.3V rail: ±0.1V
   - 10V rail: ±0.2V
   - 5V rail: ±0.1V

### 2b. RP2040 Section
1. Place RP2040 (U1, QFN-56) — align pin 1 dot with PCB marker
2. Place W25Q128 flash (U2, SOIC-8)
3. Place 12 MHz crystal (Y1) and load capacitors (22pF each)
4. Place decoupling caps (100nF on each VCC pin)
5. Place USB-C connector (J1) and 27Ω series resistors
6. Place BOOTSEL button (SW4) and RUN reset circuit
7. Reflow
8. **Test**: Connect USB-C to computer. Should appear as RPI-RP2
   drive when BOOTSEL held during power-up.

### 2c. 74HC595 Shift Register Chain
1. Place 9× 74HC595 (U4-U12, SOIC-16) in a row
2. Place 100nF decoupling on each VCC pin (C11-C19)
3. Place 10kΩ pull-up on OE line (R77)
4. Reflow
5. **Test**: Scope GP0/GP1/GP2 while running a test program.

### 2d. BJT Driver Array (72 channels)
This is the most time-consuming part. Use a stencil for the SOT-23
pads.

1. Place 72× MMBT3904 (Q1-Q72, SOT-23, NPN)
2. Place 72× MMBT3906 (Q73-Q144, SOT-23, PNP)
3. Place 72× 1kΩ base resistors (R1-R72, 0805)
4. Reflow
5. **Test**: Apply 10V to the rail. Drive one 74HC595 output HIGH.
   Verify 10V at the corresponding transducer pad. Drive LOW,
   verify 0V. Repeat for a few channels.

### 2e. ESP32-C3 Module
1. Place ESP32-C3-WROOM-02 (U3) — handle with care (antenna)
2. Place 32.768 kHz crystal (Y2) and load caps
3. Place LED2 (green, BLE status) and current-limit resistor
4. Reflow (lower temp if module has solder already)
5. **Test**: Flash BLE bridge firmware. Should advertise as "Levia Forge".

### 2f. Peripherals
1. Place SSD1306 OLED header (4-pin, 0.1" pitch)
2. Place VL53L0X breakout connector (6-pin)
3. Place microSD socket (J2)
4. Place joystick connector (J4, 5-pin)
5. Place rotary encoder pins (J5, 5-pin)
6. Place buttons (SW1, SW2)
7. Place reed switch (SW3)
8. Place LSM6DSO (U18, QFN-14) and decoupling
9. Reflow or hand-solder through-hole parts

## Step 3: 3D-Printed Mechanical Parts

### Top Array Mount
- Material: PETG (heat-resistant, slightly flexible)
- Print settings: 0.2mm layer height, 30% infill
- File: `hardware/array_mount_top.stl`
- 36 holes for MA40S4S transducers (10mm diameter)
- Curved profile (R = 40mm spherical cap)
- Mounts to the enclosure top with 4× M3 screws

### Bottom Array Mount
- Same as top but mirrored
- File: `hardware/array_mount_bottom.stl`

### Enclosure Base
- Material: PETG
- File: `hardware/enclosure_base.stl`
- Holds PCB, battery holder, and array mounts
- Has cutouts for USB-C, SD card, joystick, encoder, OLED

## Step 4: Transducer Installation

1. Press-fit 36 MA40S4S transducers into the top mount (silver side
   facing down toward the trap zone). Label them T00-T35.
2. Press-fit 36 MA40S4S into the bottom mount (silver side facing up).
   Label them B00-B35.
3. Solder 30 AWG wires from each transducer to the PCB driver pads.
   **Keep all wire lengths equal within each array (±5 mm).**
   Unequal wires cause phase errors.
4. Use ribbon cable or individual wires with consistent routing.

## Step 5: Final Assembly

1. Mount the bottom array to the enclosure base (screws pointing up)
2. Install the PCB in the base (4× M3 standoffs)
3. Mount the top array above the PCB (4× M3 standoffs + side panels)
4. Install the VL53L0X breakout on the top mount center, pointing down
5. Wire VL53L0X to the PCB (I2C + power, 4 wires)
6. Install the OLED on the front panel
7. Install the joystick, encoder, and buttons on the front panel
8. Install the reed switch on the lid frame
9. Insert 2× 18650 batteries
10. Close the enclosure

## Step 6: Firmware Flashing

### RP2040
```bash
cd firmware/build
cmake .. -DPICO_SDK_PATH=/path/to/pico-sdk
make -j4
# Hold BOOTSEL, connect USB-C, release BOOTSEL
cp levia_forge.uf2 /media/$USER/RPI-RP2/
```

### ESP32-C3
```bash
cd firmware/esp32c3
idf.py set-target esp32c3
idf.py flash
```

## Step 7: Testing

1. Power on. OLED should show "LEVIA FORGE v1.0"
2. Drop a 2mm styrofoam bead into the cavity
3. Press MODE button. The bead should levitate at the center.
4. Move joystick: bead should move in X/Y
5. Turn encoder: bead should move up/down in Z
6. Press MODE again: pattern changes (twin, vortex, etc.)
7. Press RELEASE: bead drops
8. Open lid: transducers should immediately stop (safety)

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| No sound from transducers | BLANK pin stuck high | Check GP3 output, 10kΩ pull-up |
| Bead won't levitate | Phase error / weak power | Check 10V rail, verify transducer wiring |
| Bead drifts to one side | Unequal wire lengths | Re-measure and trim wires |
| OLED blank | I2C address wrong | Try 0x3D instead of 0x3C |
| BLE not found | ESP32-C3 not flashed | Flash BLE bridge firmware |
| Overheating | Too many transducers active | Reduce to single trap, check 10V current |