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
"""

import argparse
import math
import os
import random
import sys
import time

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

# Positions (col, row) for each letter on the board
def compute_positions():
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
        "vocabulary": ["SOON", "Beware".upper(), "FIRE", "CHANGE", "COMETH",
                       "THE END", "DAWN", "AFTER", "SHALL", "WILL BE",
                       "INEVITABLE", "MARK MY WORDS", "PROPHECY", "BE READY"],
        "farewell": "IT IS WRITTEN",
        "favor_yes": 0.5,
    },
]


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def move_to(row, col):
    sys.stdout.write(f"\033[{row};{col}H")

ANSI_RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

# ---------------------------------------------------------------------------
# Board rendering
# ---------------------------------------------------------------------------

def render_board(spirit_color, planchette_pos, trail=None):
    """Render the Ouija board into a grid, then print it."""
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
                    grid[ty][tx] = DIM + char + ANSI_RESET

    # Build output buffer
    out = []
    out.append(spirit_color + BOLD + "  ╔" + "═" * (BOARD_WIDTH) + "╗" + ANSI_RESET)
    # Title bar
    title = "  THE SPIRIT BOARD  "
    title_line = "║" + title.center(BOARD_WIDTH) + "║"
    out.append(spirit_color + BOLD + title_line + ANSI_RESET)
    out.append(spirit_color + BOLD + "  ╠" + "═" * (BOARD_WIDTH) + "╣" + ANSI_RESET)

    for y in range(BOARD_HEIGHT):
        row_chars = []
        for x in range(BOARD_WIDTH):
            row_chars.append(grid[y][x])
        out.append("  " + spirit_color + "║" + ANSI_RESET + "".join(row_chars) + spirit_color + "║" + ANSI_RESET)

    out.append(spirit_color + BOLD + "  ╚" + "═" * (BOARD_WIDTH) + "╝" + ANSI_RESET)

    # Planchette overlay — drawn on top using ANSI positioning
    # We'll draw the planchette at its (col, row) position
    planchette_overlay = render_planchette(planchette_pos, spirit_color)

    lines = "\n".join(out)
    return lines, planchette_overlay


def render_planchette(pos, color):
    """Return the planchette as a set of (row, col, char) for overlay."""
    px, py = pos
    # Heart-shaped planchette pointing down
    #    .---.
    #   /     \
    #  |   ◉   |
    #   \  V  /
    #    \ V /
    #     V
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
    clear_screen()
    board, planchette = render_board(spirit_color, planchette_pos, trail)

    print(board)
    # Draw planchette overlay using cursor positioning
    # Board starts at col 3 (due to "  ║"), row offset
    board_top = 4  # first board row printed at line 4
    board_left = 3  # "  ║" → content starts at col 3 (1-indexed)
    for (row, col, ch) in planchette:
        if ch == "◉":
            sys.stdout.write(f"\033[{board_top + row};{board_left + col}H{spirit_color}{BOLD}{ch}{ANSI_RESET}")
        elif ch in ("V", "│", "▔"):
            sys.stdout.write(f"\033[{board_top + row};{board_left + col}H{spirit_color}{ch}{ANSI_RESET}")
        else:
            sys.stdout.write(f"\033[{board_top + row};{board_left + col}H{DIM}{ch}{ANSI_RESET}")
    sys.stdout.write("\033[0m\n")

    # Info area below board
    print()
    if question:
        print(f"  {DIM}You asked:{ANSI_RESET} {question}")
    if spelled:
        # Display the spelled-out message with a ghostly effect
        msg = "".join(spelled)
        print(f"  {spirit_color}{BOLD}The spirits spell:{ANSI_RESET} {spirit_color}{msg}{ANSI_RESET}")
    for line in info_lines:
        print(f"  {line}")
    if prompt:
        print()
        print(f"  {DIM}{prompt}{ANSI_RESET}")
    sys.stdout.flush()


def animate_to(target_pos, spirit_color, trail, info_lines, question, spelled,
               speed=0.06, prompt=None):
    """Animate the planchette from current position to target_pos."""
    current = list(PLANCHETTE_HOME) if not trail else trail[-1][:2]
    # If we have a trail, start from the last position
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

        # Age existing trail entries
        trail = [(t[0], t[1], t[2] + 1) for t in trail if t[2] < 5]
        trail.append((pos[0], pos[1], 0))

        draw_frame(spirit_color, pos, trail, info_lines, question, spelled, prompt)
        time.sleep(speed)

    return (tx, ty), trail


def ease_in_out(t):
    """Smoothstep easing for organic planchette motion."""
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Spirit response generation
# ---------------------------------------------------------------------------

def generate_response(spirit, question):
    """Generate a sequence of 'tokens' the planchette will spell out.

    Tokens are either letters (single char) or special markers like
    ('YES',), ('NO',), ('GOODBYE',), or ('PAUSE', n) for dramatic pauses.
    """
    tokens = []
    style = spirit["style"]
    vocab = spirit["vocabulary"]
    favor_yes = spirit["favor_yes"]

    q_lower = question.lower().strip()

    # Yes/No questions
    yn_words = ["is", "are", "will", "can", "do", "does", "did", "should",
                "could", "would", "am", "have", "has", "was", "were"]
    first_word = q_lower.split()[0].rstrip("?") if q_lower.split() else ""
    is_yn = first_word in yn_words or q_lower.endswith("?") and len(q_lower) < 40

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
    """Map a token to a board position."""
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


# ---------------------------------------------------------------------------
# Main séance loop
# ---------------------------------------------------------------------------

def print_intro(spirit):
    clear_screen()
    print()
    print(f"  {spirit['color']}{BOLD}{'━' * 50}{ANSI_RESET}")
    print(f"  {spirit['color']}{BOLD}      ✟  TERMINAL SÉANCE  ✟{ANSI_RESET}")
    print(f"  {spirit['color']}{BOLD}{'━' * 50}{ANSI_RESET}")
    print()
    print(f"  {DIM}The candles flicker. The room grows cold...{ANSI_RESET}")
    print(f"  {DIM}A presence makes itself known:{ANSI_RESET}")
    print()
    print(f"  {spirit['color']}{BOLD}  ☽  {spirit['name']}{ANSI_RESET}")
    print(f"  {DIM}     {spirit['desc']}{ANSI_RESET}")
    print()
    print(f"  {DIM}Place your fingers on the planchette.{ANSI_RESET}")
    print(f"  {DIM}Ask your question, then press ENTER...{ANSI_RESET}")
    print()
    print(f"  {DIM}[r] summon a different spirit  [q] end the séance{ANSI_RESET}")
    print()
    sys.stdout.flush()


def conduct_seance(args):
    spirit = random.choice(SPIRITS)
    spirit_color = spirit["color"]

    trail = []
    spelled = []

    print_intro(spirit)
    input()
    clear_screen()

    info_lines = [f"{DIM}The planchette begins to tremble...{ANSI_RESET}"]
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
            spirit = random.choice([s for s in SPIRITS if s["name"] != spirit["name"]])
            spirit_color = spirit["color"]
            trail = []
            spelled = []
            print_intro(spirit)
            input()
            clear_screen()
            info_lines = [f"{DIM}A new presence stirs...{ANSI_RESET}"]
            draw_frame(spirit_color, PLANCHETTE_HOME, trail, info_lines, None, None,
                       "Ask your question and press ENTER")
            continue

        question = user_input
        spelled = []
        tokens = generate_response(spirit, question)

        info_lines = [f"{spirit_color}{BOLD}{spirit['name']} responds...{ANSI_RESET}"]

        current_pos = (PLANCHETTE_HOME[0], PLANCHETTE_HOME[1])
        speed = 0.05 if not args.slow else 0.15

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
        farewell = spirit["farewell"]
        info_lines.append(f"{spirit_color}{BOLD}The planchette drifts to GOODBYE...{ANSI_RESET}")
        # Move to goodbye
        current_pos, trail = animate_to((GOODBYE_POS[0] + 3, GOODBYE_POS[1]),
                                        spirit_color, trail, info_lines, question,
                                        spelled, speed=speed)
        time.sleep(1.0)

        spelled_str = "".join(spelled).strip()
        info_lines = [
            f"{DIM}The planchette grows still.{ANSI_RESET}",
            "",
            f"  {spirit_color}{BOLD}Message:{ANSI_RESET} {spirit_color}{spelled_str}{ANSI_RESET}",
            f"  {DIM}— {spirit['name']}{ANSI_RESET}",
            "",
            f"{DIM}Ask another question, [r] for new spirit, [q] to quit{ANSI_RESET}",
        ]
        draw_frame(spirit_color, current_pos, trail, info_lines, question, spelled)


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Séance — an interactive Ouija board simulator"
    )
    parser.add_argument("--slow", action="store_true",
                        help="Slow planchette movement for dramatic effect")
    args = parser.parse_args()

    try:
        hide_cursor()
        conduct_seance(args)
    finally:
        show_cursor()
        clear_screen()
        print(f"{DIM}The candles are extinguished. The séance has ended.{ANSI_RESET}")
        print(f"{DIM}The spirits rest. Until next time... ✟{ANSI_RESET}")


if __name__ == "__main__":
    main()