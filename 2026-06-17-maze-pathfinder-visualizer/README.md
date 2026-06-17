# 🏛️ Maze Generator & Pathfinder Visualizer

**v1.3.0** — Generate mazes with five algorithms and watch five pathfinding solvers explore them in real-time ASCII animation, right in your terminal.

## What It Does

This tool combines **maze generation** and **pathfinding visualization**. Generate a perfect maze using one of five algorithms, then animate a solver exploring it step by step — showing you exactly how the search frontier expands, which cells get visited, and the final solution path.

Run **compare mode** to race all five solvers on the same maze and see which one visits the fewest cells. Use **heatmap mode** to overlay visit-frequency data from all solvers, revealing the corridors every algorithm explores. Save mazes to JSON, load them later, export solutions to plain text, or print path coordinates for scripting.

## Features

### Maze Generation Algorithms
- **DFS (Recursive Backtracker)** — Creates long winding corridors with a strong directional bias. The most classic maze generation method.
- **Prim's** — Grows the maze organically from a seed cell, producing more branching paths with shorter dead ends.
- **Kruskal's** — Randomly merges disjoint sets using Union-Find, creating a more uniform distribution of passages.
- **Eller's** — Memory-efficient row-by-row algorithm that's great for wide mazes.
- **Wilson's** — Loop-erased random walk producing uniform random spanning trees. Every possible maze is equally likely — the gold standard for fairness.

### Pathfinding Algorithms
- **BFS (Breadth-First Search)** — Explores layer by layer. Guarantees the shortest path but visits many cells.
- **DFS (Depth-First Search)** — Dives deep before backtracking. Fast but the path is rarely optimal.
- **A\*** — Uses Manhattan distance heuristic + actual cost. Optimal and efficient — the default solver.
- **Greedy Best-First** — Chases the goal using heuristic only. Often fast but can take suboptimal paths.
- **Dijkstra** — Uniform cost search using a priority queue. Optimal like BFS; included as a classic reference algorithm.

### Visualization & Output
- **Color-coded ASCII rendering** — walls (dim `█`), visited cells (gray `·`), frontier (cyan `○`), solution path (gold `◆`), start (`S`), end (`E`)
- **Real-time animation** — watch the algorithm think, with percentage progress per step
- **Step counter** — shows cells explored / total passable cells at each frame
- **Compare mode** — run all five solvers on the same maze and compare stats side-by-side with efficiency ratings; ties broken by fewest cells explored
- **Heatmap mode** (`--heatmap`) — overlay visit frequency from all solvers using gradient characters, revealing hot spots and under-explored areas
- **Maze difficulty rating** — Easy / Medium / Hard / Expert based on size, dead-end density, and branching factor
- **Solution path output** (`--show-path`) — print the full solution path as `(row,col)` coordinates
- **Custom start/end positions** (`--start` / `--end`) — solve from any cell to any cell
- **Configurable speed** — slow it down to study or speed it up for results
- **Maze statistics** — dead ends, branching factor, reachable passage count, difficulty rating
- **Save/Load** — persist mazes as JSON files, reload and solve them with any algorithm
- **Export** — save solved mazes to plain text files (no ANSI codes); works in both single-solver and compare mode
- **Version flag** — `--version` support
- **Robust file validation** — `--load` validates JSON structure thoroughly and reports clear errors

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
python3 maze_pathfinder.py -g prim
python3 maze_pathfinder.py -g kruskal
python3 maze_pathfinder.py -g ellers
python3 maze_pathfinder.py -g wilson       # New! Unbiased random spanning tree
```

### Choose pathfinding algorithm
```bash
python3 maze_pathfinder.py -s bfs
python3 maze_pathfinder.py -s dfs
python3 maze_pathfinder.py -s greedy
python3 maze_pathfinder.py -s dijkstra     # New! Classic uniform-cost search
```

### Adjust maze size
```bash
python3 maze_pathfinder.py -r 6 -c 20
```

### Show visit-frequency heatmap
```bash
python3 maze_pathfinder.py --heatmap -r 8 -c 20
```

### Custom start and end positions
```bash
python3 maze_pathfinder.py --start 3,3 --end 15,59 -r 8 -c 30
```

### Print the solution path as coordinates
```bash
python3 maze_pathfinder.py --show-path --no-animate -r 5 -c 10
```

### Compare all solvers on the same maze
```bash
python3 maze_pathfinder.py --compare
```

### Compare mode with no animation (just the final result)
```bash
python3 maze_pathfinder.py --compare --no-animate
```

### Show maze statistics (with difficulty rating)
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
  Difficulty:     Medium
```

### Save a maze to JSON
```bash
python3 maze_pathfinder.py --save maze.json -r 10 -c 20 --seed 42
```

### Load and solve a saved maze
```bash
python3 maze_pathfinder.py --load maze.json -s greedy
```

### Export solution to a plain text file
```bash
python3 maze_pathfinder.py --export result.txt -r 5 -c 15
```

### Export with compare mode
```bash
python3 maze_pathfinder.py --compare --export result.txt -r 5 -c 15
```

### Export heatmap to text
```bash
python3 maze_pathfinder.py --heatmap --export heatmap.txt -r 8 -c 20
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
# maze_pathfinder.py 1.3.0
```

