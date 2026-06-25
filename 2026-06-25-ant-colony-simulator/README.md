# Terminal Ant Colony Simulator

An emergent behavior simulation where ants forage for food, leave pheromone trails, and collectively discover optimal paths — all rendered as a real-time animated visualization in the terminal.

## How It Works

Each ant follows simple rules with no central coordination:

1. **Wander** — When no pheromone trail is detected, ants explore randomly with forward momentum
2. **Follow Trails** — When pheromone is sensed, ants bias their movement toward the strongest scent
3. **Pick Up Food** — When an ant steps on a food cell, it picks up one unit and turns toward home
4. **Return Home** — Carrying ants deposit strong pheromone trails as they head back to the nest, reinforcing successful paths
5. **Evaporation** — Pheromone diffuses and decays over time, so unused trails fade away

The result is **emergent intelligence**: ants self-organize into efficient foraging highways, preferentially exploiting the closest food sources first and dynamically rerouting when sources deplete.

## Features

- **Real-time curses visualization** with color-coded display
- **Pheromone trails** rendered as intensity-graded symbols (from `·` to `◉`)
- **Multiple food sources** placed randomly around the map in clusters
- **Diffusion & evaporation** — pheromones spread to neighbors and decay over time
- **Interactive controls**: pause, speed up/slow down, reset
- **Statistics panel** showing food collected, ants carrying, pheromone levels, and efficiency

## Visual Legend

| Symbol | Meaning |
|--------|---------|
| `·` | Very faint pheromone trail |
| `∘` | Light pheromone trail |
| `○` | Medium pheromone trail |
| `◎` | Strong pheromone trail |
| `◉` | Very strong pheromone trail |
| `·` (gray) | Searching ant |
| `●` (orange) | Ant carrying food |
| `▓`/`▒` (red) | Food source |
| `░` + `⌂` (blue) | Nest |

## Installation

Requires Python 3.7+ with no external dependencies (uses only the standard library).

```bash
# Clone or download the project
cd daily-ideas/2026-06-25-ant-colony-simulator

# No installation needed — just run it
python3 ant_colony.py
```

## Usage

```bash
# Run with defaults (60 ants, 20 FPS)
python3 ant_colony.py

# More ants for denser trails
python3 ant_colony.py --ants 120

# Faster simulation
python3 ant_colony.py --fps 30

# Slower evaporation (longer-lasting trails)
python3 ant_colony.py --evaporation 0.998
```

### Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `+` / `=` | Speed up (1x → 2x → ... → 10x) |
| `-` | Slow down |
| `R` | Reset simulation |
| `Q` / `ESC` | Quit |

## How It Looks

When you run the simulation, you'll see:

1. **Initially**: Ants swarm around the nest (blue `⌂` in the center) and explore outward
2. **Discovery**: Once an ant finds food (red `▓` clusters), it picks it up (turns orange `●`) and heads home
3. **Trail Formation**: The returning ant leaves a pheromone trail (green/yellow symbols), which other ants follow
4. **Highway Emergence**: Within minutes, you'll see clear "highways" of pheromone connecting the nest to food sources
5. **Dynamic Rerouting**: When a food source depletes, the trail fades and ants redirect to remaining sources

## Implementation Details

- **Ant agents** are lightweight with `__slots__` for efficiency
- **Pheromone grid** uses floating-point values with diffusion to 4-neighbors and exponential evaporation
- **Rendering** uses curses color-pair runs for efficient screen updates
- **No external dependencies** — pure Python standard library

## Parameters to Experiment With

- `NUM_ANTS_DEFAULT` — More ants = faster trail formation, more visual density
- `EVAPORATION_RATE` — Higher = trails persist longer; lower = trails fade faster
- `DIFFUSION_RATE` — How much pheromone spreads to adjacent cells per tick
- `PHEROMONE_DEPOSIT` — How much pheromone an ant deposits per step
- `WANDER_STRENGTH` — Probability of continuing in the current direction vs. turning randomly