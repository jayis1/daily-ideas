# Metro Map Puzzler

Metro Map Puzzler is a pure-Python CLI that generates small fictional subway systems, renders them as ASCII maps, and turns each network into route-planning puzzles.

## Description

Given a random seed, the program builds a connected metro network with named stations, multiple lines, transfer hubs, and deterministic layouts. You can inspect the map, list stations, print summary statistics, solve trips between stations, export the generated network as JSON, or play an interactive quiz.

## Features

- Reproducible network generation with `--seed`
- Connected multi-line metro maps with interchange stations
- ASCII map rendering with optional ANSI colors
- Route solving with two optimization modes:
  - `balanced` — minimize stops first, then transfers
  - `transfers` — minimize transfers first, then stops
- Fuzzy station lookup with typo suggestions
- Alphabetical station index with coordinates and serving lines
- Network summary stats, including busiest interchange and longest line
- JSON export for generated maps
- Interactive quiz mode
- Standard-library only; no third-party dependencies
- Unit tests for generation, routing, rendering, parsing, export, and quiz EOF handling

## Requirements

- Python 3.11+

## Installation

```bash
cd ~/daily-ideas/2026-08-28-metro-map-puzzler
```

No package installation is required.

## How to run

### Default snapshot

```bash
python3 metro_map_puzzler.py
```

This prints:

- the generated metro map
- the station legend
- network statistics
- a featured puzzle
- the optimal route answer

### Help

```bash
python3 metro_map_puzzler.py --help
```

### Version

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

- `--seed SEED` — use a reproducible seed
- `--width WIDTH` — map width in characters
- `--height HEIGHT` — map height in characters
- `--lines LINES` — number of lines to generate, from `2` to `7`
- `--snapshot` — explicitly print the default snapshot view
- `--quiz ROUNDS` — start quiz mode for the given number of rounds
- `--solve FROM TO` — solve a route between two station names
- `--route-mode {balanced,transfers}` — choose stop-first or transfer-first solving
- `--list-stations` — print an alphabetical station list
- `--stats` — print only the network summary
- `--export PATH` — write the generated network to JSON
- `--no-color` — disable ANSI colors
- `--version` — print the version and exit

## Usage examples

### Print a network summary

```bash
python3 metro_map_puzzler.py --seed 77 --stats
```

### List all stations

```bash
python3 metro_map_puzzler.py --seed 77 --list-stations
```

### Solve a route

```bash
python3 metro_map_puzzler.py --seed 77 --solve "Grand Bridge" "Moon Depot"
```

### Prefer fewer transfers

```bash
python3 metro_map_puzzler.py --seed 77 --solve "Grand Bridge" "Moon Depot" --route-mode transfers
```

### Export JSON

```bash
python3 metro_map_puzzler.py --seed 77 --export exports/metro_seed_77.json --stats
```

### Play quiz mode

```bash
python3 metro_map_puzzler.py --seed 77 --quiz 3
```

Quiz commands:

- `hint` or `show` — reveal the best route
- `quit` — end the quiz early

## JSON export

The export file contains:

- seed
- width and height
- station list with IDs, names, and coordinates
- line definitions and station order
- computed network statistics

## Error handling notes

- Empty station names are rejected with a clear error message.
- Mistyped station names return close-match suggestions when available.
- Exporting to a directory path fails gracefully with a user-facing error instead of a traceback.
- Quiz mode exits cleanly if standard input closes unexpectedly.
- The generator retries nearby seeds automatically if one layout attempt fails.

## Running tests

```bash
python3 -m unittest -v test_metro_map_puzzler.py
```

## Known issues

- Station names vary by seed, so route examples should be adapted to the currently generated map.
- The map is optimized for terminal readability, not geographic realism.

## Changelog

### Bug-fix update

- Fixed quiz mode crashing with `EOFError` when input is closed or redirected.
- Fixed JSON export crashing with a traceback when the export destination is a directory.
- Fixed empty `--solve` station names producing a misleading ambiguity error.
- Added tests covering the above bug fixes.
