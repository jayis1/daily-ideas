# 🐜 Terminal Ant Colony Simulator

A real-time emergent behavior simulation where ants forage for food, leave pheromone trails, and collectively discover optimal paths — all rendered as colorful ASCII art in your terminal.

Watch as simple rules produce complex intelligence: ants self-organize into efficient foraging highways, preferentially exploit the closest food sources, and dynamically reroute when sources deplete.

## ✨ Features

- **Real-time curses visualization** with color-coded pheromone intensity display
- **Pheromone trail dynamics** — ants deposit pheromones that diffuse to neighbors and evaporate over time
- **Multiple food sources** placed randomly in clusters around the map
- **Wall obstacles** — random walls that ants must navigate around, demonstrating pathfinding emergence
- **Headless batch mode** — run simulations without a terminal UI for benchmarking and research
- **JSON output** — export simulation statistics as structured JSON
- **Reproducible runs** — set a random seed for deterministic simulations
- **Interactive controls** — pause, speed up/slow down, reset, and toggle legend overlay
- **Live statistics panel** — food collected, ants carrying, pheromone levels, efficiency metrics, average delivery time, best forager stats
- **Terminal resize handling** — adapts to window size changes mid-simulation
- **`--version` and `--help` flags** for standard CLI tooling
- **Comprehensive test suite** — 32 tests covering ant behavior, simulation logic, headless mode, edge cases, and more

## 🎮 Visual Legend

| Symbol | Color | Meaning |
|--------|-------|---------|
| `·` | gray | Searching ant |
| `●` | orange | Ant carrying food |
| `▓`/`▒`/`█` | red | Food source (intensity by remaining amount) |
| `░` + `⌂` | blue | Nest (center symbol surrounded by border) |
| `▓` | dark gray | Wall obstacle |
| `·` | dim | Very faint pheromone trail |
| `∘` | dark green | Light pheromone trail |
| `○` | bright green | Medium pheromone trail |
| `◎` | bright green | Strong pheromone trail |
| `◉` | yellow | Very strong pheromone trail |

## 🚀 Installation

Requires **Python 3.7+** with no external dependencies (uses only the standard library).

```bash
# Clone or download the project
cd daily-ideas/2026-06-25-ant-colony-simulator

# Run it directly — no pip install needed
python3 ant_colony.py
```

For running the test suite:

```bash
pip install pytest
python3 -m pytest test_ant_colony.py -v
```

## 📖 Usage

### Interactive Mode (default)

```bash
# Run with defaults (60 ants, 3 walls, 20 FPS)
python3 ant_colony.py

# More ants for denser trail formation
python3 ant_colony.py --ants 120

# Add more wall obstacles for complex pathfinding
python3 ant_colony.py --walls 8

# Disable walls entirely
python3 ant_colony.py --no-walls

# Slower evaporation = longer-lasting trails
python3 ant_colony.py --evaporation 0.998

# Set a seed for reproducible runs
python3 ant_colony.py --seed 42

# Show version
python3 ant_colony.py --version

# Full help
python3 ant_colony.py --help
```

### Headless Mode (batch/benchmark)

```bash
# Run 2000 ticks in headless mode, print summary
python3 ant_colony.py --headless --ticks 2000

# Output results as JSON (for scripting/pipelines)
python3 ant_colony.py --headless --ticks 3000 --seed 42 --json

# Benchmark with walls
python3 ant_colony.py --headless --ants 100 --walls 5 --ticks 5000 --json
```

### Controls (interactive mode)

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume simulation |
| `+` / `=` | Speed up (1× → 2× → ... → 10×) |
| `-` | Slow down |
| `R` | Reset simulation with new random layout |
| `L` | Toggle legend overlay |
| `Q` / `ESC` | Quit |

## 🔬 How It Works

Each ant follows simple rules with no central coordination:

1. **Wander** — When no pheromone trail is detected, ants explore randomly with forward momentum
2. **Follow Trails** — When pheromone is sensed, ants bias their movement toward the strongest scent
3. **Pick Up Food** — When an ant steps on a food cell, it picks up one unit and turns toward home
4. **Return Home** — Carrying ants deposit strong pheromone trails as they head back to the nest, reinforcing successful paths
5. **Evaporation** — Pheromone diffuses to 4-connected neighbors and decays exponentially, so unused trails fade away

### Emergent Behavior

The magic is in the feedback loop: ants returning from food lay down pheromone, which attracts more ants, which find the food and return, reinforcing the trail. Shorter paths accumulate more pheromone because ants traverse them faster. This naturally optimizes for the shortest route — no central planner needed.

### Wall Obstacles

Wall obstacles (`▓`) block ant movement and pheromone diffusion. Ants must find paths around them, demonstrating how the colony dynamically discovers detours. Watch pheromone trails reroute in real time when the shortest path is blocked.

## 📊 Statistics

The info panel tracks:

- **Food collected / total** — Progress toward collecting all food
- **Carrying** — How many ants are currently carrying food back
- **Max pheromone** — Current strongest trail intensity
- **Efficiency** — Food collected per 1000 ant-steps
- **Avg delivery ticks** — Average time for an ant to complete a food delivery round trip
- **Best forager** — Most deliveries by a single ant
- **Sources remaining** — Active food clusters left

## 🧪 Testing

```bash
# Run the full test suite (32 tests)
python3 -m pytest test_ant_colony.py -v

# Run a quick smoke test in headless mode
python3 ant_colony.py --headless --ticks 100 --seed 42
```

Test coverage includes:
- Ant initialization and pheromone sensing
- Carrying ants biasing movement toward home
- Searching ants following pheromone trails
- Simulation step advancement and food collection
- Pheromone evaporation and diffusion
- Wall collision avoidance
- Ants staying within grid bounds
- Reproducibility with seeds
- Headless mode output and JSON export
- Edge cases (minimum grid, single ant, many ants)
- Grid integrity (non-negative food and pheromone values)

## ⚙️ Parameters to Experiment With

| Parameter | Default | Effect |
|-----------|---------|--------|
| `--ants` / `-a` | 60 | More ants = faster trail formation, denser visual |
| `--walls` / `-w` | 3 | More walls = more complex pathfinding |
| `--no-walls` | off | Disable walls entirely |
| `--evaporation` | 0.995 | Higher = trails persist longer; lower = faster fade |
| `--fps` / `-f` | 20 | Animation speed (frames per second) |
| `--seed` | random | Set for reproducible simulation layouts |
| `DIFFUSION_RATE` | 0.12 | How much pheromone spreads to adjacent cells per tick |
| `PHEROMONE_DEPOSIT` | 40.0 | Base pheromone deposit per ant step |
| `WANDER_STRENGTH` | 0.35 | Probability of continuing current direction vs. random turn |

Internal constants can be edited directly in `ant_colony.py`.

## 🏗 Implementation Details

- **Ant agents** use `__slots__` for memory efficiency and track individual statistics (deliveries, carrying time)
- **Pheromone grid** uses floating-point values with diffusion to 4-connected neighbors and exponential evaporation
- **Rendering** uses curses color-pair runs for efficient screen updates
- **Wall obstacles** are stored as a set for O(1) collision lookup
- **Statistics tracking** includes per-ant delivery counts, average delivery time, peak pheromone levels, and completion detection
- **No external dependencies** — pure Python standard library