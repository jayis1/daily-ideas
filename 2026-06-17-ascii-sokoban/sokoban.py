#!/usr/bin/env python3
"""
ASCII Sokoban — A terminal-based implementation of the classic box-pushing puzzle game.

Move the player (@) to push boxes ($) onto goal positions (.).
A box on a goal is displayed as *.
Use WASD or arrow keys to move. Press 'u' to undo, 'r' to restart, 'q' to quit.

Requires: Python 3.7+ with a terminal that supports ANSI/VT100 escape codes.

Usage:
    python3 sokoban.py              # Play from level 1
    python3 sokoban.py -l 3         # Start at level 3
    python3 sokoban.py --ascii      # Use ASCII characters instead of Unicode
    python3 sokoban.py --help       # Show help
    python3 sokoban.py --version    # Show version
"""

import sys
import tty
import termios
import copy
import re
import time
import argparse
from collections import deque

__version__ = "1.2.0"

# ─── Unicode tile set ──────────────────────────────────────────────
UNICODE_TILES = {
    "wall":       "█",
    "floor":      " ",
    "player":     "☺",
    "box":        "■",
    "goal":       "◇",
    "box_goal":   "◆",
    "player_goal": "☻",
    "border_h":   "━",
    "corner_tl":  "┏",
    "corner_tr":  "┓",
    "corner_bl":  "┗",
    "corner_br":  "┛",
    "side_v":     "┃",
    "top_border": "╍",
    "star":       "★",
    "warn":       "⚠",
}

# ─── ASCII tile set (for terminals without Unicode support) ────────
ASCII_TILES = {
    "wall":       "#",
    "floor":      " ",
    "player":     "@",
    "box":        "$",
    "goal":       ".",
    "box_goal":   "*",
    "player_goal": "+",
    "border_h":   "-",
    "corner_tl":  "+",
    "corner_tr":  "+",
    "corner_bl":  "+",
    "corner_br":  "+",
    "side_v":     "|",
    "top_border": "-",
    "star":       "*",
    "warn":       "!",
}

