# Brew Sense — Assembly Guide

## Kit Contents

| Item | Qty | Description |
|------|-----|-------------|
| Brew Sense PCB | 1 | 72mm × 38mm, 4-layer FR4 |
| STM32L476RG | 1 | Pre-soldered QFP-64 MCU |
| ESP32-C3-MINI-1 | 1 | Wi-Fi/BLE module |
| DS18B20 probe | 1 | Waterproof temperature probe, 150mm cable |
| BMP388 breakout | 1 | Barometric pressure sensor |
| Senseair S8 | 1 | NDIR CO₂ sensor module |
| EZO-pH | 1 | pH probe interface module |
| Piezo elements | 2 | Murata MA40S4S for densitometer |
| SSD1306 OLED | 1 | 128×32 I2C display |
| 316L stainless tube | 1 | Vibrating tube for densitometer |
| Silicone tubing | 1 | 200mm, 4mm ID, for CO₂ port |
| O-ring | 1 | 18mm ID silicone, for enclosure |
| AAA battery holder | 1 | 2× AAA side-by-side |
| USB-C connector | 1 | 16-pin SMD |
| RGB LED | 1 | 0805 common anode |
| Piezo buzzer | 1 | SMD 5mm magnetic |
| Passive components | ~40 | Resistors, capacitors, inductors |

## Tools Required

- Soldering iron (fine tip, temperature controlled)
- Solder (0.5mm, 63/37 or lead-free)
- Flux paste
- Hot air rework station (for QFN/QFP packages)
- Multimeter
- ST-Link v2 or Black Magic Probe (for STM32 programming)
- USB-C cable
- 2× AAA alkaline batteries
- Isopropyl alcohol (for cleaning)

## Assembly Steps

### Step 1: Passive Components (0402 R/C)

1. Apply flux paste to all passive component pads
2. Place all 0402 resistors and capacitors using tweezers
3. Reflow with hot air or soldering iron
4. Key components:
   - 4.7kΩ × 8 (I²C pull-ups: SDA, SCL × 3 buses + 1-Wire)
   - 100nF × 12 (decoupling on each VDD pin)
   - 10µF × 4 (bulk decoupling)
   - 100kΩ × 2 (battery voltage divider)
   - 1MΩ × 1 (pH probe input protection)

### Step 2: Main MCU (STM32L476RG)

1. Align pin 1 marker (dot) with PCB silkscreen
2. Apply flux paste to all pads
3. Place the LQFP-64 package carefully
4. Reflow with hot air (260°C peak, 60s above 217°C)
5. Inspect all 64 joints under magnification
6. Touch up any bridges with flux and soldering iron

### Step 3: Power Supply (TPS62740 + MCP73871)

1. Solder TPS62740 (VSON-10) — careful with thermal pad
2. Apply solder paste to thermal pad first
3. Solder MCP73871 (QFN-20) — similar thermal pad technique
4. Add inductors (10µH for TPS62740) and output capacitors
5. Verify 3.3V output: connect USB-C, measure between VDD and GND

### Step 4: I²C Sensors

1. Solder BMP388 (LGA-10) with minimal solder paste
2. Solder EZO-pH module via I²C header pins
3. Add I²C pull-up resistors (4.7kΩ × 6: SDA/SCL for 3 buses)

### Step 5: Display and Connectors

1. Solder SSD1306 OLED module (header pins)
2. Solder USB-C receptacle (through-hole tabs + SMD pins)
3. Solder AAA battery holder (through-hole)

### Step 6: Co-Processor and Sensors

1. Solder ESP32-C3-MINI-1 module (antenna pointing away from PCB)
2. Solder Senseair S8 module (on PCB edge, gas port aligned)
3. Connect DS18B20 probe to 3-pin header (VDD, DATA, GND)
4. Connect pH probe BNC connector to EZO-pH module

### Step 7: Densitometer Assembly

