# Therma Weave — PID Tuning Guide

## Overview

The Therma Weave uses PID (Proportional-Integral-Derivative) controllers to maintain target temperatures in each heating zone. This guide explains how PID works, how to tune it for your specific garment, and how to use the built-in auto-tune feature.

## PID Basics

A PID controller continuously calculates an "error" value as the difference between the desired temperature (setpoint) and the measured temperature. It then applies a correction based on proportional, integral, and derivative terms:

```
Output(t) = Kp × e(t) + Ki × ∫e(t)dt + Kd × de(t)/dt
```

Where:
- **e(t)** = Target temperature - Current temperature (the "error")
- **Kp** = Proportional gain (how aggressively to respond to error)
- **Ki** = Integral gain (how to handle persistent error)
- **Kd** = Derivative gain (how to dampen oscillation)

### Each Term Explained

| Term | Symbol | Effect | Too High | Too Low |
|------|--------|--------|----------|---------|
| Proportional | Kp | Direct response to error | Oscillation, overshoot | Slow approach, never reaches target |
| Integral | Ki | Corrects persistent offset | Oscillation, integral windup | Steady-state error |
| Derivative | Kd | Anticipates future error | Noise amplification, jitter | Overshoot on setpoint change |

## Default Parameters

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| Kp | 2.5 | Moderate response for typical garment (50g fabric) |
| Ki | 0.08 | Slow integral to avoid windup |
| Kd | 0.4 | Light damping to prevent oscillation |

These defaults work well for:
- Heated jacket (polyester shell, ~50g heating element per zone)
- 12V supply, 3Ω per zone (~4A max)
- Moderate insulation (no wind)

## Tuning for Different Garments

### Thin Garments (T-shirt liner, gloves)
- **Kp**: 1.5–2.0 (lower — thin material heats fast)
- **Ki**: 0.12 (slightly higher — compensate for fast heat loss)
- **Kd**: 0.2 (lower — less oscillation expected)

### Thick Garments (parka, sleeping bag)
- **Kp**: 3.0–4.0 (higher — more thermal mass to overcome)
- **Ki**: 0.05 (lower — slow thermal response, less windup)
- **Kd**: 0.6 (higher — more damping needed)

### High-Power Applications (seat cushion, blanket)
- **Kp**: 1.0–1.5 (lower — high power heats quickly)
- **Ki**: 0.15 (higher — large thermal mass needs persistent drive)
- **Kd**: 0.3 (moderate — dampen fast response)

## Auto-Tune Procedure

Therma Weave includes a Ziegler-Nichols auto-tune feature that automatically determines optimal PID parameters.

### How It Works

1. The controller applies 50% duty cycle until temperature rises past the target
2. Then applies 0% duty cycle until temperature falls below target
3. It measures the oscillation amplitude (Ku) and period (Tu)
4. Calculates PID parameters using Ziegler-Nichols rules:
   - **Kp** = 0.6 × Ku
   - **Ki** = 2 × Kp / Tu
   - **Kd** = Kp × Tu / 8

### Running Auto-Tune

```bash
# Via BLE Python script
python3 scripts/pid_autotune.py --mac AA:BB:CC:DD:EE:FF --zone 0

# Via serial console
PID:AUTOTUNE 0
```

### Auto-Tune Requirements
- Start with the garment at room temperature (20–25°C)
- Target temperature must be at least 10°C above ambient
- No external heating/cooling during the test
- Allow 5–10 minutes per zone
- Auto-tune runs on one zone at a time

### After Auto-Tune
- The new PID parameters are saved to NVS automatically
- Verify stable operation for 10 minutes before relying on the tuned values
- If oscillation occurs, reduce Kp by 20% and Ki by 50%

## Manual Tuning Procedure

If auto-tune doesn't produce satisfactory results, tune manually:

### Step 1: Set Ki and Kd to Zero
```
ZONE:PID 0 2.0 0.0 0.0
```

### Step 2: Increase Kp Until Oscillation
Gradually increase Kp until the temperature oscillates around the setpoint. Note the Kp value where oscillation starts (Ku) and the oscillation period (Tu).

### Step 3: Set Kp to 60% of Ku
```
ZONE:PID 0 1.2 0.0 0.0   # if Ku = 2.0
```

### Step 4: Add Ki
Start with Ki = 2 × Kp / Tu. If Tu was measured in seconds:
```
ZONE:PID 0 1.2 0.08 0.0   # for Tu ≈ 30 seconds
```

### Step 5: Add Kd
Start with Kd = Kp × Tu / 8:
```
ZONE:PID 0 1.2 0.08 0.45
```

### Step 6: Fine-Tune
- If overshoot is too high: increase Kd, decrease Kp
- If response is too slow: increase Kp, decrease Kd
- If there's steady-state error: increase Ki slightly
- If there's oscillation: decrease Kp, increase Kd

## Activity-Adaptive Behavior

The IMU detects activity level and adjusts the effective target temperature:

| Activity | Adjustment | Reasoning |
|----------|-----------|-----------|
| Still | 0°C (target as-set) | No body heat contribution |
| Walking | -3°C | Muscular activity generates heat |
| Running | -6°C | Significant metabolic heat |
| Fall detected | All zones OFF for 30s, then max heat | Possible hypothermia |

To disable activity adaptation, set the IMU to "still" mode via BLE or serial:
```
SENSOR:ACTIVITY_MODE STILL
```

## Common Tuning Problems

| Problem | Cause | Solution |
|---------|-------|----------|
| Temperature oscillates ±3°C | Kp too high | Reduce Kp by 30% |
| Temperature overshoots by >5°C | Ki windup | Reduce Ki, add anti-windup limit |
| Never reaches target temperature | Kp too low or Ki too low | Increase Kp by 50% |
| Temperature slowly drifts | Ki too low | Increase Ki by 50% |
| Noisy duty cycle (jittery) | Kd too high | Reduce Kd by 50% |
| Oscillation after activity change | Thermal lag | Increase Kd, add 5-second thermal delay |

## Saving and Loading Parameters

```bash
# Save current parameters to NVS (persists across reboots)
SYSTEM:SAVE

# Load parameters from NVS (happens automatically at boot)
SYSTEM:LOAD

# Factory reset (restores default PID values)
SYSTEM:FACTORY_RESET
```