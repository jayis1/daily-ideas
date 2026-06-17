#!/usr/bin/env python3
"""
Maze Generator & Pathfinder Visualizer
========================================
Generates mazes using different algorithms and visualizes
pathfinding algorithms solving them in real-time ASCII animation.

Features:
  - 4 maze generation algorithms (DFS, Prim's, Kruskal's, Eller's)
  - 4 pathfinding algorithms (BFS, DFS, A*, Greedy Best-First)
  - Real-time color-coded ASCII animation
  - Compare mode to race all solvers side-by-side
  - Save/load mazes as JSON
  - Export final result to text file (no ANSI codes)
  - Maze statistics (dead ends, corridor length, branching factor)
  - Deterministic seed support for reproducible mazes
  - Customizable start/end positions

Version: 1.2.0
"""

import json
import random
import time
import sys
import os
import argparse
from collections import deque
import heapq

__version__ = "1.2.0"

# ─── Constants ───────────────────────────────────────────────────────────────

WALL = "█"
PATH = " "
VISITED = "·"
FRONTIER = "○"
START = "S"
END = "E"
SOLUTION = "◆"
DEAD_END = "✕"

# ─── Maze Generation ──────────────────────────────────────────────────────────

class Cell:
    """Represents a single cell in the maze grid with four directional walls."""

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.walls = {"N": True, "S": True, "E": True, "W": True}
        self.visited = False

    def to_dict(self):
        """Serialize cell state to a dictionary."""
        return {
            "row": self.row,
            "col": self.col,
            "walls": dict(self.walls),
        }

    @classmethod
    def from_dict(cls, d):
        """Deserialize cell from a dictionary."""
        cell = cls(d["row"], d["col"])
        cell.walls = d["walls"]
        cell.visited = False
        return cell


OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
DIRECTIONS = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
}


class MazeGrid:
    """Internal representation: a grid of cells with walls between them.

    Each cell tracks which of its four walls (N, S, E, W) are still standing.
    Generation algorithms remove walls to carve passages, and to_bitmap()
    converts this into a 2D character grid for rendering and pathfinding.
    """

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.cells = [[Cell(r, c) for c in range(cols)] for r in range(rows)]

    def get(self, r, c):
        """Return the cell at (r, c), or None if out of bounds."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.cells[r][c]
        return None

    def neighbors(self, cell):
        """Return adjacent cells that are connected (wall removed between them)."""
        result = []
        for d, (dr, dc) in DIRECTIONS.items():
            n = self.get(cell.row + dr, cell.col + dc)
            if n and not cell.walls[d]:
                result.append(n)
        return result

    def dead_ends(self):
        """Return list of cells that are dead ends (exactly one open passage)."""
        ends = []
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                open_count = sum(1 for w in cell.walls.values() if not w)
                if open_count == 1:
                    ends.append(cell)
        return ends

    def stats(self, bitmap=None):
        """Compute maze statistics: dead ends, avg corridor length, branching factor.

        Args:
            bitmap: Pre-computed bitmap to avoid recomputing. If None, computed here.
        """
        dead_end_list = self.dead_ends()
        num_dead_ends = len(dead_end_list)
        total_cells = self.rows * self.cols

        # Count cells by number of open passages (branching factor)
        passage_counts = {}
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                open_count = sum(1 for w in cell.walls.values() if not w)
                passage_counts[open_count] = passage_counts.get(open_count, 0) + 1

        # Average open passages per cell (branching factor)
        total_passages = sum(k * v for k, v in passage_counts.items())
        avg_branching = total_passages / total_cells if total_cells > 0 else 0

        # Longest corridor (BFS from start)
        if bitmap is None:
            bitmap = self.to_bitmap()
        start = (1, 1)
        visited_bfs = {start}
        queue = deque([start])
        max_dist = 0
        while queue:
            pos = queue.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = pos[0] + dr, pos[1] + dc
                if 0 <= nr < len(bitmap) and 0 <= nc < len(bitmap[0]):
                    if bitmap[nr][nc] != WALL and (nr, nc) not in visited_bfs:
                        visited_bfs.add((nr, nc))
                        queue.append((nr, nc))

        reachable = len(visited_bfs)

        return {
            "size": f"{self.rows}×{self.cols}",
            "total_cells": total_cells,
            "dead_ends": num_dead_ends,
            "dead_end_pct": f"{100 * num_dead_ends / total_cells:.1f}%" if total_cells > 0 else "0%",
            "avg_branching": f"{avg_branching:.2f}",
            "reachable_passages": reachable,
        }

    def to_bitmap(self):
        """Convert the cell-wall maze to a 2D character bitmap (2R+1 x 2C+1).

        Each cell maps to position (2r+1, 2c+1) in the bitmap. Walls between
        cells are represented at even row/col positions. This format is used
        for both rendering and pathfinding.
        """
        h = 2 * self.rows + 1
        w = 2 * self.cols + 1
        grid = [[WALL for _ in range(w)] for _ in range(h)]
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                gr, gc = 2 * r + 1, 2 * c + 1
                grid[gr][gc] = PATH
                if not cell.walls["S"] and r + 1 < self.rows:
                    grid[gr + 1][gc] = PATH
                if not cell.walls["E"] and c + 1 < self.cols:
                    grid[gr][gc + 1] = PATH
        return grid

    def to_dict(self):
        """Serialize the entire maze to a dictionary for JSON export."""
        return {
            "rows": self.rows,
            "cols": self.cols,
            "cells": [
                [self.cells[r][c].to_dict() for c in range(self.cols)]
                for r in range(self.rows)
            ],
        }

    @classmethod
    def from_dict(cls, d):
        """Deserialize a maze from a dictionary."""
        maze = cls(d["rows"], d["cols"])
        maze.cells = [
            [Cell.from_dict(d["cells"][r][c]) for c in range(d["cols"])]
            for r in range(d["rows"])
        ]
        return maze

    def to_json(self):
        """Serialize the maze to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str):
        """Deserialize a maze from a JSON string."""
        return cls.from_dict(json.loads(json_str))


