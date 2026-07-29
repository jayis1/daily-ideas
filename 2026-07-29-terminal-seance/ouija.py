#!/usr/bin/env python3
"""
Terminal Séance — an interactive Ouija board simulator.

Conduct a séance in your terminal. The planchette glides across the board,
spelling out messages from beyond. Ask a question, wait for the spirits...

Controls:
  ENTER   — ask a question / continue
  r       — re-roll the spirit (new personality)
  q       — quit the séance
  SPACE   — skip the animation of the current letter
  h       — help / show controls
  s       — save current session transcript to a file

CLI flags:
  --version        — print version and exit
  --list-spirits   — list all available spirits and exit
  --spirit NAME    — summon a specific spirit by name (case-insensitive)
  --no-color       — disable ANSI colors (accessibility / pipe-friendly)
  --slow           — slow, dramatic planchette movement
  --fast           — faster planchette (for the impatient)
  --log FILE       — append session Q&A to FILE
  --demo           — non-interactive auto-séance (cycles through spirits)
  --seed N         — deterministic random seed (reproducible séances)
"""

import argparse
import math
import os
import random
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

__version__ = "1.1.0"

# ---------------------------------------------------------------------------
# Board layout
# ---------------------------------------------------------------------------

BOARD_WIDTH = 60
BOARD_HEIGHT = 22

# Row 1: YES | NO corner moons
# Row 2-4: LETTERS (A-M top arc, N-Z bottom arc)
# Row 5: NUMBERS
# Row 6: "GOODBYE"
# Decorative: sun & moon in corners, stars

LETTERS_TOP = list("ABCDEFGHIJKLM")
LETTERS_BOTTOM = list("NOPQRSTUVWXYZ")
NUMBERS = list("0123456789")


def compute_positions():
    """Compute (col, row) positions for every letter and number on the board.

    Top arc letters (A-M) get a gentle downward bulge in the middle;
    bottom arc letters (N-Z) get the mirror-image upward bulge, giving
    the classic two-arc Ouija layout.  Numbers sit on a straight line
    below the arcs.
    """
    positions = {}
    # Top arc: A-M spread across with slight curve (middle higher)
    top_y_base = 7
    for i, ch in enumerate(LETTERS_TOP):
        col = 6 + i * 4
        # arc: middle letters slightly higher (smaller y)
        arc = -int(round(1.5 * math.sin(math.pi * i / (len(LETTERS_TOP) - 1))))
        positions[ch] = (col, top_y_base + arc)
    # Bottom arc: N-Z (middle lower)
    bottom_y_base = 11
    for i, ch in enumerate(LETTERS_BOTTOM):
        col = 6 + i * 4
        arc = int(round(1.5 * math.sin(math.pi * i / (len(LETTERS_BOTTOM) - 1))))
        positions[ch] = (col, bottom_y_base + arc)
    # Numbers row
    for i, ch in enumerate(NUMBERS):
        col = 12 + i * 4
        positions[ch] = (col, 16)
    return positions


LETTER_POS = compute_positions()

