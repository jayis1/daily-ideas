# Measurement Theory — Phyto Pulse

## Plant Electrophysiology: A Brief Primer

Plants are not electrically inert. They generate and propagate electrical signals that serve as rapid, long-range communication — analogous to (but much slower than) animal nervous systems. Three principal signal types are measured:

### 1. Action Potential (AP)

A **regenerative, all-or-nothing** depolarization that propagates along the phloem and xylem vascular tissue.

| Property | Typical Range |
|----------|--------------|
| Amplitude | 10–100 mV (extracellular) |
| Duration | 10–100 ms |
| Propagation speed | 0.5–20 cm/s |
| Refractory period | 0.5–2 s |
| Mechanism | Ca²⁺ influx → Cl⁻ efflux → depolarization; K⁺ efflux → repolarization |

**Trigger plants:**
- **Venus flytrap** (*Dionaea muscipula*): Two touches to trigger hairs within ~20 s → AP cascade → trap closure in <0.5 s. The "memory" is the interval between the two APs.
- **Mimosa pudica**: Touch to petiole → AP propagates → pulvinus cells lose turgor → leaf folds. Propagation visible at ~10 cm/s.
- **Sensitive plants** (*Mimosa*, *Biophytum*): Touch-triggered APs for predator avoidance.

### 2. Variation Potential (VP)

A **graded, slow depolarization** that propagates from wounded tissue via hydraulic pressure waves (not action potentials). The amplitude depends on wound severity — it is not all-or-nothing.

| Property | Typical Range |
|----------|--------------|
| Amplitude | 5–50 mV (extracellular, distance-dependent) |
| Duration | 1–10 s |
| Propagation speed | 0.05–0.5 cm/s (much slower than AP) |
| Mechanism | Wound-induced hydraulic wave → ROS/chemical propagation → gradual depolarization |

**Trigger:** Any wounding (cutting, herbivore attack, burning). The VP carries information about damage severity — plants use it for systemic defense signaling.

### 3. Slow-Wave Potential (SWP)

**Gradual (minutes) voltage shifts** associated with:

| Stimulus | Expected SWP |
|----------|-------------|
| Light → Dark transition | 10–50 mV depolarization over 1–5 min |
| Dark → Light transition | Hyperpolarization |
| Water stress (drought) | Gradual depolarization over hours |
| Circadian rhythm | ~24 h oscillation, 5–20 mV amplitude |

The SWP reflects the combined effect of ion pump activity (H⁺-ATPase), photosynthetic activity, and transpiration-driven electrical changes.

---

## Measurement Methodology

### Surface (Extracellular) Measurement

The Phyto Pulse uses **surface measurement** — two Ag/AgCl electrodes placed on the plant surface, measuring the differential voltage as electrical signals propagate past the electrode pair.

#### Why surface (not intracellular)?

Intracellular measurement (impaling a cell with a glass microelectrode) is the gold standard for plant electrophysiology but:
- Requires expensive micromanipulators and microelectrode pullers
- Is destructive (the cell is punctured)
- Cannot be done in the field
- Requires a Faraday cage and vibration isolation

Surface measurement:
- Is non-destructive
- Works in the field, on any plant
- Uses cheap ($1.50) electrodes
- Captures the propagating wave as it passes — amplitude is attenuated but waveform shape is preserved
- Standard technique in field plant electrophysiology (e.g., Volkov et al.)

#### Electrode-Plant Interface

The waxy plant cuticle is a poor conductor. A KCl-agar gel bridge overcomes this:
- The 0.1 M KCl provides mobile ions (K⁺, Cl⁻) that carry charge across the cuticle
- The agar gel immobilizes the solution (no spill, stays in contact)
- The Ag/AgCl pellet provides a stable half-cell potential (~+220 mV vs SHE)

The interface has an impedance of ~100 kΩ–1 MΩ (depending on contact quality), well within the INA333's 10 GΩ input impedance budget.

#### Differential Configuration

```
E1 (active, leaf) ──── INA333 IN+
E2 (reference, stem) ── INA333 IN−
```

The differential voltage E1 − E2 cancels:
- Common-mode environmental noise (60 Hz mains, EMI)
- Common-mode electrode offset (both Ag/AgCl pellets have similar half-cell potentials)
- Common-mode thermal drift

Only the propagating signal (which arrives at E1 but not E2, or with different timing) survives as differential.

The INA333's CMRR of 114 dB (at G=100) suppresses common-mode by a factor of 500,000:1 — far exceeding any realistic common-mode noise.

### Signal Amplitude

Extracellular surface measurements of plant APs yield:
- **Venus flytrap**: 10–80 mV at the trap, attenuating to 1–10 mV at 10 cm distance
- **Mimosa pudica**: 5–50 mV near the pulvinus, 1–5 mV at distal petiole
- **Arabidopsis**: 0.5–5 mV (very small, requires high gain)
- **Root signals**: 0.1–1 mV (requires G=1001×)

