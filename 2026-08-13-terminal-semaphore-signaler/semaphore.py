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
  - Decodes semaphore position pairs back into text
  - Renders an animated ASCII stick figure holding the flags
  - Supports interactive mode, file mode, demo mode, and export mode
  - Shows the flag angle diagram and letter meaning for each frame
  - Supports optional ANSI color output for richer visualization
  - Includes special signals: Attention, Error/Cancel, Correct, Rest
  - Can output machine-readable JSON for integration with other tools

Version: 2.1.0
"""

import argparse
import sys
import time
import math
import string
import os
import json as json_module

__version__ = "2.1.0"

# ---------------------------------------------------------------------------
# Semaphore encoding
# ---------------------------------------------------------------------------
# The eight flag positions are numbered 1–8, clockwise from the signaler's
# perspective, starting at the "down" position:
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
# Key: position number -> angle in degrees from horizontal-right, CCW
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

# Human-readable names for each position
POSITION_NAMES = {
    1: "down",
    2: "down-right",
    3: "right",
    4: "up-right",
    5: "up",
    6: "up-left",
    7: "left",
    8: "down-left",
}

# Semaphore letter encoding: letter -> (left_arm_pos, right_arm_pos)
# Using the standard ITU flag semaphore chart.
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

# Build a reverse lookup: (left, right) -> letter.
# Note: semaphore pairs are unordered (left/right is symmetric), so we
# store both orderings.
SEMAPHORE_REVERSE = {}
for _letter, (_lp, _rp) in SEMAPHORE.items():
    SEMAPHORE_REVERSE[(_lp, _rp)] = _letter
    SEMAPHORE_REVERSE[(_rp, _lp)] = _letter

# Numeric flag: the "J" position is used to switch to numbers.
# In number mode, letters map differently. We handle digits by using a
# "numerals" preamble (J) then the letter-based codes.
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

# Reverse numeral map: letter -> digit
NUMERAL_REVERSE = {v: k for k, v in NUMERAL_MAP.items()}

# Special signals (standard semaphore commands)
SPECIAL_SIGNALS = {
    'REST':       (1, 1),    # both arms down = rest / attention
    'ATTENTION':  (5, 5),    # both flags up = attention / start of message
    'ERROR':      (4, 8),    # flags crossed = error / cancel last character
    'CORRECT':    (2, 4),    # acknowledge / correct / ready to receive
    'NUMERALS':   (2, 6),    # same as J — switch to number mode
    'LETTERS':    (3, 6),    # same as P — return to letter mode
}

REST = SPECIAL_SIGNALS['REST']


def encode_text(text):
    """
    Encode text into a sequence of semaphore frames.
    Returns a list of (char, left_pos, right_pos, label) tuples.
    Handles letters, digits, and spaces (space = rest position).
    Unknown characters produce a rest frame with a descriptive label.
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
                # Letters return to letter mode (use "P" = resume letters)
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


def decode_positions(positions):
    """
    Decode a sequence of semaphore position pairs back into text.

    Args:
        positions: A list of (left, right) tuples representing semaphore
                   flag positions. Each pair is treated as one frame.

    Returns:
        The decoded text string. Number mode is handled via the J/numerals
        signal. Unknown pairs produce '?'.

    The J position (2,6) is ambiguous: it can be the letter J or the
    "numerals" preamble. We use lookahead — if the *next* frame decodes
    as a digit-mapped letter (A–I), then J is treated as the numerals
    preamble; otherwise it is the letter J.

    Example:
        >>> decode_positions([(8, 1), (7, 1)])
        'AB'
    """
    result = []
    in_number_mode = False
    j_key = SEMAPHORE['J']  # (2, 6)
    j_keys = {j_key, (j_key[1], j_key[0])}  # both orderings
    digit_letters = set(NUMERAL_MAP.values())  # letters A-I that map to digits

    i = 0
    while i < len(positions):
        pair = positions[i]
        left, right = pair
        key = (left, right)

        # Check for rest / space
        if key == REST or (left == 1 and right == 1):
            result.append(' ')
            in_number_mode = False
            i += 1
            continue

        # Check for numerals signal (J position = (2, 6) or (6, 2))
        if key in j_keys:
            # Lookahead: is the next frame a digit-mapped letter?
            if i + 1 < len(positions):
                next_key = positions[i + 1]
                next_letter = SEMAPHORE_REVERSE.get(next_key)
                if next_letter is not None and next_letter in digit_letters:
                    # This J is the numerals preamble
                    in_number_mode = True
                    i += 1
                    continue
            # No valid digit follows — treat as letter J
            if in_number_mode:
                digit = NUMERAL_REVERSE.get('J')
                if digit is not None:
                    result.append(digit)
                else:
                    in_number_mode = False
                    result.append('J')
            else:
                result.append('J')
            i += 1
            continue

        # Look up the letter
        letter = SEMAPHORE_REVERSE.get(key)
        if letter is None:
            result.append('?')
            i += 1
            continue

        if in_number_mode:
            # Map letter to digit if possible
            digit = NUMERAL_REVERSE.get(letter)
            if digit is not None:
                result.append(digit)
            else:
                # Not a valid numeral letter — exit number mode
                in_number_mode = False
                result.append(letter)
        else:
            result.append(letter)
        i += 1

    return ''.join(result)


