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

Controls:
  Arrow keys / hjkl — move cursor
  r / Space         — rotate pipe clockwise
  f                 — flow (check solution)
  n                 — new puzzle
  q                 — quit

Dependencies: None (uses only standard library + curses)
"""

import curses
import random
import sys
import math
from collections import deque
from enum import IntEnum


# ─── Direction helpers ───────────────────────────────────────────────

class Dir(IntEnum):
    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3

    def opposite(self):
        return Dir((self + 2) % 4)

    def delta(self):
        """Return (dr, dc) for moving in this direction."""
        return [(-1, 0), (0, 1), (1, 0), (0, -1)][self]


# ─── Pipe definitions ────────────────────────────────────────────────

class PipeType:
    """Each pipe type has a set of connections (directions it links)."""

    def __init__(self, connections, chars):
        """connections: tuple of Dir values; chars: tuple of 4 rotation renderings."""
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

def generate_puzzle(rows, cols, difficulty=1):
    """
    Generate a random pipes puzzle.

    Strategy:
    1. Pick source (left edge) and drain (right edge) rows
    2. Create a random spanning tree of grid cells
    3. Add external connections (LEFT on source, RIGHT on drain)
    4. Place pipe segments matching the edges + external connections
    5. Scramble rotations

    difficulty: 1 = mostly straights/elbows, 2+ = more tees/crosses
    """
    # Place source and drain FIRST so we can force external connections
    source_row = random.randint(0, rows - 1)
    drain_row = random.randint(0, rows - 1)
    while rows > 1 and drain_row == source_row:
        drain_row = random.randint(0, rows - 1)

    # Build random spanning tree using Kruskal's
    all_cells = [(r, c) for r in range(rows) for c in range(cols)]
    edge_list = []
    for r, c in all_cells:
        for d in Dir:
            dr, dc = d.delta()
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if (r, c) < (nr, nc):
                    edge_list.append((r, c, nr, nc))
    random.shuffle(edge_list)

    # Union-Find
    parent = {cell: cell for cell in all_cells}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
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

    # With difficulty 2+, add some extra edges (loops) to create more complex pipes
    if difficulty >= 2:
        extra_count = max(1, (rows * cols) // 6)
        random.shuffle(edge_list)
        added = 0
        for r1, c1, r2, c2 in edge_list:
            if ((r1, c1), (r2, c2)) not in tree_edges:
                edges[(r1, c1)].add((r2, c2))
                edges[(r2, c2)].add((r1, c1))
                added += 1
                if added >= extra_count:
                    break

    # Now build connection direction sets per cell, INCLUDING external connections
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
            # Easy: random rotation, different from correct
            rotations = [0, 1, 2, 3]
            rotations.remove(correct_rotation)
            scrambled = random.choice(rotations)
        else:
            scrambled = random.randint(0, 3)

        grid[(r, c)] = (ptype, scrambled, correct_rotation)

    source = (source_row, -1)
    drain = (drain_row, cols)

    return grid, rows, cols, source, drain


def _find_rotation(ptype, conn_dirs):
    """Find the rotation (0-3) that matches the given connection directions."""
    for rot in range(4):
        if pipe_connections(ptype, rot) == conn_dirs:
            return rot
    # Fallback: find best partial match
    for rot in range(4):
        conns = pipe_connections(ptype, rot)
        if conn_dirs.issubset(conns):
            return rot
    return 0


# ─── Flow checking ───────────────────────────────────────────────────

def check_flow(grid, rows, cols, source, drain):
    """
    Check if water flows from source to drain.
    Returns (solved: bool, filled: set of cells water reaches).
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

    # BFS
    queue = deque([start])
    filled.add(start)

    while queue:
        r, c = queue.popleft()
        ptype, rotation, _ = grid[(r, c)]
        conns = pipe_connections(ptype, rotation)

        for d in conns:
            dr, dc = d.delta()
            nr, nc = r + dr, c + dc

            # Check drain
            if nr == drain_row and nc == cols and d == Dir.RIGHT:
                # Water exits to drain — check if drain cell also connects
                # We just need a path to exit on the right
                pass

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

    # Check if any filled cell in the rightmost column connects RIGHT
    for r in range(rows):
        if (r, cols - 1) in filled:
            ptype, rotation, _ = grid[(r, cols - 1)]
            conns = pipe_connections(ptype, rotation)
            if Dir.RIGHT in conns and r == drain_row:
                return True, filled

    return False, filled


# ─── Game renderer ───────────────────────────────────────────────────

