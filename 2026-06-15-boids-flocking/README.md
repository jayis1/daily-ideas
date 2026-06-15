# 🐦 Boids Flocking Simulator

A real-time terminal simulation of Craig Reynolds' classic **Boids algorithm** — watch emergent flocking behavior arise from just three simple rules: **separation**, **alignment**, and **cohesion**.

## Description

This simulator brings the famous 1986 boids algorithm to your terminal with full interactive controls. Flocks of ASCII birds (represented by characters like `o`, `>`, `^`, `·`) navigate the screen, avoiding obstacles, fleeing from predators, and forming beautiful emergent patterns — all from decentralized local rules with no global coordination.

The project implements:
- **Separation** — steer to avoid crowding nearby flockmates
- **Alignment** — steer towards the average heading of nearby flockmates  
- **Cohesion** — steer towards the average position of nearby flockmates
- **Predator avoidance** — boids flee from predator entities (added dynamically)
- **Obstacle avoidance** — boids steer around circular obstacles
- **Edge wrapping** — boids that leave one side reappear on the opposite side

## Features

- 🎮 **Real-time interactive simulation** running at ~30 FPS in any terminal
- 🐦 **Emergent flocking behavior** from three simple rules
- 🦅 **Predators** that chase and eat boids (press `P` to add)
- 🧱 **Obstacles** that boids navigate around (press `O` to add)
- 🎯 **Three preset behaviors**: tight flocking, loose swarm, balanced (keys `1`, `2`, `3`)
- 📊 **Tunable parameters** — adjust separation/alignment/cohesion weights live
- 🌊 **Trail visualization** — toggle trails to see flight paths (press `T`)
- 🧭 **Direction arrows** — show velocity direction vectors (press `V`)
- 🔍 **Debug mode** — inspect first boid's position and velocity (press `D`)
- ⏸️ **Pause/resume** with spacebar
- 🔄 **Reset simulation** with `R`
- 🎨 **Color-coded boids** in cyan, green, yellow, and magenta

## Installation

```bash
# No external dependencies needed — uses only Python standard library (curses)
# Just clone and run!

git clone https://github.com/yourusername/daily-ideas.git
cd daily-ideas/2026-06-15-boids-flocking
```

**Requirements:**
- Python 3.7+
- A terminal with color support (most modern terminals work)
- `curses` library (included with Python on Linux/macOS; on Windows, install `windows-curses`)

## How to Run

```bash
# Run with default settings (50 boids)
python3 boids.py

# Custom number of boids
python3 boids.py --boids 100

# Start with predators
python3 boids.py --predators 2

# Start with obstacles
python3 boids.py --obstacles 5

# Full chaos mode
python3 boids.py --boids 150 --predators 3 --obstacles 8

# See all options
python3 boids.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume simulation |
| `T` | Toggle trail visualization |
| `D` | Toggle debug info (first boid's pos/vel) |
| `V` | Toggle velocity direction arrows |
| `P` | Add a predator at random position |
| `O` | Add an obstacle at random position |
| `B` | Add 10 more boids |
| `+` / `-` | Increase / Decrease separation weight |
| `1` | Preset: **Tight flocking** (low sep, high ali/coh) |
| `2` | Preset: **Loose swarm** (high sep, low ali/coh) |
| `3` | Preset: **Balanced** (default weights) |
| `R` | Reset simulation |
| `Q` | Quit |

## Usage Examples

### Watch natural flocking emerge
```bash
python3 boids.py --boids 80
```
Start with 80 boids and watch them naturally organize into flocks.

### Predator-prey dynamics
```bash
python3 boids.py --boids 60 --predators 2
```
Two predators chase the flock. Boids scatter and regroup as predators pick off stragglers. The flock count decreases as boids get eaten!

### Obstacle course navigation
```bash
python3 boids.py --boids 70 --obstacles 5
```
Boids flow around obstacles like a fluid, creating beautiful streaming patterns.

### Full interactive playground
```bash
python3 boids.py --boids 100
```
Then press `P` to drop in predators, `O` for obstacles, `V` for arrows, `T` for trails — experiment with the behavior presets using `1`, `2`, `3`.

## How It Works

The simulation implements Craig Reynolds' 1986 Boids model using three behavioral rules applied to each boid at every timestep:

1. **Separation**: Each boid steers away from nearby flockmates within a close radius (default 6 units), weighted by inverse distance — the closer the neighbor, the stronger the repulsion.

2. **Alignment**: Each boid steers towards the average velocity of flockmates within a medium radius (default 15 units), matching the flock's general direction.

3. **Cohesion**: Each boid steers towards the center of mass of flockmates within a larger radius (default 20 units), keeping the flock together.

Additional forces:
- **Predator flee**: When a predator is within hunt range, boids experience a strong repulsive force proportional to inverse distance.
- **Obstacle avoidance**: Near circular obstacles, boids receive a steering force away from the obstacle center.

All forces are combined as weighted vectors and the resulting velocity is clamped to a maximum speed. Reynolds-style **steering** (desired velocity minus current velocity, limited by max force) ensures smooth, naturalistic turns.

## Running Tests

```bash
python3 -m pytest test_boids.py -v
```

36 tests covering Vec2 math, boid physics, all flocking rules, predator/obstacle interactions, edge wrapping, and stability under extended simulation runs.