def decode_position_string(pos_str):
    """
    Parse a string of position pairs and decode them.

    Accepts formats like:
      "1,8 1,7 3,7"     (space-separated pairs, comma within pair)
      "1,8;1,7;3,7"     (semicolon-separated pairs)
      "1,8:1,7:3,7"     (colon-separated pairs)
      "8-1 7-1 7-3"     (dash within pair, space between)
      "1/8 2/7"         (slash within pair, space between)

    Between-pair separators: whitespace, semicolons, colons.
    Within-pair separators: commas, dashes, slashes.

    Returns the decoded text.
    """
    import re

    # Normalize between-pair separators: replace ; and : with spaces
    pos_str = pos_str.replace(';', ' ').replace(':', ' ')
    # Split into tokens by whitespace
    tokens = pos_str.split()

    positions = []
    for token in tokens:
        # Try to split on the first within-pair separator (comma, dash, slash)
        match = re.split(r'[,\-/]', token, maxsplit=1)
        if len(match) == 2:
            try:
                left = int(match[0].strip())
                right = int(match[1].strip())
                positions.append((left, right))
            except ValueError:
                pass  # skip malformed tokens
        else:
            # No separator found — try parsing as two single-digit numbers
            # concatenated (e.g. "18" -> (1, 8))
            if len(token) == 2 and token.isdigit():
                positions.append((int(token[0]), int(token[1])))
            # Otherwise skip the malformed token

    return decode_positions(positions)


# ---------------------------------------------------------------------------
# ANSI Color support
# ---------------------------------------------------------------------------

# ANSI color codes
COLORS = {
    'reset':  '\033[0m',
    'red':    '\033[31m',
    'green':  '\033[32m',
    'yellow': '\033[33m',
    'blue':   '\033[34m',
    'magenta':'\033[35m',
    'cyan':   '\033[36m',
    'white':  '\033[37m',
    'bold':   '\033[1m',
}


def colorize(text, color, enabled=True):
    """Wrap text in ANSI color codes if color is enabled."""
    if not enabled or color not in COLORS:
        return text
    return f"{COLORS[color]}{text}{COLORS['reset']}"


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

CANVAS_W = 40
CANVAS_H = 22


def make_canvas():
    """Create an empty canvas (list of lists of characters)."""
    return [[' '] * CANVAS_W for _ in range(CANVAS_H)]


def set_pixel(canvas, x, y, ch):
    """Safely set a pixel on the canvas. Ignores out-of-bounds writes."""
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

    # Head — draw a small circle
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


