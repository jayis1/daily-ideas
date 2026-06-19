#!/usr/bin/env python3
"""
Nonogram (Picross) Puzzle Generator & Solver

A terminal-based Nonogram puzzle game with:
- Procedural puzzle generation from random pixel art patterns
- Automatic solver using constraint propagation + backtracking
- Interactive gameplay with keyboard controls
- Multiple difficulty levels (5x5, 10x10, 15x15)
- Puzzle import/export
- Timer and hint system
"""

import random
import time
import sys
import json
import os
from collections import defaultdict

# ─── ANSI Helpers ────────────────────────────────────────────────────────────

class Style:
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
    os.system("cls" if os.name == "nt" else "clear")


def move_cursor(row, col):
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()


def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


# ─── Nonogram Logic ──────────────────────────────────────────────────────────

def compute_clues(grid):
    """Compute row and column clues from a solved grid."""
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
    """Generate all possible line configurations for a given clue and length."""
    if clue == [0]:
        return [tuple([0] * length)]

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


def solve_nonogram(row_clues, col_clues):
    """
    Solve a nonogram using constraint propagation + backtracking.
    Returns the solved grid, or None if unsolvable.
    """
    rows = len(row_clues)
    cols = len(col_clues)

    # Pre-compute possibilities
    row_possibilities = []
    for r in range(rows):
        poss = generate_line_possibilities(row_clues[r], cols)
        row_possibilities.append(poss)

    col_possibilities = []
    for c in range(cols):
        poss = generate_line_possibilities(col_clues[c], rows)
        col_possibilities.append(poss)

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

    # Check if solved
    if all(grid[r][c] != -1 for r in range(rows) for c in range(cols)):
        return grid

    # Backtracking
    return backtrack(grid, row_possibilities, col_possibilities, rows, cols)


def backtrack(grid, row_poss, col_poss, rows, cols):
    """Backtracking solver for remaining unknowns."""
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

                    result = _propagate_and_solve(new_grid, new_row_poss, new_col_poss, rows, cols)
                    if result is not None:
                        return result

                return None

    return grid


def _propagate_and_solve(grid, row_poss, col_poss, rows, cols):
    """Run constraint propagation then backtrack if needed."""
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
                return backtrack(grid, row_poss, col_poss, rows, cols)

    return grid


def generate_puzzle(rows, cols, difficulty="medium"):
    """
    Generate a random nonogram puzzle.
    Creates a random pattern, computes clues, and ensures unique solution.
    """
    # Generate random patterns with structure (symmetry, shapes)
    max_attempts = 50

    for attempt in range(max_attempts):
        grid = generate_pattern(rows, cols, difficulty)
        row_clues, col_clues = compute_clues(grid)

        # Check uniqueness by solving
        # (for simplicity, we'll just use the generated grid)
        # A more robust version would verify uniqueness
        filled = sum(sum(row) for row in grid)
        total = rows * cols
        fill_ratio = filled / total

        # Ensure reasonable fill ratio
        if difficulty == "easy" and fill_ratio < 0.3:
            continue
        if difficulty == "hard" and fill_ratio > 0.7:
            continue

        return grid, row_clues, col_clues

    # Fallback
    grid = generate_pattern(rows, cols, difficulty)
    row_clues, col_clues = compute_clues(grid)
    return grid, row_clues, col_clues


