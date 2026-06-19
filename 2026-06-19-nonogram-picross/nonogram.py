#!/usr/bin/env python3
"""
Nonogram (Picross) Puzzle Generator & Solver

A terminal-based Nonogram puzzle game with:
- Procedural puzzle generation from random pixel art patterns
- Automatic solver using constraint propagation + backtracking
- Interactive gameplay with keyboard controls
- Multiple difficulty levels (5x5, 10x10, 15x15)
- Puzzle import/export with compact encoding
- Undo support and seed-based reproducibility
- Timer and hint system with mistake tracking
- Solution uniqueness verification (fixed in v3.0.0)
- Save and load game state
- Count solutions mode (--count-solutions)
- No-color mode (--no-color)
- --help and --version flags

Version: 3.0.0
"""

import random
import time
import sys
import json
import os
import copy
from collections import defaultdict

__version__ = "3.0.0"

# ─── ANSI Helpers ────────────────────────────────────────────────────────────

# Global no-color flag for suppressing ANSI codes
_NO_COLOR = False


class Style:
    """ANSI escape code constants for terminal formatting."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_WHITE = "\033[47m"
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_GRAY = "\033[100m"


def clear_screen():
    """Clear the terminal screen (cross-platform)."""
    os.system("cls" if os.name == "nt" else "clear")


def move_cursor(row, col):
    """Move the terminal cursor to (row, col)."""
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()


def hide_cursor():
    """Hide the terminal cursor."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Show the terminal cursor."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


# ─── Nonogram Logic ──────────────────────────────────────────────────────────

def compute_clues(grid):
    """
    Compute row and column clues from a solved grid.

    Each clue is a list of consecutive block lengths.
    An entirely empty row/column gets a clue of [0].

    Args:
        grid: 2D list of 0s and 1s

    Returns:
        Tuple of (row_clues, col_clues), each a list of lists of ints.
    """
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    row_clues = []
    for r in range(rows):
        clue = []
        count = 0
        for c in range(cols):
            if grid[r][c]:
                count += 1
            else:
                if count > 0:
                    clue.append(count)
                count = 0
        if count > 0:
            clue.append(count)
        if not clue:
            clue = [0]
        row_clues.append(clue)

    col_clues = []
    for c in range(cols):
        clue = []
        count = 0
        for r in range(rows):
            if grid[r][c]:
                count += 1
            else:
                if count > 0:
                    clue.append(count)
                count = 0
        if count > 0:
            clue.append(count)
        if not clue:
            clue = [0]
        col_clues.append(clue)

    return row_clues, col_clues


def generate_line_possibilities(clue, length):
    """
    Generate all possible line configurations for a given clue and line length.

    Uses recursive backtracking to enumerate every valid placement of
    the clue blocks within the line. Each configuration is a tuple of
    0s (empty) and 1s (filled).

    Args:
        clue: List of ints representing block lengths (e.g. [2, 1])
        length: Length of the line

    Returns:
        List of tuples, each a valid configuration.
    """
    if clue == [0]:
        return [tuple([0] * length)]

    # Quick feasibility check: minimum length needed for this clue
    min_length = sum(clue) + len(clue) - 1
    if min_length > length:
        return []

    results = []

    def place(clue_idx, pos, line):
        if clue_idx == len(clue):
            results.append(tuple(line + [0] * (length - len(line))))
            return

        block_len = clue[clue_idx]
        remaining_clue = sum(clue[clue_idx:]) + (len(clue) - clue_idx - 1)
        max_start = length - remaining_clue

        for start in range(pos, max_start + 1):
            new_line = line + [0] * (start - pos) + [1] * block_len
            next_pos = start + block_len
            if clue_idx < len(clue) - 1:
                new_line.append(0)
                next_pos += 1
            place(clue_idx + 1, next_pos, new_line)

    place(0, 0, [])
    return results

def solve_nonogram(row_clues, col_clues, timeout=60):
    """
    Solve a nonogram using constraint propagation + backtracking.

    First applies constraint propagation to deduce cells, then uses
    backtracking for remaining unknowns. Includes a timeout to prevent
    hanging on very large puzzles.

    Args:
        row_clues: List of row clue lists
        col_clues: List of column clue lists
        timeout: Maximum seconds to spend solving (default 60)

    Returns:
        Solved grid (list of lists) or None if unsolvable/timeout.
    """
    rows = len(row_clues)
    cols = len(col_clues)
    start_time = time.time()

    # Pre-compute possibilities
    row_possibilities = []
    for r in range(rows):
        poss = generate_line_possibilities(row_clues[r], cols)
        if not poss:
            return None  # Infeasible clue
        row_possibilities.append(list(poss))

    col_possibilities = []
    for c in range(cols):
        poss = generate_line_possibilities(col_clues[c], rows)
        if not poss:
            return None  # Infeasible clue
        col_possibilities.append(list(poss))

    # Grid: -1 = unknown, 0 = empty, 1 = filled
    grid = [[-1] * cols for _ in range(rows)]

    def propagate():
        changed = True
        while changed:
            changed = False

            # Filter row possibilities against current grid
            for r in range(rows):
                new_poss = []
                for poss in row_possibilities[r]:
                    valid = True
                    for c in range(cols):
                        if grid[r][c] != -1 and grid[r][c] != poss[c]:
                            valid = False
                            break
                    if valid:
                        new_poss.append(poss)

                if len(new_poss) == 0:
                    return False
                if len(new_poss) < len(row_possibilities[r]):
                    changed = True
                    row_possibilities[r] = new_poss

                # Fix known cells
                for c in range(cols):
                    if grid[r][c] == -1:
                        vals = set(poss[c] for poss in row_possibilities[r])
                        if len(vals) == 1:
                            grid[r][c] = vals.pop()
                            changed = True

            # Filter column possibilities against current grid
            for c in range(cols):
                new_poss = []
                for poss in col_possibilities[c]:
                    valid = True
                    for r in range(rows):
                        if grid[r][c] != -1 and grid[r][c] != poss[r]:
                            valid = False
                            break
                    if valid:
                        new_poss.append(poss)

                if len(new_poss) == 0:
                    return False
                if len(new_poss) < len(col_possibilities[c]):
                    changed = True
                    col_possibilities[c] = new_poss

                for r in range(rows):
                    if grid[r][c] == -1:
                        vals = set(poss[r] for poss in col_possibilities[c])
                        if len(vals) == 1:
                            grid[r][c] = vals.pop()
                            changed = True

        return True

    if not propagate():
        return None

    # Check timeout
    if time.time() - start_time > timeout:
        return None

    # Check if solved
    if all(grid[r][c] != -1 for r in range(rows) for c in range(cols)):
        return grid

    # Backtracking
    return backtrack(grid, row_possibilities, col_possibilities, rows, cols, start_time, timeout)


