# Firefly Sync Garden

Firefly Sync Garden is a terminal animation that simulates a drifting colony of pulse-coupled fireflies. Each firefly moves through a tiny ASCII night garden, blinks on its own rhythm, and nudges nearby neighbors toward synchronization. The result is a calm emergent light show that becomes more coordinated over time.

## Features

- Animated terminal firefly simulation with emergent synchronization
- Deterministic seeds for reproducible gardens
- Snapshot mode for generating a single still frame
- Adjustable coupling strength, flash radius, speed, jitter, and population size
- ANSI color palettes plus ASCII-only / no-color output modes
- Live status metrics including flash count, phase order, and synchronized ratio
- Standard-library-only implementation
- Unit tests for synchronization math and deterministic rendering

## What it does

The program models each firefly as a moving oscillator:

1. every firefly drifts through the garden with slight random steering
2. its phase increases until it flashes
3. a flash boosts the phases of nearby fireflies
4. repeated local boosts gradually create synchronized pulses

This is a lightweight terminal take on pulse-coupled synchronization systems seen in real firefly swarms.

## Requirements

- Python 3.11+
- A terminal that supports ANSI escape sequences for the animated color mode
- `pytest` only if you want to run the tests with pytest

The application itself uses only the Python standard library.

## Installation

```bash
cd ~/daily-ideas/2026-08-25-firefly-sync-garden
```

No extra packages are required.

## How to run

### Animated garden

```bash
python3 firefly_sync_garden.py
```

### Reproducible run with a custom palette

```bash
python3 firefly_sync_garden.py --seed 7 --palette violet --steps 240 --count 42
```

### ASCII-only snapshot

```bash
python3 firefly_sync_garden.py --snapshot --ascii --no-color --seed 11 --warmup 180
```

## Usage

```text
usage: firefly_sync_garden.py [-h] [--width WIDTH] [--height HEIGHT] [--count COUNT]
                              [--steps STEPS] [--fps FPS] [--seed SEED]
                              [--coupling COUPLING] [--radius RADIUS] [--speed SPEED]
                              [--jitter JITTER] [--warmup WARMUP] [--snapshot]
                              [--palette {amber,mint,ocean,violet}] [--ascii]
                              [--no-color] [--no-status] [--version]
```

## Options

- `--width` / `--height` — size of the garden in terminal cells
- `--count` — number of simulated fireflies
- `--steps` — animation length in frames
- `--fps` — animation speed
- `--seed` — reproducible random seed
- `--coupling` — how strongly flashes pull nearby phases forward
- `--radius` — neighborhood size for flash influence
- `--speed` — movement speed cap
- `--jitter` — randomness in steering
- `--warmup` — simulation steps before printing a snapshot
- `--snapshot` — print one frame instead of animating
- `--palette` — choose `amber`, `mint`, `ocean`, or `violet`
- `--ascii` — avoid Unicode glow characters
- `--no-color` — disable ANSI colors
- `--no-status` — omit the metrics line
- `--version` — print the version string

## Usage examples

### Calm, slow, highly synchronized colony

```bash
python3 firefly_sync_garden.py --count 28 --coupling 0.28 --radius 9 --fps 14 --steps 220
```

### Dense swarm with faster motion

```bash
python3 firefly_sync_garden.py --count 64 --speed 0.9 --jitter 0.1 --palette ocean
```

### Quiet still frame for a README or log file

```bash
python3 firefly_sync_garden.py --snapshot --no-color --ascii --width 60 --height 18 --seed 23 > frame.txt
```

## Running tests

```bash
pytest -q test_firefly_sync_garden.py
```

You can also run the built-in unittest module:

```bash
python3 -m unittest test_firefly_sync_garden.py
```

## Notes

- The simulation is intentionally stylized rather than biologically exact.
- Synchronization depends on seed, population density, coupling, and radius.
- Unicode mode looks best in a modern terminal font, but ASCII mode is available for portability.
