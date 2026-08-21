# Pulse Hound — RF Hunting Guide

## Introduction

The Pulse Hound is designed for one primary purpose: **finding RF emitters**. This guide covers practical techniques for using the device in real-world scenarios.

## Basic Operation

### Sweep Mode (Default)

1. Power on — the device starts in SWEEP mode
2. The OLED shows a scrolling waterfall; the right panel shows current RSSI in dBm
3. Audio clicks at a rate proportional to signal strength — **you don't need to watch the screen**
4. Walk slowly through the area. As you approach a transmitter, the clicks accelerate
5. When clicks become rapid (>20/s) or continuous, you're within 1–2 meters of the source

### Direction Finding Mode

1. Press the **DF** button — the stepper rotates the antenna through 360° (~30 seconds)
2. The OLED shows a compass arrow pointing toward the strongest signal
3. The bearing is relative to the device's orientation — note the direction, walk 5–10 meters, and repeat
4. **Triangulation**: take bearings from 2–3 positions; the intersection is the source location
5. The bearing accuracy is ±5° under good conditions (strong signal, no multipath)

### Signal Classification

The device labels detected signals as:

| Label | Meaning | Common Sources |
|-------|---------|----------------|
| **CW** | Continuous wave | Analog wireless mic, AM/FM bug, oscillator leakage |
| **WFL** | WiFi/BLE bursty | WiFi beacon, Bluetooth advertisement, Zigbee |
| **CEL** | Cellular pulsed | GSM/UMTS/LTE/5G, GPS tracker |
| **RAD** | Radar/UWB | Motion sensor, UWB ranging chip |
| **THM** | Thermal drift | Not a signal — environmental noise |
| **???** | Unknown | Unclassified — investigate further |

## Scenario: Hotel Room Bug Sweep

1. Enter the room, place the Pulse Hound on a stable surface
2. Wait 30 seconds for the baseline to establish (note the noise floor reading)
3. Walk slowly around the room, sweeping all surfaces:
   - Behind the TV and alarm clock
   - Inside/behind the lamp
   - Under the bed and furniture
   - Around the smoke detector
   - Behind wall art and mirrors
   - Inside the bathroom (around the exhaust fan)
   - Near electrical outlets
4. **Normal signals**: WiFi (−40 to −70 dBm, bursty), cellular (−50 to −80 dBm, pulsed)
5. **Suspicious signals**: 
   - Strong CW (continuous) signal coming from a non-obvious location → possible analog bug
   - Strong WiFi/BLE from an unexpected direction → possible hidden camera
   - Any signal that intensifies as you approach a specific object
6. Use DF mode to get a bearing, then physically inspect the indicated direction

## Scenario: Finding a Hidden WiFi Camera

1. Switch to SWEEP mode
2. Walk the room — you'll see a bursty WiFi/BLE signal (the camera's WiFi beacon)
3. Follow the audio clicks toward the strongest signal
4. When you're close, switch to DF mode to pinpoint the exact bearing
5. The camera is typically hidden in: smoke detectors, alarm clocks, USB chargers, picture frames, air fresheners

## Scenario: Hunting RF Interference

1. Identify the affected frequency band (e.g., 2.4 GHz WiFi interference)
2. The Pulse Hound detects the *total* RF energy, not per-frequency — so use the audio to walk toward the strongest emitter
3. Common interference sources: microwave ovens (2.45 GHz leakage), baby monitors, cordless phones, faulty LED drivers, switching power supplies
4. Use DF mode to get a bearing from multiple positions

## Scenario: EMC Pre-Compliance Sniffing

1. Power your prototype device on
2. Sweep around the enclosure — note the RSSI at various distances
3. The AD8318 detects unintentional EMI from clock harmonics, switching regulators, and digital buses
4. A "hot spot" on the enclosure indicates where shielding is inadequate
5. Compare before/after adding shielding or ferrite beads

## Tips for Best Results

### Audio Feedback
- **Trust the audio**: the click rate is your primary feedback — you can hunt while looking at the room, not the screen
- **Sensitivity**: in a quiet environment, even −70 dBm produces audible clicks (~2/s)
- **Boost mode**: long-press SCAN to increase click sensitivity (doubles the rate at low RSSI)

### Direction Finding
- DF works best in open spaces — multipath reflections in dense indoor environments can confuse the bearing
- Take bearings from at least 3 positions, 5–10 m apart, for accurate triangulation
- Strong signals (> −30 dBm) give the best bearing accuracy; weak signals near the noise floor are unreliable

### Signal Identification
- **WiFi routers**: bursty, periodic (every ~100 ms beacon), −40 to −70 dBm
- **Bluetooth beacons**: very bursty (short advertisements), −50 to −80 dBm
- **Cellular phones**: strong pulsed signal when actively transmitting (call, data), −30 to −60 dBm
- **GPS trackers**: periodic cellular bursts (every 10–60 s), brief strong signal
- **Analog wireless mics**: continuous CW, −30 to −60 dBm, very stable RSSI
- **Microwave ovens**: 2.45 GHz CW when running, −40 to −70 dBm at 1 m

### Range Estimation

The RSSI at distance *d* from a transmitter with power *P_tx* (in dBm) is approximately:

```
RSSI = P_tx − 20·log10(d) − 20·log10(f_MHz) + 27.5    (free space)
```

| Transmitter Power | RSSI at 1 m | RSSI at 10 m | RSSI at 100 m |
|-------------------|-------------|--------------|----------------|
| +10 dBm (10 mW)   | −10 dBm     | −30 dBm      | −50 dBm        |
| 0 dBm (1 mW)       | −20 dBm     | −40 dBm      | −60 dBm        |
| −10 dBm (0.1 mW)  | −30 dBm     | −50 dBm      | −70 dBm        |
| −20 dBm (BLE)     | −40 dBm     | −60 dBm      | −80 dBm        |

Indoor range is typically 10–15 dB less (walls, furniture absorb RF).

## Limitations

- The AD8318 is a **total-power detector** — it cannot distinguish between two signals at different frequencies that are present simultaneously. For frequency-specific hunting, a real spectrum analyzer is needed.
- The 28BYJ-48 stepper is slow (~30 s per 360° sweep) — not suitable for fast-moving targets.
- The directional antenna is optimized for 2.4 GHz; sub-GHz antennas (e.g., 433 MHz, 868 MHz) will need a different antenna with worse directivity at small size.
- Multipath reflections indoors can cause bearing errors — always corroborate with audio + triangulation.

## Legal Considerations

- The Pulse Hound is a **passive receiver** — it does not transmit anything. Using a receiver to detect RF signals is legal in most jurisdictions.
- In some countries, it is illegal to possess or use "bug detection" equipment without a license (check your local laws).
- This device is for legitimate security, engineering, and educational purposes only.