#!/usr/bin/env python3
"""
ASCII Sokoban — A terminal-based implementation of the classic box-pushing puzzle game.

Move the player (@) to push boxes (■) onto goal positions (◇).
A box on a goal is displayed as ◆.
Use WASD or arrow keys to move. Press 'u' to undo, 'r' to restart, 'q' to quit.

Requires: Python 3.7+ with a terminal that supports ANSI/VT100 escape codes.
"""

import sys
import tty
import termios
import copy
import time
from collections import deque

# ─── Unicode tile set ──────────────────────────────────────────────
WALL      = "█"
FLOOR     = " "
PLAYER    = "☺"
BOX       = "■"
GOAL      = "◇"
BOX_GOAL  = "◆"
PLAYER_GOAL = "☻"

# ─── Level definitions ─────────────────────────────────────────────
# Each level is a list of strings. Legend:
#   # = wall   . = goal   $ = box   @ = player   + = player on goal
#     * = box on goal   space = floor
LEVELS = [
    # Level 1 — Tutorial: one box, one goal
    [
        "  ####  ",
        "  #  #  ",
        "  #$ #  ",
        "###  ###",
        "#  $ .#",
        "# @. ##",
        "#####  ",
    ],
    # Level 2 — Two boxes, two goals
    [
        "######  ",
        "#    ## ",
        "#  $. # ",
        "#  $.## ",
        "##  ### ",
        " # @ #  ",
        " #####  ",
    ],
    # Level 3 — L-shape
    [
        "#####   ",
        "#   #   ",
        "# $ ### ",
        "# $ . # ",
        "## .### ",
        " #@ #   ",
        " ####   ",
    ],
    # Level 4 — Tight corridors
    [
        " ######",
        "##    #",
        "# $ $ #",
        "# . . #",
        "## # ##",
        " # @ #",
        " #####",
    ],
    # Level 5 — Challenge (4 boxes, 4 goals)
    [
        "  #####   ",
        "###   ##  ",
        "# .$  #  ",
        "# # .$##  ",
        "# .$ $ #  ",
        "## .#@ #  ",
        " #   ##   ",
        " #####    ",
    ],
]

# ─── Parser ─────────────────────────────────────────────────────────

def parse_level(lines):
    """Convert level text into internal grid representation."""
    # Pad all lines to the same length
    max_len = max(len(l) for l in lines)
    rows = [l.ljust(max_len) for l in lines]
    height = len(rows)
    width = max_len

    walls   = set()
    goals   = set()
    boxes   = set()
    player  = None

    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            pos = (r, c)
            if ch == '#':
                walls.add(pos)
            elif ch == '.':
                goals.add(pos)
            elif ch == '$':
                boxes.add(pos)
            elif ch == '@':
                player = pos
            elif ch == '+':  # player on goal
                player = pos
                goals.add(pos)
            elif ch == '*':  # box on goal
                boxes.add(pos)
                goals.add(pos)
            # space = floor, nothing to record

    # Determine which floor cells are reachable (inside the walls)
    # using flood-fill from the player
    floor = set()
    visited = set()
    queue = deque([player])
    while queue:
        p = queue.popleft()
        if p in visited or p in walls:
            continue
        visited.add(p)
        floor.add(p)
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            np_ = (p[0]+dr, p[1]+dc)
            if 0 <= np_[0] < height and 0 <= np_[1] < width and np_ not in walls and np_ not in visited:
                queue.append(np_)

    return {
        'walls': walls,
        'goals': frozenset(goals),
        'boxes': boxes,
        'player': player,
        'floor': floor,
        'height': height,
        'width': width,
    }

# ─── Renderer ────────────────────────────────────────────────────────

def render(state):
    """Return a list of strings representing the current game state."""
    h, w = state['height'], state['width']
    lines = []
    for r in range(h):
        row_chars = []
        for c in range(w):
            pos = (r, c)
            if pos in state['walls']:
                row_chars.append(WALL)
            elif pos == state['player']:
                if pos in state['goals']:
                    row_chars.append(PLAYER_GOAL)
                else:
                    row_chars.append(PLAYER)
            elif pos in state['boxes']:
                if pos in state['goals']:
                    row_chars.append(BOX_GOAL)
                else:
                    row_chars.append(BOX)
            elif pos in state['goals']:
                row_chars.append(GOAL)
            elif pos in state['floor']:
                row_chars.append(FLOOR)
            else:
                row_chars.append(' ')
        lines.append(''.join(row_chars))
    return lines

# ─── Game logic ──────────────────────────────────────────────────────

DIRS = {
    'w': (-1, 0), 'up':    (-1, 0),
    's': (1, 0),  'down':  (1, 0),
    'a': (0, -1), 'left':  (0, -1),
    'd': (0, 1),  'right': (0, 1),
}