# ─── Generation Algorithms ────────────────────────────────────────────────────

def generate_dfs(rows, cols, seed=None):
    """Recursive-backtracker (DFS) maze generation.

    Creates long winding corridors with a strong directional bias.
    The most classic and widely-used maze generation method.
    """
    if rows < 2 or cols < 2:
        raise ValueError(f"Maze must be at least 2x2, got {rows}x{cols}")

    rng = random.Random(seed)
    maze = MazeGrid(rows, cols)
    stack = []
    start = maze.get(0, 0)
    start.visited = True
    stack.append(start)
    while stack:
        current = stack[-1]
        unvisited = []
        for d, (dr, dc) in DIRECTIONS.items():
            n = maze.get(current.row + dr, current.col + dc)
            if n and not n.visited:
                unvisited.append((d, n))
        if unvisited:
            d, n = rng.choice(unvisited)
            current.walls[d] = False
            n.walls[OPPOSITE[d]] = False
            n.visited = True
            stack.append(n)
        else:
            stack.pop()
    return maze


def generate_prim(rows, cols, seed=None):
    """Prim's algorithm maze generation.

    Grows the maze organically from a seed cell, producing more branching
    paths with shorter dead ends compared to DFS.
    """
    if rows < 2 or cols < 2:
        raise ValueError(f"Maze must be at least 2x2, got {rows}x{cols}")

    rng = random.Random(seed)
    maze = MazeGrid(rows, cols)
    start = maze.get(0, 0)
    start.visited = True
    walls = []
    for d, (dr, dc) in DIRECTIONS.items():
        n = maze.get(start.row + dr, start.col + dc)
        if n and not n.visited:
            walls.append((start, d, n))
    while walls:
        idx = rng.randint(0, len(walls) - 1)
        cell, d, n = walls.pop(idx)
        if not n.visited:
            cell.walls[d] = False
            n.walls[OPPOSITE[d]] = False
            n.visited = True
            for d2, (dr2, dc2) in DIRECTIONS.items():
                n2 = maze.get(n.row + dr2, n.col + dc2)
                if n2 and not n2.visited:
                    walls.append((n, d2, n2))
    return maze


