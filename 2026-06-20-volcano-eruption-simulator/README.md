# 🌋 Volcano Eruption Simulator

A terminal-based ASCII simulation of a volcanic eruption with procedurally generated terrain, lava fountains, flowing lava, pyroclastic flows, ash clouds, seismic activity, a day/night cycle, and four eruption types — all rendered in colorful ANSI 256-color art.

![Phase: ERUPTING](https://img.shields.io/badge/phase-ERUPTING-red) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![Version](https://img.shields.io/badge/version-2.0.0-orange)

## Features

### Core Simulation
- **Procedural Mountain Terrain** — Each run generates a unique volcano shape with rolling foothills and a distinct crater, smoothed for natural appearance
- **4 Eruption Phases** — Dormant → Building → Erupting → Subsiding, each with distinct visual behavior and smooth transitions
- **Lava Fountains & Bombs** — Particles launched from the crater with realistic gravity and spread, depositing on terrain as persistent lava flows
- **Flowing Lava** — Lava deposits spread downhill along terrain contours, cooling from bright red → orange → dark over time
- **Ash Plumes & Smoke** — Thick columns of ash and wispy smoke rise from the crater; plinian eruptions produce wider, taller columns
- **Sparks & Embers** — Bright sparks fly from eruptions with trail effects
- **Pyroclastic Flows** — Fast-moving currents of hot gas and rock that rush down the mountainside (higher chance in Vulcanian and Plinian eruptions)
- **Seismic Tremors** — Screen shakes proportional to eruption intensity and type
- **Day/Night Cycle** — Smooth transitions between daylight and starry night skies; lava glows brighter at night with ambient illumination
- **Crater Glow** — The volcanic vent glows red/orange during active eruptions
- **Real-Time Stats Panel** — Shows eruption phase, type, VEI, intensity bar, seismic activity, particle count, lava flow count, and more
- **Auto-Eruption** — Volcanoes erupt on their own schedule if you just watch (can be disabled)

### Eruption Types
- **🌋 Hawaiian** — Gentle lava fountains, fluid lava flows (VEI 0-2)
- **💥 Strombolian** — Moderate explosions, incandescent bombs (VEI 1-4)
- **💨 Vulcanian** — Violent ash eruptions, dense plumes (VEI 2-5)
- **☁️ Plinian** — Catastrophic column, massive ash plume, pyroclastic flows (VEI 3-8)

### VEI Tracking
The Volcanic Explosivity Index (VEI, scale 0-8) is tracked in real time, reflecting eruption intensity and type. Max VEI encountered is displayed in the stats panel.

### New in v2.0
- **4 eruption types** (Hawaiian, Strombolian, Vulcanian, Plinian) with different behaviors
- **Pyroclastic flows** that rush down the mountainside
- **VEI (Volcanic Explosivity Index)** tracking and display
- **Smooth day/night transitions** instead of abrupt switching
- **Screenshot save** (`s` key) — saves a plain-text snapshot of the current scene
- **CLI flags** — `--version`, `--help`, `--seed`, `--intensity`, `--type`, `--fps`, `--no-auto-erupt`, `--night`, `--width`, `--height`
- **Terrain smoothing** for more natural-looking mountains
- **Comprehensive test suite** (46 tests)

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
# Basic usage
python3 volcano.py

# Start with a specific eruption type
python3 volcano.py --type plinian

# Start with night mode and high intensity
python3 volcano.py --night --intensity 0.9

# Reproducible terrain with seed
python3 volcano.py --seed 12345

# Disable auto-eruptions (manual control only)
python3 volcano.py --no-auto-erupt

# Custom frame rate
python3 volcano.py --fps 30

# Show version
python3 volcano.py --version

# Show help
python3 volcano.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Trigger a new eruption |
| `+` / `=` | Increase eruption intensity |
| `-` | Decrease eruption intensity |
| `t` | Cycle eruption type (Hawaiian → Strombolian → Vulcanian → Plinian) |
| `r` | Regenerate terrain (new mountain) |
| `d` | Toggle day/night manually |
| `s` | Save screenshot to text file |
| `q` | Quit |

## Usage Examples

**Watch a dormant volcano with gentle smoke:**
```bash
python3 volcano.py
# Just watch — smoke will gently rise from the crater
```

**Trigger a massive Plinian eruption:**
```bash
python3 volcano.py --type plinian
# Press SPACE to trigger the catastrophic eruption
# Watch for pyroclastic flows rushing down the slopes
```

**Night mode eruption (spectacular glow effects):**
```bash
python3 volcano.py --night
# Press SPACE to erupt — lava illuminates surrounding terrain with ambient glow
# Stars twinkle in the background
```

**Reproducible demo with manual control:**
```bash
python3 volcano.py --seed 42 --no-auto-erupt
# Predictable terrain, eruptions only when you press SPACE
```

**Gentle Hawaiian lava fountains:**
```bash
python3 volcano.py --type hawaiian --intensity 0.4
# Fluid, peaceful lava flows
```

## How It Works

- **Terrain Generation**: A procedural cone shape with sinusoidal noise creates a natural-looking mountain. The crater is carved as an indentation at the peak. Two smoothing passes reduce jagged edges.
- **Eruption Types**: Each type (Hawaiian, Strombolian, Vulcanian, Plinian) defines different particle rates, ash rates, lava flow rates, pyroclastic flow chances, and shake multipliers, producing distinct visual behaviors.
- **Particle System**: Each frame spawns particles (lava bombs, ash, smoke, sparks) based on eruption intensity and type. Particles follow ballistic trajectories with gravity and wind.
- **Lava Flows**: When lava particles hit the terrain surface, they deposit as persistent lava flow cells that slowly spread downhill and cool over time (changing from bright red → orange → dark).
- **Pyroclastic Flows**: During Vulcanian and Plinian eruptions, fast-moving pyroclastic flows can spawn and rush down the mountainside, expanding as they go.
- **Eruption State Machine**: A 4-phase state machine controls the overall eruption behavior with smooth transitions between dormant and active states.
- **VEI Tracking**: The Volcanic Explosivity Index is dynamically calculated based on eruption intensity and type, with real-time display and max VEI tracking.
- **Seismic Activity**: Shake intensity is derived from eruption phase, intensity, and type, creating screen tremors during eruptions.
- **Day/Night Rendering**: Smooth transitions between day and night; stars are procedurally placed in the night sky; lava emits ambient glow to nearby cells during nighttime.
- **Screenshot Save**: Press `s` to save the current scene as a plain-text file (ANSI codes stripped) with timestamp.

## Running Tests

```bash
python3 test_volcano.py
```

The test suite includes 46 tests covering:
- Particle and PyroclasticFlow creation and behavior
- VolcanoSimulator initialization, terrain generation, eruption state machine
- All eruption types and their configurations
- VEI tracking, intensity clamping, state transitions
- Rendering, stats display, screenshot saving
- ANSI helper functions
- Eruption type parameter validation