### Full options
```
usage: maze_pathfinder.py [-h] [--rows ROWS] [--cols COLS]
                           [--generator {dfs,prim,kruskal,ellers,wilson}]
                           [--solver {bfs,dfs,astar,greedy,dijkstra}]
                           [--speed SPEED] [--seed SEED] [--start R,C]
                           [--end R,C] [--no-animate] [--compare] [--heatmap]
                           [--stats] [--show-path] [--save FILE]
                           [--load FILE] [--export FILE] [--version]
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

**Wilson's maze with Dijkstra solver:**
```bash
python3 maze_pathfinder.py -g wilson -s dijkstra -r 10 -c 20
```

**Heatmap of all solver visit patterns:**
```bash
python3 maze_pathfinder.py --heatmap -r 8 -c 20 --no-animate
```

**Custom start and end with path output:**
```bash
python3 maze_pathfinder.py --start 1,1 --end 19,39 --show-path -r 10 -c 20
```

**Deterministic maze for benchmarking:**
```bash
python3 maze_pathfinder.py -r 10 -c 25 --seed 999 --no-animate --compare
```

**Save, then load and solve with a different algorithm:**
```bash
python3 maze_pathfinder.py --save my_maze.json -r 8 -c 15 --seed 7
python3 maze_pathfinder.py --load my_maze.json -s dijkstra --no-animate
```

**Get stats, path, and export:**
```bash
python3 maze_pathfinder.py --stats --show-path --export solution.txt -r 6 -c 12
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

### Heatmap Characters

| Char | Level | Meaning |
|------|-------|---------|
| ` ` | 0 | Never visited |
| `.` | 1 | Rarely visited |
| `:` | 2 | Light traffic |
| `-` | 3 | Moderate traffic |
| `=` | 4 | Moderate traffic |
| `+` | 5 | Above average |
| `*` | 6 | Well-traveled |
| `#` | 7 | Frequently visited |
| `%` | 8 | Heavily visited |
| `@` | 9 | Visited by every solver |

## How It Works

1. **Generation**: A `MazeGrid` of cells with directional walls (N/S/E/W) is created. The chosen algorithm removes walls to carve passages, then the grid is converted to a 2D character bitmap (2R+1 × 2C+1).

2. **Pathfinding**: The bitmap is converted to an adjacency graph. Each solver is a Python generator that yields `(visited_set, frontier_set, path_or_none)` at each step, enabling frame-by-frame animation.

3. **Rendering**: Each frame overlays the algorithm's state onto the maze bitmap with ANSI color codes, then clears the terminal for the next frame. Step progress shows percentage of passable cells explored.

4. **Heatmap**: All five solvers are run on the same maze. Each cell's visit count is tallied and mapped to a gradient character, showing which areas are always explored vs. which are solver-specific.

5. **Difficulty**: Computed from maze size (bigger = harder), dead-end density (more = harder), and average branching factor (more open passages = harder). Rated Easy / Medium / Hard / Expert.

## Error Handling

The tool validates inputs and provides clear error messages:
- Maze dimensions below 2×2 are rejected
- Negative animation speeds are rejected
- Loading a missing file reports `Error: File not found`
- Invalid JSON reports the parse error
- Malformed maze files (wrong cell types, missing keys, dimension mismatches) report specific `Error:` messages instead of crashing with tracebacks
- Custom start/end positions that land on walls are rejected with a clear message
- Invalid position format is caught and explained

## Running Tests

```bash
python3 -m pytest test_maze_pathfinder.py -v
```

The test suite covers all five generation algorithms, all five solvers, maze connectivity validation, serialization round-trips, rendering, heatmap computation, difficulty rating, custom positions, file I/O, input validation for malformed data, edge cases, and more (72 tests total).

## Changelog

### v1.3.0
- **Added**: Wilson's algorithm (`-g wilson`) for unbiased random spanning tree maze generation — every maze is equally likely
- **Added**: Dijkstra's algorithm (`-s dijkstra`) as a fifth pathfinding solver — classic uniform-cost search
- **Added**: `--heatmap` flag to show visit-frequency overlay from all solvers, with gradient characters (`.:-=+*#%@`) and color coding
- **Added**: `--start R,C` and `--end R,C` flags for custom start/end positions, with wall-cell and bounds validation
- **Added**: `--show-path` flag to print the full solution path as `(row,col)` coordinates
- **Added**: Maze difficulty rating (Easy / Medium / Hard / Expert) in `--stats` output, based on size, dead-end density, and branching factor
- **Added**: Progress percentage in animation steps (e.g., `Exploring... 42% visited (50/119)`)
- **Added**: Type hints throughout the codebase for better IDE support and readability
- **Added**: Heatmap export support via `--heatmap --export FILE`
- **Added**: 14 new tests covering Wilson generation, Dijkstra solver, heatmap computation, difficulty rating, and custom positions
- **Fixed**: Wilson's algorithm could loop infinitely when picking out-of-bounds directions during random walks — now only valid in-bounds neighbors are considered
- **Improved**: Compare mode now includes Dijkstra in the solver lineup (5 solvers instead of 4)