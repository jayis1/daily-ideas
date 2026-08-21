# Hive Mind — Assembly Guide

## Overview

The Hive Mind is a 100×70 mm, 4-layer PCB that mounts under a beehive and monitors colony health through weight, temperature, acoustic, and bee traffic sensors. This guide walks you through assembling the device from components to deployment.

---

## Tools Required

- Soldering iron (temperature-controlled, fine tip)
- Solder (lead-free SAC305 recommended)
- Flux pen
- Tweezers (ESD-safe, fine tip for 0402 components)
- Multimeter
- Magnifying lamp or microscope (for 0402/QFN parts)
- Hot air rework station (recommended for QFN packages)
- USB-C cable
- ST-Link v2 or similar SWD programmer
- 3 mm and 5 mm hex drivers (for load cell and enclosure)

---

## Bill of Materials

See `hardware/BOM.csv` for the complete parts list.

---

## Step-by-Step Assembly

### 1. PCB Fabrication

Order the PCB from JLCPCB or similar:
- 100 × 70 mm, 4-layer FR4
- 1.6 mm thickness
- ENIG surface finish (better for hand soldering)
- Minimum hole size: 0.2 mm
- Minimum trace width: 0.15 mm (use 0.3 mm for RF traces)

### 2. Solder Order (lowest profile first)

#### Passives (0402 — smallest first)
1. **Decoupling capacitors C1–C12** (100 nF, 0402): Place one next to each IC's VDD pin. These are the most tedious — use flux and a fine tip.
2. **Pull-up resistors R1–R6** (4.7 kΩ, 0402): I²C pullups (R1–R4) and 1-Wire pullup (R5).
3. **IR LED series resistors R7–R8** (220 Ω, 0402): Current limiting for IR LEDs.
4. **Status LED resistors R9–R10** (1 kΩ, 0402): Green and red LEDs.
5. **Bulk capacitors C13–C14** (10 µF, 0805): VDD bulk decoupling.

#### Small ICs
6. **ME6211 (U9)** — SOT-23-5 LDO regulator. Place near battery input.
7. **TP4056 (U8)** — SSOP-8 battery charger. Place near USB-C connector.
8. **CH340E (U10)** — SSOP-20 USB-UART bridge. Place near USB-C connector.
9. **HX711 (U2)** — SOIC-16 load cell ADC. Place near load cell connector.

#### Sensors
10. **BME280 (U7)** — LGA-8 ambient sensor. Hot air recommended.
11. **ICS-43434 (U6)** — LGA-6 MEMS microphone. Hot air required. Pay attention to the sound port orientation — it must face up through the PCB opening.
12. **DS18B20 (U3–U5)** — TO-92 package. Solder with short leads; these will be at the end of cables.

#### Main ICs
13. **STM32WL55JC (U1)** — QFN-48 with 0.5 mm pitch. Hot air required. Apply paste, align carefully, reflow. Verify with microscope.
14. **SSD1306 OLED (OLED1)** — Pre-mounted on 0.91" module with I²C header. Solder 4-pin header.

#### RF
15. **SKY13330 (U11)** — DFN-6 RF switch. Hot air required. Place near antenna trace.
16. **Crystal Y1** (32 MHz) — 3225 package. Place near STM32WL.
17. **Crystal Y2** (32.768 kHz) — 3215 package. Place near STM32WL.
18. **RF inductor L1** (10 nH, 0402) — Part of the RF matching network.

#### Connectors and Modules
19. **USB-C connector (J1)** — SMD, 16-pin. Secure with solder on mechanical tabs first.
20. **18650 battery holder** — SMD or through-hole depending on variant.
21. **Load cell connector** — 4-pin JST-PH (E+, E-, A+, A-).
22. **DS18B20 cable connectors** — 3-pin JST-PH (VDD, DQ, GND) × 3.
23. **IR gate connectors** — 4-pin JST-PH each (VDD, GND, LED+, photo).
24. **Antenna wire** — 86 mm (868 MHz) or 82 mm (915 MHz) soldered to RF output pad.

#### Final Components
25. **IR break-beam sensors (TCRT1000)** — Mount in 3D-printed entrance gate, not on PCB.
26. **Load cell** — Mount on aluminum bracket under the hive.
27. **DS18B20 probes** — Insert into hive frames at floor/mid/crown levels.
28. **18650 LiFePO₄ battery** — Insert into holder after all soldering is done.

### 3. Visual Inspection