YES_POS = (20, 3)
NO_POS = (BOARD_WIDTH - 24, 3)
GOODBYE_POS = (BOARD_WIDTH // 2 - 4, 19)
PLANCHETTE_HOME = (BOARD_WIDTH // 2, 14)

# ---------------------------------------------------------------------------
# Spirits — each has a personality that shapes responses
# ---------------------------------------------------------------------------

SPIRITS = [
    {
        "name": "The Whisperer",
        "color": "\033[38;5;141m",  # purple
        "desc": "a faint, sorrowful presence",
        "style": "cryptic",
        "vocabulary": ["SHADOWS", "REMEMBER", "COLD", "FORGOTTEN", "SILENCE",
                       "BENEATH", "WHISPERS", "DREAM", "FADING", "LONG AGO",
                       "STILL HERE", "WAITING", "ALONE", "DARKNESS"],
        "farewell": "FADE",
        "favor_yes": 0.35,
    },
    {
        "name": "Captain Aldous",
        "color": "\033[38;5;75m",  # sea blue
        "desc": "an old sea captain lost in 1887",
        "style": "nautical",
        "vocabulary": ["STORM", "DROWNED", "THE SEA", "MY SHIP", "COMPASS",
                       "NORTH STAR", "DEEP", "WAVES", "ANCHOR", "NO LAND",
                       "FOG", "CAPTAIN", "GO DOWN", "ALL HANDS"],
        "farewell": "SINK",
        "favor_yes": 0.5,
    },
    {
        "name": "Little Rose",
        "color": "\033[38;5;217m",  # pink
        "desc": "a child who never grew up",
        "style": "childish",
        "vocabulary": ["PLAY", "MAMA", "HIDE", "SEEK", "DOLL", "GARDEN",
                       "TIRED", "SLEEPY", "PRETTY", "MY FRIEND", "COME PLAY",
                       "DON'T GO", "STAY", "LAUGH"],
        "farewell": "NIGHT NIGHT",
        "favor_yes": 0.6,
    },
    {
        "name": "The Mathematician",
        "color": "\033[38;5;114m",  # green
        "desc": "a scholar obsessed with prime numbers",
        "style": "precise",
        "vocabulary": ["7", "13", "42", "101", "313", "INFINITE",
                       "PRIME", "RECUR", "SEQUENCE", "PI", "PROOF",
                       "UNDEFINED", "ZERO", "CONVERGE"],
        "farewell": "0",
        "favor_yes": 0.45,
    },
    {
        "name": "The Jester",
        "color": "\033[38;5;220m",  # gold
        "desc": "a trickster who never tells a straight answer",
        "style": "mischievous",
        "vocabulary": ["MAYBE", "PERHAPS", "WHO KNOWS", "FOOL", "DANCE",
                       "LAUGH", "TRICK", "NOTHING", "EVERYTHING", "UPSIDE DOWN",
                       "TEE HEE", "GUESS", "NEVER", "ALWAYS"],
        "farewell": "BOO",
        "favor_yes": 0.55,
    },
    {
        "name": "The Prophet",
        "color": "\033[38;5;196m",  # red
        "desc": "a seer who speaks only of what is to come",
        "style": "prophetic",
        "vocabulary": ["SOON", "BEWARE", "FIRE", "CHANGE", "COMETH",
                       "THE END", "DAWN", "AFTER", "SHALL", "WILL BE",
                       "INEVITABLE", "MARK MY WORDS", "PROPHECY", "BE READY"],
        "farewell": "IT IS WRITTEN",
        "favor_yes": 0.5,
    },
    {
        "name": "The Inventor",
        "color": "\033[38;5;208m",  # orange
        "desc": "a Victorian tinkerer trapped between gears",
        "style": "mechanical",
        "vocabulary": ["GEAR", "STEAM", "CLOCKWORK", "INVENT", "WIRE",
                       "LEVER", "PATENT", "ENGINE", "SPRING", "COG",
                       "TURN", "POWER", "MACHINE", "FORWARD"],
        "farewell": "STOP",
        "favor_yes": 0.48,
    },
    {
        "name": "The Mourner",
        "color": "\033[38;5;60m",  # muted blue-grey
        "desc": "a widow in perpetual grief, endlessly waiting",
        "style": "sorrowful",
        "vocabulary": ["MY LOVE", "COME BACK", "TOO SOON", "EMPTY", "ALWAYS",
                       "NEVER AGAIN", "TEARS", "GRAVE", "FLOWERS", "WINTER",
                       "COLD HANDS", "PROMISE", "FORGIVE", "WHY"],
        "farewell": "REST",
        "favor_yes": 0.3,
    },
]

# Quick lookup for --spirit flag (case-insensitive)
SPIRIT_BY_NAME = {s["name"].lower(): s for s in SPIRITS}

# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

ANSI_RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

# When --no-color is used these are all replaced with ""
_NO_COLOR = False


def _c(code: str) -> str:
    """Return the ANSI *code* unless --no-color is active."""
    return "" if _NO_COLOR else code


def set_no_color(enabled: bool):
    """Globally enable/disable ANSI color output."""
    global _NO_COLOR
    _NO_COLOR = enabled


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def hide_cursor():
    if not _NO_COLOR:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()


def show_cursor():
    if not _NO_COLOR:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def move_to(row, col):
    sys.stdout.write(f"\033[{row};{col}H")


def get_terminal_size():
    """Return (cols, rows) of the terminal, with a sensible fallback."""
    try:
        size = os.get_terminal_size(sys.stdout.fileno())
        return size.columns, size.lines
    except (OSError, ValueError, AttributeError):
        return 80, 24


def check_terminal_size():
    """Warn (but don't abort) if the terminal is smaller than the board."""
    cols, rows = get_terminal_size()
    warnings = []
    if cols < BOARD_WIDTH + 4:
        warnings.append(f"Terminal width {cols} is narrow; board needs ~{BOARD_WIDTH + 4} cols.")
    if rows < BOARD_HEIGHT + 10:
        warnings.append(f"Terminal height {rows} is short; board needs ~{BOARD_HEIGHT + 10} rows.")
    return warnings

# ---------------------------------------------------------------------------
# Board rendering
# ---------------------------------------------------------------------------


def render_board(spirit_color, planchette_pos, trail=None):
    """Render the Ouija board into a grid, then return it as a string.

    Returns a tuple ``(board_str, planchette_overlay)`` where *board_str* is
    the full board as a printable string and *planchette_overlay* is a list
    of ``(row, col, char)`` tuples that should be drawn on top using ANSI
    cursor positioning.
    """
    grid = [[" " for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]

    # Border
    for x in range(BOARD_WIDTH):
        grid[0][x] = "═"
        grid[BOARD_HEIGHT - 1][x] = "═"
    for y in range(BOARD_HEIGHT):
        grid[y][0] = "║"
        grid[y][BOARD_WIDTH - 1] = "║"
    # Corners
    grid[0][0] = "╔"
    grid[0][BOARD_WIDTH - 1] = "╗"
    grid[BOARD_HEIGHT - 1][0] = "╚"
    grid[BOARD_HEIGHT - 1][BOARD_WIDTH - 1] = "╝"

    # YES / NO
    for i, ch in enumerate("YES"):
        grid[YES_POS[1]][YES_POS[0] + i] = ch
    for i, ch in enumerate("NO"):
        grid[NO_POS[1]][NO_POS[0] + i] = ch

    # GOODBYE
    bye = "GOODBYE"
    for i, ch in enumerate(bye):
        grid[GOODBYE_POS[1]][GOODBYE_POS[0] + i] = ch

    # Sun (top-left corner decoration) — small
    sun = ["\\ | /", "- O -", "/ | \\"]
    for i, line in enumerate(sun):
        for j, ch in enumerate(line):
            if 1 + i < BOARD_HEIGHT - 1 and 2 + j < BOARD_WIDTH - 1:
                grid[1 + i][2 + j] = ch

    # Moon (top-right) — small
    moon = ["/   \\", "(    )", "\\___/"]
    for i, line in enumerate(moon):
        for j, ch in enumerate(line):
            cy = 1 + i
            cx = BOARD_WIDTH - 7 + j
            if cy < BOARD_HEIGHT - 1 and 0 < cx < BOARD_WIDTH - 1:
                grid[cy][cx] = ch

    # Letters
    for ch, (cx, cy) in LETTER_POS.items():
        if 0 < cx < BOARD_WIDTH - 1 and 0 < cy < BOARD_HEIGHT - 1:
            grid[cy][cx] = ch

    # Decorative stars
    star_spots = [(3, 28), (3, 35), (4, 22), (4, 42), (18, 8), (18, 50), (17, 30)]
    for sy, sx in star_spots:
        if 0 < sx < BOARD_WIDTH - 1 and 0 < sy < BOARD_HEIGHT - 1:
            grid[sy][sx] = "*"

    # Trail (faint planchette path)
    if trail:
        for (tx, ty, age) in trail:
            if 0 < tx < BOARD_WIDTH - 1 and 0 < ty < BOARD_HEIGHT - 1 and age < 5:
                char = "·" if age < 2 else " " if age > 3 else "⋅"
                if char.strip() and grid[ty][tx] == " ":
                    grid[ty][tx] = _c(DIM) + char + _c(ANSI_RESET)

    sc = _c(spirit_color)
    bold = _c(BOLD)
    reset = _c(ANSI_RESET)

    # Build output buffer
    out = []
    out.append(sc + bold + "  ╔" + "═" * (BOARD_WIDTH) + "╗" + reset)
    # Title bar
    title = "  THE SPIRIT BOARD  "
    title_line = "║" + title.center(BOARD_WIDTH) + "║"
    out.append(sc + bold + title_line + reset)
    out.append(sc + bold + "  ╠" + "═" * (BOARD_WIDTH) + "╣" + reset)

    for y in range(BOARD_HEIGHT):
        row_chars = []
        for x in range(BOARD_WIDTH):
            row_chars.append(grid[y][x])
        out.append("  " + sc + "║" + reset + "".join(row_chars) + sc + "║" + reset)

    out.append(sc + bold + "  ╚" + "═" * (BOARD_WIDTH) + "╝" + reset)

    # Planchette overlay — drawn on top using ANSI positioning
    planchette_overlay = render_planchette(planchette_pos, spirit_color)

    lines = "\n".join(out)
    return lines, planchette_overlay


def render_planchette(pos, color):
    """Return the planchette as a list of (row, col, char) tuples for overlay.

    The planchette is a heart-shaped piece with a glowing peephole (◉)
    and a pointed bottom (V) that indicates the selected letter.
    """
    px, py = pos
    shape = []
    # Top curve
    for dx in range(-4, 5):
        shape.append((py - 2, px + dx, "▔"))
    # Sides
    shape.append((py - 1, px - 4, "│"))
    shape.append((py - 1, px + 4, "│"))
    # Hole (the peephole)
    shape.append((py - 1, px - 1, "("))
    shape.append((py - 1, px, "◉"))
    shape.append((py - 1, px + 1, ")"))
    # Pointed bottom
    shape.append((py, px - 3, "\\"))
    shape.append((py, px + 3, "/"))
    shape.append((py + 1, px - 2, "\\"))
    shape.append((py + 1, px + 2, "/"))
    shape.append((py + 2, px - 1, "\\"))
    shape.append((py + 2, px + 1, "/"))
    shape.append((py + 3, px, "V"))
    return shape


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

def draw_frame(spirit_color, planchette_pos, trail, info_lines, question=None,
               spelled=None, prompt=None):
    """Render a single frame of the board + planchette + info area."""
    clear_screen()
    board, planchette = render_board(spirit_color, planchette_pos, trail)

    print(board)
    # Draw planchette overlay using cursor positioning
    # Board starts at col 3 (due to "  ║"), row offset
    board_top = 4  # first board row printed at line 4
    board_left = 3  # "  ║" → content starts at col 3 (1-indexed)
    sc = _c(spirit_color)
    bold = _c(BOLD)
    dim = _c(DIM)
    reset = _c(ANSI_RESET)
    for (row, col, ch) in planchette:
        if ch == "◉":
            sys.stdout.write(f"\033[{board_top + row};{board_left + col}H{sc}{bold}{ch}{reset}")
        elif ch in ("V", "│", "▔"):
            sys.stdout.write(f"\033[{board_top + row};{board_left + col}H{sc}{ch}{reset}")
        else:
            sys.stdout.write(f"\033[{board_top + row};{board_left + col}H{dim}{ch}{reset}")
    sys.stdout.write("\033[0m\n")

    # Info area below board
    print()
    if question:
        print(f"  {dim}You asked:{reset} {question}")
    if spelled:
        msg = "".join(spelled)
        print(f"  {sc}{bold}The spirits spell:{reset} {sc}{msg}{reset}")
    for line in info_lines:
        print(f"  {line}")
    if prompt:
        print()
        print(f"  {dim}{prompt}{reset}")
    sys.stdout.flush()


def animate_to(target_pos, spirit_color, trail, info_lines, question, spelled,
               speed=0.06, prompt=None):
    """Animate the planchette from its current position to *target_pos*.

    The planchette follows a smoothstep-eased path with a sinusoidal wobble
    for a supernatural feel.  Each intermediate position is recorded into
    *trail* with an age counter so that a faint dotted path fades behind it.
    """
    if trail:
        current = [trail[-1][0], trail[-1][1]]
    else:
        current = [PLANCHETTE_HOME[0], PLANCHETTE_HOME[1]]

    tx, ty = target_pos
    steps = max(6, int(math.hypot(tx - current[0], ty - current[1]) * 1.5))

    for step in range(1, steps + 1):
        frac = ease_in_out(step / steps)
        cx = current[0] + (tx - current[0]) * frac
        cy = current[1] + (ty - current[1]) * frac
        # Add a slight wobble for supernatural feel
        wobble_x = math.sin(step * 0.4) * 0.4
        wobble_y = math.cos(step * 0.3) * 0.3
        pos = (int(cx + wobble_x), int(cy + wobble_y))

        # Age existing trail entries and prune old ones
        trail = [(t[0], t[1], t[2] + 1) for t in trail if t[2] < 5]
        trail.append((pos[0], pos[1], 0))

        draw_frame(spirit_color, pos, trail, info_lines, question, spelled, prompt)
        time.sleep(speed)

    return (tx, ty), trail


def ease_in_out(t):
    """Smoothstep easing (``3t² - 2t³``) for organic planchette motion.

    Returns 0 at t=0, 1 at t=1, and is monotonically increasing in between.
    """
    t = max(0.0, min(1.0, t))  # clamp for safety
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Spirit response generation
# ---------------------------------------------------------------------------

# Words that typically begin a yes/no question
YN_WORDS = frozenset([
    "is", "are", "will", "can", "do", "does", "did", "should",
    "could", "would", "am", "have", "has", "was", "were", "shall",
    "may", "might", "must",
])


def generate_response(spirit, question):
    """Generate a sequence of tokens the planchette will spell out.

    Tokens are tuples:
      * ``("LETTER", ch)``  — move to a single character
      * ``("SPECIAL", "YES"|"NO"|"GOODBYE")`` — move to a special board word

    Yes/no questions have a 40% chance of a YES/NO answer (weighted by the
    spirit's ``favor_yes`` bias).  Otherwise 1–3 words are drawn from the
    spirit's vocabulary.  There's a 15% chance the session ends with GOODBYE.
    """
    tokens = []
    vocab = spirit["vocabulary"]
    favor_yes = spirit["favor_yes"]

    q_lower = question.lower().strip()
    if not q_lower:
        # Empty / whitespace question → spirit says something cryptic anyway
        word = random.choice(vocab)
        for ch in word:
            tokens.append(("LETTER", ch))
        return tokens

    words = q_lower.split()
    first_word = words[0].rstrip("?,.!") if words else ""
    is_yn = first_word in YN_WORDS or (q_lower.endswith("?") and len(q_lower) < 40)

    # Sometimes answer YES / NO
    if is_yn and random.random() < 0.4:
        if random.random() < favor_yes:
            tokens.append(("SPECIAL", "YES"))
        else:
            tokens.append(("SPECIAL", "NO"))
        # Maybe add a word after
        if random.random() < 0.3:
            word = random.choice(vocab)
            for ch in word:
                tokens.append(("LETTER", ch))
            tokens.append(("LETTER", " "))
        return tokens

    # Otherwise spell out words from vocabulary
    num_words = random.randint(1, 3)
    chosen = random.sample(vocab, min(num_words, len(vocab)))
    for word in chosen:
        for ch in word:
            tokens.append(("LETTER", ch))
        tokens.append(("LETTER", " "))

    # Sometimes end with GOODBYE
    if random.random() < 0.15:
        tokens.append(("SPECIAL", "GOODBYE"))

    return tokens


def get_target_position(token):
    """Map a token to a (col, row) position on the board.

    Falls back to ``PLANCHETTE_HOME`` for anything unrecognised.
    """
    if token[0] == "SPECIAL":
        if token[1] == "YES":
            return (YES_POS[0] + 1, YES_POS[1])
        elif token[1] == "NO":
            return (NO_POS[0] + 1, NO_POS[1])
        elif token[1] == "GOODBYE":
            return (GOODBYE_POS[0] + 3, GOODBYE_POS[1])
    elif token[0] == "LETTER":
        ch = token[1]
        if ch == " ":
            return PLANCHETTE_HOME
        if ch in LETTER_POS:
            return LETTER_POS[ch]
    return PLANCHETTE_HOME


def tokens_to_string(tokens):
    """Convert a token list into the human-readable spelled message."""
    parts = []
    for tok in tokens:
        if tok[0] == "LETTER":
            parts.append(tok[1])
        elif tok[0] == "SPECIAL":
            parts.append(f"[{tok[1]}]")
    return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Session logging
# ---------------------------------------------------------------------------

class SessionLog:
    """Append-only transcript of the séance for ``--log``."""

    def __init__(self, path):
        self.path = path
        self.entries = []
        if path:
            # Write a header if the file is new / empty
            already_exists = os.path.exists(path) and os.path.getsize(path) > 0
            with open(path, "a", encoding="utf-8") as f:
                if not already_exists:
                    f.write("# Terminal Séance — Session Log\n")
                    f.write(f"# Created {datetime.now().isoformat(timespec='seconds')}\n\n")

    def add(self, spirit_name, question, answer):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "spirit": spirit_name,
            "question": question,
            "answer": answer,
        }
        self.entries.append(entry)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"## {entry['timestamp']} — {spirit_name}\n")
                f.write(f"**Q:** {question}\n")
                f.write(f"**A:** {answer}\n\n")

    def summary(self):
        if not self.entries:
            return "No questions were asked."
        lines = [f"Session had {len(self.entries)} exchange(s):"]
        for e in self.entries:
            lines.append(f"  • [{e['spirit']}] {e['question']} → {e['answer']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main séance loop
# ---------------------------------------------------------------------------

def print_intro(spirit):
    clear_screen()
    sc = _c(spirit["color"])
    bold = _c(BOLD)
    dim = _c(DIM)
    reset = _c(ANSI_RESET)
    print()
    print(f"  {sc}{bold}{'━' * 50}{reset}")
    print(f"  {sc}{bold}      ✟  TERMINAL SÉANCE  ✟{reset}")
    print(f"  {sc}{bold}{'━' * 50}{reset}")
    print()
    print(f"  {dim}The candles flicker. The room grows cold...{reset}")
    print(f"  {dim}A presence makes itself known:{reset}")
    print()
    print(f"  {sc}{bold}  ☽  {spirit['name']}{reset}")
    print(f"  {dim}     {spirit['desc']}{reset}")
    print()
    print(f"  {dim}Place your fingers on the planchette.{reset}")
    print(f"  {dim}Ask your question, then press ENTER...{reset}")
    print()
    print(f"  {dim}[r] new spirit   [q] quit   [s] save log   [h] help{reset}")
    print()
    sys.stdout.flush()


def pick_spirit(name=None, exclude=None):
    """Choose a spirit.  If *name* is given, look it up; otherwise random.

    *exclude* is a spirit name to avoid (used by the 'r' re-roll command).
    Raises ``ValueError`` if a specific *name* is not found.
    """
    if name:
        key = name.strip().lower()
        if key not in SPIRIT_BY_NAME:
            raise ValueError(
                f"No spirit named '{name}'. Available: "
                + ", ".join(s["name"] for s in SPIRITS)
            )
        return SPIRIT_BY_NAME[key]
    candidates = SPIRITS
    if exclude:
        candidates = [s for s in SPIRITS if s["name"] != exclude]
    return random.choice(candidates)


def list_spirits():
    """Print a formatted table of all available spirits."""
    print(f"\n  {'Name':<22} {'Style':<14} {'YES-bias':<9} Description")
    print(f"  {'─' * 22} {'─' * 14} {'─' * 8} {'─' * 36}")
    for s in SPIRITS:
        print(f"  {s['name']:<22} {s['style']:<14} {s['favor_yes']:<9.0%} {s['desc']}")
    print()


def conduct_seance(args):
    """Main interactive séance loop."""
    session_log = SessionLog(args.log) if args.log else None

    try:
        spirit = pick_spirit(name=args.spirit)
    except ValueError as e:
        print(f"  {_c(DIM)}{e}{_c(ANSI_RESET)}")
        return

    spirit_color = spirit["color"]
    trail = []
    spelled = []

    # Show terminal-size warnings before starting
    for w in check_terminal_size():
        print(f"  {_c(DIM)}⚠ {w}{_c(ANSI_RESET)}")
    time.sleep(1.5)

    print_intro(spirit)
    input()
    clear_screen()

    info_lines = [f"{_c(DIM)}The planchette begins to tremble...{_c(ANSI_RESET)}"]
    draw_frame(spirit_color, PLANCHETTE_HOME, trail, info_lines, None, None,
               "Ask your question and press ENTER (or 'r' for new spirit, 'q' to quit)")

    while True:
        try:
            user_input = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "exit"):
            break
        if user_input.lower() == "r":
            spirit = pick_spirit(exclude=spirit["name"])
            spirit_color = spirit["color"]
            trail = []
            spelled = []
            print_intro(spirit)
            input()
            clear_screen()
            info_lines = [f"{_c(DIM)}A new presence stirs...{_c(ANSI_RESET)}"]
            draw_frame(spirit_color, PLANCHETTE_HOME, trail, info_lines, None, None,
                       "Ask your question and press ENTER")
            continue
        if user_input.lower() == "h":
            clear_screen()
            print(f"  {_c(DIM)}── Controls ──{_c(ANSI_RESET)}")
            print(f"  ENTER   ask a question / submit")
            print(f"  r       summon a different spirit")
            print(f"  s       save session transcript")
            print(f"  q       end the séance")
            print(f"  Ctrl+C  quit immediately")
            print()
            input(f"  {_c(DIM)}Press ENTER to return...{_c(ANSI_RESET)}")
            draw_frame(spirit_color, PLANCHETTE_HOME, trail, info_lines, None, None,
                       "Ask your question and press ENTER")
            continue
        if user_input.lower() == "s":
            if session_log and session_log.entries:
                print(f"  {_c(DIM)}Session log saved to {args.log}{_c(ANSI_RESET)}")
            elif session_log:
                print(f"  {_c(DIM)}Log file is open ({args.log}) but no exchanges yet.{_c(ANSI_RESET)}")
            else:
                print(f"  {_c(DIM)}No log file configured (use --log FILE to enable).{_c(ANSI_RESET)}")
            time.sleep(1.5)
            continue

        question = user_input
        spelled = []
        tokens = generate_response(spirit, question)

        info_lines = [f"{_c(spirit_color)}{_c(BOLD)}{spirit['name']} responds...{_c(ANSI_RESET)}"]

        current_pos = (PLANCHETTE_HOME[0], PLANCHETTE_HOME[1])
        if args.fast:
            speed = 0.02
        elif args.slow:
            speed = 0.15
        else:
            speed = 0.05

        for token in tokens:
            if token[0] == "LETTER" and token[1] == " ":
                # Brief pause at home
                current_pos, trail = animate_to(PLANCHETTE_HOME, spirit_color, trail,
                                                info_lines, question, spelled, speed=speed)
                spelled.append(" ")
                time.sleep(0.2)
                continue

            target = get_target_position(token)
            # Animate to a point near the target (not exactly on it)
            jitter = (random.randint(-1, 1), random.randint(0, 1))
            target = (target[0] + jitter[0], target[1] + jitter[1])
            current_pos, trail = animate_to(target, spirit_color, trail,
                                            info_lines, question, spelled, speed=speed)
            # Linger on the letter
            time.sleep(0.3)

            if token[0] == "LETTER":
                spelled.append(token[1])
            elif token[0] == "SPECIAL":
                spelled.append(f"[{token[1]}]")

        # Final flourish
        time.sleep(0.5)
        info_lines.append(
            f"{_c(spirit_color)}{_c(BOLD)}The planchette drifts to GOODBYE...{_c(ANSI_RESET)}"
        )
        current_pos, trail = animate_to((GOODBYE_POS[0] + 3, GOODBYE_POS[1]),
                                        spirit_color, trail, info_lines, question,
                                        spelled, speed=speed)
        time.sleep(1.0)

        spelled_str = "".join(spelled).strip()
        # Record in session log
        if session_log:
            session_log.add(spirit["name"], question, spelled_str)

        info_lines = [
            f"{_c(DIM)}The planchette grows still.{_c(ANSI_RESET)}",
            "",
            f"  {_c(spirit_color)}{_c(BOLD)}Message:{_c(ANSI_RESET)} {_c(spirit_color)}{spelled_str}{_c(ANSI_RESET)}",
            f"  {_c(DIM)}— {spirit['name']}{_c(ANSI_RESET)}",
            "",
            f"{_c(DIM)}Ask another question, [r] for new spirit, [q] to quit{_c(ANSI_RESET)}",
        ]
        draw_frame(spirit_color, current_pos, trail, info_lines, question, spelled)

    # Print session summary if logging
    if session_log and session_log.entries:
        print()
        print(f"  {_c(DIM)}── Session Summary ──{_c(ANSI_RESET)}")
        for line in session_log.summary().splitlines():
            print(f"  {line}")


# ---------------------------------------------------------------------------
# Non-interactive demo mode (--demo)
# ---------------------------------------------------------------------------

DEMO_QUESTIONS = [
    "Is anyone there?",
    "What is your name?",
    "Why do you linger?",
    "Will you find peace?",
    "What lies beyond?",
]


def run_demo(args):
    """Run a non-interactive auto-séance that cycles through all spirits.

    Useful for screenshots, CI, or environments without a TTY.  Each spirit
    answers one demo question; the board is rendered as static frames.
    """
    dim = _c(DIM)
    reset = _c(ANSI_RESET)
    print(f"\n  {dim}── Terminal Séance Demo Mode ──{reset}\n")
    for i, spirit in enumerate(SPIRITS):
        question = DEMO_QUESTIONS[i % len(DEMO_QUESTIONS)]
        tokens = generate_response(spirit, question)
        answer = tokens_to_string(tokens)

        sc = _c(spirit["color"])
        bold = _c(BOLD)
        print(f"  {sc}{bold}☽  {spirit['name']}{reset}")
        print(f"  {dim}     {spirit['desc']}{reset}")
        print(f"  {dim}Q:{reset} {question}")
        print(f"  {dim}A:{reset} {sc}{answer}{reset}")
        print()

        # Render a static board frame
        board, planchette = render_board(spirit["color"], PLANCHETTE_HOME)
        print(board)
        print()
        if not args.fast:
            time.sleep(1.0)

    print(f"  {dim}── End of demo ──{reset}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="Terminal Séance — an interactive Ouija board simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Summon the spirits. Ask your questions. Trust the planchette. ✟",
    )
    parser.add_argument("--version", action="version",
                        version=f"Terminal Séance v{__version__}")
    parser.add_argument("--slow", action="store_true",
                        help="Slow planchette movement for dramatic effect")
    parser.add_argument("--fast", action="store_true",
                        help="Fast planchette movement (impatient mode)")
    parser.add_argument("--spirit", metavar="NAME", default=None,
                        help="Summon a specific spirit by name (case-insensitive)")
    parser.add_argument("--list-spirits", action="store_true",
                        help="List all available spirits and exit")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors (accessibility / pipe-friendly)")
    parser.add_argument("--log", metavar="FILE", default=None,
                        help="Append session Q&A transcript to FILE (Markdown)")
    parser.add_argument("--demo", action="store_true",
                        help="Non-interactive auto-séance (cycles through spirits)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible séances")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Apply global flags
    if args.no_color:
        set_no_color(True)
    if args.seed is not None:
        random.seed(args.seed)

    # --list-spirits: print and exit
    if args.list_spirits:
        list_spirits()
        return

    # --demo: non-interactive
    if args.demo:
        run_demo(args)
        return

    # Validate mutually exclusive speed flags
    if args.slow and args.fast:
        parser.error("--slow and --fast are mutually exclusive")

    try:
        hide_cursor()
        conduct_seance(args)
    finally:
        show_cursor()
        clear_screen()
        dim = _c(DIM)
        reset = _c(ANSI_RESET)
        print(f"{dim}The candles are extinguished. The séance has ended.{reset}")
        print(f"{dim}The spirits rest. Until next time... ✟{reset}")


if __name__ == "__main__":
    main()