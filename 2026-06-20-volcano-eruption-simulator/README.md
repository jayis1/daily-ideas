# 🌋 Volcano Eruption Simulator

A terminal-based ASCII simulation of a volcanic eruption with procedurally generated terrain, lava fountains, flowing lava, pyroclastic flows, ash clouds, seismic tremors, a day/night cycle, and four eruption types — all rendered in colorful ANSI 256-color art.

![Phase: ERUPTING](https://img.shields.io/badge/phase-ERUPTING-red) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![Version](https://img.shields.io/badge/version-2.1.0-orange)

## Features

### Core Simulation
- **Procedural Mountain Terrain** — Each run generates a unique volcano shape with rolling foothills and a distinct crater, smoothed for natural appearance
- **4 Eruption Phases** — Dormant → Building → Erupting → Subsiding, each with distinct visual behavior and smooth transitions
- **Lava Fountains & Bombs** — Particles launched from the crater with realistic gravity and spread, depositing on terrain as persistent lava flows
- **Flowing Lava** — Lava deposits spread downhill along terrain contours, cooling from bright red → orange → dark over time
- **Ash Plumes & Smoke** — Thick columns of ash and wispy smoke rise from the crater; Plinian eruptions produce wider, taller columns
- **Sparks & Embers** — Bright sparks fly from eruptions with trail effects
- **Pyroclastic Flows** — Fast-moving currents of hot gas and rock that rush down the mountainside (higher chance in Vulcanian and Plinian eruptions)
- **Seismic Tremors** — Screen shakes proportional to eruption intensity and type, now properly rendered with buffer offset
- **Day/Night Cycle** — Smooth color blending between daylight and starry night skies; lava glows brighter at night with ambient illumination
- **Crater Glow** — The volcanic vent glows red/orange during active eruptions
- **Real-Time Stats Panel** — Shows eruption phase, type, VEI, intensity bar, seismic activity, particle count, lava flow count, and more (adapts to terminal width)
- **Auto-Eruption** — Volcanoes erupt on their own schedule if you just watch (can be disabled)

### Eruption Types
- **🌋 Hawaiian** — Gentle lava fountains, fluid lava flows (VEI 0–2)
- **💥 Strombolian** — Moderate explosions, incandescent bombs (VEI 1–4)
- **💨 Vulcanian** — Violent ash eruptions, dense plumes (VEI 2–5)
- **☁️ Plinian** — Catastrophic column, massive ash plume, pyroclastic flows (VEI 3–8)

### VEI Tracking
The Volcanic Explosivity Index (VEI, scale 0–8) is tracked in real time, reflecting eruption intensity and type. Max VEI encountered is displayed in the stats panel.

## How to Install

No external dependencies required — uses only Python standard library.

```bash
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

- **Terrain Generation**: A procedural cone shape with sinusoidal noise creates a natural-looking mountain. The crater is carved as an indentation at the peak. Two smoothing passes reduce jagged edges. Mountain characters are deterministic (based on position) to prevent visual flicker.
- **Eruption Types**: Each type (Hawaiian, Strombolian, Vulcanian, Plinian) defines different particle rates, ash rates, lava flow rates, pyroclastic flow chances, and shake multipliers, producing distinct visual behaviors.
- **Particle System**: Each frame spawns particles (lava bombs, ash, smoke, sparks) based on eruption intensity and type. Particles follow ballistic trajectories with gravity and wind.
- **Lava Flows**: When lava particles hit the terrain surface, they deposit as persistent lava flow cells that slowly spread downhill and cool over time (changing from bright red → orange → dark). Capped at 500 cells for performance.
- **Pyroclastic Flows**: During Vulcanian and Plinian eruptions, fast-moving pyroclastic flows can spawn and rush down the mountainside, expanding as they go.
- **Eruption State Machine**: A 4-phase state machine controls the overall eruption behavior with smooth transitions between dormant and active states. Very low intensity triggers (< 0.05) result in a brief seismic rumble that quickly subsides.
- **VEI Tracking**: The Volcanic Explosivity Index is dynamically calculated based on eruption intensity and type, with real-time display and max VEI tracking.
- **Seismic Activity & Shake**: Shake intensity is derived from eruption phase, intensity, and type. The shake offset is applied to the entire frame buffer, shifting all rendered content to simulate earthquake tremors.
- **Day/Night Rendering**: Sky color smoothly interpolates between day and night values based on the `day_transition` variable. Mountain and interior colors also blend between day and night palettes. Stars are rendered using a deterministic local random instance (no global seed pollution).
- **Screenshot Save**: Press `s` to save the current scene as a plain-text file (ANSI codes stripped) with timestamp.

## Running Tests

```bash
python3 test_volcano.py
```

The test suite includes 51 tests covering:
- Particle and PyroclasticFlow creation and behavior
- VolcanoSimulator initialization, terrain generation, eruption state machine
- All eruption types and their configurations
- VEI tracking, intensity clamping, state transitions
- Rendering, stats display, screenshot saving
- ANSI helper functions
- Eruption type parameter validation
- Zero-intensity eruption handling (no full eruption from intensity 0)
- Shake effect rendering
- Smooth day/night color blending
- Stats line width adaptation

## Changelog

### v2.1.0 — Bug Fix Release

**Fixed bugs:**
1. **Earthquake shake now renders** — `shake_x`/`shake_y` were computed every frame but never applied to the render output. The entire frame buffer is now shifted by the shake offset to create visible screen tremors during eruptions.
2. **Mountain terrain no longer flickers** — Mountain face characters used `random.choice()` each frame, causing a distracting flicker effect. Now uses deterministic characters based on grid position `(x + y * 7) % 2`.
3. **Smooth day/night color blending** — Sky color previously used a binary threshold (`day_transition > 0.5`) switching abruptly between day and night colors. Now smoothly interpolates between night (16) and day (195) ANSI colors based on `day_transition`. Mountain and terrain colors also blend smoothly.
4. **Display clears stale content** — `display()` previously used only `\033[H` (cursor home) without clearing, causing old frame content to persist. Now uses `\033[H\033[J` to clear from cursor to end of screen.
5. **Zero-intensity eruptions handled correctly** — `trigger_eruption(0.0)` previously led to a full eruption because the building phase threshold was `target * 0.6 = 0.0`, causing an immediate transition to "erupting" phase with minimum intensity 0.3. Now intensities below 0.05 go directly to "subsiding" phase, producing only a brief seismic rumble. The building phase also has a minimum threshold of 0.05.
6. **Stats panel adapts to terminal width** — Stats bars and controls line were fixed-width (80–95 chars), overflowing on narrow terminals. Bar lengths now scale with terminal width, and a compact controls line is used below 70 columns.
7. **Night star rendering no longer pollutes global random seed** — Previously used `random.seed()` to reset the global seed after rendering stars, which could cause nondeterministic behavior. Now uses a local `random.Random()` instance for star placement.

### v2.0.0 — Initial Enhanced Release

- 4 eruption types (Hawaiian, Strombolian, Vulcanian, Plinian)
- Pyroclastic flows
- VEI tracking and display
- Smooth day/night transitions
- Screenshot save capability
- CLI flags (`--version`, `--help`, `--seed`, `--intensity`, `--type`, `--fps`, `--no-auto-erupt`, `--night`, `--width`, `--height`)
- Terrain smoothing
- Comprehensive test suite (46 tests)