def generate_kruskal(rows, cols, seed=None):
    """Kruskal's algorithm maze generation.

    Randomly merges disjoint sets using Union-Find, creating a more
    uniform distribution of passages. Produces mazes with many short
    dead ends.
    """
    if rows < 2 or cols < 2:
        raise ValueError(f"Maze must be at least 2x2, got {rows}x{cols}")

    rng = random.Random(seed)
    maze = MazeGrid(rows, cols)

    # Union-Find with path compression and union by rank
    parent = {}
    rank = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # Path compression
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True

    for r in range(rows):
        for c in range(cols):
            key = (r, c)
            parent[key] = key
            rank[key] = 0

    edges = []
    for r in range(rows):
        for c in range(cols):
            if r + 1 < rows:
                edges.append(((r, c), "S", (r + 1, c)))
            if c + 1 < cols:
                edges.append(((r, c), "E", (r, c + 1)))
    rng.shuffle(edges)

    for (r1, c1), d, (r2, c2) in edges:
        if union((r1, c1), (r2, c2)):
            maze.get(r1, c1).walls[d] = False
            maze.get(r2, c2).walls[OPPOSITE[d]] = False

    return maze


def generate_ellers(rows, cols, seed=None):
    """Eller's algorithm maze generation — efficient for wide mazes.

    Builds the maze row by row, using O(cols) memory. Great for
    generating very wide mazes efficiently.
    """
    if rows < 2 or cols < 2:
        raise ValueError(f"Maze must be at least 2x2, got {rows}x{cols}")

    rng = random.Random(seed)
    maze = MazeGrid(rows, cols)
    # Each cell's set id
    set_id = {}
    next_id = 0

    for r in range(rows):
        # Assign set ids for unassigned cells in this row
        for c in range(cols):
            key = (r, c)
            if key not in set_id:
                set_id[key] = next_id
                next_id += 1

        # Decide horizontal merges (east walls)
        for c in range(cols - 1):
            if r == rows - 1 or rng.random() < 0.5:
                k1 = (r, c)
                k2 = (r, c + 1)
                if set_id[k1] != set_id[k2]:
                    maze.get(r, c).walls["E"] = False
                    maze.get(r, c + 1).walls["W"] = False
                    old_id = set_id[k2]
                    new_id = set_id[k1]
                    for k in list(set_id.keys()):
                        if set_id[k] == old_id:
                            set_id[k] = new_id

        # If last row, skip vertical connections
        if r == rows - 1:
            break

        # Decide vertical connections (south walls)
        # For each set in this row, connect at least one cell downward
        sets_in_row = {}
        for c in range(cols):
            sid = set_id[(r, c)]
            if sid not in sets_in_row:
                sets_in_row[sid] = []
            sets_in_row[sid].append(c)

        connected_down = set()
        for sid, members in sets_in_row.items():
            # Connect at least one member downward
            rng.shuffle(members)
            connect_count = rng.randint(1, len(members))
            for i in range(connect_count):
                c = members[i]
                maze.get(r, c).walls["S"] = False
                maze.get(r + 1, c).walls["N"] = False
                set_id[(r + 1, c)] = sid
                connected_down.add((r + 1, c))

    return maze


GENERATORS = {
    "dfs": generate_dfs,
    "prim": generate_prim,
    "kruskal": generate_kruskal,
    "ellers": generate_ellers,
}


# ─── Pathfinding Algorithms ───────────────────────────────────────────────────

def _bitmap_to_graph(bitmap):
    """Convert bitmap grid to adjacency list for pathfinding.

    Each passable cell (non-WALL) becomes a node with edges to its
    cardinal neighbors that are also passable.
    """
    h, w = len(bitmap), len(bitmap[0])
    graph = {}
    for r in range(h):
        for c in range(w):
            if bitmap[r][c] != WALL:
                graph[(r, c)] = []
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and bitmap[nr][nc] != WALL:
                        graph[(r, c)].append((nr, nc))
    return graph


