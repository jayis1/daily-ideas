# Echo Trap — Assembly Guide

This guide walks through the assembly, weatherproofing, and field deployment of an Echo Trap. It assumes familiarity with surface-mount soldering and basic IP-rated enclosure preparation.

---

## 1. PCB Fabrication

Order the 4-layer PCB (Gerbers in `schematic/`) with:

- **4 layers, 1 oz copper** (sufficient for the low-current design)
- **ENIG finish** (flat pads for the QFN packages — SX1262, ESP32-S3 module)
- **0.2 mm minimum trace / 0.2 mm minimum space**
- **1.6 mm board thickness** for mechanical rigidity
- **Solder mask over the RF area** (keep the 915 MHz trace antenna clear of mask for tuning)

Recommended fabricators: JLCPCB, PCBWay, Elecrow.

---

## 2. Bill of Materials

The complete BOM is in `hardware/BOM.csv`. Key components:

| Ref | Part | Notes |
|-----|------|-------|
| U1 | ESP32-S3-WROOM-1-N8R8 | The main SoC — dual-core 240 MHz with vector instructions for CNN inference |
| U2 | SX1262 | Semtech sub-GHz LoRa transceiver, QFN-24 |
| U3, U4 | ICS-43434 ×2 | Dual I²S MEMS microphones — the acoustic front end |
| U5 | SHT40 | Sensirion temperature/humidity sensor |
| U6 | TSL2591 | AMS ambient light sensor (day/night detection) |
| U7 | MAX17048 | I²C fuel gauge for battery state-of-charge |
| U8 | MCP73871 | Solar charge controller with load sharing |
| U9 | TPS63020 | Buck-boost for the 3.3 V rail |
| U10 | DRV8601 | Motor driver for the suction fan |
| FAN1 | 30 mm blower | 5 V brushless blower fan for insect capture |

---

## 3. Soldering Order

### 3.1. Power supply first

1. Solder the **TPS63020** (U9) and its inductor L1, the input/output caps (C2, C3).
2. Solder the **MCP73871** (U8) solar charger and its inductor L2, input filter (C4, C5).
3. Apply power via the 18650 battery holder and verify:
   - 3.3 V on the TPS63020 output (multimeter)
   - The MCP73871 charges the 18650 when the solar panel is connected
   - The amber LED blinks when the panel is in light

### 3.2. SoC and digital core

1. Solder the **ESP32-S3-WROOM-1** (U1) module. Use a hot-air station — the castellated module pads need good thermal contact.
2. Solder the decoupling caps (C1 — one per 3V3 pin).
3. **Do not power yet.** Verify no shorts between 3V3 and GND with a multimeter.

### 3.3. LoRa radio

1. Solder the **SX1262** (U2) QFN-24. Use solder paste + hot plate or hot-air.
2. Solder the SX1262 matching network caps (C6, C7) and the 915 MHz antenna.
3. Connect via USB and flash the firmware (see section 5).

### 3.4. Acoustic front end

1. Solder the two **ICS-43434** MEMS microphones (U3, U4) on the interior wall of the enclosure PCB, with their bottom ports facing outward through the hydrophobic mesh openings.
2. Verify the I²S clock lines (SCK, WS) reach both mics with equal trace lengths.

### 3.5. Sensors and fan driver

1. Solder the **SHT40** (U5), **TSL2591** (U6), and **MAX17048** (U7) on the I²C bus.
2. Solder the **DRV8601** (U10) fan driver and the fan connector.
3. Solder the UV LED array (LED1 × 3) on the funnel mount board.

---

## 4. Enclosure Assembly

### 4.1. PCB mounting

1. Mount the main PCB inside the IP65 ABS enclosure using standoffs.
2. Route the mic ports to align with the hydrophobic mesh openings in the enclosure wall.
3. Mount the solar panel on the exterior of the lid with weatherproof adhesive (silicone sealant).

### 4.2. Intake funnel

1. 3D-print the intake funnel (matte black PLA or PETG) — STL files are in `docs/funnel.stl`.
2. Mount the UV LED star-board at the center of the funnel, above the fan.
3. Mount the 30 mm blower fan below the UV LEDs, oriented to pull air downward.
4. Attach the removable collection vial (15 mL centrifuge tube with mesh bottom) below the fan.

### 4.3. Weatherproofing

1. Apply silicone sealant around all cable penetrations (solar panel, fan, UV LED wires).
2. Verify the enclosure gasket is seated properly — close the lid and check with a water spray test.
3. The hydrophobic mesh (Gore acoustic vent) over the mic ports must be pressed flush — no gaps.

---

## 5. Firmware Flashing

1. Connect a USB-C cable to the ESP32-S3 (J1).
2. Hold the PROG button (SW1) and press RESET (or power-cycle) to enter download mode.
3. Flash the firmware:
   ```
   cd firmware/
   idf.py set-target esp32s3
   idf.py build
   idf.py -p /dev/ttyUSB0 flash monitor
   ```
4. Watch the serial monitor — you should see:
   ```
   echo-trap: Echo Trap v1.0 starting...
   echo-trap: All subsystems initialized
   echo-trap: Tasks created. System running.
   ```

---

## 6. LoRaWAN Provisioning

1. Create a LoRaWAN device on your network server (TTN, Chirpstack, Helium).
2. Get the **AppEUI**, **AppKey**, and **DevEUI**.
3. Use the companion script to provision over BLE:
   ```
   python scripts/lorawan_config.py --addr AA:BB:CC:DD:EE:FF \
       --appeui 0000000000000001 \
       --appkey 00112233445566778899AABBCCDDEEFF \
       --deveui 0000000000000001
   ```
4. The device will attempt OTAA join on next boot. The green LED lights when joined.

---

## 7. Field Deployment

### 7.1. Placement

- Mount the Echo Trap at **crop canopy height** (1–2 m above the crop).
- Face the intake funnel toward the prevailing wind (insects approach upwind).
- Ensure the solar panel faces south (northern hemisphere) at a 30–45° tilt.
- Secure with the strap/zip-tie bracket to a trellis wire, stake, or pole.

### 7.2. Collection vial

- The mesh collection vial captures target pests for lab confirmation.
- Check and replace the vial every 1–2 weeks (or when full).
- Label the vial with the date and location for species ID.

### 7.3. Verification

1. After deployment, the green LED should blink every 15 min (uplink sent).
2. Check the dashboard (TTN/Chirpstack) — you should see summary uplinks with species counts.
3. To test the fan, use the field_test script:
   ```
   python scripts/field_test.py --addr AA:BB:CC:DD:EE:FF
   ```
   This sends a test command that triggers the fan and UV LED.

---

## 8. Maintenance

- **Monthly**: Wipe the solar panel clean with a damp cloth.
- **Biweekly**: Replace the collection vial.
- **Seasonally**: Inspect the hydrophobic mesh for clogging; replace if dirty.
- **Annually**: Check the 18650 battery health via the dashboard (battery % trend).

---

## License

MIT — build it, deploy it, count bugs with it.