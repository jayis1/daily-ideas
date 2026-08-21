# Scribe Nib — Calibration Guide

## Why Calibrate?

The Scribe Nib uses a factory-trained CNN model that works well for most
handwriting styles (~82% accuracy). However, everyone writes differently —
stroke speed, pen angle, writing pressure, and character proportions vary
significantly between individuals. Calibration adapts the device to your
specific handwriting, improving accuracy to ~94%.

## Calibration Modes

### Quick Calibration (2 minutes)

Write 24 representative characters (digits + common letters). This adjusts:
- Z-axis gravity baseline (for pen-up/pen-down detection)
- Stroke scaling (how large/small you write)
- Writing speed profile (for ODR and integration time)

**Best for**: First-time setup, or when switching between users.

### Full Calibration (10 minutes)

Write all 62 characters (0-9, A-Z, a-z) three times each. This creates a
complete personalized profile with fine-tuned thresholds.

**Best for**: Maximum accuracy, professional use, or if quick calibration
doesn't provide satisfactory results.

### Adaptive Mode (ongoing)

The Scribe Nib continuously learns from corrections. When the connected
app sends back corrected characters, the device adjusts its internal model
incrementally.

**Best for**: Day-to-day use — accuracy improves over time automatically.

## How to Calibrate

### Method 1: Using the Python script

```bash
# Quick calibration (default profile 1)
python3 scripts/calibrate_user.py --mac AA:BB:CC:DD:EE:FF

# Full calibration (profile 2)
python3 scripts/calibrate_user.py --mac AA:BB:CC:DD:EE:FF --profile 2 --full

# Specify repeat count
python3 scripts/calibrate_user.py --mac AA:BB:CC:DD:EE:FF --repeats 5
```

### Method 2: Using the mobile app

1. Open the Scribe Nib companion app
2. Tap "Calibrate" → "Quick" or "Full"
3. Follow the on-screen prompts
4. Profile is saved automatically

### Method 3: Double-tap on the clip

Double-tap the capacitive touch pads on the clip to cycle through profiles.
Hold the touch for 3 seconds to start an inline calibration sequence.

## Calibration Tips

### Writing Surface
- Use a **firm, flat surface** (desk, table, hard notebook)
- Avoid soft surfaces (cushions, fabric) — they reduce pen-up detection accuracy
- Paper thickness doesn't matter — the IMU detects contact, not pressure

### Pen Type
- Works with any pen, pencil, or stylus
- Heavier pens produce larger Z-axis transients (easier to detect)
- Very light pens (e.g., plastic disposable) may need higher pen-down threshold

### Writing Style
- **Write naturally** — don't modify your handwriting for the device
- Write at your **normal speed**
- Use your **normal character proportions**
- Don't worry about perfection — the model handles variation

### Environment
- Calibrate in a **quiet magnetic environment** (away from speakers, monitors)
- Avoid calibrating near large metal objects (they distort the magnetometer)
- Room temperature is ideal (extreme cold affects IMU performance)

## User Profiles

The Scribe Nib stores 4 profiles:

| Profile | Purpose | NVS Key |
|---------|---------|---------|
| 0 | Factory default (read-only) | prof0 |
| 1 | User 1 | prof1 |
| 2 | User 2 | prof2 |
| 3 | User 3 | prof3 |

### Switching Profiles

- **BLE**: Write to characteristic 0xFFB5
- **Touch**: Double-tap the clip pads
- **UART**: Send `PROFILE <n>` command over serial

### Sharing a Device

If multiple people share one Scribe Nib:
1. Each person uses a different profile (1-3)
2. Switch profile by double-tapping before writing
3. The OLED briefly shows "P1", "P2", or "P3"
4. A short vibration confirms the switch

## Troubleshooting Calibration

### "Characters are recognized but often wrong"
- Run full calibration with 5 repeats
- Check that the IMU is centered on the pen (clip properly positioned)
- Try a different writing surface

### "Pen-up/pen-down not detected reliably"
- The gravity baseline may be wrong
- Re-run quick calibration (it recalibrates gravity)
- Write on a harder surface for sharper transients

### "Drift accumulates over a long writing session"
- This is expected — position estimation drifts without zero-velocity updates
- The Scribe Nib resets position at each pen-up
- For long cursive writing, lift the pen briefly every 3-4 characters

### "Special gestures not recognized"
- Gestures require deliberate, quick motions
- Swipe gestures need speed > 2 m/s
- Circle gesture needs > 315° of rotation
- Try making gestures larger and faster