def solve_bfs(bitmap, start, end):
    """Breadth-First Search — yields (visited_set, frontier_set, path_or_None).

    Explores layer by layer. Guarantees the shortest path but visits
    many cells. Good for demonstrating uniform-cost exploration.
    """
    graph = _bitmap_to_graph(bitmap)
    visited = {start}
    frontier = deque([start])
    parent = {start: None}

    while frontier:
        current = frontier.popleft()
        if current == end:
            # Reconstruct path by following parent pointers
            path = []
            node = end
            while node is not None:
                path.append(node)
                node = parent[node]
            yield set(visited), set(frontier), list(reversed(path))
            return
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                frontier.append(neighbor)
        yield set(visited), set(frontier), None

    yield set(visited), set(), None  # No path found


def solve_dfs(bitmap, start, end):
    """Depth-First Search — yields exploration steps.

    Dives deep before backtracking. Fast but the path is rarely optimal.
    Shows the top of the stack as the frontier indicator.
    """
    graph = _bitmap_to_graph(bitmap)
    visited = set()
    stack = [start]
    parent = {start: None}

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        if current == end:
            path = []
            node = end
            while node is not None:
                path.append(node)
                node = parent[node]
            yield set(visited), set(stack[-20:]), list(reversed(path))
            return
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                parent[neighbor] = current
                stack.append(neighbor)
        yield set(visited), set(stack[-20:]), None  # Show top of stack as frontier

    yield set(visited), set(), None


def solve_astar(bitmap, start, end):
    """A* Search — uses Manhattan distance heuristic + actual cost.

    Optimal and efficient — the best general-purpose solver.
    Uses f(n) = g(n) + h(n) where g is actual cost and h is heuristic.
    """
    graph = _bitmap_to_graph(bitmap)

    def heuristic(pos):
        return abs(pos[0] - end[0]) + abs(pos[1] - end[1])

    open_set = [(heuristic(start), 0, start)]
    g_score = {start: 0}
    parent = {start: None}
    visited = set()
    frontier_set = {start}

    while open_set:
        f, cost, current = heapq.heappop(open_set)
        frontier_set.discard(current)

        if current in visited:
            continue
        visited.add(current)

        if current == end:
            path = []
            node = end
            while node is not None:
                path.append(node)
                node = parent[node]
            yield set(visited), set(frontier_set), list(reversed(path))
            return

        for neighbor in graph.get(current, []):
            if neighbor in visited:
                continue
            tentative_g = cost + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                parent[neighbor] = current
                f_score = tentative_g + heuristic(neighbor)
                heapq.heappush(open_set, (f_score, tentative_g, neighbor))
                frontier_set.add(neighbor)

        yield set(visited), set(frontier_set), None

    yield set(visited), set(), None


def solve_greedy(bitmap, start, end):
    """Greedy Best-First Search — uses heuristic only, no cost tracking.

    Chases the goal using only the Manhattan distance heuristic. Often
    fast but can take suboptimal paths in complex mazes.
    """
    graph = _bitmap_to_graph(bitmap)

    def heuristic(pos):
        return abs(pos[0] - end[0]) + abs(pos[1] - end[1])

    open_set = [(heuristic(start), start)]
    visited = set()
    parent = {start: None}
    frontier_set = {start}

    while open_set:
        _, current = heapq.heappop(open_set)
        frontier_set.discard(current)

        if current in visited:
            continue
        visited.add(current)

        if current == end:
            path = []
            node = end
            while node is not None:
                path.append(node)
                node = parent[node]
            yield set(visited), set(frontier_set), list(reversed(path))
            return

        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                parent[neighbor] = current
                heapq.heappush(open_set, (heuristic(neighbor), neighbor))
                frontier_set.add(neighbor)

        yield set(visited), set(frontier_set), None

    yield set(visited), set(), None


SOLVERS = {
    "bfs": solve_bfs,
    "dfs": solve_dfs,
    "astar": solve_astar,
    "greedy": solve_greedy,
}


# ─── Rendering ────────────────────────────────────────────────────────────────