def render_figure_colored(left_pos, right_pos):
    """
    Render the stick figure with ANSI color codes applied.
    Returns the canvas as a list of strings with color escape sequences.
    The head is cyan, the torso/legs are white, the left arm/flag are
    yellow, and the right arm/flag are green.
    """
    canvas = make_canvas()

    cx, cy = CANVAS_W // 2, 10

    # Head (cyan)
    head_r = 2
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        hx = cx + round(head_r * math.cos(rad))
        hy = cy - 3 + round(-head_r * math.sin(rad))
        set_pixel(canvas, hx, hy, '@')
    set_pixel(canvas, cx, cy - 3, '@')

    # Torso (white)
    draw_line(canvas, cx, cy, cx, cy + 5, '|')

    # Legs (white)
    draw_line(canvas, cx, cy + 5, cx - 3, cy + 9, '\\')
    draw_line(canvas, cx, cy + 5, cx + 3, cy + 9, '/')

    # Left arm (yellow)
    l_angle = POSITIONS.get(left_pos, -90)
    l_dx, l_dy = angle_to_delta(l_angle, length=6)
    lsx, lsy = cx - 1, cy
    ltx, lty = lsx + l_dx, lsy + l_dy
    draw_line(canvas, lsx, lsy, ltx, lty, '-')
    draw_flag(canvas, ltx, lty, '#')

    # Right arm (green)
    r_angle = POSITIONS.get(right_pos, -90)
    r_dx, r_dy = angle_to_delta(r_angle, length=6)
    rsx, rsy = cx + 1, cy
    rtx, rty = rsx + r_dx, rsy + r_dy
    draw_line(canvas, rsx, rsy, rtx, rty, '-')
    draw_flag(canvas, rtx, rty, '#')

    # Now convert to strings with color applied
    # Track which pixels are which color
    color_map = {}  # (x, y) -> color name
    # Head
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        hx = cx + round(head_r * math.cos(rad))
        hy = cy - 3 + round(-head_r * math.sin(rad))
        if 0 <= hy < CANVAS_H and 0 <= hx < CANVAS_W:
            color_map[(hx, hy)] = 'cyan'
    if 0 <= (cy - 3) < CANVAS_H and 0 <= cx < CANVAS_W:
        color_map[(cx, cy - 3)] = 'cyan'

    # Mark left arm pixels
    l_pixels = _line_pixels(lsx, lsy, ltx, lty)
    for px, py in l_pixels:
        color_map[(px, py)] = 'yellow'
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            color_map[(ltx + dx, lty + dy)] = 'yellow'

    # Mark right arm pixels
    r_pixels = _line_pixels(rsx, rsy, rtx, rty)
    for px, py in r_pixels:
        color_map[(px, py)] = 'green'
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            color_map[(rtx + dx, rty + dy)] = 'green'

    # Torso and legs = white
    for y in range(CANVAS_H):
        for x in range(CANVAS_W):
            ch = canvas[y][x]
            if ch in '|/\\':
                color_map[(x, y)] = 'white'

    # Build colored output
    lines = []
    for y in range(CANVAS_H):
        row = []
        for x in range(CANVAS_W):
            ch = canvas[y][x]
            if ch == ' ':
                row.append(' ')
            else:
                color = color_map.get((x, y), 'white')
                row.append(colorize(ch, color, enabled=True))
        lines.append(''.join(row))

    return lines


def _line_pixels(x0, y0, x1, y1):
    """Return list of (x, y) pixels for a Bresenham line (without drawing)."""
    pixels = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        pixels.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return pixels


def render_diagram(left_pos, right_pos):
    """
    Render a small compass-diagram showing which positions are active.
    Active positions are highlighted with [brackets].
    """
    # Base grid with position numbers
    grid = [
        "      6    7    8      ",
        "       \\  |  /        ",
        "    5-- O --1          ",
        "       /  |  \\        ",
        "      4    3    2      ",
    ]

    # Coordinates of each position number in the grid.
    # These must point at the digit character for each position in the
    # grid strings above. Verified by scanning the grid for digit chars.
    pos_coords = {
        1: (12, 2),   # row 2: "    5-- O --1          "  -> '1' at index 12
        2: (16, 4),   # row 4: "      4    3    2      "  -> '2' at index 16
        3: (11, 4),   # row 4: "      4    3    2      "  -> '3' at index 11
        4: (6, 4),    # row 4: "      4    3    2      "  -> '4' at index 6
        5: (4, 2),    # row 2: "    5-- O --1          "  -> '5' at index 4
        6: (6, 0),    # row 0: "      6    7    8      "  -> '6' at index 6
        7: (11, 0),   # row 0: "      6    7    8      "  -> '7' at index 11
        8: (16, 0),   # row 0: "      6    7    8      "  -> '8' at index 16
    }

    # Build highlighted version. We need to replace single characters
    # with bracketed versions like "[N]", which changes the string length.
    # Track replacements per row and rebuild each row string at the end.
    replacements = {}  # (row_idx, col_idx) -> replacement string
    for pos, (px, py) in pos_coords.items():
        if pos == left_pos or pos == right_pos:
            if py < len(grid) and px < len(grid[py]):
                replacements[(py, px)] = f"[{grid[py][px]}]"

    result = []
    for y, line in enumerate(grid):
        chars = list(line)
        # Apply replacements left-to-right, building a new string.
        # Since replacements expand single chars, we track an offset.
        out = []
        for x, ch in enumerate(chars):
            if (y, x) in replacements:
                out.append(replacements[(y, x)])
            else:
                out.append(ch)
        result.append(''.join(out))

    # Add active positions label
    active = sorted(set([left_pos, right_pos]))
    pos_descs = [f"{p}({POSITION_NAMES.get(p, '?')})" for p in active]
    label_line = f"  Active positions: {', '.join(str(p) for p in active)}  ({', '.join(pos_descs)})"
    return result + [label_line]


