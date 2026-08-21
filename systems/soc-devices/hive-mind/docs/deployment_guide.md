# Hive Mind — Deployment Guide

## Apiary Installation

### 1. Choose a Hive Stand

The Hive Mind load cell must be the **sole support point** on one side of the hive. Options:

- **Single-point mounting**: Replace one hive stand leg with the load cell bracket. The other three legs are standard.
- **Platform mounting**: Place the entire hive on a weighing platform with the load cell as the rear support point.

> **Important**: The load cell must bear the full weight on one axis. Uneven loading causes errors. Use a rigid aluminum bracket (included in STL files in `hardware/`).

### 2. Install the Load Cell

1. Mount the aluminum bracket to the hive stand using M5 bolts.
2. Place the 50 kg beam load cell between the bracket and the hive floor.
3. Route the 4-conductor cable (E+, E-, A+, A-) through the cable gland into the Hive Mind enclosure.
4. Connect to the JST-PH 4-pin header on the PCB (labelled `LC`).

### 3. Install Temperature Probes

1. Drill 3 mm holes in the hive frames at three heights:
   - **Floor**: 10 mm above the bottom board
   - **Mid**: Center of the brood area (approximately frame 5, midway up)
   - **Crown**: Just below the crown board / inner cover
2. Push the DS18B20 probes (in silicone-sheathed cables) into the holes.
3. Seal each hole with beeswax to prevent drafts and propolis entry.
4. Connect the 3-pin JST-PH connectors to the PCB (labelled `T1`, `T2`, `T3`).

### 4. Install the IR Entrance Gate

1. 3D-print the entrance gate (STL file in `hardware/entrance_gate.stl`).
2. The gate has two channels, each with an IR LED/phototransistor pair:
   - **Outgoing channel**: Bees leaving the hive pass through this beam.
   - **Incoming channel**: Bees entering the hive pass through this beam.
3. Mount the gate at the hive entrance using hive staples or screws.
4. Connect the 4-pin JST-PH cables to the PCB (labelled `IR-OUT`, `IR-IN`).

### 5. Mount the Enclosure

1. Mount the IP65 ABS enclosure under the hive stand or on the side wall.
2. Ensure the antenna wire points upward (vertical polarization for 868/915 MHz).
3. Route all cables through cable glands and tighten.
4. Apply silicone sealant around all cable glands.

### 6. Mount the Solar Panel

1. Mount the 5 W solar panel on a south-facing bracket (Northern Hemisphere) at approximately 45° angle.
2. Connect the solar panel cable to the PCB (labelled `SOLAR`).
3. Ensure the panel gets direct sunlight for at least 4 hours per day.

### 7. Insert the Battery

1. Insert a freshly charged 18650 LiFePO₄ (3.2 V, 1500 mAh minimum) cell into the holder.
2. The TP4056 charger will manage charging from USB-C or solar panel.
3. **Important**: Use LiFePO₄ (3.2 V), NOT standard Li-ion (3.7 V). The ME6211 LDO needs at least 3.5 V input for regulation, and the solar panel provides 5–6 V.

---

## Calibration

### Weight Calibration

You must calibrate the load cell after installation:

1. Tare the empty platform:
   ```
   > weight tare
   ```

2. Place a known weight on the platform (e.g., 10 kg = 10000 g):
   ```
   > weight calibrate 10000
   ```

3. Verify:
   ```
   > weight read
   Weight: 10002 g (10.0 kg)
   ```

4. Save the calibration:
   ```
   > save
   ```

### Temperature Probe Assignment

On first boot, probes are auto-assigned by ROM ID order (first found = floor, second = mid, third = crown). To reassign:

1. Scan for probes:
   ```
   > temp scan
   Found 3 probes:
   [0] 28:FF:A1:B2:C3:D4:E5:01 -> floor
   [1] 28:FF:11:22:33:44:55:66 -> mid
   [2] 28:FF:AA:BB:CC:DD:EE:FF -> crown
   ```

2. If needed, swap assignments:
   ```
   > temp assign 28:FF:AA:BB:CC:DD:EE:FF floor
   ```

