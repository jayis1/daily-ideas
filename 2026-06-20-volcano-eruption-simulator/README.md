# 🌋 Volcano Eruption Simulator

A terminal-based ASCII simulation of a volcanic eruption with procedurally generated terrain, lava fountains, flowing lava, ash clouds, seismic activity, and a day/night cycle — all rendered in colorful ANSI art.

![Volcano Erupting](https://img.shields.io/badge/phase-ERUPTING-red) ![Python](https://img.shields.io/badge/python-3.8+-blue)

## Features

- **Procedural Mountain Terrain** — Each run generates a unique volcano shape with rolling foothills and a distinct crater
- **4 Eruption Phases** — Dormant → Building → Erupting → Subsiding, each with distinct visual behavior
- **Lava Fountains & Bombs** — Particles launched from the crater with realistic gravity and spread
- **Flowing Lava** — Lava deposits on the terrain and slowly spreads downhill, cooling over time
- **Ash Plumes & Smoke** — Thick columns of ash and wispy smoke rise from the crater
- **Sparks & Embers** — Bright sparks fly from eruptions with trail effects
- **Seismic Tremors** — Screen shakes proportional to eruption intensity
- **Day/Night Cycle** — Automatic toggling between daylight and starry night skies; lava glows brighter at night
- **Crater Glow** — The volcanic vent glows red/orange during active eruptions
- **Real-Time Stats Panel** — Shows eruption phase, intensity bar, seismic activity, particle count, and more
- **Auto-Eruption** — Volcanoes erupt on their own schedule if you just watch!

## How to Install

No external dependencies required — uses only Python standard library.

```bash
# Clone or download the project
cd ~/daily-ideas/2026-06-20-volcano-eruption-simulator

# Make executable (optional)
chmod +x volcano.py
```

Requires Python 3.8+ and a terminal that supports ANSI 256-color codes (most modern terminals do).

## How to Run

```bash
python3 volcano.py
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Trigger a new eruption |
| `+` / `=` | Increase eruption intensity |
| `-` | Decrease eruption intensity |
| `r` | Regenerate terrain (new mountain) |
| `d` | Toggle day/night manually |
| `q` | Quit |

## Usage Examples

**Watch a dormant volcano with gentle smoke:**
```bash
python3 volcano.py
# Just watch — smoke will gently rise from the crater
```

**Trigger a massive eruption:**
```bash
# Press SPACE multiple times for cascading eruptions
# Press + to crank up the intensity
```

**Night mode eruption (spectacular glow effects):**
```bash
# Press 'd' to toggle to night, then SPACE to erupt
# Lava illuminates surrounding terrain with ambient glow
```

## How It Works

- **Terrain Generation**: A procedural cone shape with sinusoidal noise creates a natural-looking mountain. The crater is carved as an indentation at the peak.
- **Particle System**: Each frame spawns particles (lava bombs, ash, smoke, sparks) based on eruption intensity. Particles follow ballistic trajectories with gravity.
- **Lava Flows**: When lava particles hit the terrain surface, they deposit as persistent lava flow cells that slowly spread downhill and cool over time (changing from bright red → orange → dark).
- **Eruption State Machine**: A 4-phase state machine controls the overall eruption behavior with smooth transitions between dormant and active states.
- **Seismic Activity**: Shake intensity is derived from eruption phase and intensity, creating screen tremors during eruptions.
- **Day/Night Rendering**: Stars are procedurally placed in the night sky; lava emits ambient glow to nearby cells during nighttime.

## What It Does

The simulator creates a living, breathing volcano scene in your terminal. In its dormant state, gentle wisps of smoke drift from the crater. Periodically (or on command), the volcano erupts — hurling lava bombs into the sky, spewing ash clouds, raining sparks, and sending rivers of lava cascading down its slopes. The ground shakes. The stats panel tracks every phase transition, seismic reading, and lava deposit. At night, the eruption creates a dramatic light show against a star-filled sky.