# ─── ANSI color codes ──────────────────────────────────────────────
class Colors:
    """ANSI color/style codes for terminal rendering."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    BG_GRAY = "\033[48;5;236m"

def colorize(text, *codes):
    """Apply ANSI codes to text, ending with RESET."""
    return "".join(codes) + text + Colors.RESET

def strip_ansi(text):
    """Remove ANSI escape sequences from a string to get its visible width."""
    return re.sub(r'\033\[[0-9;]*[A-Za-z]', '', text)

# ─── Level definitions ─────────────────────────────────────────────
# Each level is a list of strings. Legend:
#   # = wall   . = goal   $ = box   @ = player   + = player on goal
#     * = box on goal   space = floor
LEVELS = [
    # Level 1 — Tutorial: two boxes, two goals
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
        " ###### ",
        "##    ##",
        "# .$   #",
        "# .$ @ #",
        "# .$   #",
        "# $.  ##",
        " ###### ",
    ],
    # Level 6 — Three boxes, zigzag paths
    [
        " ##### ",
        "##   ##",
        "# $ . #",
        "#  $  #",
        "# .$.@#",
        "##   ##",
        " ##### ",
    ],
    # Level 7 — Four boxes, open layout
    [
        " ######",
        "##    #",
        "# .$. #",
        "# .$  #",
        "## $@ #",
        " # .$ #",
        " ######",
    ],
    # Level 8 — The Gauntlet (3 boxes, narrow passages)
    [
        " ######",
        " #    #",
        "##$.$.#",
        "# $  .#",
        "# @ ###",
        "######  ",
    ],
]

# ─── Parser ─────────────────────────────────────────────────────────

def parse_level(lines):
    """Convert level text into internal grid representation.

    Args:
        lines: List of strings representing the level layout.

    Returns:
        Dict with keys: walls, goals, boxes, player, floor, height, width.

    Raises:
        ValueError: If no player position is found in the level.
    """
    # Pad all lines to the same length
    max_len = max(len(l) for l in lines) if lines else 0
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

    if player is None:
        raise ValueError(f"No player position (@) found in level definition")

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
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            np_ = (p[0] + dr, p[1] + dc)
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

def render(state, tiles=None, use_color=False):
    """Return a list of strings representing the current game state.

    Args:
        state: Game state dict from parse_level or try_move.
        tiles: Tile set to use (UNICODE_TILES or ASCII_TILES). Defaults to UNICODE_TILES.
        use_color: If True, apply ANSI color codes to the rendered output.

    Returns:
        List of strings, one per row of the game board.
    """
    if tiles is None:
        tiles = UNICODE_TILES

    h, w = state['height'], state['width']
    lines = []
    for r in range(h):
        row_chars = []
        for c in range(w):
            pos = (r, c)
            char = _render_cell(state, pos, tiles)
            if use_color and tiles is not UNICODE_TILES:
                # No color for ASCII mode
                row_chars.append(char)
            elif use_color:
                row_chars.append(_colorize_cell(state, pos, char))
            else:
                row_chars.append(char)
        lines.append(''.join(row_chars))
    return lines


def _render_cell(state, pos, tiles):
    """Determine the character for a single cell."""
    if pos in state['walls']:
        return tiles["wall"]
    elif pos == state['player']:
        if pos in state['goals']:
            return tiles["player_goal"]
        else:
            return tiles["player"]
    elif pos in state['boxes']:
        if pos in state['goals']:
            return tiles["box_goal"]
        else:
            return tiles["box"]
    elif pos in state['goals']:
        return tiles["goal"]
    elif pos in state['floor']:
        return tiles["floor"]
    else:
        return ' '


def _colorize_cell(state, pos, char):
    """Apply ANSI color to a rendered cell character."""
    if pos in state['walls']:
        return colorize(char, Colors.BG_GRAY, Colors.WHITE)
    elif pos == state['player']:
        if pos in state['goals']:
            return colorize(char, Colors.BOLD, Colors.YELLOW)
        else:
            return colorize(char, Colors.BOLD, Colors.GREEN)
    elif pos in state['boxes']:
        if pos in state['goals']:
            return colorize(char, Colors.BOLD, Colors.GREEN)
        else:
            return colorize(char, Colors.BOLD, Colors.YELLOW)
    elif pos in state['goals']:
        return colorize(char, Colors.CYAN)
    else:
        return char

# ─── Game logic ──────────────────────────────────────────────────────

DIRS = {
    'w': (-1, 0), 'up':    (-1, 0),
    's': (1, 0),  'down':  (1, 0),
    'a': (0, -1), 'left':  (0, -1),
    'd': (0, 1),  'right': (0, 1),
}

def try_move(state, direction):
    """Attempt to move the player in the given direction.

    Args:
        state: Current game state dict.
        direction: Tuple (dr, dc) representing the movement direction.

    Returns:
        New state dict if the move is valid, None if the move is invalid.
        The returned state includes 'pushed' key set to True if a box was pushed.
    """
    dr, dc = direction
    pr, pc = state['player']
    new_player = (pr + dr, pc + dc)

    # Can't move into a wall
    if new_player in state['walls']:
        return None

    # Out of bounds check
    if not (0 <= new_player[0] < state['height'] and 0 <= new_player[1] < state['width']):
        return None

    pushed = False

    # If there's a box, try to push it
    if new_player in state['boxes']:
        new_box = (new_player[0] + dr, new_player[1] + dc)
        # Box can't be pushed into a wall or another box or out of bounds
        if new_box in state['walls'] or new_box in state['boxes']:
            return None
        if not (0 <= new_box[0] < state['height'] and 0 <= new_box[1] < state['width']):
            return None
        # Push the box
        new_boxes = set(state['boxes'])
        new_boxes.remove(new_player)
        new_boxes.add(new_box)
        pushed = True
        return {
            **state,
            'player': new_player,
            'boxes': new_boxes,
            'pushed': True,
        }

    # Simple move (no box pushed)
    # Copy boxes set to avoid shared mutable reference
    return {
        **state,
        'player': new_player,
        'boxes': set(state['boxes']),
        'pushed': False,
    }

def is_win(state):
    """Check if all goals have boxes on them.

    Returns False if there are no goals (vacuous truth is incorrect here;
    an empty goal set means the level is malformed).
    """
    if not state['goals']:
        return False
    return state['goals'] <= frozenset(state['boxes'])

# ─── Deadlock detection ─────────────────────────────────────────────

def is_simple_deadlock(state):
    """Detect simple corner deadlocks: a box in a corner that is not on a goal.

    A box is in a "corner" if it has walls on two perpendicular adjacent sides.
    This is the most common and easily detectable deadlock pattern.
    """
    for box in state['boxes']:
        if box in state['goals']:
            continue
        r, c = box
        wall_up    = (r - 1, c) in state['walls']
        wall_down  = (r + 1, c) in state['walls']
        wall_left  = (r, c - 1) in state['walls']
        wall_right = (r, c + 1) in state['walls']
        if (wall_up and wall_left) or (wall_up and wall_right) or \
           (wall_down and wall_left) or (wall_down and wall_right):
            return True
    return False


def is_wall_deadlock(state):
    """Detect boxes stuck against a wall with no goal along that wall line.

    A box is only considered wall-line deadlocked if it is in a *corridor*
    — i.e., it has walls on BOTH sides of the perpendicular axis, meaning
    it can ONLY slide along the wall line and cannot be pushed away from it.

    For example, a box with a wall above AND below can only move left/right.
    If no goal is reachable along that row, the box is deadlocked.
    """
    walls = state['walls']
    goals = state['goals']

    for box in state['boxes']:
        if box in goals:
            continue
        r, c = box

        # Check horizontal corridor deadlock (wall above AND below → can only slide left/right)
        wall_up = (r - 1, c) in walls
        wall_down = (r + 1, c) in walls

        if wall_up and wall_down:
            # The box is in a horizontal corridor — it can only slide left/right
            if not _goal_reachable_on_wall_line(state, box, horizontal=True):
                return True

        # Check vertical corridor deadlock (wall left AND right → can only slide up/down)
        wall_left = (r, c - 1) in walls
        wall_right = (r, c + 1) in walls

        if wall_left and wall_right:
            # The box is in a vertical corridor — it can only slide up/down
            if not _goal_reachable_on_wall_line(state, box, horizontal=False):
                return True

    return False


def _goal_reachable_on_wall_line(state, box, horizontal=True):
    """Check if a goal is reachable along a wall line for a box.

    If horizontal=True, checks if the box can slide left/right along a
    horizontal corridor to reach a goal. If horizontal=False, checks up/down
    along a vertical corridor.

    Note: This is a heuristic — it checks that no wall blocks the path to a
    goal, but does not account for other boxes that may temporarily block the
    path (since boxes can be moved). This may produce false negatives
    (missing a true deadlock) but avoids false positives.
    """
    r, c = box
    walls = state['walls']
    goals = state['goals']

    if horizontal:
        # Scan left and right along the row for goals that are reachable
        # (no wall blocking the path)
        for dc in (-1, 1):
            cc = c + dc
            while 0 <= cc < state['width']:
                if (r, cc) in walls:
                    break  # wall blocks the path
                if (r, cc) in goals:
                    return True  # found a reachable goal
                cc += dc
    else:
        # Scan up and down along the column for goals
        for dr in (-1, 1):
            rr = r + dr
            while 0 <= rr < state['height']:
                if (rr, c) in walls:
                    break
                if (rr, c) in goals:
                    return True
                rr += dr

    return False


def detect_deadlock(state):
    """Combined deadlock detection. Returns True if any deadlock pattern is found."""
    return is_simple_deadlock(state) or is_wall_deadlock(state)

# ─── Input handling ──────────────────────────────────────────────────

def get_key():
    """Read a single keypress from stdin (handles arrow keys and escape sequences).

    Returns:
        String key identifier: 'up', 'down', 'left', 'right', 'esc', 'quit',
        or the lowercase character pressed.
    """
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
    except (IOError, OSError):
        return 'quit'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# ─── Terminal helpers ────────────────────────────────────────────────

def clear_screen():
    """Clear the terminal screen and move cursor to top-left."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move_cursor(row, col):
    """Move the terminal cursor to the specified position."""
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

