# Firefly Sync Garden

Firefly Sync Garden is a single-file Python terminal experience that simulates a drifting colony of pulse-coupled fireflies. Each firefly wanders through a wraparound night sky, flashes on its own rhythm, and pulls nearby neighbors toward synchronization. You can watch the swarm animate live, capture a still snapshot, or run a headless analysis that exports synchronization metrics to CSV.

## Features

- Animated firefly garden rendered directly in the terminal
- Emergent synchronization driven by local flash coupling
- Toroidal / wraparound interaction model so edge fireflies still affect each other
- Curated presets for `classic`, `calm`, `swarm`, and `storm` moods
- Deterministic seeds for reproducible runs
- Snapshot mode for generating a single still frame
- Headless analysis mode with textual metrics summary
- CSV export for per-frame flash and synchronization data
- ANSI color palettes plus ASCII-only and no-color output modes
- Live status line showing flashes, phase order, and sync ratio
- Standard-library-only implementation
- Unit tests for core simulation, presets, and CSV export

## What it does

The simulation models each firefly as a moving oscillator:

1. a firefly drifts through the garden with slight random steering
2. its internal phase advances every frame
3. once the phase reaches a threshold, it flashes and resets
4. nearby fireflies receive a phase boost based on distance
5. repeated local interactions can produce large-scale synchronized flashing

This creates a lightweight terminal visualization inspired by pulse-coupled oscillator systems.

## Requirements

- Python 3.11+
- A terminal with ANSI escape support for the full animated color experience
- `pytest` only if you want to run the tests with pytest

The application itself depends only on the Python standard library.

## Installation

```bash
cd ~/daily-ideas/2026-08-25-firefly-sync-garden
```

No packages need to be installed.

## How to run

### Animated garden

```bash
python3 firefly_sync_garden.py
```

### Use a preset with a deterministic seed

```bash
python3 firefly_sync_garden.py --preset calm --seed 7
```

### Generate a snapshot

```bash
python3 firefly_sync_garden.py --snapshot --ascii --no-color --seed 11 --warmup 180
```

### Run headless analysis and export metrics

```bash
python3 firefly_sync_garden.py --analyze --preset storm --steps 240 --seed 3 --csv metrics.csv
```

## Usage

```text
usage: firefly_sync_garden.py [-h] [--width WIDTH] [--height HEIGHT] [--count COUNT]
                              [--steps STEPS] [--fps FPS] [--seed SEED]
                              [--coupling COUPLING] [--radius RADIUS] [--speed SPEED]
                              [--jitter JITTER] [--phase-step PHASE_STEP]
                              [--warmup WARMUP] [--snapshot] [--analyze] [--csv CSV]
                              [--summary-only] [--preset {calm,classic,storm,swarm}]
                              [--palette {amber,mint,ocean,violet}] [--ascii]
                              [--no-color] [--no-status] [--version]
```

## Options

- `--width` / `--height` — size of the garden in terminal cells
- `--count` — number of simulated fireflies
- `--steps` — frames to animate or analyze
- `--fps` — animation speed in frames per second
- `--seed` — reproducible random seed
- `--coupling` — how strongly flashes pull nearby fireflies forward
- `--radius` — distance over which flashes have influence
- `--speed` — maximum movement speed
- `--jitter` — randomness in steering
- `--phase-step` — base oscillator advance per frame
- `--warmup` — number of simulation steps before rendering a snapshot
- `--snapshot` — print a single still frame instead of animating
- `--analyze` — run the simulation headlessly and print a metrics report
- `--csv` — save per-frame analysis metrics to CSV; requires `--analyze`
- `--summary-only` — in analysis mode, skip printing the final frame
- `--preset` — choose a curated behavior profile: `classic`, `calm`, `swarm`, or `storm`
- `--palette` — select a color palette: `amber`, `mint`, `ocean`, or `violet`
- `--ascii` — avoid Unicode glow characters
- `--no-color` — disable ANSI colors
- `--no-status` — hide the status line
- `--version` — print the version string

## Usage examples

### Soft, meditative garden

```bash
python3 firefly_sync_garden.py --preset calm --steps 220 --seed 12
```

### Fast, dense swarm

```bash
python3 firefly_sync_garden.py --preset swarm --width 90 --height 26 --seed 4
```

### High-coupling experimental run

```bash
python3 firefly_sync_garden.py --count 40 --coupling 0.35 --radius 10 --phase-step 0.05 --palette violet
```

### Quiet frame for a text file

```bash
python3 firefly_sync_garden.py --snapshot --no-color --ascii --width 60 --height 18 --seed 23 > frame.txt
```

### Metrics report without rendering the frame

```bash
python3 firefly_sync_garden.py --analyze --summary-only --steps 300 --seed 9
```

## Analysis output

`--analyze` prints a synchronization summary including:

- total flashes
- peak flashes in a single frame
- average and maximum phase order
- average and maximum synchronized ratio
- final mean phase
- first frame where the swarm reached at least 90% synchronization

When `--csv` is provided, the tool writes one row per frame with these columns:

- `frame`
- `flashes`
- `order`
- `synced_ratio`
- `mean_phase`

## Running tests

```bash
python3 -m unittest test_firefly_sync_garden.py
```

Or with pytest:

```bash
pytest -q test_firefly_sync_garden.py
```

## Notes

- The simulation is intentionally stylized rather than biologically exact.
- Synchronization depends heavily on seed, density, coupling, and radius.
- Unicode mode looks best in a modern terminal font, but ASCII mode is available for portability.
- The analysis mode is useful for comparing presets or tuning parameters over repeatable seeded runs.
