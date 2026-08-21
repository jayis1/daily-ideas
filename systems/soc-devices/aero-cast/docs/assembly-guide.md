# Aero Cast — Assembly Guide

## Overview

This guide walks you through assembling the Aero Cast pocket 3-axis ultrasonic anemometer. The device consists of two PCB assemblies connected by a flat flexible cable (FFC):

1. **Main body PCB** (120 × 65 mm): RP2040, ESP32-C3, power, display, SD, buttons
2. **Sensor head PCB** (60 × 60 mm): 6 ultrasonic transducers, TIA, mux, BME280

## Tools Required

- Soldering iron (fine tip, temperature-controlled)
- Solder (0.6mm, 63/37 or lead-free)
- Flux pen
- Tweezers (fine, anti-magnetic)
- Multimeter
- Magnifier or microscope (for 0805 SMD parts)
- 3D printer (for enclosure and sensor head clips)
- M2.5 / M3 tap and drill bits

## Assembly Steps

### Step 1: Main Body PCB — Power Supply

1. **U8 TP4056** (SOIC-8): Solder the Li-ion charger IC first.
2. **USB-C connector**: Solder the USB-C receptacle. Use flux and check for bridges.
3. **D1, D2** (1N4148, SOD-123): Protection diodes. Cathode band aligns with PCB silk.
4. **L1** (10µH inductor): Charge pump inductor for HV supply.
5. **C1, C2** (10µF tantalum): Input/output filter caps for TP4056.
6. **U9 AP2112-3.3** (SOT-23-5): 3.3V LDO regulator.
7. **R1, R2** (1MΩ, 0805): Battery voltage divider (2:1).
8. **18650 battery holder**: Solder or screw-mount the spring-loaded battery holder.
9. **Test point**: Check 3.3V rail with multimeter. Should read 3.28–3.35V.

### Step 2: Main Body PCB — RP2040 MCU

1. **U1 RP2040** (QFN-56): This is the hardest part. Use stencil + reflow soldering, or careful hand soldering with flux. Align pin 1 corner.
2. **U10 W25Q16** (SOIC-8): QSPI flash for program storage.
3. **Y1** (24 MHz crystal, 3225 package): System crystal with two 22pF caps (C3, C4).
4. **Decoupling caps**: Place 100nF caps (C5–C20) near each IC's VDD pin.
5. **R3, R4** (27Ω): USB series resistors (if using USB debug).
6. **Buttons**: Solder 3× tactile switches (SW1=PWR, SW2=MODE, SW3=AVG).
7. **LEDs**: Solder blue (D3) and green (D4) 0805 LEDs with 1kΩ current-limit resistors.

### Step 3: Main Body PCB — ESP32-C3 Wireless

1. **U2 ESP32-C3-MINI-1**: Solder the castellated module. Keep antenna area clear of copper.
2. **R5, R6** (10kΩ): ESP32-C3 boot-mode pull-ups.
3. **U11** (AP2112 or shared 3.3V): ESP32-C3 shares the main 3.3V rail.

### Step 4: Main Body PCB — Display & SD

1. **SSD1306 OLED**: Solder the 4-pin I2C OLED module (pre-assembled). Use a 0.1" header or direct solder.
2. **microSD socket**: Solder the Molex microSD card socket. Check card detect switch continuity.

### Step 5: Main Body PCB — Analog Frontend

1. **U4 TC4427** (SOIC-8, ×2): HV MOSFET drivers for transducer excitation.
2. **U5 CD4052B** (SOIC-16): Analog multiplexer for transducer pair selection.
3. **U6 OPA2350** (SO-8): Dual op-amp for TIA and envelope detector.
4. **U7 TLV3201** (SOT-23-5): Fast comparator for echo edge detection.
5. **U12 MCP4911** (SOIC-8): SPI DAC for comparator threshold.
6. **R7** (100kΩ) + **C21** (10pF): TIA feedback network.
7. **D5, D6** (1N4148): Envelope detector diodes.
8. **C22, C23** (1nF): Envelope detector capacitors.
9. **C24–C27** (1µF): Analog supply decoupling.
10. **Guard ring**: Ensure the TIA input net is surrounded by a ground guard ring.

### Step 6: Sensor Head PCB

1. **6× MS-P4010 transducers**: Solder the 40 kHz ultrasonic transducers. They have a polarity (driven side vs. ground side) — check the PCB silk.
2. **BME280**: Solder the BME280 module on the sensor head PCB (for accurate ambient temperature at the measurement point).
3. **FFC connectors**: Solder 2× 10-pin FFC connectors (one on main body, one on sensor head).
4. **M3 standoffs**: Install 3× M3×40mm nylon standoffs on the sensor head PCB to create the tripod geometry. The bottom 3 transducers mount at 120° spacing, 40mm from center.

