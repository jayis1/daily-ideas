# 🌌 N-Body Gravity Simulator

A real-time terminal-based gravitational N-body simulation. Spawn celestial bodies, watch orbits form, witness collisions and mergers, and observe chaotic gravitational dynamics — all in your terminal with colored trails and mass-coded glyphs.

## Features

### Core Simulation
- **Newtonian Gravity**: Every body attracts every other body with `F = G·m₁·m₂/r²`
- **Softening Parameter**: Prevents infinite forces at zero distance (`ε = 0.5`) for numerical stability
- **Symplectic Euler Integration**: Better energy conservation than naive Euler
- **Collision & Merging**: Bodies that get too close merge with conservation of momentum and mass
- **Sub-stepping**: At high speed, the simulation takes multiple smaller steps per frame for stability

### Interactive Controls
- **Click to Spawn**: Left-click to place a body; drag to set its initial velocity
- **Right-Click for Stars**: Right-click and drag to spawn massive stellar objects
- **Preset Scenes**: Press `1` for solar system, `2` for binary star, `3` for figure-8 three-body
- **Delete Nearest**: Press `D` to remove the body closest to the cursor
- **Pause/Resume**: `SPACE` to toggle simulation
- **Speed Control**: `+`/`-` to speed up or slow down (0.1x to 20x)
- **Toggle Trails/Grid/Energy/Help**: `T`, `G`, `E`, `H`
- **Follow Center of Mass**: Press `F` to track the system's center of mass
- **Reset/Clear**: `R` to reset, `C` to clear all bodies

### Visualization
- **Color-Coded Trails**: Each body leaves a fading trail in a unique color
- **Mass Visualization**: Body characters scale with mass — from `·` (dust) to `★` (supergiant)
- **Glow Effect**: Massive bodies (≥50 mass) show a surrounding glow
- **Energy Display**: Shows kinetic, potential, and total energy (toggle with `E`)
- **Center-of-Mass Tracking**: Press `F` to follow the center of mass with a `+` marker
- **Default Scene**: Starts with a central star and 5 orbiting planets

### CLI Flags
- `--help` — Show usage information and controls
- `--version` — Print version number
- `--scene {solar,binary,figure8,cluster}` — Choose starting scene

## How to Install

Requires Python 3.8+ with `curses` (included on macOS/Linux by default).

```bash
# No external dependencies needed — just clone and run
cd ~/daily-ideas/2026-06-16-nbody-gravity-simulator
```

On some minimal Linux installs, you may need:
```bash
pip install windows-curses   # Windows only
# Linux/macOS: curses is built-in
```

## How to Run

```bash
# Default solar system scene
python3 nbody_sim.py

# Start with a binary star system
python3 nbody_sim.py --scene binary

# Start with the figure-8 three-body problem
python3 nbody_sim.py --scene figure8

# Start with a random cluster (chaotic collapse)
python3 nbody_sim.py --scene cluster

# Show version
python3 nbody_sim.py --version

# Show help
python3 nbody_sim.py --help
```

## Controls

| Key / Input        | Action                              |
|--------------------|-------------------------------------|
| **Left Click**     | Spawn a body (drag to set velocity) |
| **Right Click**    | Spawn a massive star (drag→vel)     |
| **1**              | Solar system scene                  |
| **2**              | Binary star scene                   |
| **3**              | Figure-8 three-body scene          |
| **SPACE**          | Pause / Resume simulation           |
| **T**              | Toggle trail rendering              |
| **G**              | Toggle background grid              |
| **F**              | Follow center of mass               |
| **D**              | Delete nearest body to cursor       |
| **E**              | Toggle energy display               |
| **+** / **=**      | Speed up simulation (up to 20x)     |
| **-**              | Slow down simulation (down to 0.1x) |
| **R**              | Reset to default solar system scene |
| **C**              | Clear all bodies                    |
| **H**              | Toggle help overlay                 |
| **Q** / **ESC**    | Quit                                |

## Usage Examples

### Default Solar System
Just run the simulator — it starts with a central star and 5 planets in stable orbits. Watch them revolve, precess, and occasionally interact.

### Binary Star System
```bash
python3 nbody_sim.py --scene binary
```
Two massive stars orbit each other with planets swirling around them in chaotic paths.

### Figure-8 Three-Body Problem
```bash
python3 nbody_sim.py --scene figure8
```
The famous periodic solution where three equal-mass bodies trace a figure-8 path. Watch it slowly drift due to numerical approximation.

### Create a Binary Star System Manually
1. Press **C** to clear the scene
2. Right-click at center-left to place a star with no velocity
3. Right-click at center-right for another star
4. Now left-click-drag to launch small planets and watch their chaotic orbits!

### Three-Body Chaos
1. Press **C** to clear
2. Left-click three bodies of similar mass in a triangle, dragging each to give tangential velocity
3. Enjoy the unpredictable dance of the three-body problem

### Collision Cascade
1. Start with the default scene
2. Press **+** to speed up the simulation
3. Right-click a massive star near the system to perturb orbits
4. Watch collisions and mergers cascade through the system

### Track Center of Mass
1. Press **F** to enable center-of-mass tracking
2. The camera will follow the system's center of gravity as bodies fly around
3. Great for watching bodies that drift off-screen

## Physics Details

- **Gravity**: `F = G·m₁·m₂ / (r² + ε²)` with softening parameter `ε = 0.5` to avoid singularities
- **Integration**: Symplectic Euler (velocity then position update) for better energy conservation
- **Sub-stepping**: At higher speed multipliers, the simulation takes `⌊speed_mult⌋` sub-steps per frame with proportionally smaller `dt`, keeping physics stable
- **Collisions**: Bodies within `0.8` units (scaled by display radius) merge with conservation of total momentum and mass
- **Energy**: Kinetic energy `KE = 0.5·m·v²` and potential energy `PE = -G·m₁·m₂/r` are computed and displayed
- **Max Bodies**: Capped at 80 for performance; N-body gravity is O(n²)

## What It Does

The simulator models gravitational interactions between point masses in 2D. Each frame:

1. Computes pairwise gravitational forces between all bodies
2. Updates velocities based on accelerations
3. Updates positions based on velocities
4. Checks for collisions and merges overlapping bodies
5. Updates center-of-mass tracking if enabled
6. Renders bodies as mass-scaled Unicode characters with colored trails

The result is a rich, emergent simulation where you can observe orbital mechanics, gravitational slingshots, tidal capture, collision cascades, and the inherent chaos of multi-body gravitational systems.

## Running Tests

```bash
python3 -m pytest test_nbody_sim.py -v
```

The test suite covers body creation, simulation stepping, orbit stability, collision merging, momentum conservation, energy computation, center-of-mass tracking, edge cases (zero-mass bodies, overlapping bodies, trail limits), and more.