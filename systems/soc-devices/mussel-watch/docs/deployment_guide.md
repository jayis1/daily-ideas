# Mussel Watch — Deployment Guide

## Pre-Deployment Checklist

- [ ] PCB assembled and tested (see assembly guide)
- [ ] Sensor head potted and leak-tested (submerge 30 min, check for water)
- [ ] Battery charged (>3.8V)
- [ ] microSD card inserted and FAT32 formatted
- [ ] LoRa antenna connected
- [ ] BLE app installed on phone
- [ ] LoRa gateway configured and receiving test packets
- [ ] Deployment ID set via BLE app
- [ ] Calibration performed (closed + open points)

## Site Selection

### Ideal deployment site

- **Water body**: River, lake, aquaculture pen, or wastewater discharge monitoring point
- **Mussel source**: Use locally-occurring bivalve species (zebra mussels, blue mussels, oysters). Do not introduce non-native species.
- **Depth**: 0.5–3 m for solar-powered surface mount; up to 30 m for the MS5837 sensor range
- **Flow**: Moderate flow is fine; avoid high-flow areas that could dislodge the clip
- **Sunlight**: Solar panel needs 4+ hours of direct sunlight per day for perpetual operation
- **LoRa coverage**: Verify gateway is within 2–15 km line-of-sight (shorter if through vegetation/buildings)

### Avoid

- Areas with heavy boat traffic (waves could dislodge the clip)
- Areas with known chemical contamination above lethal levels for bivalves (the mussel dies → no data)
- Freezing conditions (mussels may naturally close for winter dormancy; interpret data accordingly)
- Areas with strong currents that could tangle the sensor cable

## Calibration Procedure

### Two-point gape calibration

This must be done *in situ* with the actual mussel you are monitoring.

1. **Closed point**:
   - Gently hold the mussel shells closed (apply light pressure, do not force)
   - Wait 5 seconds for the Hall voltage to stabilize
   - Press and hold the mode button for >2 seconds to enter calibrate mode (blue LED blinks 5×)
   - OR: Use the BLE app → write `0x00` to characteristic `0x1906` (calibrate_closed, channel 0)
   - The firmware records the current Hall voltage as the 0° (closed) reference
   - The blue LED blinks once to confirm

2. **Open point**:
   - Release the mussel and wait for it to open naturally (this may take 1–4 hours)
   - When the gape is at maximum (the mussel is actively filter-feeding), trigger calibration
   - Use the BLE app → write `0x00` to characteristic `0x1907` (calibrate_open, channel 0)
   - The firmware records the current Hall voltage as the maximum-open reference
   - The blue LED blinks twice to confirm

3. **Verify**:
   - In the BLE app, watch the `gape_live` (0x1908) characteristic
   - When the mussel is open, you should see a value near 10–15°
   - When closed, you should see a value near 0°
   - If values are inverted or erratic, re-calibrate

### Multi-mussel calibration

If using multiple mussel heads (up to 4 via the TCA9548A mux):
- Short-press the mode button to cycle the active head count (1→2→3→4→1)
- Calibrate each head separately by writing the channel number (0–3) to the calibrate characteristics

## Deployment Steps

1. **Attach the sensor clip to the mussel**
   - Gently open the titanium clip and position it on the mussel shell
   - The Hall sensor arm should be on the fixed (lower) valve
   - The magnet should be on the mobile (upper) valve
   - Ensure the clip is secure but not pinching the soft tissue

2. **Submerge the sensor head**
   - Lower the sensor head + mussel into the water to the desired depth
   - The MS5837 will record the deployment depth
   - The DS18B20 will record water temperature

3. **Mount the electronics pod**
   - Secure the pod above water on a pole, buoy, or dock
   - The BME280 (barometric) must be in air, not submerged
   - Ensure the solar panel faces the sun (south-facing in northern hemisphere)
   - Tilt the solar panel ~30° from horizontal for optimal rain shedding and sun capture

4. **Verify operation**
   - Blue LED should blink periodically (normal mode)
   - Use the BLE app to check live data before leaving the site
   - Confirm LoRa uplinks appear at the gateway
   - Note the deployment coordinates and deployment ID

5. **Monitor**
   - Check the gateway dashboard for regular uplinks (every 15 minutes by default)
   - The first 24 hours establish the circadian rhythm baseline
   - After 24 hours, rhythm deviation detection becomes active

## Data Interpretation

### Normal mussel behaviour

| Time of day | Expected gape | Notes |
|-------------|---------------|-------|
| Daytime (feeding) | 5–15° (open) | Active filter-feeding |
| Night | 1–8° (partially closed) | Reduced activity, not fully closed |
| Disturbance | 0–2° (closed) | Brief closures from physical disturbance |
| Low tide (intertidal) | 0° (closed) | Natural — not an alert |

### Alert interpretation

| Alert code | Meaning | Action |
|-----------|---------|--------|
| 1 (Closure event) | Mussel closed for >30s | Check water-quality context (temp, DO) |
| 2 (Sustained closure) | Mussel closed >10 minutes | Likely pollutant — investigate water source |
| 3 (Rhythm deviation) | Unusual gape pattern for this hour | Monitor; may indicate sublethal stress |
| 4 (Multi-mussel event) | ≥2 mussels closed simultaneously | Strong environmental signal — collect water sample |
| 5 (Temperature anomaly) | Sudden temp change >5°C | Thermal pollution or natural event (storm) |
| 6 (DO anomaly) | Dissolved O₂ < 4 mg/L | Hypoxia — check for algal bloom or stagnation |
| 7 (Low battery) | Battery <20% | Check solar panel orientation / shading |

## Maintenance

- **Monthly**: Visual inspection of solar panel (clean if fouled), check enclosure for water ingress
- **Quarterly**: Replace the silica gel desiccant in the electronics pod
- **Annually**: Replace the LiPo battery (LiPo lifespan ~2–3 years in solar cycling)
- **As needed**: Re-calibrate if the magnet or Hall sensor shifts position

## Ethical Considerations

- Use bivalves that are already present at the monitoring site whenever possible
- Do not introduce non-native species
- Handle mussels gently — they are living organisms
- The clip should not restrict the mussel's natural movement
- In areas where the monitored species is protected, obtain appropriate permits
- Remove the sensor if the mussel shows signs of stress (shell damage, weight loss)