# Metro Map Puzzler

Metro Map Puzzler is a standard-library Python project that procedurally generates a fictional subway network, renders it as an ASCII transit diagram, and turns the result into route-finding puzzles. Every seed creates a different miniature city with named stations, multiple colored lines, transfer hubs, and an optimal trip to discover.

## Features

- Procedural metro-map generation with reproducible seeds
- Multiple named train lines with transfer stations
- ASCII map rendering with optional ANSI colors
- Automatic route solving using fewest-stops, fewest-transfers search
- Snapshot mode that prints a map, a puzzle prompt, and the optimal answer
- Interactive quiz mode for playing several trip-planning rounds
- Direct solve mode for routing between any two station names on the generated map
- Standard-library-only implementation
- Unit tests for generation, rendering, puzzle selection, and solving

## What it does

The program builds a tiny fictional transit system by laying down several subway lines across a grid. Stations get memorable names like `Silver Market` or `Moon Yard`, some of them become transfer points shared by multiple lines, and the resulting network is guaranteed to be connected.

Once the network exists, the app can:

1. print the map and a featured puzzle
2. challenge you interactively to name the best route
3. solve any trip between two stations
4. show how many stops and transfers the optimal trip requires

The route solver treats each ride segment as one stop and uses transfers as a tie-breaker, so solutions feel like realistic quick-trip recommendations for a tiny subway.

## Requirements

- Python 3.11 or newer
- A terminal for the interactive quiz experience
- No third-party packages required

## Installation

```bash
cd ~/daily-ideas/2026-08-28-metro-map-puzzler
```

That is enough to run the project.

## How to run

### Default snapshot

```bash
python3 metro_map_puzzler.py
```

### Generate a different city

```bash
python3 metro_map_puzzler.py --seed 77
```

### Interactive quiz mode

```bash
python3 metro_map_puzzler.py --quiz 3
```

### Solve a specific trip

```bash
python3 metro_map_puzzler.py --seed 77 --solve "Grand Bridge" "Moon Depot"
```

### Monochrome output

```bash
python3 metro_map_puzzler.py --seed 77 --no-color
```

## Usage

```text
usage: metro_map_puzzler.py [-h] [--seed SEED] [--width WIDTH] [--height HEIGHT]
                             [--lines LINES] [--snapshot] [--quiz ROUNDS]
                             [--solve FROM TO] [--no-color] [--version]
```

## Options

- `--seed` — reproducible random seed for the generated transit network
- `--width` / `--height` — map dimensions; use at least `24x12`
- `--lines` — number of train lines to generate, from `2` to `7`
- `--snapshot` — explicitly request the default map+puzzle output
- `--quiz ROUNDS` — play an interactive routing quiz
- `--solve FROM TO` — compute the best route between two named stations
- `--no-color` — disable ANSI colors even in a TTY
- `--version` — print the current version

## Usage examples

### Print a compact planning puzzle

```bash
python3 metro_map_puzzler.py --seed 12 --width 48 --height 18
```

### Build a denser network with more lines

```bash
python3 metro_map_puzzler.py --seed 145 --lines 6 --width 60 --height 22
```

### Ask for a route after reading the station legend

```bash
python3 metro_map_puzzler.py --seed 12 --solve "Harbor Garden" "Signal Arcade"
```

### Play a short challenge set

```bash
python3 metro_map_puzzler.py --seed 12 --quiz 2
```

Answer quiz prompts by typing the station names in order, separated by commas. You can also type `hint`, `show`, or `quit`.

## Running tests

```bash
python3 -m unittest -v test_metro_map_puzzler.py
```

## File overview

- `metro_map_puzzler.py` — generator, renderer, puzzle engine, and CLI
- `test_metro_map_puzzler.py` — automated tests
- `README.md` — project documentation

## Notes

- Station names depend on the random seed, so solve examples should be run after inspecting the generated station legend.
- Different seeds produce different puzzle difficulty and transfer patterns.
- ANSI colors appear only when output is attached to a TTY unless you force monochrome with `--no-color`.
