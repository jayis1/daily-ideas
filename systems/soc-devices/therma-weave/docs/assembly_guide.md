# Therma Weave — Assembly Guide

## Overview

This guide walks you through assembling a Therma Weave multi-zone heated textile controller from components to a working device.

## Tools Required

- Soldering iron (temperature-controlled, 300–350°C tip)
- Solder (0.5mm Sn63/Pb37 or lead-free equivalent)
- Flux pen
- Tweezers (fine tip, ESD-safe)
- Multimeter
- Magnifying lamp or microscope (for 0402 passives)
- Hot air rework station (optional, for IC packages)
- PCB vise or helping hands
- Wire strippers
- Crimping tool for JST-PH connectors

## Component Placement Order

Assemble in the following order (lowest profile to highest):

### 1. SMD Passives (0402/0805)
1. All 0.1µF decoupling capacitors (12 total, one per IC)
2. All 10kΩ pull-up resistors (4× I2C, 10× voltage dividers)
3. All 10µF bulk capacitors
4. All 22µF filter capacitors
5. 68µH inductor (LM2596)
6. All 4.7kΩ I2C pull-ups
7. 100kΩ and 10kΩ VBAT voltage divider
8. 0.01Ω current sense shunt resistor (2512 package)

### 2. IC Packages (small to large)
1. INA199A2 (SOT-23-5)
2. AP2112-3.3 (SOT-223)
3. LM393 (SOIC-8)
4. 74HC4051PW (TSSOP-16)
5. 74HC32 (SOIC-14)
6. TC4427COA ×2 (SOIC-8)
7. BME280 (LGA-8 2.5×2.5)
8. LSM6DS3TR-C (LGA-14 2.5×3)
9. ESP32-C3-MINI-1 (module)

### 3. Power Components
1. Schottky diode (SOD-123)
2. 1N4148 flyback diodes ×4 (SOD-323)
3. LM2596-5.0 (TO-263-5)
4. IRF3205 MOSFETs ×4 (D2PAK-3)

### 4. Connectors (tallest components)
1. JST-PH 4-pin connectors ×4 (heater zones)
2. JST-PH 3-pin connector (battery)
3. XT30 panel mount connector (12V input)
4. USB-C receptacle

### 5. OLED Display
1. SSD1306 128×64 OLED module (solder or header-mount)

## Soldering Notes

### BME280 and LSM6DS3
- These are LGA packages with pads underneath. Use hot air rework station or solder paste + reflow.
- Apply flux, position chip, apply hot air at 260°C until solder flows.
- Do not apply excessive force — the pads are fragile.

### IRF3205 MOSFETs
- The D2PAK-3 package has a large thermal pad. Use a generous solder fillet.
- The pad serves as both electrical drain connection and thermal dissipation path.
- Ensure good copper pour connection to the ground plane on bottom layer.

### 0.01Ω Shunt Resistor
- The 2512 package current sense resistor must be soldered with minimal thermal stress.
- Use a Kelvin (4-wire) measurement to verify the resistance after soldering.

### 68µH Inductor
- Position close to the LM2596 output. The switching node (pin 2) should have short traces.

## Post-Assembly Checks

### Visual Inspection
1. Check for solder bridges on all ICs (especially fine-pitch TSSOP-16 and SOIC-14)
2. Verify all polarized components are oriented correctly
3. Check that no passive components are tombstoned
4. Verify USB-C connector alignment

### Continuity Tests
1. **VBAT to GND**: Should be high impedance (>1kΩ)
2. **3.3V to GND**: Should be >1kΩ
3. **5V to GND**: Should be >500Ω
4. **12V heater bus to GND**: Should be >100Ω

### Power-On Test
1. Connect 12V DC supply (current-limited to 0.5A initially)
2. Measure 5V rail: should be 4.95–5.05V
3. Measure 3.3V rail: should be 3.25–3.35V
4. Verify ESP32-C3 boots (check UART debug output at 115200 baud)
5. Verify OLED displays "Therma Weave v1.0" splash screen