class PipesPuzzle:
    # Color scheme
    COLOR_BG = 0
    COLOR_PIPE = 1
    COLOR_WATER = 2
    COLOR_CURSOR = 3
    COLOR_SOURCE = 4
    COLOR_DRAIN = 5
    COLOR_SOLVED = 6
    COLOR_HEADER = 7

    def __init__(self, stdscr, rows=7, cols=9, difficulty=2):
        self.stdscr = stdscr
        self.rows = rows
        self.cols = cols
        self.difficulty = difficulty
        self.cursor_r = 0
        self.cursor_c = 0
        self.moves = 0
        self.solved = False
        self.filled = set()
        self.show_flow = False
        self.message = ""
        self.message_timer = 0

        self._init_colors()
        self.new_puzzle()

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()

        # Define color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)      # pipe
        curses.init_pair(2, curses.COLOR_BLUE, -1)       # water
        curses.init_pair(3, curses.COLOR_YELLOW, -1)     # cursor
        curses.init_pair(4, curses.COLOR_GREEN, -1)      # source
        curses.init_pair(5, curses.COLOR_RED, -1)        # drain
        curses.init_pair(6, curses.COLOR_GREEN, -1)      # solved
        curses.init_pair(7, curses.COLOR_WHITE, -1)      # header
        curses.init_pair(8, curses.COLOR_CYAN, curses.COLOR_CYAN)    # water fill bg
        curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLUE)   # cursor on water
        curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_GREEN) # solved cell

    def new_puzzle(self):
        self.grid, self.rows, self.cols, self.source, self.drain = \
            generate_puzzle(self.rows, self.cols, self.difficulty)
        self.cursor_r = 0
        self.cursor_c = 0
        self.moves = 0
        self.solved = False
        self.filled = set()
        self.show_flow = False
        self.message = "New puzzle! Rotate pipes to connect source → drain."
        self.message_timer = 120

    def rotate_cw(self):
        if self.solved:
            return
        r, c = self.cursor_r, self.cursor_c
        ptype, rotation, correct = self.grid[(r, c)]
        new_rotation = (rotation + 1) % 4
        self.grid[(r, c)] = (ptype, new_rotation, correct)
        self.moves += 1
        self.show_flow = False

    def check_solution(self):
        if self.solved:
            return
        solved, filled = check_flow(self.grid, self.rows, self.cols,
                                     self.source, self.drain)
        self.filled = filled
        self.show_flow = True
        if solved:
            self.solved = True
            self.message = f"🎉 SOLVED in {self.moves} moves! Press 'n' for new puzzle."
            self.message_timer = 9999
        else:
            self.message = f"Not connected yet. {len(filled)} cells filled. Keep rotating!"
            self.message_timer = 120

    def handle_key(self, key):
        if key in (ord('q'), ord('Q'), 27):  # 27 = ESC
            return False

        if key == ord('n') or key == ord('N'):
            self.new_puzzle()
            return True

        if self.solved and key not in (ord('n'), ord('N'), ord('q'), ord('Q')):
            return True

        # Movement
        moved = False
        if key in (curses.KEY_UP, ord('k'), ord('K')):
            self.cursor_r = max(0, self.cursor_r - 1)
            moved = True
        elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
            self.cursor_r = min(self.rows - 1, self.cursor_r + 1)
            moved = True
        elif key in (curses.KEY_LEFT, ord('h'), ord('H')):
            self.cursor_c = max(0, self.cursor_c - 1)
            moved = True
        elif key in (curses.KEY_RIGHT, ord('l'), ord('L')):
            self.cursor_c = min(self.cols - 1, self.cursor_c + 1)
            moved = True

        # Rotate
        if key in (ord('r'), ord('R'), ord(' ')):
            self.rotate_cw()

        # Flow check
        if key in (ord('f'), ord('F'), 10):  # 10 = Enter
            self.check_solution()

        return True

    def draw(self):
        stdscr = self.stdscr
        stdscr.clear()

        max_y, max_x = stdscr.getmaxyx()
        grid_w = self.cols * 2 + 4  # +2 for source/drain columns, +2 for borders
        grid_h = self.rows + 4       # +2 for borders, +2 for header/footer

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
                stdscr.addstr(ty + i, start_x, line, curses.color_pair(7) | curses.A_BOLD)
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
        flow_text = f"Flow: {len(self.filled)}/{self.rows * self.cols}" if self.show_flow else ""

        try:
            stdscr.addstr(status_y, start_x, moves_text, curses.color_pair(7))
            if flow_text:
                stdscr.addstr(status_y, start_x + 15, flow_text, curses.color_pair(2))
        except curses.error:
            pass

        # Message
        if self.message and self.message_timer > 0:
            msg_y = status_y + 1
            msg_color = curses.color_pair(6) | curses.A_BOLD if self.solved else curses.color_pair(7)
            try:
                stdscr.addstr(msg_y, start_x, self.message, msg_color)
            except curses.error:
                pass
            self.message_timer -= 1

        # Controls
        ctrl_y = status_y + 3
        controls = "hjkl/↑↓←→:move  r/Space:rotate  f/Enter:flow  n:new  q:quit"
        try:
            stdscr.addstr(ctrl_y, start_x, controls, curses.color_pair(7))
        except curses.error:
            pass

        stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(0)   # Blocking input
    stdscr.keypad(True)  # Enable special keys

    # Parse args
    rows = 7
    cols = 9
    difficulty = 2
    if len(sys.argv) > 1:
        try:
            rows = int(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        try:
            cols = int(sys.argv[2])
        except ValueError:
            pass
    if len(sys.argv) > 3:
        try:
            difficulty = int(sys.argv[3])
        except ValueError:
            pass

    # Clamp
    rows = max(3, min(15, rows))
    cols = max(3, min(20, cols))
    difficulty = max(1, min(3, difficulty))

    game = PipesPuzzle(stdscr, rows, cols, difficulty)

    while True:
        game.draw()
        key = stdscr.getch()
        if not game.handle_key(key):
            break


if __name__ == "__main__":
    curses.wrapper(main)