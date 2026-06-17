#!/usr/bin/env python3
"""
Maze Generator & Pathfinder Visualizer
========================================
Generates mazes using different algorithms and visualizes
pathfinding algorithms solving them in real-time ASCII animation.
"""

import random
import time
import sys
import os
import argparse
from collections import deque
import heapq

# ─── Constants ───────────────────────────────────────────────────────────────

WALL = "█"
PATH = " "
VISITED = "·"
FRONTIER = "○"
START = "S"
END = "E"
SOLUTION = "◆"

# ─── Maze Generation ──────────────────────────────────────────────────────────

class Cell:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.walls = {"N": True, "S": True, "E": True, "W": True}
        self.visited = False

OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
DIRECTIONS = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
}


class MazeGrid:
    """Internal representation: a grid of cells with walls between them."""

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.cells = [[Cell(r, c) for c in range(cols)] for r in range(rows)]

    def get(self, r, c):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.cells[r][c]
        return None

    def neighbors(self, cell):
        result = []
        for d, (dr, dc) in DIRECTIONS.items():
            n = self.get(cell.row + dr, cell.col + dc)
            if n and not cell.walls[d]:
                result.append(n)
        return result

    def to_bitmap(self):
        """Convert the cell-wall maze to a 2D character bitmap (2R+1 x 2C+1)."""
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


# ─── Generation Algorithms ────────────────────────────────────────────────────

def generate_dfs(rows, cols, seed=None):
    """Recursive-backtracker (DFS) maze generation."""
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
    """Prim's algorithm maze generation."""
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
    """Kruskal's algorithm maze generation."""
    rng = random.Random(seed)
    maze = MazeGrid(rows, cols)

    # Union-Find
    parent = {}
    rank = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
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
    """Eller's algorithm maze generation — efficient for wide mazes."""
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
                    for k in set_id:
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
    """Convert bitmap grid to adjacency list."""
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
    """Breadth-First Search — yields (visited_set, frontier_set, path_or_None)."""
    graph = _bitmap_to_graph(bitmap)
    visited = {start}
    frontier = deque([start])
    parent = {start: None}

    while frontier:
        current = frontier.popleft()
        if current == end:
            # Reconstruct path
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
    """Depth-First Search — yields exploration steps."""
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
            yield set(visited), set(), list(reversed(path))
            return
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                parent[neighbor] = current
                stack.append(neighbor)
        yield set(visited), set(stack[-20:]), None  # Show top of stack as frontier

    yield set(visited), set(), None


def solve_astar(bitmap, start, end):
    """A* Search — uses Manhattan distance heuristic."""
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
    """Greedy Best-First Search — uses heuristic only, no cost tracking."""
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


# ─── Rendering ─────────────────────────────────────────────────────────────────

def render(bitmap, visited=None, frontier=None, solution=None, start=None, end=None):
    """Render the maze bitmap with overlaid pathfinding state."""
    h, w = len(bitmap), len(bitmap[0])
    lines = []
    for r in range(h):
        row_chars = []
        for c in range(w):
            pos = (r, c)
            if pos == start:
                row_chars.append(f"\033[92m{START}\033[0m")
            elif pos == end:
                row_chars.append(f"\033[91m{END}\033[0m")
            elif solution and pos in solution:
                row_chars.append(f"\033[93m{SOLUTION}\033[0m")
            elif frontier and pos in frontier:
                row_chars.append(f"\033[96m{FRONTIER}\033[0m")
            elif visited and pos in visited:
                row_chars.append(f"\033[90m{VISITED}\033[0m")
            elif bitmap[r][c] == WALL:
                row_chars.append(f"\033[2m{WALL}\033[0m")
            else:
                row_chars.append(PATH)
        lines.append("".join(row_chars))
    return "\n".join(lines)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Maze Generator & Pathfinder Visualizer"
    )
    parser.add_argument(
        "--rows", "-r", type=int, default=12, help="Maze rows (default: 12)"
    )
    parser.add_argument(
        "--cols", "-c", type=int, default=30, help="Maze columns (default: 30)"
    )
    parser.add_argument(
        "--generator",
        "-g",
        choices=list(GENERATORS.keys()),
        default="dfs",
        help="Maze generation algorithm (default: dfs)",
    )
    parser.add_argument(
        "--solver",
        "-s",
        choices=list(SOLVERS.keys()),
        default="astar",
        help="Pathfinding algorithm (default: astar)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0.02,
        help="Animation delay in seconds (default: 0.02)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-animate",
        action="store_true",
        help="Skip animation, just show final result",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run all solvers on the same maze and compare stats",
    )
    args = parser.parse_args()

    rows = max(2, args.rows)
    cols = max(2, args.cols)

    # Generate maze
    gen_func = GENERATORS[args.generator]
    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    maze = gen_func(rows, cols, seed=seed)
    bitmap = maze.to_bitmap()

    start_pos = (1, 1)
    end_pos = (2 * rows - 1, 2 * cols - 1)

    if args.compare:
        # Run all solvers and compare
        print(f"\033[1m  Maze Pathfinder Comparison\033[0m")
        print(f"  Maze: {rows}×{cols}  |  Generator: {args.generator}  |  Seed: {seed}")
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

        # Header
        print(f"  {'Algorithm':<12} {'Visited':>10} {'Path Len':>10} {'Steps':>10}")
        print(f"  {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10}")
        for name, vis, plen, steps in results:
            print(f"  {name:<12} {vis:>10} {plen:>10} {steps:>10}")

        # Now animate the best one (shortest path)
        best = min(results, key=lambda x: x[2] if x[2] > 0 else float("inf"))
        print(f"\n  Animating {best[0]} (shortest path: {best[2]} steps)...")
        print()

        solver = SOLVERS[best[0]]
        for visited, frontier, solution in solver(bitmap, start_pos, end_pos):
            if not args.no_animate:
                clear_screen()
            frame = render(bitmap, visited, frontier, solution, start_pos, end_pos)
            print(frame)
            if solution:
                print(
                    f"\n  \033[1m{best[0].upper()}\033[0m — Path length: {len(solution)}, "
                    f"Cells explored: {len(visited)}"
                )
            if not args.no_animate:
                time.sleep(args.speed)
        return

    # Single solver animation
    solver = SOLVERS[args.solver]
    clear_screen()
    print(f"\033[1m  Maze Generator & Pathfinder Visualizer\033[0m")
    print(f"  Maze: {rows}×{cols}  |  Generator: {args.generator}  |  Solver: {args.solver}  |  Seed: {seed}")
    print()

    for visited, frontier, solution in solver(bitmap, start_pos, end_pos):
        if not args.no_animate:
            clear_screen()
            print(f"\033[1m  Maze Generator & Pathfinder Visualizer\033[0m")
            print(f"  Maze: {rows}×{cols}  |  Generator: {args.generator}  |  Solver: {args.solver}  |  Seed: {seed}")
            print()

        frame = render(bitmap, visited, frontier, solution, start_pos, end_pos)
        print(frame)

        if solution:
            print(
                f"\n  \033[1m{args.solver.upper()}\033[0m — Path length: {len(solution)}, "
                f"Cells explored: {len(visited)}"
            )
        else:
            explored = len(visited) if visited else 0
            print(f"  Exploring... cells visited: {explored}")

        if not args.no_animate:
            time.sleep(args.speed)


if __name__ == "__main__":
    main()