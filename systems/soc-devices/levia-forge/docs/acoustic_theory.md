# Levia Forge — Acoustic Radiation Force Theory

## Overview

Levia Forge uses acoustic radiation pressure to levitate and manipulate
small objects in mid-air. This document explains the physics behind the
device.

## Acoustic Radiation Pressure

When a sound wave reflects off a surface, it exerts a pressure known as
the acoustic radiation pressure. For a plane standing wave, the
radiation pressure on a small sphere is:

```
P_rad = (4π/3) · a³ · k · E · Φ · sin(2kz)
```

where:
- `a` = sphere radius
- `k` = wavenumber (2π/λ)
- `E` = acoustic energy density
- `Φ` = acoustic contrast factor
- `z` = position along the standing wave axis

## Acoustic Contrast Factor

The contrast factor Φ determines whether an object is attracted to
pressure nodes (minimum pressure) or pressure antinodes (maximum
pressure):

```
Φ = (5ρ_p - 2ρ_0) / (2ρ_p + ρ_0) - (1/3) · (κ_p / κ_0)
```

where:
- `ρ_p`, `ρ_0` = particle and medium density
- `κ_p`, `κ_0` = particle and medium compressibility

For most solid objects in air (ρ_p >> ρ_0), Φ > 0, meaning the object
is attracted to pressure **nodes** (where particle velocity is maximum
but pressure amplitude is zero).

## Phased Array Focusing

Instead of a simple standing wave between two flat transducers, Levia
Forge uses a phased array of 72 transducers. Each transducer emits a
40 kHz wave with a controlled phase delay. The phase for transducer *i*
to focus at point **p** is:

```
φ_i = (2π / λ) · |t_i - p|
```

where **t_i** is the 3D position of transducer *i* and λ = c/f ≈ 8.575 mm
at 343 m/s.

When all 72 waves arrive at **p** in phase, they constructively
interfere, creating a pressure maximum at **p**. Surrounding regions
have lower pressure. The pressure node (trap) forms slightly above or
below the focal point due to the standing wave nature of the opposing
arrays.

## Gor'kov Potential

The radiation force on a small sphere in an arbitrary acoustic field
can be expressed using the Gor'kov potential:

```
U = V · [ (f_0 · |p|²) / (2ρ_0c²) - (f_1 · 3ρ_0|v|²) / 4 ]
```

where:
- `V` = sphere volume
- `p` = acoustic pressure (rms)
- `v` = particle velocity (rms)
- `f_0 = 1 - (ρ_0c²)/(ρ_p c_p²)` — monopole coefficient
- `f_1 = 2(ρ_p - ρ_0)/(2ρ_p + ρ_0)` — dipole coefficient

The force is the gradient of this potential:

```
F = -∇U
```

Objects are trapped at minima of U. For high-density objects (ρ_p >> ρ_0),
both f_0 and f_1 are positive, so the trap is at pressure nodes (|p| = 0)
with high velocity.

## Phase Quantization

Levia Forge quantizes the phase to 256 steps:

```
φ_quantized = round(φ / 2π × 256) mod 256
```

Each step corresponds to 360°/256 ≈ 1.41°. At 40 kHz (λ = 8.575 mm),
the spatial resolution of one phase step is:

```
Δz = λ / 256 ≈ 33.5 µm
```

This is far finer than the trap size (~2-4 mm), so quantization noise
is negligible.

## Transducer Drive

Each transducer is driven with a 10 Vpp square wave at 40 kHz. The
acoustic pressure at the focus is approximately:

```
p_focus ≈ N × p_0 × (d / (2λ × z_f))
```

where:
- N = number of transducers (72)
- p_0 = pressure from single transducer at 10 Vpp (~50 Pa at 10 cm)
- d = transducer diameter (10 mm)
- z_f = focal distance (~35 mm)
- λ = wavelength (8.575 mm)

This gives p_focus ≈ 72 × 50 × (10 / (2 × 8.575 × 35)) ≈ 2,400 Pa.

The radiation force on a 1mm styrofoam bead (ρ = 30 kg/m³) is:

```
F ≈ (π/6) × a³ × k × p² / (ρ_0 × c²) ≈ 0.5 µN
```

Gravity on a 1mm styrofoam bead (mass ~15 µg):

```
F_g = m × g ≈ 0.15 µN
```

The radiation force (0.5 µN) exceeds gravity (0.15 µN), enabling
levitation.

## Vortex Trap

A vortex beam is created by adding an azimuthal phase gradient:

```
φ_i = (2π/λ) × |t_i - p| + ℓ × θ_i
```

where θ_i is the azimuthal angle of transducer *i* relative to the
focal axis, and ℓ is the topological charge. This creates a phase
singularity at the center, producing a hollow pressure field (toroidal
trap) that can rotate particles via angular momentum transfer.

## Twin Trap

The twin trap creates two adjacent focal points, useful for holding two
particles or creating a more stable trap. This is achieved by
alternating the focus between two points for different subsets of
transducers.

## Transport (Conveyor)

By sweeping the focal point along one axis over time, particles can be
transported across the working volume. The transport speed is limited by
the trap stiffness and particle inertia:

```
v_max ≈ (trap_stiffness / particle_mass) × (trap_radius / 2π)
```

For typical parameters, v_max ≈ 50 mm/s.

## References

1. Gor'kov, S.P. "On the forces acting on a small particle in an
   acoustical field in an ideal fluid." Soviet Physics—Doklady, 1962.
2. Marzo, A. et al. "Holographic acoustic elements for manipulation of
   sound fields." Nature Communications, 2015.
3. Marzo, A. and Drinkwater, B.W. "Holographic acoustic tweezers."
   PNAS, 2019.
4. Fushimi, T. et al. "Acoustic levitation: Recent progress and
   applications." Applied Physics Letters, 2021.
5. Foresti, D. et al. "Acoustic levitation at the nanoscale."
   Advanced Materials, 2022.