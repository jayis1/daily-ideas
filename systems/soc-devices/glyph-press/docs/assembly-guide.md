# Glyph Press — Assembly Guide

## Overview

The Glyph Press is a portable Braille embosser built around an RP2040 MCU. It embosses physical Braille dots onto paper or label tape using 16 micro-solenoids driven by DRV8833 H-bridges, with a NEMA8 stepper for paper feed.

## Tools Required

- Soldering iron (fine tip) + solder + flux paste
- Hot plate or reflow oven (for QFN RP2040)
- Digital multimeter
- Small Phillips screwdriver
- Tweezers (for SMD parts)
- PC with Python 3.8+
- Picoprobe or Raspberry Pi Pico (for SWD flashing)
- 3D printer (for mechanical parts)

## PCB Assembly

### 1. Main Board

1. **Stencil and apply solder paste** to the main PCB.
2. **Place components** in order:
   - U1 (RP2040, QFN-56) — orientation per KiCad footprint
   - U2 (W25Q16 flash, SOIC-8)
   - U6 (TPS63020, SON-14)
   - U7 (TLV70033, SOT-23-5)
   - U8 (MCP73831, DFN-8)
   - U9 (DW01A, SOT-23-6)
   - U10 (FS8205A, SOT-23-6)
   - All passives (0402/0603 resistors, capacitors)
3. **Reflow** on hot plate or reflow oven (lead-free profile: 245°C peak).
4. **Hand-solder** through-hole parts:
   - J1 (USB-C receptacle)
   - J2 (JST-PH battery connector)
   - J3 (6-pin SWD header)
   - J4 (microSD socket)
   - SW1-3 (tactile buttons)
   - ENC1 (rotary encoder)
   - BUZ1 (piezo buzzer)
5. **Verify power rails**: connect USB-C, check 3.3V on TPS63020 output and 4.2V on battery charge pin.

### 2. Solenoid Driver Board

1. Solder 8× DRV8833 (TSSOP-16) and 2× 74HC595 (SOIC-16) on the solenoid driver PCB.
2. Solder 16 solenoid connectors (2-pin JST or header pins).
3. Connect flyback diodes (1N4148 or Schottky) across each solenoid pair.
4. Connect ribbon cable from main board to driver board (SPI + enable lines).

### 3. Mechanical Assembly

1. **Print parts** (see `docs/` for STL files):
   - Embosser head frame (holds 16 solenoids)
   - Paper feed assembly (roller mount, idler, paper slot)
   - Top cover with OLED window
   - Bottom case with battery compartment
2. **Assemble embosser head**:
   - Insert 16 solenoids into the head frame (2 columns of 8)
   - Insert hardened steel pins (1.5mm × 15mm) into each solenoid plunger
   - Mount the silicone rubber anvil strip below the head
   - Adjust pin height so pins protrude ~1mm when solenoids are activated
3. **Assemble paper feed**:
   - Mount NEMA8 stepper with knurled feed roller
   - Install spring-loaded idler roller
   - Mount TCRT5000 sensor in the paper slot
   - Mount SG90 servo for paper release
4. **Final assembly**:
   - Mount embosser head on the paper feed assembly
   - Connect solenoid wires to driver board
   - Mount OLED, buttons, encoder, buzzer in the top cover
   - Place battery in bottom compartment
   - Connect battery to J2

### 4. Firmware Flash

1. Connect Picoprobe to SWD header (J3):
   - Picoprobe SWDIO → J3 pin 1
   - Picoprobe SWCLK → J3 pin 2
   - GND → J3 pin 3
   - 3.3V → J3 pin 4
2. Build and flash:
   ```bash
   cd firmware
   mkdir build && cd build
   cmake ..
   make -j4
   openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg \
       -c "program glyph_press.elf verify reset exit"
   ```

### 5. Braille Table Loading

Load language tables into external flash:
```bash
python scripts/load_tables.py --port /dev/ttyACM0
```

### 6. Testing

1. Power on — you should hear the startup melody (C-E-G).
2. OLED shows "Glyph Press Ready".
3. Send a test command:
   ```bash
   python scripts/glyph_send.py --port /dev/ttyACM0 --test --monitor
   ```
4. The device should emboss the Braille alphabet on paper/label tape.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| OLED blank | I2C wiring or address | Check SDA/SCL, try 0x3D address |
| Stepper doesn't move | TMC2209 EN or wiring | EN must be low to enable; check STEP pin |
| Solenoids don't fire | DRV8833 enable or shift register | Check 74HC595 latch timing; verify VMOT power |
| Dots too light | Force setting or pin height | Increase force (MODE + encoder), adjust pin protrusion |
| Dots too deep | Force too high | Decrease force setting |
| Paper jams | Feed roller dirty or wrong media | Clean roller, use 80-160 gsm paper |
| BLE not found | HC-05 not paired | Pair with PIN 1234 or 0000 |
| Battery short life | Solenoid power draw | Check for stuck solenoids (always-on) |