def render(bitmap, visited=None, frontier=None, solution=None,
           start=None, end=None, dead_ends=None, use_color=True):
    """Render the maze bitmap with overlaid pathfinding state.

    Args:
        bitmap: 2D list of characters representing the maze.
        visited: Set of (row, col) positions already explored.
        frontier: Set of (row, col) positions in the search frontier.
        solution: Set of (row, col) positions forming the solution path.
        start: (row, col) position of the start cell.
        end: (row, col) position of the end cell.
        dead_ends: Set of (row, col) dead-end positions to mark.
        use_color: If True, use ANSI color codes; if False, plain text.

    Returns:
        String representation of the rendered maze.
    """
    # Convert solution list to set for O(1) lookup
    if solution and isinstance(solution, list):
        solution = set(solution)

    h, w = len(bitmap), len(bitmap[0])
    lines = []
    for r in range(h):
        row_chars = []
        for c in range(w):
            pos = (r, c)
            if pos == start:
                row_chars.append(f"\033[92m{START}\033[0m" if use_color else START)
            elif pos == end:
                row_chars.append(f"\033[91m{END}\033[0m" if use_color else END)
            elif solution and pos in solution:
                row_chars.append(f"\033[93m{SOLUTION}\033[0m" if use_color else SOLUTION)
            elif frontier and pos in frontier:
                row_chars.append(f"\033[96m{FRONTIER}\033[0m" if use_color else FRONTIER)
            elif visited and pos in visited:
                row_chars.append(f"\033[90m{VISITED}\033[0m" if use_color else VISITED)
            elif dead_ends and pos in dead_ends:
                row_chars.append(f"\033[31m{DEAD_END}\033[0m" if use_color else DEAD_END)
            elif bitmap[r][c] == WALL:
                row_chars.append(f"\033[2m{WALL}\033[0m" if use_color else WALL)
            else:
                row_chars.append(PATH)
        lines.append("".join(row_chars))
    return "\n".join(lines)


def clear_screen():
    """Clear the terminal screen in a cross-platform way."""
    os.system("cls" if os.name == "nt" else "clear")


# ─── File I/O ─────────────────────────────────────────────────────────────────