After soldering:
- Check all joints under magnification for bridges, cold joints, or missing solder
- Verify polarity of electrolytic/tantalum caps (none in this design, but check USB-C orientation)
- Check for solder balls under QFN packages
- Use multimeter continuity mode to verify:
  - VDD to GND is NOT shorted
  - I²C SDA/SCL lines have pull-ups to VDD
  - 1-Wire line has pull-up to VDD
  - HX711 DOUT and SCK are connected to PA1/PA2 respectively

### 4. First Power-Up

1. **Do NOT insert the battery yet.**
2. Connect USB-C to a 5 V supply.
3. Measure voltage at the ME6211 output (should be 3.3 V).
4. Measure VDD rail (should be 3.3 V).
5. Check for hot components (touch test — nothing should be warm).
6. Insert 18650 LiFePO₄ battery. The TP4056 should indicate charging.

### 5. Firmware Flashing

1. Connect ST-Link SWDIO, SWCLK, GND, and 3.3V to the SWD header (4-pin unpopulated pads on PCB).
2. Flash the firmware:
   ```bash
   st-flash write hive_mind.bin 0x08000000
   ```
3. Connect USB-C to a computer. Open a serial terminal at 115200 baud, 8N1.
4. Verify boot messages appear.

### 6. Sensor Verification

1. **Load cell**: Place a known weight (e.g., 1 kg) on the platform and use the USB console to calibrate:
   ```
   > weight calibrate 1000
   > weight tare
   > weight read
   ```
2. **Temperature probes**: Verify three DS18B20 probes are detected:
   ```
   > temp scan
   Found 3 probes:
   [0] 28:FF:A1:B2:C3:D4:E5:01 -> floor
   [1] 28:FF:11:22:33:44:55:66 -> mid
   [2] 28:FF:AA:BB:CC:DD:EE:FF -> crown
   > temp read
   Floor: 25.3°C  Mid: 34.8°C  Crown: 32.1°C
   ```
3. **BME280**: Verify ambient readings:
   ```
   > bme read
   T: 22.5°C  H: 65.2%  P: 1013.4 hPa
   ```
4. **Acoustic**: Verify MEMS mic is working:
   ```
   > acoustic test
   Capturing 2s audio... Dominant freq: 245 Hz Class: QUEENRIGHT
   ```
5. **OLED**: Press user button to verify display shows data.
6. **IR gates**: Wave your finger through each gate and verify counting:
   ```
   > bee test
   Counting for 10s... In: 3  Out: 2
   ```

### 7. LoRaWAN Provisioning

1. Register the device on The Things Network (TTN):
   - Note the DevEUI (auto-generated from STM32 UID96)
   - Generate an AppEUI and AppKey
2. Program via USB console:
   ```
   > lora set_appeui 70B3D57ED0000000
   > lora set_appkey 2B7E151628AED2A6ABF7158809CF4F3C
   > lora join otaa
   Joining... Joined!
   > lora test_tx
   TX sent on port 2, 21 bytes
   ```
3. Verify uplink appears in TTN console.

---

## Enclosure Assembly

1. Place the PCB in the IP65 ABS enclosure.
2. Route the following through cable glands:
   - USB-C (waterproof gland)
   - Antenna wire (gland with grommet)
   - DS18B20 cables × 3 (gland each or multi-hole gland)
   - Load cell cable (4-conductor gland)
   - IR gate cables × 2 (multi-hole gland)
   - Solar panel cable (gland)
3. Seal all glands with silicone sealant for weather resistance.
4. Mount the enclosure under the hive stand, away from direct rain.
5. Mount the solar panel on a south-facing bracket (Northern Hemisphere).

---

## Deployment

See `docs/deployment_guide.md` for apiary installation instructions.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| No serial output | Bad USB connection or CH340E driver | Install CH340E driver, check USB-C cable |
| LoRaWAN won't join | Wrong AppKey or no gateway nearby | Verify AppKey, check gateway coverage |
| Load cell reads 0 | HX711 wiring or load cell disconnected | Check 4-wire connection to load cell |
| Temperature reads -999°C | DS18B20 not detected on 1-Wire bus | Check pullup resistor, verify ROM IDs |
| Acoustic always "DEAD" | MEMS mic I2S not connected | Check I2S wiring, verify ICS-43434 VDD |
| OLED blank | I2C address or wiring | Try I2C scan to find OLED at 0x3C |
| Battery drains fast | HX711 always on | Check PB7 power-enable pin is toggling |
| Bee counts all zero | IR gate misaligned | Check IR LED/phototransistor alignment |

---

*SoC Device Inventions — jayis1*