The Phyto Pulse's four gain ranges (2×/11×/101×/1001×) cover the full range:
- G=2×: large slow-wave potentials (±2.5 V)
- G=11×: normal AP range (±200 mV) — most common
- G=101×: small/distant signals (±20 mV)
- G=1001×: root/Arabidopsis signals (±2 mV)

### Noise Budget

| Source | Noise (µVrms, 0.1–100 Hz) | Referred to input |
|--------|--------------------------|-------------------|
| Ag/AgCl electrode junction | ~1.0 | input |
| 1 MΩ bias resistor (Johnson) | ~0.6 | input |
| INA333 input noise | ~0.6 | input |
| ADS1256 @ G=64, 1 kSPS | ~0.7 | input (after PGA) |
| Vmid reference (OPA2333) | ~0.1 | input |
| **Total (RSS)** | **~1.5** | input |

This gives **5 µV minimum detectable signal** (3:1 SNR), sufficient for even the smallest root signals.

### Bandwidth

Plant electrical signals occupy a narrow band:
- AP: DC–100 Hz (most energy in 1–50 Hz)
- VP: DC–10 Hz (slow, minutes-long)
- SWP: DC–0.01 Hz (ultra-slow)

The Phyto Pulse bandpass filter (0.5 Hz HP + 100 Hz LP):
- Removes DC drift (electrode settling, temperature)
- Removes 60 Hz mains (partially — the LP at 100 Hz passes it, but the INA CMRR handles most)
- Preserves the full AP waveform

For SWP analysis, a separate 0.01 Hz LP path computes the 60 s windowed mean.

---

## Spike Detection Algorithm

### Adaptive Threshold

The detector uses an adaptive threshold based on the running statistics of the signal:

```
threshold = baseline + k × σ
```

where:
- `baseline` = exponentially-weighted moving average (τ = 5 s)
- `σ` = running standard deviation (recomputed every 10 s)
- `k` = 5.0 (default sensitivity; configurable)

This adapts to changing noise conditions (e.g., electrode drift, environmental interference) without manual tuning.

### Refractory Period

A 50 ms refractory period prevents double-counting on multi-phase spikes (some APs have an undershoot that could trigger a second detection).

### Feature Extraction

For each detected spike, 6 features are extracted:

| Feature | Computation | Diagnostic value |
|---------|-------------|------------------|
| Amplitude | peak - baseline | Signal strength, propagation distance |
| Duration | first to last threshold crossing | AP vs VP discrimination (10 ms vs 10 s) |
| Area | trapezoidal integral | Total charge transfer |
| Rise time | 10% → 90% of peak | APs are fast (~5 ms), VPs slow (~100 ms) |
| Decay τ | exponential fit | APs have short τ (~10 ms), VPs long (~1 s) |
| Asymmetry | rise / (rise + decay) | APs ≈ 0.5 (symmetric), VPs ≈ 0.05 (slow decay) |

### Classification (int8 CNN)

A small 1D-CNN classifies each spike into 3 classes:

```
AP: short duration (10-100 ms), symmetric, fast rise/decay
VP: long duration (1-10 s), asymmetric, slow decay
ART: 60 Hz pickup (periodic), motion artifact (transient), electrode pop (step)
```

The network has ~3,200 int8 parameters (4 KB flash), runs in 0.8 ms on the STM32G474 (170 MHz Cortex-M4F with CMSIS-NN).

---

## Propagation Velocity Measurement

With a single electrode pair, we detect when a signal arrives but cannot measure propagation speed. For velocity measurement:

### Option 1: Two Phyto Pulse devices

Place two devices at known distances along the plant. Compare event timestamps (both share the same session clock via BLE sync). Velocity = Δdistance / Δtime.

### Option 2: Sequential electrodes (future firmware)

If a future version uses a 4-channel ADC (ADS1256 has 8 inputs), place 4 electrodes at 1 cm intervals along the stem. Cross-correlate channels to find propagation delay → velocity.

Typical velocities:
- Venus flytrap: 10–20 cm/s
- Mimosa pudica: 1–10 cm/s
- Arabidopsis: 0.5–2 cm/s
- Tree xylem: 0.1–1 cm/s (VP, hydraulic propagation)

---

## References

1. Volkov, A.G. (Ed.) *Plant Electrophysiology*. Springer, 2012.
2. Fromm, J. & Lautner, S. "Electrical signals and their physiological significance in plants." *Plant, Cell & Environment* 30:249-257, 2007.
3. Favre, P. & Agosti, R.D. "Plant action potentials: a systemic signaling." *Plant Signaling & Behavior* 2:104-106, 2007.
4. Stahlberg, R. & Cosgrove, D.J. "Slow wave potentials in the apoplast of the higher plant." *Planta* 203:192-199, 1997.
5. Markin, V.S., Volkov, A.G., & Chua, L. "Mechanism of variation potential origin in higher plants." *Plant Signaling & Behavior* 8:e24431, 2013.