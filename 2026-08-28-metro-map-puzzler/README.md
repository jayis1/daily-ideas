# Metro Map Puzzler

Metro Map Puzzler is a standard-library Python CLI that generates a fictional subway network, renders it as ASCII art, and turns the map into route-planning puzzles. Each seed creates a small but connected transit system with named stations, colored lines, transfer hubs, and solvable journeys.

## What it does

The app builds a miniature metro network on a grid, then lets you:

- inspect the generated map and station legend
- view a featured puzzle and its optimal answer
- solve routes between arbitrary stations
- choose whether routing should prefer fewer stops or fewer transfers
- list all stations in alphabetical order
- print a compact network summary
- export the generated system to JSON for reuse elsewhere
- play an interactive quiz mode

## Features

- Reproducible procedural metro generation with `--seed`
- Connected multi-line transit networks with shared interchange stations
- ASCII rendering with optional ANSI colors
- Route solving with two optimization modes:
  - `balanced`: fewest stops first, then fewer transfers
  - `transfers`: fewest transfers first, then fewer stops
- Built-in station search with partial matching and typo suggestions
- Network statistics including interchange count and longest line
- JSON export for generated maps
- Interactive quiz mode for trip-planning challenges
- Unit tests covering generation, solving, rendering, station parsing, and export
- No third-party dependencies

## Requirements

- Python 3.11+
- A terminal if you want to use quiz mode interactively

## Installation

```bash
cd ~/daily-ideas/2026-08-28-metro-map-puzzler
```

No package install is required.

## How to run

### Default snapshot

```bash
python3 metro_map_puzzler.py
```

This prints:

- the metro map
- a station legend
- a network summary
- a featured puzzle
- the best route answer

### Show help

```bash
python3 metro_map_puzzler.py --help
```

### Show version

```bash
python3 metro_map_puzzler.py --version
```

## Usage

```text
usage: metro_map_puzzler.py [-h] [--seed SEED] [--width WIDTH] [--height HEIGHT]
                             [--lines LINES] [--snapshot] [--quiz ROUNDS]
                             [--solve FROM TO]
                             [--route-mode {balanced,transfers}]
                             [--list-stations] [--stats] [--export PATH]
                             [--no-color] [--version]
```

## Command-line options

- `--seed SEED` — use a reproducible random seed
- `--width WIDTH` — map width in characters
- `--height HEIGHT` — map height in characters
- `--lines LINES` — number of lines to generate, from `2` to `7`
- `--snapshot` — explicitly print the default map + puzzle view
- `--quiz ROUNDS` — play an interactive quiz for the given number of rounds
- `--solve FROM TO` — solve a route between two station names
- `--route-mode {balanced,transfers}` — pick the optimization strategy for `--solve`
- `--list-stations` — print an alphabetical station index
- `--stats` — print a compact network summary
- `--export PATH` — write the generated metro network to a JSON file
- `--no-color` — disable ANSI color output
- `--version` — print the program version

## Examples

### Generate a different city

```bash
python3 metro_map_puzzler.py --seed 77
```

### Solve a route with the default stop-first planner

```bash
python3 metro_map_puzzler.py --seed 77 --solve "Grand Bridge" "Moon Depot"
```

### Solve a route while prioritizing fewer transfers

```bash
python3 metro_map_puzzler.py --seed 77 --solve "Grand Bridge" "Moon Depot" --route-mode transfers
```

### Print only network stats

```bash
python3 metro_map_puzzler.py --seed 77 --stats
```

### List all stations alphabetically

```bash
python3 metro_map_puzzler.py --seed 77 --list-stations
```

### Export a generated network to JSON

```bash
python3 metro_map_puzzler.py --seed 77 --export exports/metro_seed_77.json --stats
```

### Play quiz mode

```bash
python3 metro_map_puzzler.py --seed 77 --quiz 3
```

In quiz mode, enter station names separated by commas. You can also type:

- `hint` — reveal the best route
- `show` — same as `hint`
- `quit` — stop the session early

## Output notes

- Station names change with the seed, so solve examples should be run after checking the legend or station list.
- If you mistype a station name, the CLI suggests close matches when possible.
- Colors are shown only on TTY output unless `--no-color` is used.
- The generator retries nearby seeds automatically if a particular layout attempt fails.

## JSON export format

The exported file contains:

- seed
- map width and height
- all stations with coordinates
- line definitions and station order
- computed network statistics

## Running tests

```bash
python3 -m unittest -v test_metro_map_puzzler.py
```

## Project files

- `metro_map_puzzler.py` — generator, renderer, puzzle engine, route solver, CLI
- `test_metro_map_puzzler.py` — unit tests
- `README.md` — project documentation
