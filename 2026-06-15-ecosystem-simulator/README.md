# 🌍 ASCII Ecosystem Simulator

A terminal-based ecosystem simulation that models the dynamics of a living world — plants grow and spread, herbivores graze and flee, predators hunt and reproduce. Watch population cycles, seasonal changes, and random environmental events unfold in real-time through an ASCII art world and live population graph.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Terminal](https://img.shields.io/badge/interface-curses-green) ![License](https://img.shields.io/badge/license-MIT-brightgreen)

## Features

- **Three-species food chain**: Plants → Herbivores → Predators, each with unique AI behaviors
- **Seasonal cycle**: Spring/Summer/Autumn/Winter affects plant growth, energy drain, and survival
- **Environmental events**: Random droughts, plagues, bounties, and storms shake up the ecosystem
- **Live population graph**: ASCII bar graph tracks species populations over time
- **Ecosystem self-stabilization**: Extinct species can "migrate" back, preventing total collapse
- **Interactive controls**: Spawn creatures, pause, adjust speed, reset the simulation
- **Wrapping world**: Toroidal map — creatures that leave one edge appear on the opposite side

## How It Works

### Species Behavior

| Species | Symbol | Behavior |
|---------|--------|----------|
| **Plant** | `♣` / `♠` | Grows over time (maturity stages: `·` → `∘` → `♣` → `♠`), spreads to adjacent cells, affected by seasons |
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

- **Drought** — Kills ~30% of plants
- **Plague** — Kills ~20% of herbivores and predators
- **Bounty** — Spawns 30 new mature plants
- **Storm** — Randomly scatters all creatures across the map

## Installation

Requires Python 3.8+ with standard library only (no external dependencies).

```bash
# Clone the repository
git clone https://github.com/yourusername/daily-ideas.git
cd daily-ideas/2026-06-15-ecosystem-simulator

# Make executable (optional)
chmod +x ecosystem.py
```

## How to Run

```bash
python3 ecosystem.py
```

> **Note**: Requires a terminal that supports curses and at least 80×55 character size. Most Linux/macOS terminals work out of the box.

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `+` / `=` | Increase speed |
| `-` | Decrease speed |
| `p` | Spawn 10 new plants |
| `h` | Spawn 1 new herbivore |
| `d` | Spawn 1 new predator |
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
# Launch, then press '+' multiple times to speed up
# Watch centuries of ecosystem dynamics in minutes
```

### Create a predator invasion
```bash
# Launch, then press 'd' several times to add predators
# Watch the herbivore population crash, followed by predator starvation
# Then watch herbivores migrate back and the cycle restart
```

### Create a lush garden
```bash
# Press 'p' multiple times to flood the world with plants
# Watch herbivores thrive, then predators boom
```

## What It Demonstrates

This simulation showcases classic ecology concepts:

- **Lotka-Volterra dynamics**: Predator-prey population oscillations
- **Carrying capacity**: Plant populations stabilize based on available space
- **Seasonal forcing**: External cycles modulate population dynamics
- **Trophic cascades**: Removing or adding top predators cascades down the food chain
- **Stochastic extinction**: Small populations can randomly go extinct
- **Migration and rescue effect**: Extinct species can recolonize from outside

## Configuration

All simulation parameters are configurable at the top of `ecosystem.py`:

```python
WORLD_WIDTH = 80        # World grid width
WORLD_HEIGHT = 40       # World grid height
INITIAL_PLANTS = 60     # Starting plant count
INITIAL_HERBIVORES = 25 # Starting herbivore count
INITIAL_PREDATORS = 8  # Starting predator count
TICK_DELAY = 0.12      # Seconds between updates
SEASON_LENGTH = 50     # Ticks per season
DISASTER_CHANCE = 0.005 # Probability of random event per tick
```

## License

MIT