# ---------------------------------------------------------------------------
# Display / animation
# ---------------------------------------------------------------------------

def clear_screen():
    """Clear the terminal screen (cross-platform)."""
    os.system('cls' if os.name == 'nt' else 'clear')


# Regex for stripping ANSI escape codes from strings
_ANSI_RE = None


def strip_ansi(text):
    """Remove all ANSI escape sequences from *text*."""
    global _ANSI_RE
    if _ANSI_RE is None:
        import re
        _ANSI_RE = re.compile(r'\033\[[0-9;]*m')
    return _ANSI_RE.sub('', text)


def visible_len(text):
    """Return the visible (non-ANSI) length of *text*."""
    return len(strip_ansi(text))


def display_frame(frame, show_diagram=True, use_color=False):
    """
    Display a single semaphore frame.

    Args:
        frame: A (char, left, right, label) tuple.
        show_diagram: Whether to show the compass diagram.
        use_color: Whether to use ANSI color in the figure.
    """
    char, left, right, label = frame

    if use_color:
        figure = render_figure_colored(left, right)
    else:
        figure = render_figure(left, right)

    # Calculate width based on visible (non-ANSI) characters
    width = max(visible_len(line) for line in figure)
    border = '+' + '-' * (width + 2) + '+'

    lines = [border]
    title = "Semaphore Signaler"
    lines.append(f"|  {title}  {' ' * (width - len(title) - 2)}|")
    lines.append(border)

    for line in figure:
        vlen = visible_len(line)
        pad = ' ' * (width - vlen)
        lines.append(f"| {line}{pad} |")

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


def animate(text, delay=1.2, show_diagram=True, loop=False, use_color=False):
    """
    Animate the semaphore encoding of text.

    Args:
        text: The text to signal.
        delay: Seconds between frames.
        show_diagram: Whether to show the compass diagram.
        loop: If True, repeat the animation until Ctrl+C.
        use_color: If True, use ANSI color in the figure.
    """
    frames = encode_text(text)

    if not frames:
        print("Nothing to signal.")
        return

    # Guard against non-positive delay (time.sleep raises ValueError for
    # negative values)
    effective_delay = max(delay, 0.01)

    try:
        while True:
            for i, frame in enumerate(frames):
                clear_screen()
                display_frame(frame, show_diagram=show_diagram, use_color=use_color)
                print(f"\n  Frame {i + 1}/{len(frames)}  |  Text: \"{text}\"")
                print("  Press Ctrl+C to stop.")
                time.sleep(effective_delay)
            if not loop:
                break
            # Pause before looping
            time.sleep(effective_delay * 2)
    except KeyboardInterrupt:
        print("\n\n  Signaling stopped.")


