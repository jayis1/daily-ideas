# 🏛️ Maze Generator & Pathfinder Visualizer

**v1.2.0** — Generate mazes with four algorithms and watch pathfinding solve them in real-time ASCII animation, right in your terminal.

## What It Does

This tool combines **maze generation** and **pathfinding visualization**. First, it carves a perfect maze using one of four generation algorithms. Then it animates a pathfinding algorithm exploring that maze step by step, showing you exactly how the search frontier expands, which cells get visited, and the final solution path.

Run **compare mode** to race all four solvers on the same maze and see which one visits the fewest cells. Save mazes to JSON, load them later, or export solutions to plain text files.

## Features

### Maze Generation Algorithms
- **DFS (Recursive Backtracker)** — Creates long winding corridors with a strong directional bias. The most classic maze generation method.
- **Prim's** — Grows the maze organically from a seed cell, producing more branching paths with shorter dead ends.
- **Kruskal's** — Randomly merges disjoint sets using Union-Find, creating a more uniform distribution of passages.
- **Eller's** — Memory-efficient row-by-row algorithm that's great for wide mazes.

### Pathfinding Algorithms
- **BFS (Breadth-First Search)** — Explores layer by layer. Guarantees the shortest path but visits many cells.
- **DFS (Depth-First Search)** — Dives deep before backtracking. Fast but the path is rarely optimal.
- **A\*** — Uses Manhattan distance heuristic + actual cost. Optimal and efficient — the default solver.
- **Greedy Best-First** — Chases the goal using heuristic only. Often fast but can take suboptimal paths.

### Visualization & Output
- **Color-coded ASCII rendering** — walls (dim `█`), visited cells (gray `·`), frontier (cyan `○`), solution path (gold `◆`), start (`S`), end (`E`)
- **Real-time animation** — watch the algorithm think
- **Step counter** — shows exploration progress at each step
- **Compare mode** — run all solvers on the same maze and compare stats side by side with efficiency ratings; ties broken by fewest cells explored
- **Configurable speed** — slow it down to study or speed it up for results
- **Maze statistics** — dead ends, branching factor, reachable passage count
- **Save/Load** — persist mazes as JSON files, reload and solve them with any algorithm
- **Export** — save solved mazes to plain text files (no ANSI codes) for sharing or piping; works with both single-solver and compare mode
- **Version flag** — `--version` support
- **Robust file validation** — `--load` validates JSON structure thoroughly (cell types, dimensions, required keys) and reports clear errors instead of crashing

## Installation

No dependencies needed — uses only Python standard library:

```bash
# Just clone and run
git clone <repo-url>
cd maze-pathfinder-visualizer
```

Requires Python 3.7+.

## Usage

### Basic — generate and solve a maze with animation
```bash
python3 maze_pathfinder.py
```

### Choose generation algorithm
```bash
python3 maze_pathfinder.py --generator prim
python3 maze_pathfinder.py --generator kruskal
python3 maze_pathfinder.py --generator ellers
```

### Choose pathfinding algorithm
```bash
python3 maze_pathfinder.py --solver bfs
python3 maze_pathfinder.py --solver dfs
python3 maze_pathfinder.py --solver greedy
```

### Adjust maze size
```bash
python3 maze_pathfinder.py --rows 6 --cols 20
```

### Compare all solvers on the same maze
```bash
python3 maze_pathfinder.py --compare
```

### Compare mode with no animation (just the final result)
```bash
python3 maze_pathfinder.py --compare --no-animate
```

### Show maze statistics
```bash
python3 maze_pathfinder.py --stats --no-animate
```

Output:
```
  Maze Statistics
  ────────────────────────
  Size:           12×30
  Total cells:    360
  Dead ends:      47 (13.1%)
  Avg branching:  1.97
  Reachable:      707 passages
```

### Save a maze to JSON
```bash
python3 maze_pathfinder.py --save maze.json -r 10 -c 20 --seed 42
```

### Load and solve a saved maze
```bash
python3 maze_pathfinder.py --load maze.json --solver greedy
```

### Export solution to a plain text file
```bash
python3 maze_pathfinder.py --export result.txt -r 5 -c 15
```

### Export with compare mode
```bash
python3 maze_pathfinder.py --compare --export result.txt -r 5 -c 15
```

### Skip animation, just show final result
```bash
python3 maze_pathfinder.py --no-animate
```

### Reproducible mazes with a seed
```bash
python3 maze_pathfinder.py --seed 42
```

### Slow down the animation for study
```bash
python3 maze_pathfinder.py --speed 0.1
```

### Check version
```bash
python3 maze_pathfinder.py --version
# maze_pathfinder.py 1.2.0
```