def try_move(state, direction):
    """Attempt to move the player in the given direction. Returns new state or None if move is invalid."""
    dr, dc = direction
    pr, pc = state['player']
    new_player = (pr + dr, pc + dc)

    # Can't move into a wall
    if new_player in state['walls']:
        return None

    # If there's a box, try to push it
    if new_player in state['boxes']:
        new_box = (new_player[0] + dr, new_player[1] + dc)
        # Box can't be pushed into a wall or another box
        if new_box in state['walls'] or new_box in state['boxes']:
            return None
        # Push the box
        new_boxes = set(state['boxes'])
        new_boxes.remove(new_player)
        new_boxes.add(new_box)
        return {
            **state,
            'player': new_player,
            'boxes': new_boxes,
        }

    # Simple move
    return {
        **state,
        'player': new_player,
    }

def is_win(state):
    """Check if all goals have boxes on them."""
    return state['goals'] <= frozenset(state['boxes'])

# ─── Deadlock detection (simple corner deadlock) ─────────────────────

def is_simple_deadlock(state):
    """Detect simple corner deadlocks: a box in a corner that is not on a goal."""
    for box in state['boxes']:
        if box in state['goals']:
            continue
        r, c = box
        # Check all four corner patterns
        wall_up = (r-1, c) in state['walls']
        wall_down = (r+1, c) in state['walls']
        wall_left = (r, c-1) in state['walls']
        wall_right = (r, c+1) in state['walls']
        if (wall_up and wall_left) or (wall_up and wall_right) or \
           (wall_down and wall_left) or (wall_down and wall_right):
            return True
    return False

# ─── Input handling ──────────────────────────────────────────────────

def get_key():
    """Read a single keypress from stdin (handles arrow keys)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # ESC sequence
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'up'
                elif ch3 == 'B':
                    return 'down'
                elif ch3 == 'C':
                    return 'right'
                elif ch3 == 'D':
                    return 'left'
                else:
                    return 'esc'
            return 'esc'
        elif ch == '\x03':  # Ctrl-C
            return 'quit'
        return ch.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# ─── Terminal helpers ────────────────────────────────────────────────

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move_cursor(row, col):
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

# ─── Main game loop ──────────────────────────────────────────────────

def play_level(level_num, level_data):
    """Play a single level. Returns True if the player won."""
    initial_state = parse_level(level_data)
    state = copy.deepcopy(initial_state)
    history = [copy.deepcopy(state)]
    moves = 0
    pushes = 0
    start_time = time.time()
    deadlock_warn = False

    while True:
        clear_screen()
        lines = render(state)
        
        # Title bar
        level_name = f"Level {level_num + 1}/{len(LEVELS)}"
        status_line = f"  Sokoban — {level_name}  |  Moves: {moves}  Pushes: {pushes}"
        
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        # Draw
        width = max(len(l) for l in lines) if lines else 40
        border = "━" * (width + 2)
        
        sys.stdout.write(f"  ╍{border}╍\n")
        sys.stdout.write(f"{status_line}  Time: {time_str}\n")
        sys.stdout.write(f"  ┏{border}┓\n")
        for line in lines:
            sys.stdout.write(f"  ┃{line}┃\n")
        sys.stdout.write(f"  ┗{border}┛\n")
        
        if deadlock_warn:
            sys.stdout.write("  ⚠ Deadlock detected! Press 'u' to undo or 'r' to restart.\n")
            deadlock_warn = False
        else:
            sys.stdout.write("\n")
        
        sys.stdout.write("  Controls: ←↑↓→ / WASD move │ u undo │ r restart │ q quit\n")
        sys.stdout.flush()

        if is_win(state):
            # Victory screen
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            sys.stdout.write(f"\n  ★ Congratulations! Level complete in {moves} moves, {pushes} pushes, {mins:02d}:{secs:02d}!\n")
            sys.stdout.write("  Press any key to continue...\n")
            sys.stdout.flush()
            get_key()
            return True

        key = get_key()

        if key == 'quit' or key == '\x03':
            return False

        if key == 'q':
            return False

        if key == 'r':
            state = copy.deepcopy(initial_state)
            history = [copy.deepcopy(state)]
            moves = 0
            pushes = 0
            start_time = time.time()
            continue

        if key == 'u':
            if len(history) > 1:
                history.pop()
                state = copy.deepcopy(history[-1])
                moves = max(0, moves - 1)
            continue

        if key in DIRS:
            direction = DIRS[key]
            new_state = try_move(state, direction)
            if new_state is not None:
                # Count pushes: if the cell we moved into had a box, it was a push
                dr, dc = direction
                moved_to = (state['player'][0] + dr, state['player'][1] + dc)
                if moved_to in state['boxes']:
                    pushes += 1
                
                state = new_state
                moves += 1
                history.append(copy.deepcopy(state))
                
                # Keep history manageable
                if len(history) > 1000:
                    history = history[-500:]
                
                # Check for deadlock
                if is_simple_deadlock(state):
                    deadlock_warn = True


def main():
    """Run the Sokoban game across all levels."""
    hide_cursor()
    try:
        current_level = 0
        while current_level < len(LEVELS):
            won = play_level(current_level, LEVELS[current_level])
            if not won:
                break
            current_level += 1
        
        clear_screen()
        if current_level >= len(LEVELS):
            print("  ★★★ All levels complete! You are a Sokoban master! ★★★\n")
        else:
            print(f"  Goodbye! You completed {current_level} of {len(LEVELS)} levels.\n")
    finally:
        show_cursor()
        clear_screen()


if __name__ == '__main__':
    main()