# ─── Stats tracking ─────────────────────────────────────────────────

class Stats:
    """Track player statistics across levels."""

    def __init__(self):
        self.total_moves = 0
        self.total_pushes = 0
        self.levels_completed = 0
        self.best_moves = {}   # level_num -> best move count
        self.best_pushes = {}  # level_num -> best push count
        self.best_times = {}  # level_num -> best time (seconds)

    def record_level(self, level_num, moves, pushes, elapsed):
        """Record stats for a completed level."""
        self.total_moves += moves
        self.total_pushes += pushes
        self.levels_completed += 1

        if level_num not in self.best_moves or moves < self.best_moves[level_num]:
            self.best_moves[level_num] = moves
        if level_num not in self.best_pushes or pushes < self.best_pushes[level_num]:
            self.best_pushes[level_num] = pushes
        if level_num not in self.best_times or elapsed < self.best_times[level_num]:
            self.best_times[level_num] = elapsed

# ─── Main game loop ──────────────────────────────────────────────────

def play_level(level_num, level_data, tiles, use_color):
    """Play a single level. Returns True if the player won.

    Args:
        level_num: Zero-based level index.
        level_data: List of strings representing the level layout.
        tiles: Tile set dict (UNICODE_TILES or ASCII_TILES).
        use_color: Whether to use ANSI colors.

    Returns:
        True if the level was completed, False if the player quit.
    """
    try:
        initial_state = parse_level(level_data)
    except ValueError as e:
        print(f"Error in level {level_num + 1}: {e}", file=sys.stderr)
        return False

    state = copy.deepcopy(initial_state)
    # Remove 'pushed' key if it doesn't exist yet
    state.pop('pushed', None)
    history = [(copy.deepcopy(state), 0, 0)]  # (state, moves, pushes) tuples
    moves = 0
    pushes = 0
    start_time = time.time()
    deadlock_warn = False

    while True:
        clear_screen()
        lines = render(state, tiles=tiles, use_color=use_color)

        # Title bar
        level_name = f"Level {level_num + 1}/{len(LEVELS)}"
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"

        boxes_on_goals = sum(1 for b in state['boxes'] if b in state['goals'])
        total_goals = len(state['goals'])
        progress = f"{boxes_on_goals}/{total_goals}"

        status_line = f"  Sokoban — {level_name}  |  Moves: {moves}  Pushes: {pushes}  Progress: {progress}  Time: {time_str}"

        # Draw bordered game area
        # Use visible width (strip ANSI codes) so borders align correctly
        width = max(len(strip_ansi(l)) for l in lines) if lines else 40
        border = tiles["border_h"] * (width + 2)

        sys.stdout.write(f"  {tiles['top_border']}{border}{tiles['top_border']}\n")
        sys.stdout.write(f"{status_line}\n")
        sys.stdout.write(f"  {tiles['corner_tl']}{border}{tiles['corner_tr']}\n")
        for line in lines:
            sys.stdout.write(f"  {tiles['side_v']}{line}{tiles['side_v']}\n")
        sys.stdout.write(f"  {tiles['corner_bl']}{border}{tiles['corner_br']}\n")

        if deadlock_warn:
            warn_msg = f"  {tiles['warn']} Deadlock detected! Press 'u' to undo or 'r' to restart."
            if use_color:
                warn_msg = colorize(warn_msg, Colors.BOLD, Colors.RED)
            sys.stdout.write(warn_msg + "\n")
            deadlock_warn = False
        else:
            sys.stdout.write("\n")

        sys.stdout.write("  Controls: \u2190\u2191\u2193\u2192 / WASD move | u undo | r restart | n next | q quit\n")
        sys.stdout.flush()

        if is_win(state):
            # Victory screen
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            win_msg = f"\n  {tiles['star']} Congratulations! Level complete in {moves} moves, {pushes} pushes, {mins:02d}:{secs:02d}!\n"
            if use_color:
                win_msg = colorize(win_msg, Colors.BOLD, Colors.GREEN)
            sys.stdout.write(win_msg)
            sys.stdout.write("  Press any key to continue...\n")
            sys.stdout.flush()
            get_key()
            return True, moves, pushes, elapsed

        key = get_key()

        if key == 'quit' or key == '\x03':
            return False, moves, pushes, elapsed

        if key == 'q':
            return False, moves, pushes, elapsed

        if key == 'r':
            state = copy.deepcopy(initial_state)
            history = [(copy.deepcopy(state), 0, 0)]
            moves = 0
            pushes = 0
            start_time = time.time()
            continue

        # 'n' to skip level (only if there's a next level)
        if key == 'n':
            if level_num + 1 < len(LEVELS):
                return True, moves, pushes, elapsed  # count as "won" to proceed
            continue

        if key == 'u':
            if len(history) > 1:
                history.pop()
                state, moves, pushes = copy.deepcopy(history[-1])
            continue

        if key in DIRS:
            direction = DIRS[key]
            new_state = try_move(state, direction)
            if new_state is not None:
                pushed_val = new_state.pop('pushed', False)
                if pushed_val:
                    pushes += 1

                state = new_state
                moves += 1
                history.append((copy.deepcopy(state), moves, pushes))

                # Keep history manageable
                if len(history) > 2000:
                    history = history[-1000:]

                # Check for deadlock
                if detect_deadlock(state):
                    deadlock_warn = True


