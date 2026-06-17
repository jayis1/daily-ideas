# 🏛️ Maze Generator & Pathfinder Visualizer

Generate mazes with multiple algorithms and watch pathfinding solve them in real-time ASCII animation — right in your terminal.

## What It Does

This tool combines two things: **maze generation** and **pathfinding visualization**. First, it carves a perfect maze using one of four generation algorithms. Then it animates a pathfinding algorithm exploring that maze step by step, showing you exactly how the search frontier expands, which cells get visited, and the final solution path.

You can also run **compare mode** to race all four solvers on the same maze and see which one visits the fewest cells.

## Features

### Maze Generation Algorithms
- **DFS (Recursive Backtracker)** — Creates long winding corridors with a strong directional bias. The most classic maze generation method.
- **Prim's** — Grows the maze organically from a seed cell, producing more branching paths with shorter dead ends.
- **Kruskal's** — Randomly merges disjoint sets, creating a more uniform distribution of passages.
- **Eller's** — Memory-efficient row-by-row algorithm that's great for wide mazes.

### Pathfinding Algorithms
- **BFS (Breadth-First Search)** — Explores layer by layer. Guarantees the shortest path but visits many cells.
- **DFS (Depth-First Search)** — Dives deep before backtracking. Fast but the path is rarely optimal.
- **A\*** — Uses Manhattan distance heuristic + actual cost. Optimal and efficient — the default solver.
- **Greedy Best-First** — Chases the goal using heuristic only. Often fast but can take suboptimal paths.

### Visualization
- **Color-coded ASCII rendering** — walls (dim), visited cells (gray dots), frontier (cyan circles), solution path (gold diamonds)
- **Real-time animation** — watch the algorithm think
- **Compare mode** — run all solvers on the same maze and compare stats side by side
- **Configurable speed** — slow it down to study or speed it up for results

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

### Full options
```
usage: maze_pathfinder.py [-h] [--rows ROWS] [--cols COLS]
                           [--generator {dfs,prim,kruskal,ellers}]
                           [--solver {bfs,dfs,astar,greedy}]
                           [--speed SPEED] [--seed SEED]
                           [--no-animate] [--compare]
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

## Color Legend

| Symbol | Color | Meaning |
|--------|-------|---------|
| `█` | Dim | Wall |
| ` ` | — | Unvisited passage |
| `·` | Gray | Visited cell |
| `○` | Cyan | Search frontier |
| `◆` | Gold | Solution path |
| `S` | Green | Start |
| `E` | Red | End |

## How It Works

1. **Generation**: A `MazeGrid` of cells with directional walls (N/S/E/W) is created. The chosen algorithm removes walls to carve passages, then the grid is converted to a 2D character bitmap (2R+1 × 2C+1).

2. **Pathfinding**: The bitmap is converted to an adjacency graph. Each solver is a Python generator that yields `(visited_set, frontier_set, path_or_none)` at each step, enabling frame-by-frame animation.

3. **Rendering**: Each frame overlays the algorithm's state onto the maze bitmap with ANSI color codes, then clears the terminal for the next frame.