# ⚙️ Rube Goldberg Machine Simulator

A terminal-based ASCII animation of absurdly complex chain-reaction machines. Watch as balls, dominoes, seesaws, buckets, pulleys, fans, springs, hammers, and more interact in hilariously over-engineered contraptions — all to accomplish a trivially simple task.

Inspired by [Rube Goldberg machines](https://en.wikipedia.org/wiki/Rube_Goldberg_machine) that use convoluted, indirect mechanisms to perform simple tasks in wildly complicated ways.

## Features

- **Interactive Menu** — Choose from preset, random, or marathon mode interactively
- **Preset Machine** — A hand-designed 10-stage machine with guaranteed good visuals
- **Random Machine** — Every run generates a unique layout from randomized stage combinations
- **Marathon Mode** — 3 random machines back-to-back
- **`--describe` Mode** — Print a text description of the machine's stages without animating
- **`--seed` Option** — Use a specific random seed for reproducible machines
- **`--speed` Option** — Control animation speed (lower = faster)
- **`--color` Option** — Enable ANSI color output for a more vivid display
- **`--version` / `--help`** — Standard CLI flags
- **Animated Chain Reactions** — Balls roll, dominoes fall, seesaws tip, buckets dump, springs bounce, fans blow, pulleys lift, hammers smash
- **Particle Effects** — Sparkles, trails, and water drops for visual flair
- **Real-time Status** — Frame counter, component count, projectile tracking
- **51 Unit Tests** — Comprehensive test suite covering components, simulation, rendering, CLI parsing, and more
- **No Dependencies** — Pure Python standard library, no pip installs needed

## Stage Types

| Stage | What Happens |
|-------|-------------|
| **Domino Chain** | Rows of dominoes falling in sequence |
| **Seesaw Launch** | A seesaw tips and flings a ball upward |
| **Bucket Dump** | A bucket tips over and spills water |
| **Hammer Smash** | A hammer swings down, triggering a spring |
| **Fan Blow** | A fan blows a gust of air, pushing a ball |
| **Spring Launch** | A spring bounces a ball skyward |
| **Funnel Redirect** | A funnel catches a ball and redirects it down |
| **Pulley Lift** | A pulley system lifts a ball up |

Each random machine selects 4–6 of these stages in a random order, so every run is unique.

## Installation

No installation required! Just clone and run with Python 3.8+.

```bash
git clone <repo-url>
cd 2026-06-25-rube-goldberg-simulator
```

## How to Run

### Interactive Mode (default)

```bash
python3 rube_goldberg.py
```

Then choose an option:

- `[1]` Preset machine (hand-designed, reliable)
- `[2]` Random machine (different every time)
- `[3]` Marathon mode (3 random machines)
- `[q]` Quit

### Command-Line Options

```bash
# Run the preset machine directly (no menu)
python3 rube_goldberg.py --preset

# Run a random machine
python3 rube_goldberg.py --random

# Run 3 random machines back-to-back
python3 rube_goldberg.py --marathon

# Use a specific seed for reproducible results
python3 rube_goldberg.py --random --seed 42

# Speed up the animation (0.03s per frame instead of 0.06s)
python3 rube_goldberg.py --random --speed 0.03

# Enable colorful ANSI output
python3 rube_goldberg.py --random --color

# Print a description of the machine stages without animation
python3 rube_goldberg.py --describe --random --seed 42

# Custom canvas dimensions
python3 rube_goldberg.py --random --width 80 --height 30

# Show version
python3 rube_goldberg.py --version

# Show help with all options
python3 rube_goldberg.py --help
```

Press `Ctrl+C` to exit at any time during animation.

### Describe Mode Example

```
$ python3 rube_goldberg.py --describe --random --seed 42

⚙️  Rube Goldberg Machine — Stage Description
==================================================

Canvas size: 78 × 20
Total components: 16
Seed: 42

Stages (in order):
----------------------------------------
  1. Hammer Smash
     A hammer swings down with great force, triggering a spring below

  2. Fan Blow
     A fan blows a gust of air, pushing a ball along a rail

  3. Funnel Redirect
     A funnel catches a ball and redirects it downward

  4. Pulley Lift
     A pulley system lifts a ball up to a higher track

  5. Bucket Dump
     A bucket tips over, spilling its contents onto the next stage

  6. Spring Launch
     A spring compresses and launches a ball skyward

Component summary:
  ball: 7
  spring: 2
  hammer: 1
  ...

Finale: 🔔 Bell → ⚑ Flag raised!
```

## Running Tests

```bash
# Run with pytest
python3 -m pytest test_rube_goldberg.py -v

# Or run directly
python3 test_rube_goldberg.py
```

The test suite includes 51 tests covering:

- Component creation, state transitions, and display characters
- Projectile types and trail behavior
- Machine generation (preset and random)
- Seeded reproducibility
- Simulation stepping and completion detection
- Rendering with and without color
- Describe mode output
- CLI argument parsing
- Edge cases and completeness checks

## How It Works

The simulator uses a component-based architecture:

1. **Components** are placed on a 2D canvas — balls, dominoes, seesaws, buckets, etc.
2. Each component has a timer that counts down; when it reaches zero, the component activates
3. Activating a component spawns **projectiles** (balls, water, air, sparks) that fly through the scene with physics (gravity, velocity)
4. Components progress through states: `idle → active → triggered → done`, changing their appearance
5. The finale features a bell (🔔 DING!) and a flag (⚑) to signal completion

The machine is rendered in real-time ASCII art with box-drawing borders, state indicators (✧ for active, ✶ for triggered), projectile trails, and sparkle effects.

## Architecture

- **`Component`** — Dataclass for each mechanical part with state, timer, position, and visual representation
- **`Projectile`** — Dataclass for moving objects (balls, water, air, sparks) with physics
- **`RubeGoldbergMachine`** — Main simulation class handling generation, stepping, rendering, and description
- **`create_preset_machine()`** — Builds the hand-designed 10-stage machine
- **`create_random_machine()`** — Generates a random machine with seeded reproducibility
- **CLI** — `argparse`-based interface with `--preset`, `--random`, `--marathon`, `--seed`, `--speed`, `--color`, `--describe`, `--width`, `--height`, `--version`