# 🌍 ASCII Ecosystem Simulator

A terminal-based ecosystem simulation that models the dynamics of a living world — plants grow and spread, herbivores graze and flee, predators hunt and reproduce. Watch population cycles, seasonal changes, water terrain, and random environmental events unfold in real-time through an ASCII art world and live population graph.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Terminal](https://img.shields.io/badge/interface-curses-green) ![Tests](https://img.shields.io/badge/tests-49%20passing-brightgreen) ![License](https://img.shields.io/badge/license-MIT-brightgreen)

## Features

- **Three-species food chain**: Plants → Herbivores → Predators, each with unique AI behaviors
- **Water terrain**: Impassable water cells (`~`) that creatures must navigate around, adding strategic depth
- **Seasonal cycle**: Spring/Summer/Autumn/Winter affects plant growth, energy drain, and survival
- **Environmental events**: Random droughts, plagues, bounties, storms, and floods shake up the ecosystem
- **Follow mode**: Press `f` to track a specific creature and watch its stats in real-time
- **Trigger events**: Press `e` to manually trigger a random environmental event
- **Live population graph**: ASCII bar graph tracks species populations over time
- **Average energy display**: Shows mean energy levels for herbivores and predators
- **Population caps**: Prevents runaway population explosions for all species
- **Ecosystem self-stabilization**: Extinct species can "migrate" back, preventing total collapse
- **Headless mode**: Run simulations without the terminal UI and output CSV or JSON data
- **Configurable**: Customize world size, initial populations, water ratio, seed, and more via CLI flags
- **Reproducible simulations**: Set `--seed` for deterministic behavior
- **Interactive controls**: Spawn creatures, pause, adjust speed, reset the simulation

## How It Works

### Species Behavior

| Species | Symbol | Behavior |
|---------|--------|----------|
| **Plant** | `♣` / `♠` | Grows over time (maturity stages: `·` → `∘` → `♣` → `♠`), spreads to adjacent land cells, affected by seasons |
| **Herbivore** | `◙` | Seeks nearby plants to eat, flees from predators, reproduces when well-fed, loses energy over time |
| **Predator** | `♦` | Hunts herbivores within vision range, wanders when no prey, reproduces when energy is high, has a hunt cooldown |

### Seasonal Effects

| Season | Effect |
|--------|--------|
| **Spring** | Plants spread 2× faster, nutrition boosted |
| **Summer** | Herbivores recover energy slightly, normal plant growth |
| **Autumn** | Plant spread reduced, some plants die off |
| **Winter** | All creatures lose extra energy, plants die more often |

### Environmental Events

| Event | Effect |
|-------|--------|
| **Drought** | Kills ~30% of plants |
| **Plague** | Kills ~20% of herbivores and predators |
| **Bounty** | Spawns 30 new mature plants |
| **Storm** | Randomly scatters all creatures across the map |
| **Flood** | Adds temporary water cells to the map |

### Water Terrain

~5% of the map is covered with water cells (displayed as `~`). Creatures cannot walk through water — they must navigate around it. This creates natural barriers and corridors that influence movement patterns and territory boundaries.

## Installation

Requires Python 3.8+ with standard library only (uses `curses` for interactive mode, which is built-in on Linux/macOS).

```bash
# Clone the repository
git clone https://github.com/yourusername/daily-ideas.git
cd daily-ideas/2026-06-15-ecosystem-simulator

# No dependencies needed — just run it!
```

## How to Run

### Interactive Mode (default)

```bash
python3 ecosystem.py
```

> **Note**: Requires a terminal that supports curses and at least 80×55 character size. Most Linux/macOS terminals work out of the box.

### Headless Mode

Run a simulation for a set number of ticks and output population data as CSV or JSON — perfect for analysis and scripting:

```bash
# Run 500 ticks, output CSV
python3 ecosystem.py --headless 500

# Run 1000 ticks, output JSON
python3 ecosystem.py --headless 1000 --format json

# Reproducible simulation with a seed
python3 ecosystem.py --headless 200 --seed 42

# Custom world size and populations
python3 ecosystem.py --headless 300 --width 100 --height 50 --plants 100 --herbivores 40 --predators 15
```

### CLI Options

```
usage: ecosystem [-h] [--version] [--headless TICKS] [--format {csv,json}]
                [--seed SEED] [--width WIDTH] [--height HEIGHT]
                [--plants PLANTS] [--herbivores HERBIVORES]
                [--predators PREDATORS] [--water WATER] [--speed SPEED]

options:
  --version              Show version number and exit
  --headless TICKS       Run in headless mode for TICKS ticks and output data
  --format {csv,json}    Output format for headless mode (default: csv)
  --seed SEED            Random seed for reproducible simulations
  --width WIDTH          World width in cells (default: 80)
  --height HEIGHT        World height in cells (default: 40)
  --plants PLANTS        Initial number of plants (default: 60)
  --herbivores HERBIVORES  Initial number of herbivores (default: 25)
  --predators PREDATORS  Initial number of predators (default: 8)
  --water WATER          Fraction of map that is water (default: 0.05)
  --speed SPEED          Initial simulation speed 1-5 (default: 1)
```

## Interactive Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `+` / `=` | Increase speed |
| `-` | Decrease speed |
| `p` | Spawn 10 new plants |
| `h` | Spawn 1 new herbivore |
| `d` | Spawn 1 new predator |
| `f` | Follow mode: cycle through herbivore → predator → off |
| `e` | Trigger a random environmental event |
| `r` / `R` | Reset simulation |
| `q` / `Q` | Quit |

## Usage Examples

### Watch nature take its course
```bash
python3 ecosystem.py
# Sit back and watch populations rise and fall
```

### Speed up the simulation
```bash
python3 ecosystem.py --speed 3
# Or press '+' multiple times to speed up inside the simulator
```

### Create a predator invasion
```bash
# Launch, then press 'd' several times to add predators
# Watch the herbivore population crash, followed by predator starvation
# Then watch herbivores migrate back and the cycle restart
```

### Run a reproducible experiment
```bash
python3 ecosystem.py --headless 1000 --seed 42 --format json > experiment.json
# Analyze the JSON output with your favorite tools
```

### Large world simulation
```bash
python3 ecosystem.py --width 120 --height 50 --plants 200 --herbivores 80 --predators 25
```

## What It Demonstrates

This simulation showcases classic ecology concepts:

- **Lotka-Volterra dynamics**: Predator-prey population oscillations
- **Carrying capacity**: Plant populations stabilize based on available space
- **Seasonal forcing**: External cycles modulate population dynamics
- **Trophic cascades**: Removing or adding top predators cascades down the food chain
- **Stochastic extinction**: Small populations can randomly go extinct
- **Migration and rescue effect**: Extinct species can recolonize from outside
- **Terrain effects**: Water barriers shape movement corridors and territory boundaries

## Testing

```bash
python3 -m pytest test_ecosystem.py -v
```

The test suite covers 49 tests including entity behavior, world simulation, seasonal effects, environmental events, headless mode output, CLI argument parsing, grid rendering, and integration tests.

## Configuration

All simulation parameters are configurable via CLI flags (see above) or by editing the constants at the top of `ecosystem.py`:

```python
WORLD_WIDTH = 80          # World grid width
WORLD_HEIGHT = 40          # World grid height
WATER_RATIO = 0.05        # Fraction of map that is water
INITIAL_PLANTS = 60        # Starting plant count
INITIAL_HERBIVORES = 25    # Starting herbivore count
INITIAL_PREDATORS = 8      # Starting predator count
TICK_DELAY = 0.12          # Seconds between updates
SEASON_LENGTH = 50         # Ticks per season
DISASTER_CHANCE = 0.005    # Probability of random event per tick
PLANT_POP_CAP = 300        # Maximum plants before culling
HERBIVORE_POP_CAP = 150    # Maximum herbivores before culling
PREDATOR_POP_CAP = 60      # Maximum predators before culling
```

## License

MIT