def save_maze(maze, filepath):
    """Save a maze to a JSON file.

    Args:
        maze: MazeGrid instance to save.
        filepath: Path to the output JSON file.
    """
    data = maze.to_dict()
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def load_maze(filepath):
    """Load a maze from a JSON file.

    Args:
        filepath: Path to the input JSON file.

    Returns:
        MazeGrid instance loaded from the file.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        ValueError: If the maze data is invalid.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    # Validate required fields
    if "rows" not in data or "cols" not in data:
        raise ValueError("Invalid maze file: missing 'rows' or 'cols'")
    if not isinstance(data["rows"], int) or not isinstance(data["cols"], int):
        raise ValueError("Invalid maze file: 'rows' and 'cols' must be integers")
    if data["rows"] < 2 or data["cols"] < 2:
        raise ValueError(f"Invalid maze dimensions: {data['rows']}x{data['cols']}")
    if "cells" not in data:
        raise ValueError("Invalid maze file: missing 'cells'")

    # Validate cells structure
    if not isinstance(data["cells"], list):
        raise ValueError("Invalid maze file: 'cells' must be a 2D array")
    if len(data["cells"]) != data["rows"]:
        raise ValueError(
            f"Invalid maze file: cells has {len(data['cells'])} rows, expected {data['rows']}"
        )
    for r, row in enumerate(data["cells"]):
        if not isinstance(row, list):
            raise ValueError(f"Invalid maze file: cells row {r} is not a list")
        if len(row) != data["cols"]:
            raise ValueError(
                f"Invalid maze file: cells row {r} has {len(row)} columns, expected {data['cols']}"
            )
        for c, cell in enumerate(row):
            if not isinstance(cell, dict):
                raise ValueError(f"Invalid maze file: cells[{r}][{c}] is not a dict")
            if "row" not in cell or "col" not in cell or "walls" not in cell:
                raise ValueError(
                    f"Invalid maze file: cells[{r}][{c}] missing 'row', 'col', or 'walls'"
                )

    return MazeGrid.from_dict(data)


def export_plain(bitmap, solution=None, start=None, end=None):
    """Render maze as plain text without ANSI color codes.

    Useful for saving to files, piping to other commands, or
    terminals that don't support ANSI escape codes.
    """
    return render(bitmap, solution=solution, start=start, end=end, use_color=False)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Maze Generator & Pathfinder Visualizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s                                    # Default: DFS maze, A* solver
  %(prog)s -g prim -s bfs                    # Prim's maze, BFS solver
  %(prog)s -r 8 -c 25 --seed 42              # Reproducible 8x25 maze
  %(prog)s --compare --speed 0.01            # Race all solvers
  %(prog)s --no-animate --stats              # Stats only, no animation
  %(prog)s --save maze.json -r 10 -c 20      # Save maze to file
  %(prog)s --load maze.json -s greedy         # Load and solve saved maze
  %(prog)s --export result.txt -r 5 -c 15    # Export solution to text file
""",
    )
    parser.add_argument(
        "--rows", "-r", type=int, default=12,
        help="Maze rows (default: 12, min: 2)"
    )
    parser.add_argument(
        "--cols", "-c", type=int, default=30,
        help="Maze columns (default: 30, min: 2)"
    )
    parser.add_argument(
        "--generator", "-g",
        choices=list(GENERATORS.keys()),
        default="dfs",
        help="Maze generation algorithm (default: dfs)"
    )
    parser.add_argument(
        "--solver", "-s",
        choices=list(SOLVERS.keys()),
        default="astar",
        help="Pathfinding algorithm (default: astar)"
    )
    parser.add_argument(
        "--speed", type=float, default=0.02,
        help="Animation delay in seconds (default: 0.02)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-animate", action="store_true",
        help="Skip animation, just show final result"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Run all solvers on the same maze and compare stats"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print maze statistics (dead ends, branching factor, etc.)"
    )
    parser.add_argument(
        "--save", metavar="FILE",
        help="Save generated maze to a JSON file"
    )
    parser.add_argument(
        "--load", metavar="FILE",
        help="Load a maze from a JSON file instead of generating"
    )
    parser.add_argument(
        "--export", metavar="FILE",
        help="Export the final solved maze to a plain text file (no ANSI codes)"
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    rows = max(2, args.rows)
    cols = max(2, args.cols)

    # Validate speed
    if args.speed < 0:
        parser.error("Speed must be non-negative")

    # Load or generate maze
    if args.load:
        try:
            maze = load_maze(args.load)
            rows, cols = maze.rows, maze.cols
            seed = "loaded"
        except FileNotFoundError:
            print(f"Error: File not found: {args.load}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {args.load}: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        gen_func = GENERATORS[args.generator]
        seed = args.seed if args.seed is not None else random.randint(0, 999999)
        maze = gen_func(rows, cols, seed=seed)

    bitmap = maze.to_bitmap()

    # Default start (top-left) and end (bottom-right) positions
    start_pos = (1, 1)
    end_pos = (2 * rows - 1, 2 * cols - 1)

    # Show stats if requested
    if args.stats:
        s = maze.stats(bitmap=bitmap)
        print(f"\033[1m  Maze Statistics\033[0m")
        print(f"  ────────────────────────")
        print(f"  Size:           {s['size']}")
        print(f"  Total cells:    {s['total_cells']}")
        print(f"  Dead ends:      {s['dead_ends']} ({s['dead_end_pct']})")
        print(f"  Avg branching:  {s['avg_branching']}")
        print(f"  Reachable:      {s['reachable_passages']} passages")
        print()

    # Save maze if requested
    if args.save:
        save_maze(maze, args.save)
        print(f"  Maze saved to: {args.save}")

    # Compare mode: run all solvers on the same maze
    if args.compare:
        print(f"\033[1m  Maze Pathfinder Comparison\033[0m")
        print(f"  Maze: {rows}×{cols}  |  Generator: {args.generator if not args.load else 'loaded'}  |  Seed: {seed}")
        print()

        results = []
        for name, solver in SOLVERS.items():
            total_visited = 0
            path_len = 0
            steps = 0
            for visited, frontier, solution in solver(bitmap, start_pos, end_pos):
                steps += 1
                total_visited = len(visited)
                if solution:
                    path_len = len(solution)
            results.append((name, total_visited, path_len, steps))

        # Print comparison table
        print(f"  {'Algorithm':<14} {'Visited':>10} {'Path Len':>10} {'Steps':>10} {'Efficiency':>12}")
        print(f"  {'─' * 14} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 12}")
        for name, vis, plen, stps in results:
            eff = f"{plen/vis*100:.1f}%" if vis > 0 else "N/A"
            print(f"  {name:<14} {vis:>10} {plen:>10} {stps:>10} {eff:>12}")

        # Find best solver: shortest path, then fewest explored as tiebreaker
        best = min(results, key=lambda x: (x[2] if x[2] > 0 else float("inf"), x[1]))
        best_solution = None
        best_visited = None

        print(f"\n  \033[93m★ Best solver: {best[0]} (path: {best[2]} steps, explored: {best[1]} cells)\033[0m")
        print(f"  Animating {best[0]}...")
        print()

        solver = SOLVERS[best[0]]
        for visited, frontier, solution in solver(bitmap, start_pos, end_pos):
            if not args.no_animate:
                clear_screen()
            else:
                # In no-animate mode, skip to the final frame
                if solution is None:
                    continue
            frame = render(bitmap, visited, frontier, solution, start_pos, end_pos)
            print(frame)
            if solution:
                best_solution = solution
                best_visited = visited
                print(
                    f"\n  \033[1m{best[0].upper()}\033[0m — Path length: {len(solution)}, "
                    f"Cells explored: {len(visited)}"
                )
            if not args.no_animate:
                time.sleep(args.speed)

        # Export if requested (was previously skipped by early return)
        if args.export:
            try:
                plain = export_plain(bitmap, solution=best_solution,
                                     start=start_pos, end=end_pos)
                with open(args.export, "w") as f:
                    f.write(plain)
                    f.write(f"\n\nPath length: {len(best_solution) if best_solution else 0}")
                    f.write(f"\nCells explored: {len(best_visited) if best_visited else 0}")
                    f.write(f"\nSolver: {best[0]} (compare mode winner)")
                print(f"\n  Result exported to: {args.export}")
            except OSError as e:
                print(f"\n  Error exporting to {args.export}: {e}", file=sys.stderr)

        return

    # Single solver animation
    solver = SOLVERS[args.solver]

    if not args.no_animate:
        clear_screen()

    header = (
        f"\033[1m  Maze Generator & Pathfinder Visualizer\033[0m\n"
        f"  Maze: {rows}×{cols}  |  "
        f"Generator: {args.generator if not args.load else 'loaded'}  |  "
        f"Solver: {args.solver}  |  Seed: {seed}"
    )

    print(header)
    print()

    step = 0
    final_solution = None
    final_visited = None

    for visited, frontier, solution in solver(bitmap, start_pos, end_pos):
        step += 1
        if not args.no_animate:
            clear_screen()
            print(header)
            print()

        frame = render(bitmap, visited, frontier, solution, start_pos, end_pos)
        print(frame)

        if solution:
            final_solution = solution
            final_visited = visited
            print(
                f"\n  \033[1m{args.solver.upper()}\033[0m — "
                f"Path length: {len(solution)}, "
                f"Cells explored: {len(visited)}, "
                f"Steps: {step}"
            )
        else:
            explored = len(visited) if visited else 0
            print(f"  Step {step} | Exploring... cells visited: {explored}")

        if not args.no_animate:
            time.sleep(args.speed)

    # Export if requested
    if args.export:
        try:
            plain = export_plain(bitmap, solution=final_solution,
                                 start=start_pos, end=end_pos)
            with open(args.export, "w") as f:
                f.write(plain)
                f.write(f"\n\nPath length: {len(final_solution) if final_solution else 0}")
                f.write(f"\nCells explored: {len(final_visited) if final_visited else 0}")
                f.write(f"\nSolver: {args.solver}")
            print(f"\n  Result exported to: {args.export}")
        except OSError as e:
            print(f"\n  Error exporting to {args.export}: {e}", file=sys.stderr)

    # Handle no solution found
    if final_solution is None and not args.compare:
        print("\n  \033[91mNo path found!\033[0m", file=sys.stderr)


if __name__ == "__main__":
    main()