def backtrack(grid, row_poss, col_poss, rows, cols, start_time, timeout):
    """
    Backtracking solver for remaining unknowns after constraint propagation.

    Picks the first unknown cell, tries filling and emptying it,
    then recursively propagates and backtracks.

    Args:
        grid: Current grid state
        row_poss: Current row possibilities
        col_poss: Current column possibilities
        rows: Number of rows
        cols: Number of columns
        start_time: When solving started (for timeout)
        timeout: Maximum solving time in seconds

    Returns:
        Solved grid or None
    """
    # Timeout check
    if time.time() - start_time > timeout:
        return None

    # Find first unknown cell
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == -1:
                # Try filling it
                for val in [1, 0]:
                    new_grid = [row[:] for row in grid]
                    new_grid[r][c] = val
                    new_row_poss = [list(p) for p in row_poss]
                    new_col_poss = [list(p) for p in col_poss]

                    # Filter possibilities
                    new_row_poss[r] = [p for p in new_row_poss[r] if p[c] == val]
                    new_col_poss[c] = [p for p in new_col_poss[c] if p[r] == val]

                    if not new_row_poss[r] or not new_col_poss[c]:
                        continue

                    result = _propagate_and_solve(new_grid, new_row_poss, new_col_poss, rows, cols, start_time, timeout)
                    if result is not None:
                        return result

                return None

    return grid


def _propagate_and_solve(grid, row_poss, col_poss, rows, cols, start_time, timeout):
    """
    Run constraint propagation then backtrack if needed.

    Args:
        grid: Current grid state
        row_poss: Current row possibilities
        col_poss: Current column possibilities
        rows: Number of rows
        cols: Number of columns
        start_time: When solving started (for timeout)
        timeout: Maximum solving time in seconds

    Returns:
        Solved grid or None
    """
    # Timeout check
    if time.time() - start_time > timeout:
        return None

    changed = True
    while changed:
        changed = False

        for r in range(rows):
            new_poss = [p for p in row_poss[r]
                        if all(grid[r][c] == -1 or grid[r][c] == p[c] for c in range(len(grid[r])))]
            if not new_poss:
                return None
            if len(new_poss) < len(row_poss[r]):
                row_poss[r] = new_poss
                changed = True
            for c in range(len(grid[r])):
                if grid[r][c] == -1:
                    vals = set(p[c] for p in row_poss[r])
                    if len(vals) == 1:
                        grid[r][c] = vals.pop()
                        changed = True

        for c in range(cols):
            new_poss = [p for p in col_poss[c]
                        if all(grid[r][c] == -1 or grid[r][c] == p[r] for r in range(len(grid)))]
            if not new_poss:
                return None
            if len(new_poss) < len(col_poss[c]):
                col_poss[c] = new_poss
                changed = True
            for r in range(len(grid)):
                if grid[r][c] == -1:
                    vals = set(p[r] for p in col_poss[c])
                    if len(vals) == 1:
                        grid[r][c] = vals.pop()
                        changed = True

    # Check contradictions
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == -1:
                return backtrack(grid, row_poss, col_poss, rows, cols, start_time, timeout)

    return grid


def verify_unique_solution(row_clues, col_clues, timeout=30):
    """
    Verify that a nonogram puzzle has exactly one solution.

    Uses count_solutions to find up to 2 solutions. Returns True
    if exactly one solution exists.

    Args:
        row_clues: Row clues for the puzzle
        col_clues: Column clues for the puzzle
        timeout: Maximum time in seconds to spend

    Returns:
        True if the puzzle has a unique solution, False otherwise.
    """
    solutions = _find_all_solutions(row_clues, col_clues, max_count=2, timeout=timeout)
    return len(solutions) == 1


def _find_all_solutions(row_clues, col_clues, max_count=2, timeout=30):
    """
    Find up to max_count solutions for a nonogram puzzle.

    Uses constraint propagation with backtracking, stopping as soon
    as max_count solutions are found.

    Args:
        row_clues: Row clues for the puzzle
        col_clues: Column clues for the puzzle
        max_count: Maximum number of solutions to find
        timeout: Maximum time in seconds to spend

    Returns:
        List of solution grids (each a 2D list of 0s and 1s)
    """
    rows = len(row_clues)
    cols = len(col_clues)
    start_time = time.time()

    # Pre-compute possibilities
    row_possibilities = []
    for r in range(rows):
        poss = generate_line_possibilities(row_clues[r], cols)
        if not poss:
            return []
        row_possibilities.append(list(poss))

    col_possibilities = []
    for c in range(cols):
        poss = generate_line_possibilities(col_clues[c], rows)
        if not poss:
            return []
        col_possibilities.append(list(poss))

    solutions = []
    _search_solutions(
        [[-1] * cols for _ in range(rows)],
        row_possibilities, col_possibilities,
        rows, cols, solutions, max_count, start_time, timeout
    )
    return solutions