### Step 7: Mechanical Assembly

1. **3D-printed enclosure**: Print the two-piece enclosure (top + bottom) in PLA or PETG.
   - Top piece: cutouts for OLED, USB-C, buttons
   - Bottom piece: battery compartment, sensor head mount
2. **Sensor head clips**: Print 6× transducer clips that hold the MS-P4010 at the correct angles on the standoffs.
3. **FFC cable**: Connect the 10-pin FFC cable (150mm) between main body and sensor head.
4. **Battery**: Insert a charged 18650 cell.
5. **Close enclosure**: Screw the enclosure together with M3 screws.

### Step 8: Initial Test

1. **Power on**: Hold PWR button for 1 second. Blue LED should light.
2. **Check OLED**: Display should show "AERO CAST" briefly, then wind data (all zeros if no wind).
3. **USB serial**: Connect USB-C to computer. Open serial terminal at 115200 baud. You should see boot messages.
4. **BME280 check**: Serial log should show `[bme280] initialized`.
5. **SD card**: Insert a microSD card. Serial log should show `[sd] card initialized`.
6. **BLE**: On your phone, scan for BLE devices. "Aero Cast" should appear.

### Step 9: Calibration

**Zero-wind calibration** is essential for accurate measurements:

1. Place the device indoors, away from HVAC vents, windows, and moving air.
2. Press MODE button until display shows "CAL MODE".
3. Hold AVG button for 3 seconds to start zero-wind calibration.
4. The device collects 100 samples (~5 seconds) and computes per-path offsets.
5. Results are stored in flash. Serial log shows the offset values.
6. Press MODE to return to normal operation.

**Path length verification** (optional, for highest accuracy):

1. Use the `aero_stream.py` script in raw mode to view individual path TOF values.
2. In still air, all 3 forward TOF values should be ~291 µs (100mm / 343 m/s).
3. If values differ by >5 µs, adjust the path length calibration via the BLE command interface.

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| No display | OLED I2C address mismatch | Check I2C scan (address 0x3C or 0x3D) |
| No echo (all paths fail) | HV driver not enabled | Check PIN_HV_EN signal, TC4427 wiring |
| Weak echo | Comparator threshold too high | Lower MCP4911 DAC value via BLE command |
| Random spikes | TIA noise / crosstalk | Check guard ring, increase C21 (TIA feedback cap) |
| BME280 not found | I2C address 0x76 vs 0x77 | Change BME280_I2C_ADDR in sdkconfig.h |
| SD card not detected | SPI wiring or card format | Reformat card as FAT32, check SPI pins |
| BLE not visible | ESP32-C3 not flashed | Flash ESP32-C3 with bridge firmware |
| Wind speed always 0 | Not calibrated | Perform zero-wind calibration |
| Direction wrong | Geometry matrix incorrect | Verify transducer mounting angles |

## Mechanical Drawings

### Sensor Head Geometry

```
Top view (looking down):

         T3 (top center)
        /  \
       /    \
      /  T7  \      (T7 is optional vertical path, not used in 3-path config)
     /        \
    T0---T4---T1
     \   |    /
      \  |   /
       \ | /
        T2

Actually for the 3-path tripod:
Bottom ring (40mm radius): T0 at 0°, T1 at 120°, T2 at 240°
Top center: T3

Path 0: T0 → T3
Path 1: T1 → T3  
Path 2: T2 → T3
```

### 3D View

```
         T3 (top, z=80mm)
        /|\
       / | \
      /  |  \     Path lengths ~89mm each
     /   |   \
    /    |    \
   T0----+----T1     (bottom ring, z=0, R=40mm)
    \    |    /
     \   |   /
      \  |  /
       \ | /
        T2
```

The bottom transducers (T0, T1, T2) are spaced 120° apart on a 40mm radius circle. The top transducer (T3) is centered above, 80mm high. Each path from bottom vertex to top center is sqrt(40² + 80²) = sqrt(8000) ≈ 89.4mm.

In production, calibrate the actual path length using the zero-wind TOF measurement.

## Safety Notes

- **18650 battery**: Use only protected 18650 cells. Never short-circuit.
- **HV drive**: The TC4427 can generate up to 20Vpp on transducer lines. Do not touch transducer terminals while powered.
- **USB-C**: The device can be powered and charged via USB-C. Do not connect non-standard USB-C sources.
- **Outdoor use**: The sensor head is not waterproof. Use a rain shield for outdoor deployment.
- **Temperature**: Operating range −20 to +50°C. Do not exceed.