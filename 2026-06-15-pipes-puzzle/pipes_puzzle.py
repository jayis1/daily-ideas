#!/usr/bin/env python3
"""
Pipes Puzzle — A terminal puzzle game where you rotate pipe segments
to connect water flow from source to drain.

Pipe types:
  ║  Straight (vertical)    — connects top & bottom
  ═  Straight (horizontal)  — connects left & right
  ╔  Elbow (top-right)      — connects top & right
  ╗  Elbow (top-left)       — connects top & left
  ╚  Elbow (bottom-right)   — connects bottom & right
  ╝  Elbow (bottom-left)    — connects bottom & left
  ╠  Tee (no top)           — connects left, right, bottom
  ╣  Tee (no left)          — connects top, right, bottom
  ╦  Tee (no bottom)        — connects top, left, right
  ╩  Tee (no top)           — connects top, left, bottom
  ╬  Cross                  — connects all four sides
  ╨ ╞ ╥ ╡  Dead End        — connects one side only

Controls:
  Arrow keys / hjkl — move cursor
  r / Space         — rotate pipe clockwise
  R                 — rotate pipe counter-clockwise
  u                 — undo last rotation
  f                 — flow (check solution / toggle flow display)
  a                 — toggle auto-flow mode (live flow updates)
  n                 — new puzzle
  q / Esc           — quit

Dependencies: None (uses only standard library + curses)
"""

import argparse
import curses
import random
import sys
import time
from collections import deque
from enum import IntEnum


# ─── Version ──────────────────────────────────────────────────────────

__version__ = "2.0.0"


# ─── Direction helpers ───────────────────────────────────────────────

class Dir(IntEnum):
    """Enum for the four cardinal directions used in pipe connections."""
    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3

    def opposite(self):
        """Return the direction opposite to this one."""
        return Dir((self + 2) % 4)

    def delta(self):
        """Return (dr, dc) for moving in this direction."""
        return [(-1, 0), (0, 1), (1, 0), (0, -1)][self]


# ─── Pipe definitions ────────────────────────────────────────────────

class PipeType:
    """Each pipe type has a set of connections (directions it links)."""

    def __init__(self, connections, chars):
        """
        Initialize a pipe type.

        Args:
            connections: tuple of Dir values at rotation 0.
            chars: tuple of 4 character renderings for rotations 0-3.
        """
        self.connections = tuple(connections)
        self.chars = chars

    def rotated(self, times=1):
        """Return a new PipeType rotated clockwise `times` times."""
        new_conns = tuple(Dir((c + times) % 4) for c in self.connections)
        new_chars = tuple(self.chars[(i - times) % 4] for i in range(4))
        return PipeType(new_conns, new_chars)


# Base pipe types (rotation 0)
# Each has 4 character representations for 0, 90, 180, 270 degree rotations
STRAIGHT = PipeType(
    (Dir.TOP, Dir.BOTTOM),
    ('║', '═', '║', '═')
)

ELBOW = PipeType(
    (Dir.TOP, Dir.RIGHT),
    ('╔', '╗', '╝', '╚')
)

TEE = PipeType(
    (Dir.LEFT, Dir.RIGHT, Dir.BOTTOM),
    ('╩', '╠', '╦', '╣')
)

CROSS = PipeType(
    (Dir.TOP, Dir.RIGHT, Dir.BOTTOM, Dir.LEFT),
    ('╬', '╬', '╬', '╬')
)

DEAD_END = PipeType(
    (Dir.TOP,),  # connects only upward at rotation 0
    ('╨', '╞', '╥', '╡')
)

# All base types
PIPE_TYPES = [STRAIGHT, ELBOW, TEE, CROSS, DEAD_END]


def pipe_char(pipe_type, rotation):
    """Get the display character for a pipe at given rotation (0-3)."""
    return pipe_type.chars[rotation % 4]


def pipe_connections(pipe_type, rotation):
    """Get the set of directions this pipe connects at given rotation."""
    return set(Dir((c + rotation) % 4) for c in pipe_type.connections)


# ─── Puzzle generation ───────────────────────────────────────────────