def _search_solutions(grid, row_poss, col_poss, rows, cols,
                      solutions, max_count, start_time, timeout):
    """
    Recursive solver that collects up to max_count solutions.

    Uses constraint propagation followed by backtracking. When a
    complete solution is found, it's appended to solutions and we
    continue searching if more solutions are needed.
    """
    if len(solutions) >= max_count:
        return

    if time.time() - start_time > timeout:
        return

    # Propagate constraints
    if not _propagate_for_search(grid, row_poss, col_poss, rows, cols):
        return

    # Check if solved
    unknown_cells = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == -1:
                unknown_cells.append((r, c))

    if not unknown_cells:
        # Found a complete solution
        solutions.append([row[:] for row in grid])
        return

    if len(solutions) >= max_count:
        return

    # Pick first unknown cell
    r, c = unknown_cells[0]

    for val in [1, 0]:
        new_grid = [row[:] for row in grid]
        new_grid[r][c] = val
        new_row_poss = [list(p) for p in row_poss]
        new_col_poss = [list(p) for p in col_poss]

        # Filter possibilities for the assigned cell
        new_row_poss[r] = [p for p in new_row_poss[r] if p[c] == val]
        new_col_poss[c] = [p for p in new_col_poss[c] if p[r] == val]

        if not new_row_poss[r] or not new_col_poss[c]:
            continue

        _search_solutions(
            new_grid, new_row_poss, new_col_poss,
            rows, cols, solutions, max_count, start_time, timeout
        )
        if len(solutions) >= max_count:
            return


def _propagate_for_search(grid, row_poss, col_poss, rows, cols):
    """
    Run constraint propagation for the solution search.

    Returns False if a contradiction is found, True otherwise.
    Modifies grid, row_poss, and col_poss in place.
    """
    changed = True
    while changed:
        changed = False

        for r in range(rows):
            new_poss = [p for p in row_poss[r]
                        if all(grid[r][c] == -1 or grid[r][c] == p[c]
                               for c in range(cols))]
            if not new_poss:
                return False
            if len(new_poss) < len(row_poss[r]):
                row_poss[r] = new_poss
                changed = True
            for c in range(cols):
                if grid[r][c] == -1:
                    vals = set(p[c] for p in row_poss[r])
                    if len(vals) == 1:
                        grid[r][c] = vals.pop()
                        changed = True

        for c in range(cols):
            new_poss = [p for p in col_poss[c]
                        if all(grid[r][c] == -1 or grid[r][c] == p[r]
                               for r in range(rows))]
            if not new_poss:
                return False
            if len(new_poss) < len(col_poss[c]):
                col_poss[c] = new_poss
                changed = True
            for r in range(rows):
                if grid[r][c] == -1:
                    vals = set(p[r] for p in col_poss[c])
                    if len(vals) == 1:
                        grid[r][c] = vals.pop()
                        changed = True

    return True