def main():
    """Run the Sokoban game across all levels."""
    parser = argparse.ArgumentParser(
        description="ASCII Sokoban — A terminal-based box-pushing puzzle game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Controls:
  Arrow keys / WASD    Move the player
  u                    Undo last move
  r                    Restart current level
  n                    Skip to next level
  q / Ctrl+C           Quit

Game Rules:
  Push all boxes onto goal positions to complete each level.
  Boxes can only be pushed (not pulled).
  A box pushed into a corner may create a deadlock!
"""
    )
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-l', '--level', type=int, default=1,
                        help='Start at a specific level (1-based, default: 1)')
    parser.add_argument('--ascii', action='store_true',
                        help='Use ASCII characters instead of Unicode tiles')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable ANSI color output')

    args = parser.parse_args()

    # Validate level number
    start_level = args.level - 1  # Convert to 0-based index
    if start_level < 0:
        start_level = 0
    if start_level >= len(LEVELS):
        print(f"Error: Level {args.level} does not exist. There are only {len(LEVELS)} levels.", file=sys.stderr)
        sys.exit(1)

    tiles = ASCII_TILES if args.ascii else UNICODE_TILES
    use_color = not args.no_color and not args.ascii  # ASCII mode implies no color by default

    stats = Stats()
    current_level = start_level

    hide_cursor()
    try:
        while current_level < len(LEVELS):
            result = play_level(current_level, LEVELS[current_level], tiles, use_color)
            won, moves, pushes, elapsed = result
            if won:
                stats.record_level(current_level, moves, pushes, elapsed)
                current_level += 1
            else:
                break

        clear_screen()
        if current_level >= len(LEVELS) and start_level == 0:
            # Completed all levels from the beginning
            print(colorize(f"  ★★★ All {len(LEVELS)} levels complete! You are a Sokoban master! ★★★", Colors.BOLD, Colors.GREEN))
            print(f"\n  Total: {stats.total_moves} moves, {stats.total_pushes} pushes across {stats.levels_completed} levels")
            print()
        elif current_level >= len(LEVELS):
            print(f"  You completed levels {start_level + 1} through {len(LEVELS)}!")
            print()
        else:
            print(f"  Goodbye! You completed {stats.levels_completed} of {len(LEVELS) - start_level} attempted levels.")
            if stats.levels_completed > 0:
                print(f"  Total: {stats.total_moves} moves, {stats.total_pushes} pushes")
            print()
    finally:
        show_cursor()
        clear_screen()


if __name__ == '__main__':
    main()