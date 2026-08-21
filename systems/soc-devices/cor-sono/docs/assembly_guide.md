# Cor Sono — Assembly Guide

## Overview

This guide covers the assembly of the Cor Sono pocket smart stethoscope, from PCB fabrication to chest piece construction and firmware flashing.

---

## 1. PCB Fabrication

- **Layers**: 2
- **Dimensions**: 38 × 82 mm
- **Material**: FR-4, 1.6 mm
- **Finish**: ENIG (gold flash) for fine-pitch ESP32-S3 module
- **Minimum trace/space**: 6/6 mil

### Order from JLCPCB or similar:
1. Export Gerbers from KiCad (File → Fabrication Outputs → Gerbers)
2. Upload the ZIP to jlcpcb.com
3. Select: 2-layer, 1.6mm, ENIG, lead-free HASL
4. Quantity: 5 ($2 total)

---

## 2. Component Placement

| Reference | Component | Footprint |
|-----------|-----------|-----------|
| U1 | ESP32-S3-WROOM-1 | SMD module, castellated |
| U2 | TP4056 | SOP-8 |
| U3 | ME6211 LDO | SOT-23-5 |
| U4 | OPA2333 | SOIC-8 |
| U5 | MAX98357A | TSSOP-16 (module) |
| U6 | SSD1306 OLED | Through-hole header (4-pin) |
| U7 | MicroSD socket | SMD |
| U8 | ICS-43434 | SMD (on chest piece PCB) |
| MIC1 | 7BB-27-3L0 piezo | Through-hole (soldered to chest piece PCB) |
| LS1 | 8Ω speaker | SMD or wire |

### Soldering order:
1. SMD passives (resistors, capacitors) — hot air or iron
2. TP4056, ME6211, OPA2333 — hot air
3. ESP32-S3 module — hot air with flux paste
4. MicroSD socket — iron + drag solder
5. MAX98357A module — iron
6. OLED header pins — iron
7. Battery holder — through-hole, iron

---

## 3. Chest Piece Construction

The chest piece is the acoustic heart of the stethoscope. It requires careful mechanical assembly.

### Materials
- 1× Murata 7BB-27-3L0 piezo disc (27 mm Ø)
- 1× 3D-printed diaphragm cup (PETG, Ø42 mm outer, Ø30 mm inner cavity)
- 1× 0.3 mm PET film (diaphragm)
- 1× ICS-43434 MEMS microphone (mounted on back side)
- Copper shielding tape
- Shielded twisted pair cable (~50 cm)

### Steps

1. **Print the diaphragm cup** (STL file in `docs/`):
   - Outer diameter: 42 mm
   - Inner cavity: 30 mm × 8 mm deep
   - Back wall: 3 mm thick with M3 cable gland

2. **Mount the piezo disc**:
   - Apply a thin bead of silicone adhesive to the rim of the piezo disc
   - Press the piezo (brass side down) into the bottom of the cavity
   - The brass plate should face the patient's skin through the diaphragm
   - Let cure for 24 hours

3. **Install the diaphragm**:
   - Cut a 35 mm disc of 0.3 mm PET film
   - Stretch it over the front opening of the cup
   - Secure with a snap-ring (3D-printed or O-ring)
   - The diaphragm should be taut like a drumhead

4. **Mount the MEMS reference mic**:
   - Solder the ICS-43434 to a small breakout PCB
   - Mount it on the **back** of the diaphragm cup (facing away from the body)
   - This captures ambient room noise, not body sounds

5. **Shielding**:
   - Wrap the piezo signal wires with copper shielding tape
   - Connect shield to GND at the main PCB only (avoid ground loops)
   - Route through shielded twisted pair cable to the main board

6. **Connector**:
   - Use a 4-pin locking connector (heater+/heater−, signal, shield)
   - Or solder directly for permanent assembly

---

## 4. Firmware Flashing

### Prerequisites
- ESP-IDF v5.2+ installed
- USB-C cable

### Steps
```bash
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

### First boot
- The OLED should display "Cor Sono / Smart Stethoscope"
- Press the RECORD button to enter ARMING state
- Place the chest piece on your chest → device enters LISTEN state
- Heart rate and classification appear on OLED + BLE/Wi-Fi

---

## 5. 3D-Printed Enclosure

- **Body**: cylindrical, Ø42 × 145 mm, split into two halves with M3 screws
- **Chest piece**: Ø42 × 12 mm cup (see above)
- **Battery compartment**: 18650 holder slides into body
- **Display window**: cutout for OLED (1.3")
- **Button cutouts**: 3× 4 mm tact buttons on the side
- **Speaker grille**: small holes on the top

STL files: `docs/cor-sono-body.stl`, `docs/cor-sono-chestpiece.stl`

---

## 6. Calibration

### Self-test
1. Power on → press RECORD → device enters ARMING
2. The built-in speaker plays a 1 kHz test tone
3. Both microphones should detect the tone
4. If self-test fails, check:
   - Piezo connection (continuity)
   - MEMS mic I²S wiring
   - OPA2333 output (should read ~1.5V DC bias)

### Volume calibration
- Turn the volume potentiometer while in LISTEN state
- Verify speaker output is audible and clear

### CNN calibration
- The model is pre-trained; no field calibration needed
- For custom datasets, retrain using `scripts/train_model.py`

---

## 7. Testing

### Heart mode test
1. Set mode to HEART
2. Place chest piece on left chest (apex, 5th intercostal space)
3. Press RECORD → listen for 15 seconds
4. Verify: HR 60–80 BPM, class "Normal" >80%

### Lung mode test
1. Set mode to LUNG
2. Place chest piece on posterior lung fields
3. Press RECORD → listen for 15 seconds
4. Verify: class "Normal" or "Crackles" (if present)

### ANC test
1. Play loud music nearby (80 dB)
2. Without ANC: contact signal is noisy
3. With ANC: ambient noise should be suppressed 15–25 dB
4. Verify classification still works in noisy environment