def generate_puzzle(rows, cols, difficulty="medium", seed=None):
    """
    Generate a random nonogram puzzle.

    Creates a random pattern, computes clues, and verifies unique solvability
    for easy/medium difficulty levels. For hard difficulty, uniqueness is not
    checked but the solver's canonical solution is used instead of the
    generator's grid.

    For easy/medium difficulties, if a unique solution is not found within
    200 attempts, the generator derives subsequent seeds deterministically
    from the original seed and keeps trying.

    Args:
        rows: Number of rows
        cols: Number of columns
        difficulty: 'easy', 'medium', or 'hard'
        seed: Optional random seed for reproducibility

    Returns:
        Tuple of (grid, row_clues, col_clues) where grid is the solver's
        canonical solution (guaranteed unique for easy/medium).
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    max_attempts = 200
    check_uniqueness = difficulty in ("easy", "medium")

    for attempt in range(max_attempts):
        # Derive a deterministic seed for each attempt
        if attempt == 0:
            attempt_rng = rng
        else:
            # Use a derived seed so that attempts are reproducible
            derived_seed = seed * 1000 + attempt if seed is not None else None
            attempt_rng = random.Random(derived_seed) if derived_seed is not None else random.Random()

        grid = generate_pattern(rows, cols, difficulty, rng=attempt_rng)
        row_clues, col_clues = compute_clues(grid)

        filled = sum(sum(row) for row in grid)
        total = rows * cols
        fill_ratio = filled / total

        # Ensure reasonable fill ratio
        if difficulty == "easy" and fill_ratio < 0.3:
            continue
        if difficulty == "hard" and fill_ratio > 0.7:
            continue

        # Avoid trivially empty puzzles
        if filled == 0:
            continue

        # Verify solvability
        solution = solve_nonogram(row_clues, col_clues, timeout=30)
        if solution is None:
            continue

        # Verify uniqueness for easier difficulties
        if check_uniqueness and rows * cols <= 225:  # Only check for reasonable sizes
            if not verify_unique_solution(row_clues, col_clues, timeout=15):
                continue
            # Use solver's solution as canonical (guaranteed unique)
            return solution, row_clues, col_clues

        # For hard difficulty (or large sizes), use solver's solution
        return solution, row_clues, col_clues

    # Fallback: generate and solve (may not be unique)
    grid = generate_pattern(rows, cols, difficulty, rng=rng)
    row_clues, col_clues = compute_clues(grid)
    solution = solve_nonogram(row_clues, col_clues, timeout=30)
    if solution is not None:
        return solution, row_clues, col_clues
    # Last resort: return the generator's grid (shouldn't happen in practice)
    return grid, row_clues, col_clues


def generate_pattern(rows, cols, difficulty, rng=None):
    """
    Generate a random pattern with structure appropriate to the difficulty.

    Args:
        rows: Grid height
        cols: Grid width
        difficulty: 'easy', 'medium', or 'hard'
        rng: Random.Random instance for reproducibility (optional)

    Returns:
        2D list of 0s and 1s
    """
    if rng is None:
        rng = random.Random()

    grid = [[0] * cols for _ in range(rows)]

    if difficulty == "easy":
        # Simple shapes - rectangles and crosses with some random fill
        num_shapes = rng.randint(1, 3)
        for _ in range(num_shapes):
            sr = rng.randint(0, rows - 1)
            sc = rng.randint(0, cols - 1)
            sh = rng.randint(1, min(3, rows - sr))
            sw = rng.randint(1, min(3, cols - sc))
            for r in range(sr, min(sr + sh, rows)):
                for c in range(sc, min(sc + sw, cols)):
                    grid[r][c] = 1

        # Add some random cells
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.25:
                    grid[r][c] = 1

    elif difficulty == "medium":
        # Horizontal/vertical symmetry patterns
        for r in range(rows):
            for c in range(cols):
                mr = rows - 1 - r
                mc = cols - 1 - c

                if rng.random() < 0.4:
                    grid[r][c] = 1
                    grid[mr][c] = 1  # Vertical symmetry
                    grid[r][mc] = 1  # Horizontal symmetry
                    grid[mr][mc] = 1  # Both

    else:  # hard
        # Random density with some clustering
        for r in range(rows):
            for c in range(cols):
                if rng.random() < 0.5:
                    grid[r][c] = 1

        # Cluster: force some adjacent cells on
        for _ in range(rows * cols // 4):
            r = rng.randint(0, rows - 1)
            c = rng.randint(0, cols - 1)
            grid[r][c] = 1
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if rng.random() < 0.6:
                        grid[nr][nc] = 1

    return grid


def check_solution(player_grid, solution):
    """
    Check if the player's grid matches the solution.

    Compares each cell: only 1 (filled) and 0 (empty) states are checked.
    Cells marked as -1 (unknown) are treated as incomplete.

    Args:
        player_grid: Player's current grid state
        solution: The correct solution grid

    Returns:
        True if all cells match the solution
    """
    for r in range(len(solution)):
        for c in range(len(solution[0])):
            pv = player_grid[r][c]
            sv = solution[r][c]
            if pv == -1:
                return False
            if pv == 1 and sv != 1:
                return False
            if pv == 0 and sv != 0:
                return False
    return True


def get_hint(grid, solution):
    """
    Find a cell that the player hasn't filled correctly.

    Prioritizes cells where the player made a mistake over empty cells.

    Args:
        grid: Player's current grid (values: -1=unknown, 0=X-mark, 1=filled)
        solution: The correct solution grid

    Returns:
        Tuple of ((row, col), is_wrong_cell) or (None, False) if no hint needed
    """
    wrong_cells = []
    empty_cells = []

    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == -1:
                empty_cells.append((r, c))
            elif grid[r][c] != solution[r][c]:
                wrong_cells.append((r, c))

    # Prefer fixing wrong cells first
    if wrong_cells:
        return random.choice(wrong_cells), True
    if empty_cells:
        r, c = random.choice(empty_cells)
        return (r, c), False
    return None, False


def export_puzzle(row_clues, col_clues, rows, cols):
    """
    Export puzzle as JSON string for sharing.

    Args:
        row_clues: Row clues
        col_clues: Column clues
        rows: Number of rows
        cols: Number of columns

    Returns:
        JSON string representation of the puzzle
    """
    data = {
        "rows": rows,
        "cols": cols,
        "row_clues": row_clues,
        "col_clues": col_clues,
    }
    return json.dumps(data)


def import_puzzle(json_str):
    """
    Import puzzle from JSON string.

    Args:
        json_str: JSON string with 'rows', 'cols', 'row_clues', 'col_clues' keys

    Returns:
        Tuple of (row_clues, col_clues, rows, cols)

    Raises:
        json.JSONDecodeError: If the string is not valid JSON
        KeyError: If required keys are missing
        ValueError: If puzzle dimensions are invalid
    """
    data = json.loads(json_str)

    # Validate required fields
    required_keys = {"rows", "cols", "row_clues", "col_clues"}
    missing = required_keys - set(data.keys())
    if missing:
        raise KeyError(f"Missing required fields: {missing}")

    rows = data["rows"]
    cols = data["cols"]

    if not isinstance(rows, int) or rows <= 0:
        raise ValueError(f"Invalid rows value: {rows}")
    if not isinstance(cols, int) or cols <= 0:
        raise ValueError(f"Invalid cols value: {cols}")
    if rows > 30 or cols > 30:
        raise ValueError(f"Puzzle too large: {rows}x{cols}. Maximum is 30x30.")

    if len(data["row_clues"]) != rows:
        raise ValueError(f"row_clues length {len(data['row_clues'])} doesn't match rows {rows}")
    if len(data["col_clues"]) != cols:
        raise ValueError(f"col_clues length {len(data['col_clues'])} doesn't match cols {cols}")

    return data["row_clues"], data["col_clues"], rows, cols


def count_solutions(row_clues, col_clues, max_count=2, timeout=30):
    """
    Count the number of solutions for a nonogram puzzle.

    Uses a modified solver that continues searching after finding
    solutions, stopping when max_count is reached or timeout expires.

    Args:
        row_clues: Row clues for the puzzle
        col_clues: Column clues for the puzzle
        max_count: Maximum number of solutions to find (default 2)
        timeout: Maximum time in seconds to spend

    Returns:
        List of solution grids found (up to max_count).
    """
    return _find_all_solutions(row_clues, col_clues, max_count=max_count, timeout=timeout)


def save_game_state(game):
    """
    Save the current game state to a JSON string.

    Args:
        game: NonogramGame instance

    Returns:
        JSON string representing the game state
    """
    data = {
        "version": __version__,
        "rows": game.rows,
        "cols": game.cols,
        "difficulty": game.difficulty,
        "seed": game.seed,
        "row_clues": game.row_clues,
        "col_clues": game.col_clues,
        "player_grid": game.player_grid,
        "cursor_r": game.cursor_r,
        "cursor_c": game.cursor_c,
        "hints_used": game.hints_used,
        "mistakes": game.mistakes,
        "elapsed": time.time() - game.start_time,
    }
    return json.dumps(data)


def load_game_state(json_str):
    """
    Load a game state from a JSON string.

    Args:
        json_str: JSON string from save_game_state()

    Returns:
        NonogramGame instance with restored state

    Raises:
        json.JSONDecodeError: If the string is not valid JSON
        KeyError: If required keys are missing
        ValueError: If the data is invalid
    """
    data = json.loads(json_str)

    required_keys = {"rows", "cols", "difficulty", "row_clues", "col_clues",
                     "player_grid", "cursor_r", "cursor_c", "hints_used", "mistakes"}
    missing = required_keys - set(data.keys())
    if missing:
        raise KeyError(f"Missing required fields: {missing}")

    rows = data["rows"]
    cols = data["cols"]
    if not isinstance(rows, int) or rows <= 0:
        raise ValueError(f"Invalid rows: {rows}")
    if not isinstance(cols, int) or cols <= 0:
        raise ValueError(f"Invalid cols: {cols}")

    # Create game from imported puzzle
    game = NonogramGame.__new__(NonogramGame)
    game.difficulty = data["difficulty"]
    game.rows = rows
    game.cols = cols
    game.seed = data.get("seed")
    game.row_clues = data["row_clues"]
    game.col_clues = data["col_clues"]

    # Solve to get the solution
    game.solution = solve_nonogram(game.row_clues, game.col_clues)
    if game.solution is None:
        raise ValueError("Cannot solve the puzzle in this saved state")

    game.player_grid = data["player_grid"]
    game.cursor_r = data["cursor_r"]
    game.cursor_c = data["cursor_c"]
    game.undo_stack = []
    game.start_time = time.time() - data.get("elapsed", 0)
    game.elapsed = data.get("elapsed", 0)
    game.hints_used = data["hints_used"]
    game.mistakes = data["mistakes"]
    game.filled_count = sum(1 for r in range(rows) for c in range(cols) if game.player_grid[r][c] == 1)
    game.game_won = False
    game.max_row_clue_len = max(len(c) for c in game.row_clues)
    game.max_col_clue_len = max(len(c) for c in game.col_clues)

    # Check if already won
    if check_solution(game.player_grid, game.solution):
        game.game_won = True

    return game


def compute_progress(player_grid, solution):
    """
    Compute completion percentage of the puzzle.

    Args:
        player_grid: Player's current grid
        solution: The solution grid

    Returns:
        Float between 0.0 and 1.0
    """
    if not solution:
        return 0.0
    total = len(solution) * len(solution[0])
    if total == 0:
        return 0.0
    correct = 0
    for r in range(len(solution)):
        for c in range(len(solution[0])):
            if player_grid[r][c] != -1 and player_grid[r][c] == solution[r][c]:
                correct += 1
    return correct / total


# ─── Terminal UI ──────────────────────────────────────────────────────────────

class NonogramGame:
    """Interactive terminal nonogram game with undo support and progress tracking."""

    # Cell states in player grid
    UNKNOWN = -1  # Not yet determined
    FILLED = 1    # Filled cell
    EMPTY = 0     # Marked as empty (X-mark)

    def __init__(self, size=10, difficulty="medium", seed=None):
        self.difficulty = difficulty
        self.rows = size
        self.cols = size
        self.seed = seed

        # Generate puzzle
        self.solution, self.row_clues, self.col_clues = generate_puzzle(
            self.rows, self.cols, difficulty, seed=seed
        )

        # Player grid: -1 = unknown, 0 = X-mark (empty), 1 = filled
        self.player_grid = [[-1] * self.cols for _ in range(self.rows)]

        # Undo stack: list of (r, c, old_value) tuples
        self.undo_stack = []

        # Cursor position
        self.cursor_r = 0
        self.cursor_c = 0

        # Timer
        self.start_time = time.time()
        self.elapsed = 0

        # Stats
        self.hints_used = 0
        self.mistakes = 0
        self.filled_count = 0
        self.game_won = False

        # Compute max clue lengths for layout
        self.max_row_clue_len = max(len(c) for c in self.row_clues)
        self.max_col_clue_len = max(len(c) for c in self.col_clues)

    def draw(self):
        """Draw the entire game board with progress indicator."""
        clear_screen()
        lines = []

        # Title bar
        title = f"  {Style.BOLD}{Style.CYAN}◇ NONOGRAM PICROSS ◇{Style.RESET}"
        diff_str = f"  {self.difficulty.upper()}  {self.rows}×{self.cols}"
        if self.seed is not None:
            diff_str += f"  seed:{self.seed}"
        elapsed = time.time() - self.start_time
        mins, secs = int(elapsed) // 60, int(elapsed) % 60
        timer = f"  ⏱ {mins:02d}:{secs:02d}"
        hints = f"  💡 Hints: {self.hints_used}"
        mistakes = f"  ✗ Mistakes: {self.mistakes}"

        # Progress bar
        progress = compute_progress(self.player_grid, self.solution)
        bar_len = 20
        filled_bar = int(progress * bar_len)
        bar = f"  [{Style.GREEN}{'█' * filled_bar}{Style.DIM}{'░' * (bar_len - filled_bar)}{Style.RESET}] {progress * 100:.0f}%"

        lines.append(f"{title}")
        lines.append(f"  {Style.DIM}{diff_str}{timer}{hints}{mistakes}{Style.RESET}")
        lines.append(bar)
        lines.append("")

        # Column clues
        col_clue_width = self.max_row_clue_len * 3 + 2
        for ci in range(self.max_col_clue_len - 1, -1, -1):
            line = " " * col_clue_width
            for c in range(self.cols):
                clue = self.col_clues[c]
                idx = len(clue) - (self.max_col_clue_len - ci)
                if 0 <= idx < len(clue):
                    text = str(clue[idx])
                else:
                    text = " "
                line += f" {text:>2}"
            lines.append(line)

        # Separator
        sep = " " * col_clue_width + "─" * (self.cols * 3 + 1)
        lines.append(sep)

        # Rows
        for r in range(self.rows):
            # Row clues
            clue_str = ""
            for ci in range(self.max_row_clue_len):
                idx = ci - (self.max_row_clue_len - len(self.row_clues[r]))
                if 0 <= idx < len(self.row_clues[r]):
                    clue_str += f"{self.row_clues[r][idx]:>2} "
                else:
                    clue_str += "   "

            line = f" {clue_str}│"

            # Cells
            for c in range(self.cols):
                cell = self.player_grid[r][c]
                is_cursor = (r == self.cursor_r and c == self.cursor_c)

                # Check if this cell is part of a completed row/col
                row_complete = self._is_row_complete(r)
                col_complete = self._is_col_complete(c)
                highlight = row_complete or col_complete

                if is_cursor:
                    if cell == 1:
                        cell_str = f"{Style.BG_WHITE}{Style.RED}█{Style.RESET}"
                    elif cell == 0:
                        cell_str = f"{Style.BG_WHITE}{Style.RED}✕{Style.RESET}"
                    else:
                        cell_str = f"{Style.BG_WHITE}{Style.RED}·{Style.RESET}"
                elif cell == 1:
                    if highlight:
                        cell_str = f"{Style.GREEN}█{Style.RESET}"
                    else:
                        cell_str = f"{Style.BOLD}█{Style.RESET}"
                elif cell == 0:
                    cell_str = f"{Style.DIM}✕{Style.RESET}"
                else:
                    cell_str = f"{Style.DIM}·{Style.RESET}"

                line += cell_str + " "

            # Row completion indicator
            if row_complete:
                line += f" {Style.GREEN}✓{Style.RESET}"
            lines.append(line)

        lines.append("")
        lines.append(f"  {Style.DIM}Controls:{Style.RESET}")
        lines.append(f"  {Style.BOLD}Arrows/WASD{Style.RESET} Move  {Style.BOLD}Space/f{Style.RESET} Fill  {Style.BOLD}x{Style.RESET} Mark  {Style.BOLD}Backspace{Style.RESET} Clear")
        lines.append(f"  {Style.BOLD}u{Style.RESET} Undo  {Style.BOLD}h{Style.RESET} Hint  {Style.BOLD}S{Style.RESET} Solve  {Style.BOLD}e{Style.RESET} Export  {Style.BOLD}W{Style.RESET} Save  {Style.BOLD}q{Style.RESET} Quit")

        if self.game_won:
            lines.append("")
            lines.append(f"  {Style.BOLD}{Style.GREEN}🎉 CONGRATULATIONS! Puzzle Solved! 🎉{Style.RESET}")
            mins_e, secs_e = int(self.elapsed) // 60, int(self.elapsed) % 60
            lines.append(f"  {Style.GREEN}Time: {mins_e:02d}:{secs_e:02d}  Hints: {self.hints_used}  Mistakes: {self.mistakes}{Style.RESET}")

        print("\n".join(lines))

    def _is_row_complete(self, r):
        """Check if a row matches the solution."""
        for c in range(self.cols):
            if self.player_grid[r][c] != self.solution[r][c]:
                return False
        return True

    def _is_col_complete(self, c):
        """Check if a column matches the solution clues."""
        for r in range(self.rows):
            if self.player_grid[r][c] != self.solution[r][c]:
                return False
        return True

    def _push_undo(self, r, c, old_val):
        """Save a cell state to the undo stack."""
        self.undo_stack.append((r, c, old_val))
        # Limit undo history to prevent excessive memory use
        if len(self.undo_stack) > 1000:
            self.undo_stack = self.undo_stack[-500:]

    def undo(self):
        """Undo the last action."""
        if not self.undo_stack:
            return
        r, c, old_val = self.undo_stack.pop()
        self.player_grid[r][c] = old_val

    def toggle_fill(self):
        """Toggle fill state of current cell."""
        r, c = self.cursor_r, self.cursor_c
        old_val = self.player_grid[r][c]
        self._push_undo(r, c, old_val)

        if old_val == 1:
            self.player_grid[r][c] = -1
        else:
            self.player_grid[r][c] = 1
            if self.player_grid[r][c] != self.solution[r][c]:
                self.mistakes += 1

    def toggle_mark(self):
        """Toggle X mark on current cell."""
        r, c = self.cursor_r, self.cursor_c
        old_val = self.player_grid[r][c]
        self._push_undo(r, c, old_val)

        if old_val == 0:
            self.player_grid[r][c] = -1
        else:
            self.player_grid[r][c] = 0

    def clear_cell(self):
        """Clear current cell back to unknown."""
        r, c = self.cursor_r, self.cursor_c
        old_val = self.player_grid[r][c]
        self._push_undo(r, c, old_val)
        self.player_grid[r][c] = -1

    def give_hint(self):
        """Reveal one cell."""
        cell, is_wrong = get_hint(self.player_grid, self.solution)
        if cell is None:
            return
        r, c = cell
        self._push_undo(r, c, self.player_grid[r][c])
        self.player_grid[r][c] = self.solution[r][c]
        self.hints_used += 1
        self._check_win()

    def auto_solve(self):
        """Solve the entire puzzle."""
        for r in range(self.rows):
            for c in range(self.cols):
                self.player_grid[r][c] = self.solution[r][c]
        self._check_win()

    def _check_win(self):
        """Check if puzzle is complete."""
        if check_solution(self.player_grid, self.solution):
            self.game_won = True
            self.elapsed = time.time() - self.start_time

    def move_cursor(self, dr, dc):
        """Move cursor by delta, clamping to grid bounds."""
        self.cursor_r = max(0, min(self.rows - 1, self.cursor_r + dr))
        self.cursor_c = max(0, min(self.cols - 1, self.cursor_c + dc))

    def play(self):
        """Main game loop with keyboard input handling."""
        hide_cursor()
        try:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)
                self.draw()

                while True:
                    ch = sys.stdin.read(1)

                    if ch == 'q':
                        break
                    elif ch == '\x1b':  # ESC sequence
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A':
                                self.move_cursor(-1, 0)
                            elif ch3 == 'B':
                                self.move_cursor(1, 0)
                            elif ch3 == 'C':
                                self.move_cursor(0, 1)
                            elif ch3 == 'D':
                                self.move_cursor(0, -1)
                    elif ch == 'w':
                        self.move_cursor(-1, 0)
                    elif ch == 's':
                        self.move_cursor(1, 0)
                    elif ch == 'a':
                        self.move_cursor(0, -1)
                    elif ch == 'd':
                        self.move_cursor(0, 1)
                    elif ch == ' ' or ch == 'f':
                        self.toggle_fill()
                    elif ch == 'x':
                        self.toggle_mark()
                    elif ch == '\x7f' or ch == '\x08':  # Backspace
                        self.clear_cell()
                    elif ch == 'h':
                        self.give_hint()
                    elif ch == 'u':
                        self.undo()
                    elif ch == 'S':
                        self.auto_solve()
                    elif ch == 'e':
                        # Export
                        self._export_and_show()
                    elif ch == 'W':
                        # Save game
                        self._save_and_show()

                    self._check_win()
                    self.draw()

                    if self.game_won:
                        # Wait for any key
                        sys.stdin.read(1)
                        break

            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        except ImportError:
            # Windows or no tty support
            print("Interactive mode requires a Unix terminal. Use --solve or --generate instead.")
        finally:
            show_cursor()

    def _export_and_show(self):
        """Export puzzle and show the code, waiting for user acknowledgment."""
        json_str = export_puzzle(self.row_clues, self.col_clues, self.rows, self.cols)
        print(f"\n\n  Puzzle exported! Copy this string to share:\n")
        print(f"  {json_str}\n")
        print("  Press any key to continue...")
        try:
            import tty, termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except (ImportError, termios.error, OSError):
            try:
                input()
            except Exception:
                pass

    def _save_and_show(self):
        """Save game state and show the code, waiting for user acknowledgment."""
        json_str = save_game_state(self)
        print(f"\n\n  Game saved! Copy this string to resume later:\n")
        print(f"  {json_str}\n")
        print("  Resume with:  nonogram.py --load '...'")
        print("  Press any key to continue...")
        try:
            import tty, termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except (ImportError, termios.error, OSError):
            try:
                input()
            except Exception:
                pass


# ─── Non-Interactive Modes ───────────────────────────────────────────────────

def print_puzzle(row_clues, col_clues, rows, cols, grid=None, player_grid=None):
    """
    Print a nonogram puzzle to the terminal (non-interactive).

    Args:
        row_clues: Row clues for display
        col_clues: Column clues for display
        rows: Number of rows
        cols: Number of columns
        grid: Optional solution grid for display
        player_grid: Optional player grid for display
    """
    max_row_clue_len = max(len(c) for c in row_clues)
    max_col_clue_len = max(len(c) for c in col_clues)

    col_clue_width = max_row_clue_len * 3 + 2

    print(f"\n  {Style.BOLD}{Style.CYAN}◇ NONOGRAM PICROSS ◇{Style.RESET}  ({rows}×{cols})\n")

    # Column clues
    for ci in range(max_col_clue_len - 1, -1, -1):
        line = " " * col_clue_width
        for c in range(cols):
            clue = col_clues[c]
            idx = len(clue) - (max_col_clue_len - ci)
            if 0 <= idx < len(clue):
                text = str(clue[idx])
            else:
                text = " "
            line += f" {text:>2}"
        print(line)

    # Separator
    sep = " " * col_clue_width + "─" * (cols * 3 + 1)
    print(sep)

    # Rows
    for r in range(rows):
        clue_str = ""
        for ci in range(max_row_clue_len):
            idx = ci - (max_row_clue_len - len(row_clues[r]))
            if 0 <= idx < len(row_clues[r]):
                clue_str += f"{row_clues[r][idx]:>2} "
            else:
                clue_str += "   "

        line = f" {clue_str}│"
        for c in range(cols):
            if player_grid and player_grid[r][c] != -1:
                cell = player_grid[r][c]
                if cell == 1:
                    line += f"{Style.BOLD}█{Style.RESET} "
                elif cell == 0:
                    line += f"{Style.DIM}✕{Style.RESET} "
                else:
                    line += "· "
            elif grid:
                if grid[r][c]:
                    line += f"{Style.BOLD}█{Style.RESET} "
                else:
                    line += f"{Style.DIM}·{Style.RESET} "
            else:
                line += "· "

        print(line)

    print()


def solve_and_display(row_clues, col_clues, rows, cols):
    """
    Solve a nonogram and display the result.

    Args:
        row_clues: Row clues
        col_clues: Column clues
        rows: Number of rows
        cols: Number of columns

    Returns:
        Solution grid or None if unsolvable
    """
    print(f"\n  {Style.BOLD}Solving {rows}×{cols} nonogram...{Style.RESET}\n")

    start = time.time()
    solution = solve_nonogram(row_clues, col_clues)
    elapsed = time.time() - start

    if solution is None:
        print(f"  {Style.RED}No solution found! The puzzle may be unsolvable.{Style.RESET}\n")
        return None

    print(f"  {Style.GREEN}Solved in {elapsed:.3f}s{Style.RESET}\n")
    print_puzzle(row_clues, col_clues, rows, cols, grid=solution)
    return solution


def generate_and_display(size, difficulty, solve=False, seed=None):
    """
    Generate a puzzle and optionally solve it.

    Args:
        size: Grid dimensions (size x size)
        difficulty: 'easy', 'medium', or 'hard'
        solve: Whether to show the solution
        seed: Optional random seed

    Returns:
        Tuple of (grid, row_clues, col_clues)
    """
    grid, row_clues, col_clues = generate_puzzle(size, size, difficulty, seed=seed)

    seed_info = f" (seed: {seed})" if seed is not None else ""
    print(f"\n  {Style.BOLD}{Style.CYAN}Generated {size}×{size} {difficulty} puzzle{seed_info}{Style.RESET}\n")
    print_puzzle(row_clues, col_clues, size, size)

    if solve:
        print(f"\n  {Style.BOLD}Solution:{Style.RESET}\n")
        print_puzzle(row_clues, col_clues, size, size, grid=grid)

    # Export
    json_str = export_puzzle(row_clues, col_clues, size, size)
    print(f"  {Style.DIM}Puzzle code: {json_str}{Style.RESET}\n")

    return grid, row_clues, col_clues


def count_and_display(row_clues, col_clues, rows, cols, max_count=2):
    """
    Count the number of solutions for a puzzle and display the results.

    Args:
        row_clues: Row clues for the puzzle
        col_clues: Column clues for the puzzle
        rows: Number of rows
        cols: Number of columns
        max_count: Maximum number of solutions to find (default 2)

    Returns:
        Number of solutions found (capped at max_count)
    """
    print(f"\n  {Style.BOLD}{Style.CYAN}Counting solutions for {rows}×{cols} puzzle...{Style.RESET}\n")
    start = time.time()
    solutions = count_solutions(row_clues, col_clues, max_count=max_count, timeout=60)
    elapsed = time.time() - start

    if len(solutions) == 0:
        print(f"  {Style.RED}No solutions found! The puzzle may be unsolvable.{Style.RESET}\n")
        return 0
    elif len(solutions) == 1:
        print(f"  {Style.GREEN}✓ Unique solution found{Style.RESET} (in {elapsed:.3f}s)")
        print(f"  {Style.GREEN}This puzzle has exactly one solution.{Style.RESET}\n")
        print_puzzle(row_clues, col_clues, rows, cols, grid=solutions[0])
    elif len(solutions) >= max_count:
        print(f"  {Style.YELLOW}⚠ Multiple solutions found{Style.RESET} (in {elapsed:.3f}s)")
        print(f"  {Style.YELLOW}Found ≥{max_count} solutions — puzzle is not unique.{Style.RESET}\n")
        for i, sol in enumerate(solutions):
            print(f"  Solution {i+1}:")
            print_puzzle(row_clues, col_clues, rows, cols, grid=sol)
    else:
        print(f"  {Style.GREEN}Found {len(solutions)} solution(s){Style.RESET} (in {elapsed:.3f}s)\n")
        for i, sol in enumerate(solutions):
            print(f"  Solution {i+1}:")
            print_puzzle(row_clues, col_clues, rows, cols, grid=sol)

    return len(solutions)


def import_and_solve(json_str, solve=True):
    """
    Import a puzzle from JSON and optionally solve it.

    Args:
        json_str: JSON string representing the puzzle
        solve: Whether to solve after importing

    Returns:
        Solution grid or None
    """
    try:
        row_clues, col_clues, rows, cols = import_puzzle(json_str)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  {Style.RED}Invalid puzzle code: {e}{Style.RESET}")
        return None

    print(f"\n  {Style.BOLD}Imported {rows}×{cols} puzzle{Style.RESET}\n")
    print_puzzle(row_clues, col_clues, rows, cols)

    if solve:
        solution = solve_and_display(row_clues, col_clues, rows, cols)
        return solution
    return None


def import_and_play(json_str):
    """
    Import a puzzle from JSON and play it interactively.

    Args:
        json_str: JSON string representing the puzzle

    Returns:
        None
    """
    try:
        row_clues, col_clues, rows, cols = import_puzzle(json_str)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  {Style.RED}Invalid puzzle code: {e}{Style.RESET}")
        return None

    # Create game from imported puzzle
    game = NonogramGame.__new__(NonogramGame)
    game.difficulty = "imported"
    game.rows = rows
    game.cols = cols
    game.seed = None
    game.row_clues = row_clues
    game.col_clues = col_clues

    # Solve to get the solution
    game.solution = solve_nonogram(row_clues, col_clues)
    if game.solution is None:
        print(f"  {Style.RED}Could not solve the imported puzzle — it may be unsolvable.{Style.RESET}")
        return None

    game.player_grid = [[-1] * cols for _ in range(rows)]
    game.undo_stack = []
    game.cursor_r = 0
    game.cursor_c = 0
    game.start_time = time.time()
    game.elapsed = 0
    game.hints_used = 0
    game.mistakes = 0
    game.filled_count = 0
    game.game_won = False
    game.max_row_clue_len = max(len(c) for c in row_clues)
    game.max_col_clue_len = max(len(c) for c in col_clues)

    game.play()
    return game


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Nonogram (Picross) Puzzle Generator & Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Play a random 10×10 puzzle
  %(prog)s --size 5                 Play a 5×5 puzzle (easy)
  %(prog)s --size 15 --difficulty hard  Play a 15×15 hard puzzle
  %(prog)s --generate --solve       Generate and show solution
  %(prog)s --generate --count-solutions  Count solutions for a puzzle
  %(prog)s --solve --puzzle '...'   Solve an imported puzzle
  %(prog)s --import-puzzle '...'    Import and play a shared puzzle
  %(prog)s --seed 42                Play a reproducible puzzle
  %(prog)s --load '...'             Resume a saved game
  %(prog)s --no-color               Disable ANSI color output
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-s", "--size", type=int, default=10,
                        help="Puzzle size (default: 10)")
    parser.add_argument("-d", "--difficulty", choices=["easy", "medium", "hard"],
                        default="medium", help="Difficulty (default: medium)")
    parser.add_argument("-g", "--generate", action="store_true",
                        help="Generate a puzzle without playing")
    parser.add_argument("--solve", action="store_true",
                        help="Show solution (with --generate)")
    parser.add_argument("--count-solutions", action="store_true",
                        help="Count and display solutions (with --generate)")
    parser.add_argument("--puzzle", type=str,
                        help="Puzzle JSON string to solve")
    parser.add_argument("--import-puzzle", type=str,
                        help="Import a puzzle JSON string and play it interactively")
    parser.add_argument("--load", type=str,
                        help="Load a saved game state from JSON string")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible puzzle generation")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")

    args = parser.parse_args()

    # Apply no-color flag globally
    global _NO_COLOR
    if args.no_color or os.environ.get("NO_COLOR"):
        _NO_COLOR = True

    # Clamp size to reasonable bounds
    if args.size < 3:
        print(f"  Puzzle size must be at least 3. Using 3.")
        args.size = 3
    elif args.size > 20:
        print(f"  Large puzzles (>20) may be slow. Using {args.size}.")

    if args.load:
        try:
            game = load_game_state(args.load)
            game.play()
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"  Invalid saved game: {e}")
    elif args.import_puzzle:
        import_and_play(args.import_puzzle)
    elif args.puzzle:
        if args.count_solutions:
            try:
                row_clues, col_clues, rows, cols = import_puzzle(args.puzzle)
                count_and_display(row_clues, col_clues, rows, cols)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"  Invalid puzzle code: {e}")
        elif args.solve:
            import_and_solve(args.puzzle, solve=True)
        else:
            try:
                row_clues, col_clues, rows, cols = import_puzzle(args.puzzle)
                print_puzzle(row_clues, col_clues, rows, cols)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"  Invalid puzzle code: {e}")
    elif args.generate:
        grid, row_clues, col_clues = generate_and_display(
            args.size, args.difficulty, solve=args.solve, seed=args.seed)
        if args.count_solutions:
            count_and_display(row_clues, col_clues, args.size, args.size)
    else:
        # Interactive game
        game = NonogramGame(size=args.size, difficulty=args.difficulty, seed=args.seed)
        game.play()


if __name__ == "__main__":
    main()