# Safety Notes — Ferro Weave

> **Read this before powering on.** Ferro Weave drives up to **±2 A
> through an inductive load** and generates **±15 V** internally.

## Hazards

### 1. Inductive kickback
The primary winding is an inductor. When the power stage switches off,
the stored energy `½LI²` must go somewhere. The LM5035 + IRFH7446
half-bridge includes **freewheeling** through the FET body diodes back
into the ±15 V rail (clamped by a 15 V TVS + bulk cap). **Do not**
disconnect the primary leads during a sweep — the resulting open-circuit
kick can exceed 100 V and damage the FETs.

### 2. Heating
At ±2 A into a low-impedance primary, the power stage dissipates up to
1.5 W. The NTC trips a thermal shutdown at 85 °C. If the enclosure lacks
ventilation, sustained sweeping will trip this repeatedly. Add the
bottom ventilation slots from the enclosure STL.

### 3. The ±15 V rail
The boost + charge-pump generates ±15 V at up to 1 A. This is below the
SELV limit (60 V) but can deliver enough current to heat a small wire or
burn a finger. Don't touch the power-stage components during a sweep.

## Protection layers (defense in depth)

| Layer | Response time | What it does |
|-------|---------------|--------------|
| Hardware OCP (LM5035 current limit) | ~200 ns | latches off the driver at 2.5 A |
| ADC analog watchdog (ADC1) | ~1 µs | firmware OCP at 2.5 A → HRTIM fault |
| STOP button → HRTIM_FLTA | hardware | forces all HRTIM outputs safe, no firmware needed |
| NTC thermal | ~1 s | shuts down the boost at 85 °C |
| `AMP_EN` gate | firmware | ±15 V rail off in standby & after disarm |
| Degauss-on-disarm | firmware | leaves the specimen unmagnetized |

## Operating limits

| Parameter | Min | Max | Notes |
|-----------|-----|-----|-------|
| Primary current | −2 A | +2 A | bipolar |
| Sweep frequency | 0.1 Hz | 1 kHz | above 1 kHz the integrator gain rolls off |
| Primary inductance | 10 µH | 100 mH | below 10 µH the OCP may trip on dI/dt |
| Specimen B_sat | — | ~2 T | limited by ±15 V × N2 / (2π·f·N2·A) |
| Ambient temp | 0 °C | 40 °C | NTC trip is on the FETs, not ambient |

## What to do if…

- **FAULT LED lights up during a sweep:** the OCP or thermal trip
  fired. Press STOP, wait 5 s, press SWEEP again. If it faults
  immediately, your primary impedance is too low (add turns) or the
  wiring is shorted.
- **The OLED shows a tilted/slanted loop:** the integrator reset isn't
  firing. Check the INTG_RESET solder joint and the 10 µs pulse.
- **The loop is a straight line:** no hysteresis — either a pure
  resistor is connected (expected) or the specimen isn't coupled to the
  secondary (check N2 continuity).
- **B_sat drifts with frequency:** normal for conductive materials (eddy
  currents); use a lower sweep frequency or a laminated/ferrite specimen.