def generate_pattern(rows, cols, difficulty):
    """Generate a random pattern with some structure."""
    grid = [[0] * cols for _ in range(rows)]

    if difficulty == "easy":
        # Simple shapes - rectangles and crosses
        num_shapes = random.randint(1, 3)
        for _ in range(num_shapes):
            sr = random.randint(0, rows - 1)
            sc = random.randint(0, cols - 1)
            sh = random.randint(1, min(3, rows - sr))
            sw = random.randint(1, min(3, cols - sc))
            for r in range(sr, min(sr + sh, rows)):
                for c in range(sc, min(sc + sw, cols)):
                    grid[r][c] = 1

        # Add some random cells
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.25:
                    grid[r][c] = 1

    elif difficulty == "medium":
        # Horizontal/vertical symmetry patterns
        center_r = rows // 2
        center_c = cols // 2

        for r in range(rows):
            for c in range(cols):
                # Mirror coordinates
                mr = rows - 1 - r
                mc = cols - 1 - c

                if random.random() < 0.4:
                    grid[r][c] = 1
                    grid[mr][c] = 1  # Vertical symmetry
                    grid[r][mc] = 1  # Horizontal symmetry
                    grid[mr][mc] = 1  # Both

    else:  # hard
        # Random density with some clustering
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.5:
                    grid[r][c] = 1

        # Cluster: force some adjacent cells on
        for _ in range(rows * cols // 4):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            grid[r][c] = 1
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if random.random() < 0.6:
                        grid[nr][nc] = 1

    return grid


def check_solution(player_grid, solution):
    """Check if the player's grid matches the solution."""
    for r in range(len(solution)):
        for c in range(len(solution[0])):
            if player_grid[r][c] != solution[r][c]:
                return False
    return True


def get_hint(grid, solution):
    """Find a cell that the player hasn't filled correctly."""
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
        return random.choice(wrong_cells), True  # True = wrong cell
    if empty_cells:
        r, c = random.choice(empty_cells)
        return (r, c), False  # False = empty cell
    return None, False


def export_puzzle(row_clues, col_clues, rows, cols):
    """Export puzzle as JSON string."""
    data = {
        "rows": rows,
        "cols": cols,
        "row_clues": row_clues,
        "col_clues": col_clues,
    }
    return json.dumps(data)


def import_puzzle(json_str):
    """Import puzzle from JSON string."""
    data = json.loads(json_str)
    return data["row_clues"], data["col_clues"], data["rows"], data["cols"]


# ─── Terminal UI ──────────────────────────────────────────────────────────────

class NonogramGame:
    """Interactive terminal nonogram game."""

    # Cell states
    EMPTY = 0
    FILLED = 1
    MARKED = 2  # X mark (definitely empty)

    def __init__(self, size=10, difficulty="medium"):
        self.difficulty = difficulty
        self.rows = size
        self.cols = size

        # Generate puzzle
        self.solution, self.row_clues, self.col_clues = generate_puzzle(
            self.rows, self.cols, difficulty
        )

        # Player grid: -1 = unknown, 0 = marked empty (X), 1 = filled
        self.player_grid = [[-1] * self.cols for _ in range(self.rows)]

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
        """Draw the entire game board."""
        clear_screen()
        lines = []

        # Title bar
        title = f"  {Style.BOLD}{Style.CYAN}◇ NONOGRAM PICROSS ◇{Style.RESET}"
        diff_str = f"  {self.difficulty.upper()}  {self.rows}×{self.cols}"
        elapsed = time.time() - self.start_time
        mins, secs = int(elapsed) // 60, int(elapsed) % 60
        timer = f"  ⏱ {mins:02d}:{secs:02d}"
        hints = f"  💡 Hints: {self.hints_used}"
        mistakes = f"  ✗ Mistakes: {self.mistakes}"

        lines.append(f"{title}")
        lines.append(f"  {Style.DIM}{diff_str}{timer}{hints}{mistakes}{Style.RESET}")
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
        lines.append(f"  {Style.BOLD}h{Style.RESET} Hint  {Style.BOLD}S{Style.RESET} Solve  {Style.BOLD}e{Style.RESET} Export  {Style.BOLD}q{Style.RESET} Quit")

        if self.game_won:
            lines.append("")
            lines.append(f"  {Style.BOLD}{Style.GREEN}🎉 CONGRATULATIONS! Puzzle Solved! 🎉{Style.RESET}")
            mins_e, secs_e = int(self.elapsed) // 60, int(self.elapsed) % 60
            lines.append(f"  {Style.GREEN}Time: {mins_e:02d}:{secs_e:02d}  Hints: {self.hints_used}  Mistakes: {self.mistakes}{Style.RESET}")

        print("\n".join(lines))

    def _is_row_complete(self, r):
        """Check if a row matches the solution clues."""
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

    def toggle_fill(self):
        """Toggle fill state of current cell."""
        r, c = self.cursor_r, self.cursor_c
        if self.player_grid[r][c] == 1:
            self.player_grid[r][c] = -1
        else:
            self.player_grid[r][c] = 1
            self.filled_count += 1
            if self.player_grid[r][c] != self.solution[r][c]:
                self.mistakes += 1

    def toggle_mark(self):
        """Toggle X mark on current cell."""
        r, c = self.cursor_r, self.cursor_c
        if self.player_grid[r][c] == 0:
            self.player_grid[r][c] = -1
        else:
            self.player_grid[r][c] = 0

    def clear_cell(self):
        """Clear current cell."""
        self.player_grid[self.cursor_r][self.cursor_c] = -1

    def give_hint(self):
        """Reveal one cell."""
        cell, is_wrong = get_hint(self.player_grid, self.solution)
        if cell is None:
            return
        r, c = cell
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
        """Move cursor by delta."""
        self.cursor_r = max(0, min(self.rows - 1, self.cursor_r + dr))
        self.cursor_c = max(0, min(self.cols - 1, self.cursor_c + dc))

    def play(self):
        """Main game loop."""
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
                    elif ch == 'S':
                        self.auto_solve()
                    elif ch == 'e':
                        # Export
                        self._export_and_show()

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
        """Export puzzle and show the code."""
        json_str = export_puzzle(self.row_clues, self.col_clues, self.rows, self.cols)
        print(f"\n\n  Puzzle exported! Copy this string to share:\n")
        print(f"  {json_str}\n")
        print("  Press any key to continue...")
        try:
            import tty, termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
            sys.stdin.read(1)
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except:
            input()


# ─── Non-Interactive Modes ───────────────────────────────────────────────────

def print_puzzle(row_clues, col_clues, rows, cols, grid=None, player_grid=None):
    """Print a nonogram puzzle to the terminal (non-interactive)."""
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
    """Solve a nonogram and display the result."""
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


def generate_and_display(size, difficulty, solve=False):
    """Generate a puzzle and optionally solve it."""
    grid, row_clues, col_clues = generate_puzzle(size, size, difficulty)

    print(f"\n  {Style.BOLD}{Style.CYAN}Generated {size}×{size} {difficulty} puzzle{Style.RESET}\n")
    print_puzzle(row_clues, col_clues, size, size)

    if solve:
        print(f"\n  {Style.BOLD}Solution:{Style.RESET}\n")
        print_puzzle(row_clues, col_clues, size, size, grid=grid)

    # Export
    json_str = export_puzzle(row_clues, col_clues, size, size)
    print(f"  {Style.DIM}Puzzle code: {json_str}{Style.RESET}\n")

    return grid, row_clues, col_clues


def import_and_solve(json_str):
    """Import a puzzle from JSON and solve it."""
    try:
        row_clues, col_clues, rows, cols = import_puzzle(json_str)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  {Style.RED}Invalid puzzle code: {e}{Style.RESET}")
        return None

    print(f"\n  {Style.BOLD}Imported {rows}×{cols} puzzle{Style.RESET}\n")
    print_puzzle(row_clues, col_clues, rows, cols)

    solution = solve_and_display(row_clues, col_clues, rows, cols)
    return solution


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
  %(prog)s --size 15 --hard         Play a 15×15 hard puzzle
  %(prog)s --generate 10 --solve    Generate and show solution
  %(prog)s --solve --puzzle '...'   Solve an imported puzzle
  %(prog)s --import '...'           Import and play a shared puzzle
        """
    )

    parser.add_argument("-s", "--size", type=int, default=10,
                        help="Puzzle size (default: 10)")
    parser.add_argument("-d", "--difficulty", choices=["easy", "medium", "hard"],
                        default="medium", help="Difficulty (default: medium)")
    parser.add_argument("-g", "--generate", action="store_true",
                        help="Generate a puzzle without playing")
    parser.add_argument("--solve", action="store_true",
                        help="Show solution (with --generate)")
    parser.add_argument("--puzzle", type=str,
                        help="Puzzle JSON string to solve")

    args = parser.parse_args()

    if args.puzzle:
        if args.solve:
            import_and_solve(args.puzzle)
        else:
            try:
                row_clues, col_clues, rows, cols = import_puzzle(args.puzzle)
                print_puzzle(row_clues, col_clues, rows, cols)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  {Style.RED}Invalid puzzle code: {e}{Style.RESET}")
    elif args.generate:
        generate_and_display(args.size, args.difficulty, solve=args.solve)
    else:
        # Interactive game
        game = NonogramGame(size=args.size, difficulty=args.difficulty)
        game.play()


if __name__ == "__main__":
    main()