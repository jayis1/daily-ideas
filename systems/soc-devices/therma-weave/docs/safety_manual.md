# Therma Weave — Safety Manual

## ⚠️ IMPORTANT SAFETY INFORMATION

**READ THIS ENTIRE DOCUMENT BEFORE ASSEMBLING OR USING THE THERMA WEAVE DEVICE.**

The Therma Weave controls heating elements that can reach temperatures sufficient to cause burns. Improper use can result in fire, burns, or battery explosion. Follow ALL safety procedures in this document.

---

## Safety Architecture

Therma Weave implements **4 independent safety layers**. All must be functional before use.

### Layer 1: Software Watchdog (ESP32-C3)
- **Response time**: ~100ms (10Hz task)
- **Function**: 
  - Monitors per-zone thermistor readings
  - Shuts down zone if temperature > 65°C
  - Shuts down zone if current > 4A
  - Shuts down zone if thermistor is open or shorted
- **Failure mode**: If ESP32-C3 crashes, Layers 2-4 still protect

### Layer 2: Hardware Comparator (LM393)
- **Response time**: <1ms
- **Function**:
  - Independent analog comparator monitoring thermistor voltage
  - If ANY thermistor voltage indicates >70°C, LM393 output goes LOW
  - LM393 output drives 74HC32 OR gate → forces all MOSFET gates LOW
  - Completely independent of ESP32-C3
- **Failure mode**: If LM393 fails, Layers 3-4 still protect

### Layer 3: Thermal Fuse (one-time, per zone)
- **Response time**: <1s
- **Function**:
  - Each heater zone has a 75°C thermal fuse in series
  - Non-resettable — if it blows, it must be replaced
  - Located at the hottest point of each zone
  - Rating: 75°C, 5A (Bel Fuse 5ST series or equivalent)
- **Failure mode**: If Layers 1-2 fail, thermal fuses provide last-resort protection

### Layer 4: BLE Alert
- **Response time**: ~500ms
- **Function**:
  - Smartphone app receives fault notifications
  - Manual emergency shutdown via BLE characteristic 0xFFBF
  - Fault history logging with timestamps
- **NOT a safety layer**: This is a convenience feature only

---

## Pre-Use Checklist

Before EVERY use session, verify:

- [ ] All thermistors read correctly (25±5°C at room temperature)
- [ ] No fault flags are active (`SAFETY:STATUS` shows no faults)
- [ ] Battery voltage is above 10.5V
- [ ] All heater zone connectors are firmly seated
- [ ] No visible damage to cables or PCB
- [ ] OLED display shows correct zone temperatures
- [ ] BLE connection is established (optional, for monitoring)

---

## Maximum Ratings

| Parameter | Maximum | Unit |
|-----------|---------|------|
| Supply voltage | 14.4 | V (3S LiPo fully charged) |
| Per-zone current | 3.0 | A (continuous) |
| Per-zone current (fault) | 4.0 | A (triggers shutdown) |
| Total current | 12 | A (all zones) |
| Per-zone power | 36 | W (at 12V) |
| Total power | 144 | W |
| Target temperature range | 30–55 | °C |
| Hard cutoff temperature | 65 | °C |
| Thermal fuse temperature | 75 | °C |
| Battery voltage range | 9.0–12.6 | V (3S LiPo) |
| Low battery cutoff | 10.5 | V |

---

## Burn Risk Assessment

| Skin Contact Duration | Temperature | Risk Level |
|----------------------|-------------|------------|
| > 8 hours | 44°C | Low (mild discomfort) |
| > 1 hour | 47°C | Moderate (possible erythema) |
| > 5 minutes | 50°C | High (first-degree burn possible) |
| > 30 seconds | 55°C | Very High (second-degree burn risk) |
| > 5 seconds | 60°C | Severe (third-degree burn risk) |

**The default maximum target temperature of 55°C is set for SAFETY. Do NOT increase the maximum target temperature above 55°C.**

---

## Battery Safety

### Approved Battery Types
- **3S LiPo** (11.1V nominal, 12.6V fully charged)
  - Minimum capacity: 2200mAh
  - Must have built-in PCM (protection circuit module)
  - Must have balance connector
- **12V DC power supply** (minimum 12A for all 4 zones)

### Battery Warnings
- ⚠️ **NEVER** use LiPo batteries without a protection circuit
- ⚠️ **NEVER** charge LiPo batteries unattended
- ⚠️ **NEVER** puncture, crush, or short-circuit a LiPo battery
- ⚠️ **NEVER** expose to temperatures above 60°C
- ⚠️ **NEVER** use a battery that is swollen, damaged, or has been dropped
- ⚠️ **ALWAYS** store LiPo batteries in a fireproof container when not in use

---

## Fire Safety

### Reduced Oxygen Environment Warning
Heating elements consume oxygen and can create fire hazards in confined spaces. **Do NOT use in:**
- Small sealed enclosures
- Under blankets while sleeping (suffocation + burn risk)
- Near flammable materials (<30cm clearance required)
- In tents without adequate ventilation

### What To Do If Smoke Or Burning Smell Is Detected
1. **IMMEDIATELY** disconnect the power supply / battery
2. Move the device away from flammable materials
3. Do NOT touch the heating elements
4. Allow to cool completely before handling
5. Inspect for damage before reuse
6. If a thermal fuse has blown, replace it before reusing

---

## EMC Compliance Note

The IRF3205 MOSFETs switch at 1kHz PWM with high current. The device includes:
- Flyback diodes (1N4148) on each MOSFET gate
- 100µF electrolytic capacitor on the 12V bus
- 0.1µF decoupling capacitors on each IC
- Proper ground plane layout

However, this device may cause electromagnetic interference with sensitive equipment. Do not use within 30cm of:
- Pacemakers or implanted medical devices
- Aviation navigation equipment
- Sensitive radio receivers

---

## Medical Disclaimer

Therma Weave is **NOT** a medical device. It has **NOT** been evaluated by the FDA or any other regulatory body. It is **NOT** intended for:
- Therapeutic use on insensate skin (diabetes, neuropathy)
- Wound warming
- Hypothermia treatment
- Any medical application

Use on insensate skin areas increases burn risk dramatically because the user cannot feel overheating. **NEVER** use on skin with reduced sensation.

---

## Warranty Limitations

This is an open-source hardware project provided AS-IS. The designers assume NO liability for:
- Burns or thermal injuries
- Fire or property damage
- Battery incidents
- Any injury resulting from use of this device

By assembling and using Therma Weave, you accept full responsibility for safe operation and agree that you have read and understood this entire safety manual.