def generate_puzzle(rows, cols, difficulty=1, seed=None):
    """
    Generate a random pipes puzzle.

    Strategy:
    1. Pick source (left edge) and drain (right edge) rows
    2. Create a random spanning tree of grid cells
    3. Add external connections (LEFT on source, RIGHT on drain)
    4. Place pipe segments matching the edges + external connections
    5. Scramble rotations

    Args:
        rows: Number of rows in the grid (3-15).
        cols: Number of columns in the grid (3-20).
        difficulty: 1 = easy (guaranteed not pre-solved), 2 = medium, 3 = hard.
        seed: Optional random seed for reproducible puzzles.

    Returns:
        Tuple of (grid_dict, rows, cols, source, drain).
        grid_dict maps (r, c) -> (PipeType, rotation, correct_rotation).
        source is (row, -1), drain is (row, cols).
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    # Validate dimensions
    rows = max(3, min(15, rows))
    cols = max(3, min(20, cols))
    difficulty = max(1, min(3, difficulty))

    # Place source and drain on different rows (if possible)
    source_row = rng.randint(0, rows - 1)
    drain_row = rng.randint(0, rows - 1)
    if rows > 1:
        while drain_row == source_row:
            drain_row = rng.randint(0, rows - 1)

    # Build random spanning tree using Kruskal's algorithm
    all_cells = [(r, c) for r in range(rows) for c in range(cols)]
    edge_list = []
    for r, c in all_cells:
        for d in Dir:
            dr, dc = d.delta()
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if (r, c) < (nr, nc):
                    edge_list.append((r, c, nr, nc))
    rng.shuffle(edge_list)

    # Union-Find with path compression
    parent = {cell: cell for cell in all_cells}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[a] = b
            return True
        return False

    # Track internal edges per cell
    edges = {cell: set() for cell in all_cells}
    tree_edges = set()

    for r1, c1, r2, c2 in edge_list:
        if union((r1, c1), (r2, c2)):
            tree_edges.add(((r1, c1), (r2, c2)))
            tree_edges.add(((r2, c2), (r1, c1)))
            edges[(r1, c1)].add((r2, c2))
            edges[(r2, c2)].add((r1, c1))

    # With difficulty 2+, add extra edges (loops) for more complex pipes
    if difficulty >= 2:
        extra_count = max(1, (rows * cols) // 6)
        non_tree = [e for e in edge_list
                    if ((e[0], e[1]), (e[2], e[3])) not in tree_edges]
        rng.shuffle(non_tree)
        added = 0
        for r1, c1, r2, c2 in non_tree:
            edges[(r1, c1)].add((r2, c2))
            edges[(r2, c2)].add((r1, c1))
            added += 1
            if added >= extra_count:
                break

    # Build connection direction sets per cell, INCLUDING external connections
    # Source cell gets Dir.LEFT, drain cell gets Dir.RIGHT
    conn_dirs_map = {}
    for r, c in all_cells:
        conn_dirs = set()
        for nr, nc in edges[(r, c)]:
            dr, dc = nr - r, nc - c
            for d in Dir:
                if d.delta() == (dr, dc):
                    conn_dirs.add(d)
        # External connections
        if r == source_row and c == 0:
            conn_dirs.add(Dir.LEFT)
        if r == drain_row and c == cols - 1:
            conn_dirs.add(Dir.RIGHT)
        conn_dirs_map[(r, c)] = conn_dirs

    # Assign pipe types and rotations
    grid = {}
    for r, c in all_cells:
        conn_dirs = conn_dirs_map[(r, c)]
        num_conns = len(conn_dirs)

        if num_conns == 4:
            ptype = CROSS
        elif num_conns == 3:
            ptype = TEE
        elif num_conns == 2:
            d1, d2 = sorted(conn_dirs)
            if d1.opposite() == d2:
                ptype = STRAIGHT
            else:
                ptype = ELBOW
        elif num_conns == 1:
            ptype = DEAD_END
        else:
            # 0 connections: shouldn't happen with spanning tree
            ptype = STRAIGHT

        # Find the correct rotation
        correct_rotation = _find_rotation(ptype, conn_dirs)

        # Scramble rotation
        if difficulty <= 1:
            # Easy: random rotation, different from correct (guarantees not pre-solved)
            rotations = [0, 1, 2, 3]
            rotations.remove(correct_rotation)
            scrambled = rng.choice(rotations)
        else:
            scrambled = rng.randint(0, 3)

        grid[(r, c)] = (ptype, scrambled, correct_rotation)

    source = (source_row, -1)
    drain = (drain_row, cols)

    return grid, rows, cols, source, drain


def _find_rotation(ptype, conn_dirs):
    """Find the rotation (0-3) that matches the given connection directions."""
    for rot in range(4):
        if pipe_connections(ptype, rot) == conn_dirs:
            return rot
    # Fallback: find best partial match (for dead-end or mismatched edges)
    for rot in range(4):
        conns = pipe_connections(ptype, rot)
        if conn_dirs.issubset(conns):
            return rot
    return 0


# ─── Flow checking ───────────────────────────────────────────────────

def check_flow(grid, rows, cols, source, drain):
    """
    Check if water flows from source to drain.

    Uses BFS from the source cell, following pipe connections.

    Args:
        grid: Grid dictionary mapping (r,c) -> (PipeType, rotation, correct_rotation).
        rows: Number of rows.
        cols: Number of columns.
        source: Source position (row, -1).
        drain: Drain position (row, cols).

    Returns:
        Tuple of (solved: bool, filled: set of cells water reaches).
    """
    filled = set()
    source_row = source[0]
    drain_row = drain[0]

    # Start from source: check if (source_row, 0) connects to LEFT
    start = (source_row, 0)
    if start not in grid:
        return False, filled

    ptype, rotation, _ = grid[start]
    conns = pipe_connections(ptype, rotation)
    if Dir.LEFT not in conns:
        return False, filled

    # BFS traversal
    queue = deque([start])
    filled.add(start)

    while queue:
        r, c = queue.popleft()
        ptype, rotation, _ = grid[(r, c)]
        conns = pipe_connections(ptype, rotation)

        for d in conns:
            dr, dc = d.delta()
            nr, nc = r + dr, c + dc

            # Check if water exits to drain
            if nr == drain_row and nc == cols and d == Dir.RIGHT:
                continue  # Valid exit; will be checked after BFS

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            if (nr, nc) in filled:
                continue

            # Check if neighbor connects back
            nptype, nrotation, _ = grid[(nr, nc)]
            nconns = pipe_connections(nptype, nrotation)
            if d.opposite() in nconns:
                filled.add((nr, nc))
                queue.append((nr, nc))

    # Check if any filled cell in the rightmost column connects RIGHT to drain
    for r in range(rows):
        if (r, cols - 1) in filled:
            ptype, rotation, _ = grid[(r, cols - 1)]
            conns = pipe_connections(ptype, rotation)
            if Dir.RIGHT in conns and r == drain_row:
                return True, filled

    return False, filled


# ─── Game state ───────────────────────────────────────────────────────

class PipesPuzzle:
    """Main game class managing state, rendering, and input."""

    # Color pair constants
    COLOR_PIPE = 1
    COLOR_WATER = 2
    COLOR_CURSOR = 3
    COLOR_SOURCE = 4
    COLOR_DRAIN = 5
    COLOR_SOLVED = 6
    COLOR_HEADER = 7
    COLOR_WATER_BG = 8
    COLOR_CURSOR_WATER = 9
    COLOR_SOLVED_CELL = 10
    COLOR_UNDO = 11

    # Version
    VERSION = __version__

    def __init__(self, stdscr, rows=7, cols=9, difficulty=2, seed=None, auto_flow=False):
        """
        Initialize the puzzle game.

        Args:
            stdscr: curses window object.
            rows: Number of rows (3-15).
            cols: Number of columns (3-20).
            difficulty: Difficulty level 1-3.
            seed: Optional random seed for reproducible puzzles.
            auto_flow: If True, continuously show flow state.
        """
        self.stdscr = stdscr
        self.rows = rows
        self.cols = cols
        self.difficulty = difficulty
        self.seed = seed
        self.auto_flow = auto_flow
        self.cursor_r = 0
        self.cursor_c = 0
        self.moves = 0
        self.solved = False
        self.filled = set()
        self.show_flow = False
        self.message = ""
        self.message_timer = 0
        self.undo_stack = []  # Stack of (r, c, old_rotation) for undo
        self.start_time = time.time()  # Timer for tracking elapsed time
        self.solve_time = None  # Time when puzzle was solved

        self._init_colors()
        self.new_puzzle()

    def _init_colors(self):
        """Initialize curses color pairs."""
        curses.start_color()
        curses.use_default_colors()

        # Define color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)      # pipe
        curses.init_pair(2, curses.COLOR_BLUE, -1)       # water
        curses.init_pair(3, curses.COLOR_YELLOW, -1)     # cursor
        curses.init_pair(4, curses.COLOR_GREEN, -1)      # source
        curses.init_pair(5, curses.COLOR_RED, -1)        # drain
        curses.init_pair(6, curses.COLOR_GREEN, -1)      # solved message
        curses.init_pair(7, curses.COLOR_WHITE, -1)      # header
        curses.init_pair(8, curses.COLOR_CYAN, curses.COLOR_CYAN)    # water fill bg
        curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLUE)   # cursor on water
        curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_GREEN) # solved cell
        curses.init_pair(11, curses.COLOR_MAGENTA, -1)  # undo hint

    def new_puzzle(self):
        """Generate a new puzzle and reset game state."""
        # Use seed if provided, otherwise increment for variety
        if self.seed is not None:
            puzzle_seed = self.seed
            self.seed += 1  # Next puzzle gets next seed
        else:
            puzzle_seed = None

        self.grid, self.rows, self.cols, self.source, self.drain = \
            generate_puzzle(self.rows, self.cols, self.difficulty, seed=puzzle_seed)
        self.cursor_r = 0
        self.cursor_c = 0
        self.moves = 0
        self.solved = False
        self.filled = set()
        self.show_flow = False
        self.undo_stack = []
        self.start_time = time.time()
        self.solve_time = None
        self.message = "Rotate pipes to connect source ▶ to drain ▶!"
        self.message_timer = 150

    def rotate_cw(self):
        """Rotate the pipe under the cursor clockwise by 90 degrees."""
        if self.solved:
            return
        r, c = self.cursor_r, self.cursor_c
        ptype, rotation, correct = self.grid[(r, c)]
        # Save state for undo
        self.undo_stack.append((r, c, rotation))
        new_rotation = (rotation + 1) % 4
        self.grid[(r, c)] = (ptype, new_rotation, correct)
        self.moves += 1
        self.show_flow = False
        if self.auto_flow:
            self._update_flow()

    def rotate_ccw(self):
        """Rotate the pipe under the cursor counter-clockwise by 90 degrees."""
        if self.solved:
            return
        r, c = self.cursor_r, self.cursor_c
        ptype, rotation, correct = self.grid[(r, c)]
        # Save state for undo
        self.undo_stack.append((r, c, rotation))
        new_rotation = (rotation - 1) % 4
        self.grid[(r, c)] = (ptype, new_rotation, correct)
        self.moves += 1
        self.show_flow = False
        if self.auto_flow:
            self._update_flow()

    def undo(self):
        """Undo the last rotation."""
        if self.solved or not self.undo_stack:
            if not self.undo_stack:
                self.message = "Nothing to undo!"
                self.message_timer = 60
            return
        r, c, old_rotation = self.undo_stack.pop()
        ptype, _, correct = self.grid[(r, c)]
        self.grid[(r, c)] = (ptype, old_rotation, correct)
        self.moves = max(0, self.moves - 1)
        self.show_flow = False
        if self.auto_flow:
            self._update_flow()
        self.message = f"Undo! (stack: {len(self.undo_stack)} left)"
        self.message_timer = 60

    def _update_flow(self):
        """Update flow state without checking for solve (for auto-flow display)."""
        solved, filled = check_flow(self.grid, self.rows, self.cols,
                                     self.source, self.drain)
        self.filled = filled
        self.show_flow = True
        if solved and not self.solved:
            self.solved = True
            self.solve_time = time.time()
            elapsed = self.solve_time - self.start_time
            self.message = (f"🎉 SOLVED in {self.moves} moves, "
                            f"{elapsed:.1f}s! Press 'n' for new puzzle.")
            self.message_timer = 9999

    def check_solution(self):
        """Manually check if the puzzle is solved and show flow."""
        if self.solved:
            return
        solved, filled = check_flow(self.grid, self.rows, self.cols,
                                     self.source, self.drain)
        self.filled = filled
        self.show_flow = True
        if solved:
            self.solved = True
            self.solve_time = time.time()
            elapsed = self.solve_time - self.start_time
            self.message = (f"🎉 SOLVED in {self.moves} moves, "
                            f"{elapsed:.1f}s! Press 'n' for new puzzle.")
            self.message_timer = 9999
        else:
            self.message = f"Not connected yet. {len(filled)}/{self.rows * self.cols} cells filled."
            self.message_timer = 120

    def get_elapsed_time(self):
        """Get elapsed time string."""
        if self.solve_time:
            elapsed = self.solve_time - self.start_time
        else:
            elapsed = time.time() - self.start_time
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def handle_key(self, key):
        """
        Handle a keypress. Returns False to quit, True to continue.

        Args:
            key: Key code from curses.getch().

        Returns:
            bool: True to continue, False to quit.
        """
        if key in (ord('q'), ord('Q'), 27):  # 27 = ESC
            return False

        if key == ord('n') or key == ord('N'):
            self.new_puzzle()
            return True

        if key == ord('u') or key == ord('U'):
            self.undo()
            return True

        # Toggle auto-flow
        if key == ord('a') or key == ord('A'):
            self.auto_flow = not self.auto_flow
            self.message = f"Auto-flow: {'ON' if self.auto_flow else 'OFF'}"
            self.message_timer = 90
            if self.auto_flow:
                self._update_flow()
            return True

        # After solving, only allow new game or quit
        if self.solved and key not in (ord('n'), ord('N'), ord('q'), ord('Q')):
            return True

        # Movement
        if key in (curses.KEY_UP, ord('k'), ord('K')):
            self.cursor_r = max(0, self.cursor_r - 1)
        elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
            self.cursor_r = min(self.rows - 1, self.cursor_r + 1)
        elif key in (curses.KEY_LEFT, ord('h'), ord('H')):
            self.cursor_c = max(0, self.cursor_c - 1)
        elif key in (curses.KEY_RIGHT, ord('l'), ord('L')):
            self.cursor_c = min(self.cols - 1, self.cursor_c + 1)

        # Rotate
        if key in (ord('r'), ord(' ')):
            self.rotate_cw()
        elif key == ord('R'):
            self.rotate_ccw()

        # Flow check
        if key in (ord('f'), ord('F'), 10):  # 10 = Enter
            self.check_solution()

        return True

    def draw(self):
        """Render the entire game state to the terminal via curses."""
        stdscr = self.stdscr
        stdscr.clear()

        max_y, max_x = stdscr.getmaxyx()

        # Calculate grid dimensions
        grid_w = self.cols * 2 + 4  # +2 for source/drain columns, +2 for borders
        grid_h = self.rows + 6       # +2 for borders, +4 for header/status/controls

        # Warn if terminal is too small
        if max_y < grid_h + 2 or max_x < grid_w + 2:
            try:
                stdscr.addstr(0, 0, f"Terminal too small! Need {grid_w + 2}x{grid_h + 2}, "
                              f"have {max_x}x{max_y}", curses.color_pair(5) | curses.A_BOLD)
                stdscr.addstr(1, 0, "Press q to quit.", curses.color_pair(7))
                stdscr.refresh()
            except curses.error:
                pass
            return

        # Calculate offsets to center
        start_x = max(0, (max_x - grid_w) // 2)
        start_y = max(0, (max_y - grid_h) // 2)

        # Title
        title = "╔══════════════════════╗"
        title2 = "║    PIPES  PUZZLE     ║"
        title3 = "╚══════════════════════╝"
        ty = start_y
        for i, line in enumerate([title, title2, title3]):
            try:
                stdscr.addstr(ty + i, start_x, line,
                              curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass

        start_y = ty + 4

        # Draw source arrow
        src_row = self.source[0]
        arrow_x = start_x + 1
        arrow_y = start_y + src_row
        try:
            src_color = curses.color_pair(4) | curses.A_BOLD
            stdscr.addstr(arrow_y, arrow_x, "▶", src_color)
        except curses.error:
            pass

        # Draw drain arrow
        drn_row = self.drain[0]
        drain_x = start_x + 2 + self.cols * 2
        drain_y = start_y + drn_row
        try:
            drn_color = curses.color_pair(5) | curses.A_BOLD
            stdscr.addstr(drain_y, drain_x, "▶", drn_color)
        except curses.error:
            pass

        # Draw grid
        for r in range(self.rows):
            for c in range(self.cols):
                ptype, rotation, _ = self.grid[(r, c)]
                ch = pipe_char(ptype, rotation)

                cell_y = start_y + r
                cell_x = start_x + 2 + c * 2

                # Determine color
                is_cursor = (r == self.cursor_r and c == self.cursor_c)
                is_filled = (r, c) in self.filled and self.show_flow

                if self.solved:
                    color = curses.color_pair(10) | curses.A_BOLD
                elif is_cursor and is_filled:
                    color = curses.color_pair(9) | curses.A_BOLD
                elif is_cursor:
                    color = curses.color_pair(3) | curses.A_BOLD
                elif is_filled:
                    color = curses.color_pair(2) | curses.A_BOLD
                else:
                    color = curses.color_pair(1)

                try:
                    stdscr.addstr(cell_y, cell_x, ch, color)
                except curses.error:
                    pass

                # Space between cells
                try:
                    stdscr.addstr(cell_y, cell_x + 1, " ", color)
                except curses.error:
                    pass

        # Status bar
        status_y = start_y + self.rows + 1
        moves_text = f"Moves: {self.moves}"
        flow_pct = ""
        if self.show_flow and self.filled:
            total = self.rows * self.cols
            pct = len(self.filled) * 100 // total
            flow_pct = f"  Flow: {len(self.filled)}/{total} ({pct}%)"
        time_text = f"  Time: {self.get_elapsed_time()}"
        difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard"}
        diff_text = f"  {difficulty_names.get(self.difficulty, '?')}"

        # Build status line pieces and write them
        x_off = 0
        status_parts = [(moves_text, curses.color_pair(7))]
        if flow_pct:
            status_parts.append((flow_pct, curses.color_pair(2)))
        status_parts.append((time_text, curses.color_pair(7)))
        status_parts.append((diff_text, curses.color_pair(7)))
        if self.auto_flow:
            status_parts.append((" [AUTO]", curses.color_pair(2) | curses.A_BOLD))
        for text, color in status_parts:
            try:
                stdscr.addstr(status_y, start_x + x_off, text, color)
                x_off += len(text)
            except curses.error:
                pass

        # Undo stack indicator
        if self.undo_stack:
            try:
                undo_text = f"  Undo: {len(self.undo_stack)}"
                stdscr.addstr(status_y + 0, start_x + grid_w - len(undo_text) - 2,
                              undo_text, curses.color_pair(11))
            except curses.error:
                pass

        # Message
        if self.message and self.message_timer > 0:
            msg_y = status_y + 1
            msg_color = (curses.color_pair(6) | curses.A_BOLD
                         if self.solved else curses.color_pair(7))
            try:
                stdscr.addstr(msg_y, start_x, self.message, msg_color)
            except curses.error:
                pass
            self.message_timer -= 1

        # Controls help
        ctrl_y = status_y + 3
        controls = ("hjkl/↑↓←→:move  r/Space:rotate  R:ccw  "
                     "f:flow  a:auto  u:undo  n:new  q:quit")
        try:
            stdscr.addstr(ctrl_y, start_x, controls, curses.color_pair(7))
        except curses.error:
            pass

        stdscr.refresh()


# ─── CLI ──────────────────────────────────────────────────────────────

def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="pipes_puzzle",
        description="Pipes Puzzle — Rotate pipe segments to connect water flow from source to drain.",
        epilog="Examples:\n"
               "  pipes_puzzle              # Default: 7x9 grid, Medium difficulty\n"
               "  pipes_puzzle 5 7 1        # 5x7 Easy\n"
               "  pipes_puzzle 10 15 3      # 10x15 Hard\n"
               "  pipes_puzzle --seed 42     # Reproducible puzzle with seed 42\n"
               "  pipes_puzzle --auto-flow   # Live flow visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "rows", nargs="?", type=int, default=7,
        help="Number of rows (3-15, default: 7)"
    )
    parser.add_argument(
        "cols", nargs="?", type=int, default=9,
        help="Number of columns (3-20, default: 9)"
    )
    parser.add_argument(
        "difficulty", nargs="?", type=int, default=2,
        help="Difficulty level 1-3 (default: 2)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible puzzles"
    )
    parser.add_argument(
        "--auto-flow", action="store_true",
        help="Automatically show water flow as you rotate pipes"
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}"
    )
    return parser.parse_args(argv)


def main(stdscr, args=None):
    """Main game loop wrapped by curses."""
    if args is None:
        args = parse_args()

    # Validate and clamp dimensions
    rows = max(3, min(15, args.rows))
    cols = max(3, min(20, args.cols))
    difficulty = max(1, min(3, args.difficulty))

    # Set up curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(0)   # Blocking input
    stdscr.keypad(True)  # Enable special keys

    game = PipesPuzzle(stdscr, rows, cols, difficulty,
                       seed=args.seed, auto_flow=args.auto_flow)

    while True:
        game.draw()
        key = stdscr.getch()
        if not game.handle_key(key):
            break


if __name__ == "__main__":
    # Parse args before curses init so --help and --version work in a terminal
    args = parse_args()
    curses.wrapper(main, args)