### I2C Bus Scan
```
I2C bus scan:
  0x29: (not populated — TSL2591 not used)
  0x3C: SSD1306 OLED ✓
  0x40: INA199 current sense ✓
  0x5A: (not populated)
  0x69: (not populated)
  0x6A: LSM6DS3 IMU ✓
  0x76: BME280 ambient ✓
```

## Connecting Heater Elements

### Wiring Diagram
```
JST-PH 4-pin connector per zone:
  Pin 1: 12V heater+ (red wire, 18 AWG)
  Pin 2: Heater- / MOSFET drain (black wire, 18 AWG)
  Pin 3: Thermistor+ (white wire, 26 AWG)
  Pin 4: Thermistor- (blue wire, 26 AWG)
```

### Heater Element Specifications
- Resistance: 3–12 Ω per zone (typical)
- Power: 12–48W per zone at 12V
- Max current: 3A per zone (4A safety cutoff)
- Wire: 18 AWG or larger for heater connections

### Thermistor Placement
- Place thermistors on the skin side of the heated garment
- Position at the hottest point of each zone
- Secure with Kapton tape or sewn pocket

## First Boot Procedure

1. Flash firmware via USB-C:
   ```bash
   idf.py set-target esp32c3
   idf.py build
   idf.py -p /dev/ttyUSB0 flash monitor
   ```

2. Connect all 4 heater zone cables

3. Connect battery or 12V supply

4. Verify UART output:
   ```
   I (xxx) THERMA_WEAVE: === Therma Weave v1.0 ===
   I (xxx) TEMP_SENS: Temperature sensor initialized
   I (xxx) CURRENT_MON: INA199 current monitor initialized
   I (xxx) AMBIENT: BME280 ambient sensor initialized
   I (xxx) ACTIVITY: LSM6DS3 initialized for activity detection
   I (xxx) OLED: SSd1306 OLED initialized
   I (xxx) SAFETY: Safety watchdog initialized
   I (xxx) ZONE_CTRL: Zone 0 initialized: target=40.0°C
   I (xxx) ZONE_CTRL: Zone 1 initialized: target=40.0°C
   I (xxx) ZONE_CTRL: Zone 2 initialized: target=40.0°C
   I (xxx) ZONE_CTRL: Zone 3 initialized: target=40.0°C
   ```

5. Connect via BLE using the companion script:
   ```bash
   python3 scripts/therma_weave_ble.py --mac AA:BB:CC:DD:EE:FF --zone 0 --target 40
   ```

6. Verify heater zones warm up and temperature readings increase

## Safety Verification

Before extended use, verify ALL safety systems:

1. **Software over-temperature**: Set zone target to 55°C. Verify zones shut off when 65°C is reached.
2. **Over-current**: Short a heater zone briefly. Verify over-current detection triggers within 100ms.
3. **Thermistor open**: Disconnect a thermistor. Verify zone shuts down and fault is reported.
4. **Thermistor short**: Short a thermistor to GND. Verify zone shuts down and fault is reported.
5. **BLE shutdown**: Send emergency shutdown command. Verify all zones turn off immediately.
6. **Hardware watchdog**: Verify LM393 comparator trips at ~70°C (requires heating thermistor externally).
7. **Battery low**: Discharge to 10.5V. Verify system enters low-battery mode.

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| OLED blank | I2C wiring or address | Check 0x3C on I2C scan |
| BME280 not found | I2C address | Check 0x76, verify pull-ups |
| LSM6DS3 not found | I2C address | Check 0x6A, verify pull-ups |
| Zone not heating | MOSFET gate not driven | Check PWM output on GPIO2-5 |
| Over-current fault | Short in heater element | Measure resistance, should be >3Ω |
| Temperature reading -127°C | Thermistor open circuit | Check connector wiring |
| Temperature reading 200°C | Thermistor short | Check for short to GND |
| BLE not advertising | Antenna issue | Verify ESP32-C3 antenna trace |
| Battery voltage always 0 | Voltage divider issue | Check 100k/10k resistor divider |