### Full options
```
usage: maze_pathfinder.py [-h] [--rows ROWS] [--cols COLS]
                           [--generator {dfs,prim,kruskal,ellers}]
                           [--solver {bfs,dfs,astar,greedy}] [--speed SPEED]
                           [--seed SEED] [--no-animate] [--compare] [--stats]
                           [--save FILE] [--load FILE] [--export FILE]
                           [--version]

Examples:
  maze_pathfinder.py                                    # Default: DFS maze, A* solver
  maze_pathfinder.py -g prim -s bfs                    # Prim's maze, BFS solver
  maze_pathfinder.py -r 8 -c 25 --seed 42              # Reproducible 8x25 maze
  maze_pathfinder.py --compare --speed 0.01            # Race all solvers
  maze_pathfinder.py --compare --no-animate            # Compare, no animation
  maze_pathfinder.py --no-animate --stats              # Stats only, no animation
  maze_pathfinder.py --save maze.json -r 10 -c 20      # Save maze to file
  maze_pathfinder.py --load maze.json -s greedy         # Load and solve saved maze
  maze_pathfinder.py --export result.txt -r 5 -c 15    # Export solution to text file
  maze_pathfinder.py --compare --export result.txt      # Export compare mode winner
```

## Examples

**Small maze with A\*:**
```bash
python3 maze_pathfinder.py -r 5 -c 12 -g dfs -s astar
```

**Large maze with compare mode:**
```bash
python3 maze_pathfinder.py -r 15 -c 40 --compare --speed 0.005
```

**Deterministic maze for benchmarking:**
```bash
python3 maze_pathfinder.py -r 10 -c 25 --seed 999 --no-animate --compare
```

**Save, then load and solve with a different algorithm:**
```bash
python3 maze_pathfinder.py --save my_maze.json -r 8 -c 15 --seed 7
python3 maze_pathfinder.py --load my_maze.json --solver bfs --no-animate
```

**Get stats and export:**
```bash
python3 maze_pathfinder.py --stats --export solution.txt -r 6 -c 12
```

**Compare mode with export:**
```bash
python3 maze_pathfinder.py --compare --export compare_result.txt -r 6 -c 12
```

## Color Legend

| Symbol | Color | Meaning |
|--------|-------|---------|
| `█` | Dim | Wall |
| ` ` | — | Unvisited passage |
| `·` | Gray | Visited cell |
| `○` | Cyan | Search frontier |
| `◆` | Gold | Solution path |
| `✕` | Red | Dead end (in stats mode) |
| `S` | Green | Start |
| `E` | Red | End |

## How It Works

1. **Generation**: A `MazeGrid` of cells with directional walls (N/S/E/W) is created. The chosen algorithm removes walls to carve passages, then the grid is converted to a 2D character bitmap (2R+1 × 2C+1).

2. **Pathfinding**: The bitmap is converted to an adjacency graph. Each solver is a Python generator that yields `(visited_set, frontier_set, path_or_none)` at each step, enabling frame-by-frame animation.

3. **Rendering**: Each frame overlays the algorithm's state onto the maze bitmap with ANSI color codes, then clears the terminal for the next frame.

## Error Handling

The tool validates inputs and provides clear error messages:
- Maze dimensions below 2×2 are rejected
- Negative animation speeds are rejected
- Loading a missing file reports `Error: File not found`
- Invalid JSON reports the parse error
- Malformed maze files (wrong cell types, missing keys, dimension mismatches) report specific `Error:` messages instead of crashing with tracebacks

## Running Tests

```bash
python3 -m pytest test_maze_pathfinder.py -v
```

The test suite covers all four generation algorithms, all four solvers, maze connectivity validation, serialization round-trips, rendering, file I/O, input validation for malformed data, edge cases, and more (58 tests total).

## Changelog

### v1.2.0
- **Fixed**: `load_maze()` crashed with unhandled `TypeError`/`KeyError`/`IndexError` on malformed JSON data (cells as string, missing cell keys, wrong dimensions). Now validates cell structure thoroughly and raises `ValueError` with clear messages.
- **Fixed**: `--export` flag was silently ignored when `--compare` was used (compare mode returned early before export). Export now works in compare mode, saving the winning solver's result.
- **Fixed**: `--compare --no-animate` printed every animation frame without clearing the screen, producing a flood of output. Now only prints the final solved frame when `--no-animate` is set.
- **Fixed**: Compare mode "best solver" selection was arbitrary when multiple solvers found the same path length. Now breaks ties by fewest cells explored (efficiency).
- **Improved**: `MazeGrid.stats()` accepts an optional `bitmap` parameter to avoid redundant `to_bitmap()` calls. `main()` now passes the already-computed bitmap.
- Added 8 new tests for `load_maze()` validation and `stats()` bitmap parameter.

### v1.1.0
- Added `--stats` flag to print maze statistics (dead ends, branching factor, reachable passages)
- Added `--save` flag to persist mazes as JSON files
- Added `--load` flag to load mazes from JSON files instead of generating
- Added `--export` flag to save solved mazes as plain text (no ANSI codes)
- Added `--version` flag showing version number
- Added step counter in animation output
- Added efficiency column in compare mode table
- Added Cell serialization (`to_dict`/`from_dict`) and MazeGrid JSON round-trip
- Added `export_plain()` for ANSI-free rendering
- Added dead-end symbol (`✕`) and stats rendering support
- Added input validation for maze dimensions and speed
- Added error handling for file I/O (missing files, invalid JSON, bad maze data)
- Improved compare mode to highlight best solver with `★` marker
- Improved code documentation with detailed docstrings
- Added comprehensive test suite (50 tests)