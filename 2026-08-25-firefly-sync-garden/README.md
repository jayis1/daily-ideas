# Firefly Sync Garden

Firefly Sync Garden is a terminal-based Python simulation of drifting, pulse-coupled fireflies. Each firefly moves through a wraparound night sky, advances its own flashing phase, and nudges nearby neighbors toward synchronization. You can watch it animate live, render a reproducible snapshot, or run a headless analysis that exports per-frame metrics.

## Features

- Live terminal animation of a glowing firefly swarm
- Wraparound/toroidal interaction model so edge neighbors still influence each other
- Curated presets: `classic`, `calm`, `swarm`, and `storm`
- Reproducible runs with `--seed`
- Snapshot mode for generating a single still frame
- Headless analysis mode with synchronization summary output
- CSV export of frame-by-frame metrics
- ANSI color palettes plus ASCII-only and no-color modes
- Built-in `--help` and `--version` support
- Standard-library-only implementation
- Unit tests for simulation behavior, CSV export, presets, and CLI validation

## What it does

The simulation treats each firefly as a moving oscillator:

1. it drifts through the garden with bounded random steering
2. its internal phase advances every frame
3. when the phase wraps past the flash threshold, it flashes and resets
4. nearby fireflies receive a phase boost based on distance
5. enough local interactions can produce partial or strong synchronization

The result is a lightweight visual toy with a useful analysis mode for comparing seeds, presets, and coupling parameters.

## Requirements

- Python 3.11 or newer
- A terminal with ANSI escape support for the full animated color experience
- `pytest` only if you want to run the optional pytest command

No third-party packages are required to run the app.

## Installation

```bash
cd ~/daily-ideas/2026-08-25-firefly-sync-garden
```

That is all you need.

## How to run

### Animated garden

```bash
python3 firefly_sync_garden.py
```

### Calm preset with a fixed seed

```bash
python3 firefly_sync_garden.py --preset calm --seed 7
```

### Snapshot mode

```bash
python3 firefly_sync_garden.py --snapshot --ascii --no-color --seed 11 --warmup 180
```

### Headless analysis with CSV export

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

- `--width` / `--height` — garden size in terminal cells; minimum `10x5`
- `--count` — number of fireflies
- `--steps` — frames to animate or analyze
- `--fps` — animation frame rate
- `--seed` — deterministic random seed
- `--coupling` — flash influence strength
- `--radius` — flash influence radius
- `--speed` — maximum drift speed
- `--jitter` — random steering amount
- `--phase-step` — base phase advance per frame
- `--warmup` — pre-snapshot simulation steps
- `--snapshot` — print a single still frame instead of animating
- `--analyze` — run headless analysis and print summary metrics
- `--csv` — write analysis metrics to a CSV file; requires `--analyze`
- `--summary-only` — skip the rendered final frame in analysis mode
- `--preset` — choose `classic`, `calm`, `swarm`, or `storm`
- `--palette` — choose `amber`, `mint`, `ocean`, or `violet`
- `--ascii` — disable Unicode glow glyphs
- `--no-color` — disable ANSI colors
- `--no-status` — hide the status line
- `--version` — print the current version

## Usage examples

### Soft, slower garden

```bash
python3 firefly_sync_garden.py --preset calm --steps 220 --seed 12
```

### Dense swarm

```bash
python3 firefly_sync_garden.py --preset swarm --width 90 --height 26 --seed 4
```

### High-coupling experiment

```bash
python3 firefly_sync_garden.py --count 40 --coupling 0.35 --radius 10 --phase-step 0.05 --palette violet
```

### Save a quiet text snapshot

```bash
python3 firefly_sync_garden.py --snapshot --no-color --ascii --width 60 --height 18 --seed 23 > frame.txt
```

### Print summary metrics only

```bash
python3 firefly_sync_garden.py --analyze --summary-only --steps 300 --seed 9
```

## Analysis output

`--analyze` reports:

- total flashes
- peak flashes in a single frame
- average and maximum phase order
- average and maximum synchronized ratio
- final phase order, sync ratio, and mean phase
- the first frame that reached at least 90% synchronization

When `--csv` is used, the export contains these columns:

- `frame`
- `flashes`
- `order`
- `synced_ratio`
- `mean_phase`

## Running tests

With the standard library:

```bash
python3 -m unittest -v test_firefly_sync_garden.py
```

Optional pytest command:

```bash
pytest -q test_firefly_sync_garden.py
```

## Known issues

- The simulation is intentionally stylized and not meant to be a biologically exact firefly model.
- Very large terminal sizes or very high firefly counts can make animation visually dense.
- Synchronization behavior is sensitive to seed, density, coupling, and radius.

## Changelog

### 1.1.1

- Fixed a CLI bug where `--analyze --csv /some/existing/directory` crashed with an unhandled `IsADirectoryError` traceback.
- Added validation so directory paths are rejected early with a clear argparse error message.
- Added defensive CSV-write error handling for other filesystem write failures.
- Added regression tests covering invalid CSV destinations.

### 1.1.0

- Added presets, headless analysis mode, CSV export, and expanded tests.