def export_frames(text, filepath, show_diagram=True, use_color=False):
    """
    Export semaphore frames to a text file (no animation).

    Args:
        text: The text to signal.
        filepath: Output file path.
        show_diagram: Whether to include diagrams.
        use_color: Whether to use ANSI color (codes are stripped from file output).
    """
    frames = encode_text(text)
    if not frames:
        print("Nothing to export.")
        return

    all_lines = []
    all_lines.append(f"# Semaphore Signal Export")
    all_lines.append(f"# Text: {text}")
    all_lines.append(f"# Frames: {len(frames)}")
    all_lines.append(f"# Generated by Terminal Semaphore Flag Signaler v{__version__}")
    all_lines.append("")

    for i, frame in enumerate(frames):
        char, left, right, label = frame
        all_lines.append(f"--- Frame {i + 1}/{len(frames)}: {label} ---")

        if use_color:
            figure = render_figure_colored(left, right)
        else:
            figure = render_figure(left, right)

        for line in figure:
            if use_color:
                # Strip ANSI codes for file export
                all_lines.append(strip_ansi(line))
            else:
                all_lines.append(line)

        all_lines.append(f"  Character: {repr(char)}  |  L={left}  R={right}  |  {label}")

        if show_diagram:
            diag = render_diagram(left, right)
            all_lines.append("")
            all_lines.extend(diag)

        all_lines.append("")

    try:
        with open(filepath, 'w') as f:
            f.write('\n'.join(all_lines))
        print(f"Exported {len(frames)} frames to '{filepath}'")
    except IOError as e:
        print(f"Error writing to '{filepath}': {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_mode(show_diagram=True, delay=1.2, use_color=False):
    """
    Run an interactive REPL for encoding text.

    Supports special commands:
      :demo     - run a demo sequence
      :chart    - show the full semaphore chart
      :file X   - signal contents of file X
      :decode X - decode position pairs (e.g. "1,8 1,7")
      :special  - show special semaphore signals
      :color    - toggle color mode
      :help     - show available commands
      :quit     - exit
    """
    color_enabled = use_color
    print("=" * 50)
    print("  Terminal Semaphore Flag Signaler")
    print(f"  Interactive Mode  (v{__version__})")
    print("=" * 50)
    print()
    print("  Type text to signal, then press Enter.")
    print("  Special commands:")
    print("    :demo    - run a demo sequence")
    print("    :chart   - show the full semaphore chart")
    print("    :file X  - signal contents of file X")
    print("    :decode X - decode position pairs (e.g. \"1,8 1,7\")")
    print("    :special - show special semaphore signals")
    print("    :color   - toggle color mode")
    print("    :help    - show available commands")
    print("    :quit    - exit")
    print()

    while True:
        try:
            prompt = "  > "
            text = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not text:
            continue

        if text == ":quit":
            print("  Goodbye!")
            break
        elif text == ":help":
            _print_interactive_help()
        elif text == ":demo":
            animate("SOS HELLO 42", delay=delay, show_diagram=show_diagram, use_color=color_enabled)
        elif text == ":chart":
            show_full_chart()
        elif text == ":special":
            show_special_signals()
        elif text == ":color":
            color_enabled = not color_enabled
            print(f"  Color mode: {'ON' if color_enabled else 'OFF'}")
        elif text.startswith(":file "):
            filepath = text[6:].strip()
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                animate(content, delay=delay, show_diagram=show_diagram, use_color=color_enabled)
            except FileNotFoundError:
                print(f"  File not found: {filepath}")
            except IOError as e:
                print(f"  Error reading file: {e}")
        elif text.startswith(":decode "):
            pos_str = text[len(":decode "):].strip()  # 8 chars in ":decode "
            decoded = decode_position_string(pos_str)
            print(f"  Decoded: {decoded}")
        else:
            animate(text, delay=delay, show_diagram=show_diagram, use_color=color_enabled)

        print()


def _print_interactive_help():
    """Print help for interactive mode commands."""
    print()
    print("  Available commands:")
    print("    <text>     - signal the given text")
    print("    :demo      - signal a demo sequence (\"SOS HELLO 42\")")
    print("    :chart     - display the full semaphore alphabet chart")
    print("    :file PATH - signal contents of a file")
    print("    :decode X  - decode position pairs, e.g. :decode 1,8 1,7 3,7")
    print("    :special   - show special semaphore signals (attention, error, etc.)")
    print("    :color     - toggle ANSI color output")
    print("    :help      - show this help")
    print("    :quit      - exit the program")
    print()


def show_full_chart():
    """Display the complete semaphore alphabet chart."""
    clear_screen()
    print("=" * 60)
    print("  Complete Semaphore Alphabet Chart")
    print("=" * 60)
    print()
    print("  Letter | Left Pos | Right Pos | Description")
    print("  -------|----------|----------|---------------------------")

    for letter in string.ascii_uppercase:
        left, right = SEMAPHORE[letter]
        l_name = POSITION_NAMES.get(left, '?')
        r_name = POSITION_NAMES.get(right, '?')
        print(f"   {letter}     |    {left}     |    {right}     | {l_name} / {r_name}")

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


def show_special_signals():
    """Display the special semaphore signals reference."""
    clear_screen()
    print("=" * 60)
    print("  Special Semaphore Signals")
    print("=" * 60)
    print()
    print("  Signal       | Positions | Description")
    print("  -------------|-----------|---------------------------")

    descriptions = {
        'REST':      'Both arms down — rest / attention',
        'ATTENTION': 'Both flags up — start of message / attention',
        'ERROR':     'Flags crossed — error / cancel last character',
        'CORRECT':   'Acknowledge / correct / ready to receive',
        'NUMERALS':  'Switch to number mode (same as J position)',
        'LETTERS':   'Return to letter mode (same as P position)',
    }

    for name, (l, r) in SPECIAL_SIGNALS.items():
        desc = descriptions.get(name, '')
        print(f"  {name:12s} |   {l}, {r}    | {desc}")

    print()
    input("  Press Enter to continue...")


# ---------------------------------------------------------------------------
# Main / CLI
# ---------------------------------------------------------------------------

def build_parser():
    """Build and return the argparse argument parser."""
    parser = argparse.ArgumentParser(
        description="Terminal Semaphore Flag Signaler — translate text into animated semaphore flag positions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s "SOS"                    Signal "SOS" with animation
  %(prog)s "HELLO WORLD" --color    Signal with ANSI color
  %(prog)s "SOS" --encode           Show positions without animation
  %(prog)s "SOS" --json             Output JSON-encoded frames
  %(prog)s "SOS" --export out.txt   Save frames to a file
  %(prog)s --decode "4,8 3,7 4,8"  Decode positions back to text
  %(prog)s --chart                  Print the semaphore alphabet chart
  %(prog)s --special                Show special semaphore signals
  %(prog)s                          Enter interactive mode
"""
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
        help='Delay between frames in seconds (default: 1.2, must be > 0)'
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
        '--color',
        action='store_true',
        help='Enable ANSI color output for the stick figure'
    )
    parser.add_argument(
        '--chart',
        action='store_true',
        help='Print the full semaphore chart and exit'
    )
    parser.add_argument(
        '--special',
        action='store_true',
        help='Print the special semaphore signals reference and exit'
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
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output encoded frames as JSON (machine-readable)'
    )
    parser.add_argument(
        '--export',
        type=str,
        metavar='FILEPATH',
        help='Export animation frames to a text file'
    )
    parser.add_argument(
        '--decode',
        type=str,
        metavar='POSITIONS',
        help='Decode semaphore position pairs to text (e.g. "4,8 3,7 4,8")'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    return parser


def main():
    """Main entry point — parse arguments and dispatch to the appropriate mode."""
    parser = build_parser()
    args = parser.parse_args()
    show_diagram = not args.no_diagram

    # --chart mode
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

    # --special mode
    if args.special:
        print("=" * 50)
        print("  Special Semaphore Signals")
        print("=" * 50)
        print()
        descriptions = {
            'REST':      'Both arms down — rest / attention',
            'ATTENTION': 'Both flags up — start of message / attention',
            'ERROR':     'Flags crossed — error / cancel last character',
            'CORRECT':   'Acknowledge / correct / ready to receive',
            'NUMERALS':  'Switch to number mode (same as J position)',
            'LETTERS':   'Return to letter mode (same as P position)',
        }
        print("  Signal       | Positions | Description")
        print("  -------------|-----------|---------------------------")
        for name, (l, r) in SPECIAL_SIGNALS.items():
            desc = descriptions.get(name, '')
            print(f"  {name:12s} |   {l}, {r}    | {desc}")
        return

    # --decode mode
    if args.decode is not None:
        decoded = decode_position_string(args.decode)
        print(f"  Decoded: {decoded}")
        return

    # Determine the text source
    if args.file:
        try:
            with open(args.file, 'r') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
            sys.exit(1)
    elif args.text:
        text = ' '.join(args.text)
    elif args.export is None and not args.json:
        # Interactive mode (only if no other output mode specified)
        interactive_mode(show_diagram=show_diagram, delay=args.delay, use_color=args.color)
        return
    else:
        # --export or --json without text — need text
        print("Error: --export and --json require text input (positional or --file).", file=sys.stderr)
        sys.exit(1)

    # --json mode
    if args.json:
        frames = encode_text(text)
        output = {
            "text": text,
            "frame_count": len(frames),
            "frames": [
                {
                    "char": char,
                    "left_position": left,
                    "right_position": right,
                    "label": label
                }
                for char, left, right, label in frames
            ]
        }
        print(json_module.dumps(output, indent=2))
        return

    # --encode mode (text output)
    if args.encode:
        frames = encode_text(text)
        print(f"Text: {text}")
        print(f"Frames: {len(frames)}")
        print("-" * 40)
        for char, left, right, label in frames:
            print(f"  {repr(char):>6}  ->  L={left}  R={right}   ({label})")
        return

    # --export mode
    if args.export:
        export_frames(text, args.export, show_diagram=show_diagram, use_color=args.color)
        return

    # Default: animate
    if args.delay <= 0:
        print("Error: --delay must be a positive number for animation mode.",
              file=sys.stderr)
        sys.exit(1)
    animate(text, delay=args.delay, show_diagram=show_diagram, loop=args.loop, use_color=args.color)


if __name__ == '__main__':
    main()