3. Verify by touching each probe and checking which temperature changes:
   ```
   > temp read
   Floor: 32.1°C  Mid: 34.8°C  Crown: 22.5°C
   ```
   (The one you're touching should show the highest temperature.)

4. Save:
   ```
   > save
   ```

### IR Gate Calibration

1. Verify each gate triggers:
   ```
   > bee calibrate
   Calibrating OUT gate... Break detected! ✓
   Calibrating IN gate... Break detected! ✓
   ```

2. If a gate doesn't trigger, adjust the IR LED/phototransistor alignment in the 3D-printed gate.

---

## LoRaWAN Setup

### Option A: The Things Network (OTAA)

1. Create a TTN account at [console.thethingsnetwork.org](https://console.thethingsnetwork.org).
2. Register a new device:
   - Get the DevEUI from the Hive Mind console:
     ```
     > lora status
     DevEUI: 70:B3:D5:7E:D0:00:00:01
     ```
   - Generate an AppEUI and AppKey in TTN.
3. Program the keys via USB console:
   ```
   > lora set_appeui 70B3D57ED0000000
   > lora set_appkey 2B7E151628AED2A6ABF7158809CF4F3C
   > lora join otaa
   Joining... Joined!
   > save
   ```
4. Verify uplinks appear in TTN console.

### Option B: Private Gateway (ABP)

1. Set network session key and app session key:
   ```
   > lora set_nwkskey <key>
   > lora set_appskey <key>
   > lora set_devaddr <addr>
   > lora join abp
   ```
2. The device will begin transmitting immediately.

### Data Rate Selection

| Region | Recommended DR | SF | Bandwidth | Range |
|--------|---------------|-----|-----------|-------|
| EU868 | DR3 | SF7 | 125 kHz | ~2 km |
| US915 | DR3 | SF7 | 125 kHz | ~2 km |
| AU915 | DR3 | SF7 | 125 kHz | ~2 km |

For rural apiaries with distant gateways, use DR0 (SF12) for maximum range (~10 km) at the cost of higher power consumption and longer airtime.

---

## Monitoring

### Dashboard Integration

The Hive Mind sends a 21-byte payload every 15 minutes. Use the Python decoder script (`scripts/decode_payload.py`) to parse the data:

```bash
python3 decode_payload.py --hex "0BAC1A1C202082049600140001E0018C073E"
```

Output:
```json
{
  "weight_g": 2988,
  "temp_floor": 21.0,
  "temp_mid": 26.0,
  "temp_crown": 24.0,
  "ambient_t": 22.0,
  "ambient_h": 56.0,
  "ambient_p": 1003.4,
  "acoustic_class": "QUEENRIGHT",
  "dominant_freq_hz": 245,
  "bee_in": 20,
  "bee_out": 15,
  "battery_v": 3.24,
  "solar_v": 5.40,
  "uptime_h": 24,
  "health_score": 82
}
```

### Grafana Dashboard

See `scripts/grafana_dashboard.json` for a pre-built Grafana dashboard that visualizes hive health data from TTN/InfluxDB.

---

## Maintenance

- **Every 3 months**: Clean solar panel with damp cloth. Check cable glands for leaks.
- **Every 6 months**: Replace 18650 LiFePO₄ battery (or verify capacity > 80%).
- **Annually**: Re-calibrate load cell. Check DS18B20 probe seals.
- **After swarm season**: Verify IR gate alignment (propolis may accumulate).

---

## Winter Operation

The Hive Mind is designed for year-round operation:

- **Temperature range**: -20°C to +60°C (DS18B20 and BME280 both support this range)
- **Battery**: LiFePO₄ performs well in cold; capacity drops ~20% at -10°C but recovers
- **Solar panel**: Snow accumulation reduces charging; angle the panel at 60° for self-clearing
- **Acoustic analysis**: Winter cluster has a distinct hum (~200 Hz, low amplitude); the classifier handles this
- **IR gates**: May frost over; the entrance gate has a small rain hood

If the device detects critical battery level (< 2.8 V), it enters ultra-low power mode:
- Sensor reads every 5 minutes instead of 30 seconds
- LoRa uplinks every 1 hour instead of 15 minutes
- Acoustic analysis disabled
- OLED display off

---

*SoC Device Inventions — jayis1*