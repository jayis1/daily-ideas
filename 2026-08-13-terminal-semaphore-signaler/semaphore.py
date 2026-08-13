#!/usr/bin/env python3
"""
Terminal Semaphore Flag Signaler
================================
Translates text into maritime semaphore flag positions, visualized as
animated ASCII stick figures. Each letter is represented by the position
of two flags held by a signaler, drawn in the terminal.

Semaphore is a system of conveying information at a distance by means of
visual signals with hand-held flags. The modern flag semaphore system
uses two flags, each held in one of 8 positions (like a compass rose),
giving 64 possible combinations — though many are reserved for numbers
and special commands.

This tool:
  - Encodes text letter-by-letter into semaphore flag positions
  - Renders an animated ASCII stick figure holding the flags
  - Supports interactive mode, file mode, and demo mode
  - Shows the flag angle diagram and letter meaning for each frame
"""

import argparse
import sys
import time
import math
import string
import os

# ---------------------------------------------------------------------------
# Semaphore encoding
# ---------------------------------------------------------------------------
# The eight flag positions are numbered 1–8, clockwise from the signaler's
# perspective, starting at the "down" position:
#
#        7   8
#         \ /
#      6-- O --2
#         / \
#        5   4
#         (3 = straight down, not drawn well diagonally but it's "down")
#
# Actually the standard convention:
#   Position 1 = straight down
#   Position 2 = down-left (45°)
#   Position 3 = horizontal left (90°)
#   ... etc.
# But different sources use different numbering. We use the widely-adopted
# "clock" convention where positions are numbered 1-8 like clock hours but
# starting from bottom:
#
#       6    7    8
#        \   |   /
#     5 -- O -- 1
#        /   |   \
#       4    3    2
#
# Each letter = two distinct positions (one per arm). Position 1 is
# "rest/down" on the right side in our convention.

# Flag positions as angles in degrees (0 = right/east, 90 = up, etc.)
# We'll define 8 compass directions the arm can point.
# Key: position number -> angle in degrees from horizontal-right, CCW
# Using standard semaphore numbering (1=down-right, going CCW):

POSITIONS = {
    1: -90,    # straight down
    2: -45,    # down-right
    3:   0,    # right (horizontal)
    4:  45,    # up-right
    5:  90,    # straight up
    6: 135,    # up-left
    7: 180,    # left (horizontal)
    8: 225,    # down-left  (== -135)
}

# Semaphore letter encoding: letter -> (left_arm_pos, right_arm_pos)
# Using the standard ITU flag semaphore chart.
# Positions 1-8 as per the diagram above.
SEMAPHORE = {
    'A': (1, 8),
    'B': (1, 7),
    'C': (1, 6),
    'D': (1, 5),
    'E': (1, 4),
    'F': (1, 3),
    'G': (1, 2),
    'H': (2, 8),
    'I': (2, 7),
    'J': (2, 6),
    'K': (2, 5),
    'L': (2, 4),
    'M': (2, 3),
    'N': (3, 8),
    'O': (3, 7),
    'P': (3, 6),
    'Q': (3, 5),
    'R': (3, 4),
    'S': (4, 8),
    'T': (4, 7),
    'U': (4, 6),
    'V': (4, 5),
    'W': (5, 8),
    'X': (5, 7),
    'Y': (5, 6),
    'Z': (6, 8),
}

# Numeric flag: the "J" position is used to switch to numbers.
# In number mode, letters map differently. For simplicity, we handle
# digits by using a "numerals" preamble (J) then the letter-based codes.
NUMERAL_MAP = {
    '0': 'J',  # J in number mode = 0
    '1': 'A',
    '2': 'B',
    '3': 'C',
    '4': 'D',
    '5': 'E',
    '6': 'F',
    '7': 'G',
    '8': 'H',
    '9': 'I',
}

# Special signals
REST = (1, 1)  # both arms down = rest / attention


def encode_text(text):
    """
    Encode text into a sequence of semaphore frames.
    Returns a list of (char, left_pos, right_pos, label) tuples.
    Handles letters, digits, and spaces (space = rest position).
    """
    frames = []
    in_number_mode = False

    for ch in text.upper():
        if ch == ' ':
            frames.append((' ', 1, 1, 'SPACE (rest)'))
            in_number_mode = False  # spaces break number runs
            continue

        if ch in string.ascii_uppercase:
            if in_number_mode:
                # Letters return to letter mode (use "C" = resume letters)
                # For simplicity we just switch back.
                in_number_mode = False
            left, right = SEMAPHORE[ch]
            frames.append((ch, left, right, f"Letter '{ch}'"))
            continue

        if ch in string.digits:
            if not in_number_mode:
                # Prepend the "numerals" signal (J position)
                j_l, j_r = SEMAPHORE['J']
                frames.append(('#', j_l, j_r, 'NUMERALS (J)'))
                in_number_mode = True
            letter = NUMERAL_MAP[ch]
            left, right = SEMAPHORE[letter]
            frames.append((ch, left, right, f"Digit '{ch}'"))
            continue

        # Unknown character — show as rest with a note
        frames.append((ch, 1, 1, f"Unknown '{ch}' (rest)"))

    return frames


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