⚠️ This is the most critical and delicate step.

1. Clean the 316L stainless tube with isopropyl alcohol
2. Apply a thin layer of cyanoacrylate adhesive to the piezo elements
3. Bond piezo element #1 (driver) to one end of the tube, centered
4. Bond piezo element #2 (receiver) to the opposite end, centered
5. Solder wires from PA4/DAC1 to piezo #1 positive terminal
6. Solder wires from PB4/TIM3 to piezo #1 negative terminal
7. Solder wires from PA0/ADC to piezo #2 positive terminal
8. Solder ground wire to piezo #2 negative terminal
9. Allow adhesive to cure 24 hours before use

### Step 8: CO₂ Port Assembly

1. Attach silicone tubing to Senseair S8 gas inlet port
2. Route tubing through the enclosure wall (sealed with O-ring)
3. The other end connects to the fermenter airlock hole

### Step 9: Enclosure

1. Place assembled PCB in polycarbonate shell
2. Route DS18B20 probe through sealed cable gland
3. Route pH probe cable through second cable gland
4. Route silicone CO₂ tube through third cable gland
5. Ensure O-ring is seated properly in the lid groove
6. Tighten all cable glands

### Step 10: Programming

1. Connect ST-Link to SWD pads (SWDIO, SWCLK, GND, 3.3V)
2. Power the board via USB-C (recommended) or batteries
3. Flash the firmware:

```bash
make all
openocd -f interface/stlink.cfg -f target/stm32l4x.cfg \
    -c "program build/brew_sense.elf verify reset exit"
```

4. Verify console output at 115200 baud on UART2 (PA2/PA3)

### Step 11: Calibration

Before first use, calibrate the densitometer:

```bash
python3 scripts/calibrate.py --port /dev/ttyUSB0
# Follow on-screen prompts:
# 1. Hold sensor in air → press Enter
# 2. Submerge in distilled water at 20°C → press Enter
# 3. Verify readings
```

And calibrate the pH probe:

```bash
# pH 4.0 buffer
python3 scripts/calibrate.py --port /dev/ttyUSB0 --ph4
# pH 7.0 buffer
python3 scripts/calibrate.py --port /dev/ttyUSB0 --ph7
```

## Testing Checklist

- [ ] 3.3V rail measures 3.25-3.35V (USB power)
- [ ] 3.3V rail measures 3.25-3.35V (battery power)
- [ ] DS18B20 reads ~25°C in air
- [ ] BMP388 reads ~1013 hPa at sea level
- [ ] S8 reads ~400-450 ppm in ambient air
- [ ] EZO-pH reads ~7.0 in pH 7.0 buffer
- [ ] OLED displays "BrewSense" on boot
- [ ] BLE advertising visible on phone
- [ ] Wi-Fi connects to configured network
- [ ] Densitometer reads ~1.000 in distilled water (after calibration)
- [ ] Densitometer reads ~0.000 in air (after calibration)
- [ ] Buzzer beeps on button press
- [ ] RGB LED changes color with fermentation stage
- [ ] Serial console responds to INFO command

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| No OLED display | I²C bus error | Check SDA/SCL pull-ups (4.7kΩ) |
| DS18B20 reads -999°C | 1-Wire error | Check PB3 pull-up, check probe wiring |
| S8 reads 0 ppm | UART error | Check PB10/PB11 wiring, 9600 baud |
| Gravity always 0.000 | Densitometer not calibrated | Run air + water calibration |
| Gravity unstable | Piezo not bonded well | Re-glue piezo elements |
| BLE not found | ESP32-C3 not responding | Check PC4/PC5 UART, check PC6 enable |
| Wi-Fi won't connect | Wrong credentials | Use serial `WIFI,ssid,pass` command |
| High power drain | Sensors not sleeping | Check sensor sleep in power_manager |
| pH reads 0.0 | EZO-pH not responding | Check I²C address (0x63) |