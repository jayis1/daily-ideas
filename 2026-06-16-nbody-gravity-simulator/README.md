# 🌌 N-Body Gravity Simulator

A real-time terminal-based gravitational N-body simulation. Spawn celestial bodies, watch orbits form, witness collisions and mergers, and observe chaotic gravitational dynamics — all in your terminal with colored trails and mass-coded glyphs.

![Terminal-based gravity simulation]

## Features

- **Newtonian Gravity**: Every body attracts every other body with `F = G·m₁·m₂/r²`
- **Click to Spawn**: Left-click to place a body; drag to set its initial velocity
- **Right-Click for Stars**: Right-click and drag to spawn massive stellar objects
- **Collision & Merging**: Bodies that get too close merge (conservation of momentum)
- **Color-Coded Trails**: Each body leaves a fading trail in a unique color
- **Mass Visualization**: Body characters scale with mass — from `·` (dust) to `★` (supergiant)
- **Glow Effect**: Massive bodies (≥50 mass) show a surrounding glow
- **Default Scene**: Starts with a central star and 5 orbiting planets
- **Full HUD**: Live body count, total mass, collision counter, speed, frame number
- **Interactive Controls**: Pause, speed up/slow down, toggle trails/grid, help overlay

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
python3 nbody_sim.py
```

## Controls

| Key / Input        | Action                              |
|--------------------|-------------------------------------|
| **Left Click**     | Spawn a body (drag to set velocity) |
| **Right Click**    | Spawn a massive star (drag→vel)     |
| **SPACE**          | Pause / Resume simulation           |
| **T**              | Toggle trail rendering              |
| **G**              | Toggle background grid               |
| **+** / **=**      | Speed up simulation (up to 20x)     |
| **-**              | Slow down simulation (down to 0.1x) |
| **R**              | Reset to default solar system scene  |
| **C**              | Clear all bodies                    |
| **H**              | Toggle help overlay                 |
| **Q** / **ESC**    | Quit                                |

## Usage Examples

### Default Solar System
Just run the simulator — it starts with a central star and 5 planets in stable orbits. Watch them revolve, precess, and occasionally interact.

### Create a Binary Star System
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

## Physics Details

- **Gravity**: `F = G·m₁·m₂ / (r² + ε²)` with softening parameter `ε = 0.5` to avoid singularities
- **Integration**: Symplectic Euler (velocity then position update) for better energy conservation
- **Collisions**: Bodies within `0.8` units (scaled by display radius) merge with conservation of total momentum and mass
- **Softening**: Prevents infinite forces at zero distance, keeping the simulation stable
- **Max Bodies**: Capped at 80 for performance; N-body gravity is O(n²)

## What It Does

The simulator models gravitational interactions between point masses in 2D. Each frame:

1. Computes pairwise gravitational forces between all bodies
2. Updates velocities based on accelerations
3. Updates positions based on velocities
4. Checks for collisions and merges overlapping bodies
5. Renders bodies as mass-scaled Unicode characters with colored trails

The result is a rich, emergent simulation where you can observe orbital mechanics, gravitational slingshots, tidal capture, collision cascades, and the inherent chaos of multi-body gravitational systems.