CANVAS_W = 40
CANVAS_H = 22


def make_canvas():
    """Create an empty canvas (list of lists of characters)."""
    return [[' '] * CANVAS_W for _ in range(CANVAS_H)]


def set_pixel(canvas, x, y, ch):
    """Safely set a pixel on the canvas."""
    if 0 <= y < CANVAS_H and 0 <= x < CANVAS_W:
        canvas[y][x] = ch


def draw_line(canvas, x0, y0, x1, y1, ch='*'):
    """Draw a line using Bresenham's algorithm."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        set_pixel(canvas, x0, y0, ch)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def draw_flag(canvas, x_tip, y_tip, flag_char='F'):
    """Draw a small flag (triangle-ish blob) at the tip of an arm."""
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            set_pixel(canvas, x_tip + dx, y_tip + dy, flag_char)


def angle_to_delta(angle_deg, length=6):
    """
    Convert an angle (degrees, 0 = right, 90 = up in screen coords
    where y increases downward so we negate) to (dx, dy).
    In our canvas, y increases downward, so 'up' means negative dy.
    """
    rad = math.radians(angle_deg)
    dx = round(length * math.cos(rad))
    dy = round(-length * math.sin(rad))  # negate because screen y is down
    return dx, dy


def render_figure(left_pos, right_pos):
    """
    Render the stick figure with flags at the given semaphore positions.
    Returns the canvas as a list of strings.
    """
    canvas = make_canvas()

    # Body center (shoulders)
    cx, cy = CANVAS_W // 2, 10

    # Head
    head_r = 2
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        hx = cx + round(head_r * math.cos(rad))
        hy = cy - 3 + round(-head_r * math.sin(rad))
        set_pixel(canvas, hx, hy, '@')
    # Fill head center
    set_pixel(canvas, cx, cy - 3, '@')

    # Torso
    draw_line(canvas, cx, cy, cx, cy + 5, '|')

    # Legs
    draw_line(canvas, cx, cy + 5, cx - 3, cy + 9, '\\')
    draw_line(canvas, cx, cy + 5, cx + 3, cy + 9, '/')

    # Left arm (from signaler's perspective = our left = screen-left)
    l_angle = POSITIONS.get(left_pos, -90)
    l_dx, l_dy = angle_to_delta(l_angle, length=6)
    # Left arm starts from the left shoulder
    lsx, lsy = cx - 1, cy
    ltx, lty = lsx + l_dx, lsy + l_dy
    draw_line(canvas, lsx, lsy, ltx, lty, '-')
    draw_flag(canvas, ltx, lty, '#')

    # Right arm (from signaler's perspective = our right = screen-right)
    r_angle = POSITIONS.get(right_pos, -90)
    r_dx, r_dy = angle_to_delta(r_angle, length=6)
    # Right arm starts from the right shoulder
    rsx, rsy = cx + 1, cy
    rtx, rty = rsx + r_dx, rsy + r_dy
    draw_line(canvas, rsx, rsy, rtx, rty, '-')
    draw_flag(canvas, rtx, rty, '#')

    # Convert to strings
    return [''.join(row) for row in canvas]


def render_diagram(left_pos, right_pos):
    """
    Render a small compass-diagram showing which positions are active.
    """
    grid = [
        "      6    7    8      ",
        "       \\  |  /        ",
        "    5-- O --1          ",
        "       /  |  \\        ",
        "      4    3    2      ",
    ]
    # Highlight active positions
    lines = grid[:]
    # We'll mark active positions with brackets
    pos_coords = {
        1: (12, 2),
        2: (19, 4),
        3: (12, 4),
        4: (6, 4),
        5: (4, 2),
        6: (6, 0),
        7: (12, 0),
        8: (18, 0),
    }
    # Build a highlight overlay
    result = []
    for y, line in enumerate(grid):
        chars = list(line)
        for pos, (px, py) in pos_coords.items():
            if py == y and (pos == left_pos or pos == right_pos):
                if px < len(chars):
                    # Surround with brackets
                    pass  # keep simple — just mark with [ ]
        result.append(''.join(chars))

    # Simpler: just annotate
    active = sorted(set([left_pos, right_pos]))
    label_line = f"  Active positions: {', '.join(str(p) for p in active)}"
    return result + [label_line]


# ---------------------------------------------------------------------------
# Display / animation
# ---------------------------------------------------------------------------

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def display_frame(frame, show_diagram=True):
    """Display a single semaphore frame."""
    char, left, right, label = frame
    figure = render_figure(left, right)

    # Top border
    width = max(len(line) for line in figure)
    border = '+' + '-' * (width + 2) + '+'

    lines = [border]
    lines.append(f"|  Semaphore Signaler  {' ' * (width - 19)}|")
    lines.append(border)

    for line in figure:
        lines.append(f"| {line.ljust(width)} |")

    lines.append(border)

    # Info line
    info = f"  Character: {repr(char)}  |  {label}"
    lines.append(info)

    if show_diagram:
        lines.append("")
        diag = render_diagram(left, right)
        lines.extend(diag)

    lines.append("")
    lines.append("  Legend: @ = head, | = torso, - = arms, # = flag")
    lines.append("  Positions 1-8 = semaphore compass (see diagram)")

    print('\n'.join(lines))


def animate(text, delay=1.2, show_diagram=True, loop=False):
    """Animate the semaphore encoding of text."""
    frames = encode_text(text)

    if not frames:
        print("Nothing to signal.")
        return

    try:
        while True:
            for i, frame in enumerate(frames):
                clear_screen()
                display_frame(frame, show_diagram=show_diagram)
                print(f"\n  Frame {i + 1}/{len(frames)}  |  Text: \"{text}\"")
                print("  Press Ctrl+C to stop.")
                time.sleep(delay)
            if not loop:
                break
            # Pause before looping
            time.sleep(delay * 2)
    except KeyboardInterrupt:
        print("\n\n  Signaling stopped.")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_mode(show_diagram=True, delay=1.2):
    """Run an interactive REPL for encoding text."""
    print("=" * 50)
    print("  Terminal Semaphore Flag Signaler")
    print("  Interactive Mode")
    print("=" * 50)
    print()
    print("  Type text to signal, then press Enter.")
    print("  Special commands:")
    print("    :demo    - run a demo sequence")
    print("    :chart   - show the full semaphore chart")
    print("    :file X  - signal contents of file X")
    print("    :quit    - exit")
    print()

    while True:
        try:
            text = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not text:
            continue

        if text == ":quit":
            print("  Goodbye!")
            break
        elif text == ":demo":
            animate("SOS HELLO 42", delay=delay, show_diagram=show_diagram)
        elif text == ":chart":
            show_full_chart()
        elif text.startswith(":file "):
            filepath = text[6:].strip()
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                animate(content, delay=delay, show_diagram=show_diagram)
            except FileNotFoundError:
                print(f"  File not found: {filepath}")
        else:
            animate(text, delay=delay, show_diagram=show_diagram)

        print()


def show_full_chart():
    """Display the complete semaphore alphabet chart."""
    clear_screen()
    print("=" * 60)
    print("  Complete Semaphore Alphabet Chart")
    print("=" * 60)
    print()
    print("  Letter | Left Pos | Right Pos")
    print("  -------|----------|----------")

    for letter in string.ascii_uppercase:
        left, right = SEMAPHORE[letter]
        print(f"   {letter}     |    {left}     |    {right}")

    print()
    print("  Position guide:")
    print("       6    7    8")
    print("        \\  |  /")
    print("     5-- O --1")
    print("        /  |  \\")
    print("       4    3    2")
    print()
    print("  Numbers: signal 'J' first, then A-I for 1-9, J for 0")
    print()
    input("  Press Enter to continue...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Terminal Semaphore Flag Signaler — translate text into animated semaphore flag positions."
    )
    parser.add_argument(
        'text',
        nargs='*',
        help='Text to signal. If omitted, enters interactive mode.'
    )
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=1.2,
        help='Delay between frames in seconds (default: 1.2)'
    )
    parser.add_argument(
        '--no-diagram',
        action='store_true',
        help='Hide the compass diagram during animation'
    )
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Loop the animation continuously'
    )
    parser.add_argument(
        '--chart',
        action='store_true',
        help='Print the full semaphore chart and exit'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Signal the contents of a file'
    )
    parser.add_argument(
        '--encode',
        action='store_true',
        help='Print the encoded positions without animation (text mode)'
    )

    args = parser.parse_args()
    show_diagram = not args.no_diagram

    if args.chart:
        print("=" * 40)
        print("  Semaphore Alphabet Chart")
        print("=" * 40)
        print()
        for letter in string.ascii_uppercase:
            left, right = SEMAPHORE[letter]
            print(f"  {letter}: left={left}, right={right}")
        print()
        print("  Positions (compass from signaler's view):")
        print("       6    7    8")
        print("        \\  |  /")
        print("     5-- O --1")
        print("        /  |  \\")
        print("       4    3    2")
        return

    if args.file:
        try:
            with open(args.file, 'r') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
    elif args.text:
        text = ' '.join(args.text)
    else:
        # Interactive mode
        interactive_mode(show_diagram=show_diagram, delay=args.delay)
        return

    if args.encode:
        # Text-only mode: print positions
        frames = encode_text(text)
        print(f"Text: {text}")
        print(f"Frames: {len(frames)}")
        print("-" * 40)
        for char, left, right, label in frames:
            print(f"  {repr(char):>6}  ->  L={left}  R={right}   ({label})")
        return

    animate(text, delay=args.delay, show_diagram=show_diagram, loop=args.loop)


if __name__ == '__main__':
    main()